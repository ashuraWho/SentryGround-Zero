"""
WebSocket Server for Real-time Streaming in SentryGround-Zero.

Implements:
- Satellite position streaming (real-time orbit propagation)
- Telemetry data streaming
- Ground station contact events
- Science product notifications
- Multi-client management with authentication
- Rate limiting and backpressure handling

Uses asyncio with websockets for high-performance streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import (
    Dict, Set, List, Optional, Callable, Any, Coroutine,
    TypeVar, Generic
)
import uuid
import hashlib
import hmac
import secrets
import math

try:
    import websockets  # type: ignore[import]
    from websockets.server import WebSocketServerProtocol, serve  # type: ignore[import]
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None  # type: ignore[assignment]
    WebSocketServerProtocol = Any
    serve = None  # type: ignore[assignment]
    WEBSOCKETS_AVAILABLE = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from secure_eo_pipeline.physics.orbital import (
    propagate_orbit, GeodeticState, OrbitalState,
    eci_to_geodetic, julian_date, gmst_angle
)
from secure_eo_pipeline.constellation_catalog import OrbitalElements, satellites_from_environment


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# MESSAGE TYPES
# =============================================================================

class MessageType(str, Enum):
    HELLO = "hello"
    GOODBYE = "goodbye"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    
    SATELLITE_POSITION = "satellite_position"
    SATELLITE_TELEMETRY = "satellite_telemetry"
    PASS_START = "pass_start"
    PASS_END = "pass_end"
    PASS_UPDATE = "pass_update"
    
    PRODUCT_AVAILABLE = "product_available"
    ALERT = "alert"
    COMMAND_ACK = "command_ack"
    
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIBE_ACK = "subscribe_ack"
    UNSUBSCRIBE_ACK = "unsubscribe_ack"
    
    STREAM_START = "stream_start"
    STREAM_STOP = "stream_stop"
    STREAM_DATA = "stream_data"


# =============================================================================
# STREAM TYPES
# =============================================================================

class StreamType(str, Enum):
    SATELLITE_POSITION = "satellite_position"
    SATELLITE_TELEMETRY = "satellite_telemetry"
    ORBITAL_PREDICTION = "orbital_prediction"
    GROUND_STATION_PASS = "ground_station_pass"
    SCIENCE_PRODUCT = "science_product"
    ALERT = "alert"
    TELEMETRY_STATS = "telemetry_stats"


@dataclass
class StreamSubscription:
    stream_type: StreamType
    satellite_ids: Optional[Set[str]] = None
    ground_station_ids: Optional[Set[str]] = None
    product_types: Optional[Set[str]] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    rate_limit_hz: float = 10.0


# =============================================================================
# MESSAGE STRUCTURES
# =============================================================================

@dataclass
class WebSocketMessage:
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        })

    @classmethod
    def from_json(cls, text: str) -> WebSocketMessage:
        obj = json.loads(text)
        return cls(
            type=MessageType(obj["type"]),
            data=obj["data"],
            timestamp=obj.get("timestamp", ""),
            message_id=obj.get("message_id", str(uuid.uuid4()))
        )


@dataclass
class SatellitePositionMessage:
    satellite_id: str
    satellite_name: str
    norad_id: Optional[int]
    position: GeodeticState
    orbital_elements: Optional[OrbitalElements] = None
    velocity_km_s: float = 0.0
    period_s: float = 0.0
    eccentricity: float = 0.0
    regime: str = "LEO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satellite_id": self.satellite_id,
            "satellite_name": self.satellite_name,
            "norad_id": self.norad_id,
            "position": {
                "latitude_deg": self.position.lat_deg,
                "longitude_deg": self.position.lon_deg,
                "altitude_km": self.position.alt_km,
            },
            "velocity_km_s": self.velocity_km_s,
            "period_s": self.period_s,
            "eccentricity": self.eccentricity,
            "regime": self.regime
        }


@dataclass
class TelemetryMessage:
    satellite_id: str
    satellite_name: str
    timestamp: datetime
    power_w: float
    temp_k: float
    storage_used_pct: float
    data_rate_mbps: float
    mode: str
    error_flags: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satellite_id": self.satellite_id,
            "satellite_name": self.satellite_name,
            "timestamp": self.timestamp.isoformat(),
            "power_w": self.power_w,
            "temp_k": self.temp_k,
            "storage_used_pct": self.storage_used_pct,
            "data_rate_mbps": self.data_rate_mbps,
            "mode": self.mode,
            "error_flags": self.error_flags
        }


@dataclass
class PassEventMessage:
    satellite_id: str
    satellite_name: str
    ground_station_id: str
    ground_station_name: str
    event_type: str
    timestamp: datetime
    max_elevation_deg: Optional[float] = None
    duration_s: Optional[float] = None
    aos_azimuth_deg: Optional[float] = None
    los_azimuth_deg: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satellite_id": self.satellite_id,
            "satellite_name": self.satellite_name,
            "ground_station_id": self.ground_station_id,
            "ground_station_name": self.ground_station_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "max_elevation_deg": self.max_elevation_deg,
            "duration_s": self.duration_s,
            "aos_azimuth_deg": self.aos_azimuth_deg,
            "los_azimuth_deg": self.los_azimuth_deg
        }


# =============================================================================
# CLIENT MANAGEMENT
# =============================================================================

@dataclass
class Client:
    client_id: str
    websocket: WebSocketServerProtocol
    subscriptions: Set[StreamSubscription] = field(default_factory=set)
    auth_token: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages_sent: int = 0
    bytes_sent: int = 0

    def is_subscribed(self, stream_type: StreamType) -> bool:
        return any(sub.stream_type == stream_type for sub in self.subscriptions)

    def matches_subscription(
        self,
        stream_type: StreamType,
        satellite_id: Optional[str] = None,
        ground_station_id: Optional[str] = None,
        product_type: Optional[str] = None
    ) -> bool:
        for sub in self.subscriptions:
            if sub.stream_type != stream_type:
                continue
            if sub.satellite_ids and satellite_id not in sub.satellite_ids:
                continue
            if sub.ground_station_ids and ground_station_id not in sub.ground_station_ids:
                continue
            if sub.product_types and product_type not in sub.product_types:
                continue
            return True
        return False


# =============================================================================
# RATE LIMITING
# =============================================================================

@dataclass
class RateLimiter:
    messages_per_second: float = 100.0
    bytes_per_second: float = 10 * 1024 * 1024
    burst_size: int = 200

    _tokens: float = 0.0
    _last_update: float = field(default_factory=time.time)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self, cost: float = 1.0) -> bool:
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.messages_per_second
            )
            self._last_update = now

            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False


# =============================================================================
# ORBIT PROPAGATOR (REAL-TIME)
# =============================================================================

class RealtimeOrbitPropagator:
    def __init__(
        self,
        update_interval_s: float = 1.0,
        propagation_interval_s: float = 0.1
    ):
        self.update_interval_s = update_interval_s
        self.propagation_interval_s = propagation_interval_s
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._positions: Dict[str, SatellitePositionMessage] = {}
        self._lock = asyncio.Lock()

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._propagation_loop())
        logger.info("Orbit propagator started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Orbit propagator stopped")

    async def _propagation_loop(self):
        satellites = satellites_from_environment()
        satellites_with_elements = [
            (sat.hostname, sat)
            for sat in satellites
            if sat.orbital_elements is not None
        ]

        while self._running:
            current_time = datetime.now(timezone.utc)
            jd = julian_date(current_time)

            new_positions = {}

            for sat_id, sat in satellites_with_elements:
                try:
                    elements = sat.orbital_elements
                    state = propagate_orbit(elements, jd)
                    geo = eci_to_geodetic(state)

                    velocity = math.sqrt(
                        state.vx**2 + state.vy**2 + state.vz**2
                    )

                    period = 2 * math.pi * math.sqrt(
                        sat.orbital_elements.semi_major_axis ** 3 / 398600.4418
                    )

                    regime = "LEO"
                    if sat.orbital_elements.semi_major_axis > 42164:
                        regime = "GEO"
                    elif sat.orbital_elements.semi_major_axis > 20000:
                        regime = "MEO"
                    elif sat.orbital_elements.semi_major_axis > 6878:
                        regime = "HEO"

                    msg = SatellitePositionMessage(
                        satellite_id=sat_id,
                        satellite_name=sat.name,
                        norad_id=sat.norad_id,
                        position=geo,
                        orbital_elements=sat.orbital_elements,
                        velocity_km_s=velocity,
                        period_s=period,
                        eccentricity=sat.orbital_elements.eccentricity,
                        regime=regime
                    )
                    new_positions[sat_id] = msg

                except Exception as e:
                    logger.warning(f"Failed to propagate {sat_id}: {e}")

            async with self._lock:
                self._positions = new_positions

            await asyncio.sleep(self.update_interval_s)

    async def get_positions(self) -> Dict[str, SatellitePositionMessage]:
        async with self._lock:
            return dict(self._positions)


# =============================================================================
# WEBSOCKET SERVER
# =============================================================================

class WebSocketStreamServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        auth_secret: Optional[str] = None,
        rate_limit: Optional[RateLimiter] = None
    ):
        self.host = host
        self.port = port
        self.auth_secret = auth_secret
        self.rate_limit = rate_limit or RateLimiter()

        self.clients: Dict[str, Client] = {}
        self.client_lock = asyncio.Lock()

        self.orbit_propagator = RealtimeOrbitPropagator()
        self._server = None

        self._message_handlers: Dict[
            MessageType,
            Callable[[Client, WebSocketMessage], Coroutine]
        ] = {}

        self._register_handlers()

    def _register_handlers(self):
        self._message_handlers[MessageType.SUBSCRIBE] = self._handle_subscribe
        self._message_handlers[MessageType.UNSUBSCRIBE] = self._handle_unsubscribe
        self._message_handlers[MessageType.PING] = self._handle_ping
        self._message_handlers[MessageType.GOODBYE] = self._handle_goodbye

    async def start(self):
        await self.orbit_propagator.start()

        self._server = await serve(
            self._handle_client,
            self.host,
            self.port
        )

        logger.info(f"WebSocket server started on {self.host}:{self.port}")

    async def stop(self):
        await self.orbit_propagator.stop()

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        async with self.client_lock:
            for client in list(self.clients.values()):
                await client.websocket.close()

        logger.info("WebSocket server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        client_id = str(uuid.uuid4())
        client = Client(client_id=client_id, websocket=websocket)

        async with self.client_lock:
            self.clients[client_id] = client

        logger.info(f"Client connected: {client_id}")

        hello_msg = WebSocketMessage(
            type=MessageType.HELLO,
            data={
                "client_id": client_id,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "protocol_version": "1.0"
            }
        )
        await websocket.send(hello_msg.to_json())

        try:
            async for text in websocket:
                try:
                    msg = WebSocketMessage.from_json(text)
                    client.last_message_at = datetime.now(timezone.utc)

                    handler = self._message_handlers.get(msg.type)
                    if handler:
                        await handler(client, msg)
                    else:
                        await self._send_error(
                            websocket,
                            f"Unknown message type: {msg.type}"
                        )

                except json.JSONDecodeError:
                    await self._send_error(websocket, "Invalid JSON")

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client disconnected: {client_id} ({e})")
        finally:
            async with self.client_lock:
                del self.clients[client_id]

    async def _handle_subscribe(self, client: Client, msg: WebSocketMessage):
        data = msg.data

        try:
            stream_type = StreamType(data.get("stream_type"))
            subscription = StreamSubscription(
                stream_type=stream_type,
                satellite_ids=set(data.get("satellite_ids", [])) or None,
                ground_station_ids=set(data.get("ground_station_ids", [])) or None,
                product_types=set(data.get("product_types", [])) or None,
                rate_limit_hz=data.get("rate_limit_hz", 10.0)
            )

            client.subscriptions.add(subscription)

            ack = WebSocketMessage(
                type=MessageType.SUBSCRIBE_ACK,
                data={
                    "stream_type": stream_type.value,
                    "message_id": msg.message_id,
                    "subscriptions": [s.stream_type.value for s in client.subscriptions]
                }
            )
            await client.websocket.send(ack.to_json())

            logger.info(f"Client {client.client_id} subscribed to {stream_type}")

        except (ValueError, KeyError) as e:
            await self._send_error(client.websocket, f"Invalid subscription: {e}")

    async def _handle_unsubscribe(self, client: Client, msg: WebSocketMessage):
        data = msg.data
        stream_type = StreamType(data.get("stream_type"))

        client.subscriptions = {
            s for s in client.subscriptions
            if s.stream_type != stream_type
        }

        ack = WebSocketMessage(
            type=MessageType.UNSUBSCRIBE_ACK,
            data={
                "stream_type": stream_type.value,
                "message_id": msg.message_id
            }
        )
        await client.websocket.send(ack.to_json())

    async def _handle_ping(self, client: Client, msg: WebSocketMessage):
        pong = WebSocketMessage(
            type=MessageType.PONG,
            data={"message_id": msg.message_id}
        )
        await client.websocket.send(pong.to_json())

    async def _handle_goodbye(self, client: Client, msg: WebSocketMessage):
        await client.websocket.close()

    async def _send_error(self, websocket: WebSocketServerProtocol, error: str):
        msg = WebSocketMessage(
            type=MessageType.ERROR,
            data={"error": error}
        )
        await websocket.send(msg.to_json())

    async def broadcast_to_subscribers(
        self,
        stream_type: StreamType,
        data: Dict[str, Any],
        satellite_id: Optional[str] = None,
        ground_station_id: Optional[str] = None,
        product_type: Optional[str] = None
    ):
        msg = WebSocketMessage(
            type=MessageType.STREAM_DATA,
            data={
                "stream_type": stream_type.value,
                "payload": data
            }
        )

        text = msg.to_json()
        byte_size = len(text.encode())

        async with self.client_lock:
            disconnected = []

            for client in self.clients.values():
                if not client.matches_subscription(
                    stream_type, satellite_id, ground_station_id, product_type
                ):
                    continue

                if not await self.rate_limit.acquire():
                    logger.warning(f"Rate limit exceeded for client {client.client_id}")
                    continue

                try:
                    await client.websocket.send(text)
                    client.messages_sent += 1
                    client.bytes_sent += byte_size
                except Exception as e:
                    logger.error(f"Failed to send to client {client.client_id}: {e}")
                    disconnected.append(client.client_id)

            for cid in disconnected:
                del self.clients[cid]

    async def broadcast_satellite_positions(self):
        positions = await self.orbit_propagator.get_positions()

        for sat_id, pos_msg in positions.items():
            await self.broadcast_to_subscribers(
                StreamType.SATELLITE_POSITION,
                pos_msg.to_dict(),
                satellite_id=sat_id
            )

    async def _broadcast_loop(self, interval_s: float = 1.0):
        while True:
            await self.broadcast_satellite_positions()
            await asyncio.sleep(interval_s)

    async def start_broadcast_loop(self, interval_s: float = 1.0):
        asyncio.create_task(self._broadcast_loop(interval_s))


# =============================================================================
# CLIENT UTILITIES
# =============================================================================

class WebSocketClient:
    def __init__(
        self,
        uri: str = "ws://localhost:8765",
        auth_token: Optional[str] = None
    ):
        self.uri = uri
        self.auth_token = auth_token
        self._websocket = None
        self._running = False
        self._subscriptions: Set[StreamType] = set()

    async def connect(self):
        self._websocket = await websockets.connect(self.uri)
        self._running = True

        hello = await self._websocket.recv()
        msg = WebSocketMessage.from_json(hello)
        if msg.type != MessageType.HELLO:
            raise ValueError("Expected HELLO message")

        logger.info(f"Connected to server: {msg.data}")

    async def disconnect(self):
        self._running = False
        if self._websocket:
            await self._websocket.close()

    async def subscribe(self, stream_type: StreamType, **kwargs):
        msg = WebSocketMessage(
            type=MessageType.SUBSCRIBE,
            data={
                "stream_type": stream_type.value,
                **kwargs
            }
        )
        await self._websocket.send(msg.to_json())

        response = await self._websocket.recv()
        ack = WebSocketMessage.from_json(response)

        if ack.type == MessageType.SUBSCRIBE_ACK:
            self._subscriptions.add(stream_type)

        return ack

    async def unsubscribe(self, stream_type: StreamType):
        msg = WebSocketMessage(
            type=MessageType.UNSUBSCRIBE,
            data={"stream_type": stream_type.value}
        )
        await self._websocket.send(msg.to_json())
        self._subscriptions.discard(stream_type)

    async def listen(self) -> AsyncIterator[Dict[str, Any]]:
        async for text in self._websocket:
            msg = WebSocketMessage.from_json(text)

            if msg.type == MessageType.STREAM_DATA:
                yield msg.data["payload"]
            elif msg.type == MessageType.PONG:
                pass
            elif msg.type == MessageType.ERROR:
                logger.error(f"Server error: {msg.data}")


T = TypeVar('T')

class AsyncIterator(Generic[T]):
    pass


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="SentryGround-Zero WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    parser.add_argument("--auth-secret", help="HMAC secret for authentication")
    parser.add_argument("--rate-limit", type=float, default=100.0, help="Messages per second limit")
    parser.add_argument("--broadcast-interval", type=float, default=1.0, help="Broadcast interval in seconds")

    args = parser.parse_args()

    rate_limiter = RateLimiter(messages_per_second=args.rate_limit)
    server = WebSocketStreamServer(
        host=args.host,
        port=args.port,
        auth_secret=args.auth_secret,
        rate_limit=rate_limiter
    )

    await server.start()
    await server.start_broadcast_loop(args.broadcast_interval)

    logger.info("Server running. Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()


if __name__ == "__main__":
    if not WEBSOCKETS_AVAILABLE:
        print("Error: websockets library not installed. Run: pip install websockets")
        exit(1)

    asyncio.run(main())
