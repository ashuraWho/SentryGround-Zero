"""
Real-time WebSocket Server for SentryGround-Zero
Provides live telemetry streaming and command interface.
"""

import os
import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import secrets

import numpy as np

try:
    import websockets
    from websockets.server import WebSocketServerProtocol, serve
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets not installed. Real-time features disabled.")


@dataclass
class TelemetryData:
    satellite_id: str
    timestamp: str
    latitude: float
    longitude: float
    altitude: float
    velocity: float
    temperature: float
    battery_level: float
    signal_strength: float
    data_rate: float
    orbit_phase: float
    mode: str
    status: str


@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    network_in: float
    network_out: float
    disk_usage: float
    active_connections: int
    timestamp: str


@dataclass
class SecurityAlert:
    alert_id: str
    severity: str
    type: str
    source: str
    description: str
    timestamp: str
    acknowledged: bool = False


class WebSocketMessage:
    """WebSocket message types"""
    TELEMETRY = "telemetry"
    METRICS = "metrics"
    SECURITY = "security"
    COMMAND = "command"
    ORBIT = "orbit"
    WEATHER = "weather"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    AUTH = "auth"


class ConnectionManager:
    """Manages WebSocket connections and subscriptions."""
    
    def __init__(self):
        self._connections: Dict[str, WebSocketServerProtocol] = {}
        self._subscriptions: Dict[str, Set[str]] = {
            WebSocketMessage.TELEMETRY: set(),
            WebSocketMessage.METRICS: set(),
            WebSocketMessage.SECURITY: set(),
            WebSocketMessage.ORBIT: set(),
            WebSocketMessage.WEATHER: set(),
        }
        self._lock = threading.Lock()
        self._session_tokens: Dict[str, dict] = {}
    
    def add_connection(self, conn_id: str, websocket: WebSocketServerProtocol):
        with self._lock:
            self._connections[conn_id] = websocket
    
    def remove_connection(self, conn_id: str):
        with self._lock:
            if conn_id in self._connections:
                del self._connections[conn_id]
            for subs in self._subscriptions.values():
                subs.discard(conn_id)
            if conn_id in self._session_tokens:
                del self._session_tokens[conn_id]
    
    def subscribe(self, conn_id: str, channel: str):
        with self._lock:
            if channel in self._subscriptions:
                self._subscriptions[channel].add(conn_id)
    
    def unsubscribe(self, conn_id: str, channel: str):
        with self._lock:
            if channel in self._subscriptions:
                self._subscriptions[channel].discard(conn_id)
    
    def broadcast(self, channel: str, message: dict):
        with self._lock:
            subscribers = self._subscriptions.get(channel, set()).copy()
            disconnected = []
            
            for conn_id in subscribers:
                websocket = self._connections.get(conn_id)
                if websocket:
                    try:
                        asyncio.run(websocket.send(json.dumps(message)))
                    except Exception:
                        disconnected.append(conn_id)
                else:
                    disconnected.append(conn_id)
            
            for conn_id in disconnected:
                self.remove_connection(conn_id)
    
    def send_to(self, conn_id: str, message: dict):
        with self._lock:
            websocket = self._connections.get(conn_id)
            if websocket:
                try:
                    asyncio.run(websocket.send(json.dumps(message)))
                except Exception:
                    self.remove_connection(conn_id)
    
    def create_session(self, conn_id: str, username: str, role: str) -> str:
        token = secrets.token_urlsafe(32)
        self._session_tokens[conn_id] = {
            "username": username,
            "role": role,
            "token": token,
            "created": datetime.utcnow().isoformat(),
        }
        return token
    
    def verify_session(self, conn_id: str, token: str) -> Optional[dict]:
        session = self._session_tokens.get(conn_id)
        if session and session.get("token") == token:
            return session
        return None
    
    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)


class TelemetryGenerator:
    """Generates realistic telemetry data for demo purposes."""
    
    def __init__(self):
        self.satellites = [
            {"id": "SENTRY-01", "regime": "LEO", "inclination": 97.4},
            {"id": "SENTRY-02", "regime": "LEO", "inclination": 53.0},
            {"id": "SENTRY-03", "regime": "MEO", "inclination": 63.4},
            {"id": "SENTRY-04", "regime": "GEO", "inclination": 0.0},
            {"id": "SENTRY-05", "regime": "HEO", "inclination": 63.4},
        ]
        self._states = {s["id"]: self._init_state(s) for s in self.satellites}
        self._orbit_params = {s["id"]: self._init_orbit(s) for s in self.satellites}
    
    def _init_state(self, sat: dict) -> dict:
        return {
            "phase": np.random.uniform(0, 2 * np.pi),
            "lat": np.random.uniform(-60, 60),
            "lon": np.random.uniform(-180, 180),
            "temp": 20 + np.random.uniform(0, 30),
            "battery": 80 + np.random.uniform(0, 20),
            "signal": 90 + np.random.uniform(-10, 10),
        }
    
    def _init_orbit(self, sat: dict) -> dict:
        base_alt = {
            "LEO": 550,
            "MEO": 20180,
            "GEO": 35786,
            "HEO": 12000,
        }.get(sat["regime"], 550)
        
        base_vel = {
            "LEO": 7.6,
            "MEO": 3.9,
            "GEO": 3.1,
            "HEO": 5.2,
        }.get(sat["regime"], 7.6)
        
        return {
            "altitude": base_alt + np.random.uniform(-10, 10),
            "velocity": base_vel + np.random.uniform(-0.1, 0.1),
            "period": 2 * np.pi * np.sqrt((base_alt + 6371) ** 3 / 398600),
        }
    
    def generate_telemetry(self, satellite_id: str) -> TelemetryData:
        if satellite_id not in self._states:
            satellite_id = list(self._states.keys())[0]
        
        state = self._states[satellite_id]
        orbit = self._orbit_params[satellite_id]
        
        state["phase"] += 0.01
        state["lat"] = 60 * np.sin(state["phase"])
        state["lon"] = (state["lon"] + 2) % 360
        state["temp"] += np.random.uniform(-0.5, 0.5)
        state["temp"] = np.clip(state["temp"], -40, 60)
        state["battery"] += np.random.uniform(-0.1, 0.1)
        state["battery"] = np.clip(state["battery"], 0, 100)
        state["signal"] += np.random.uniform(-1, 1)
        state["signal"] = np.clip(state["signal"], 0, 100)
        
        return TelemetryData(
            satellite_id=satellite_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            latitude=round(state["lat"], 4),
            longitude=round(state["lon"], 4),
            altitude=round(orbit["altitude"], 2),
            velocity=round(orbit["velocity"], 3),
            temperature=round(state["temp"], 2),
            battery_level=round(state["battery"], 1),
            signal_strength=round(state["signal"], 1),
            data_rate=round(10 + np.random.uniform(0, 5), 2),
            orbit_phase=round(state["phase"] % (2 * np.pi), 4),
            mode="NOMINAL",
            status="ACTIVE",
        )
    
    def generate_metrics(self) -> SystemMetrics:
        import psutil
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            net = psutil.net_io_counters()
            disk = psutil.disk_usage('/').percent
        except:
            cpu = np.random.uniform(20, 60)
            mem = np.random.uniform(30, 70)
            net = type('obj', (object,), {'bytes_recv': 0, 'bytes_sent': 0})()
            disk = np.random.uniform(40, 60)
        
        return SystemMetrics(
            cpu_percent=round(cpu, 1),
            memory_percent=round(mem, 1),
            network_in=round(net.bytes_recv / 1e6, 2),
            network_out=round(net.bytes_sent / 1e6, 2),
            disk_usage=round(disk, 1),
            active_connections=0,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )


class WebSocketServer:
    """
    WebSocket server for real-time mission control.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.connections = ConnectionManager()
        self.telemetry = TelemetryGenerator()
        self._running = False
        self._broadcast_thread: Optional[threading.Thread] = None
        self._handlers: Dict[str, Callable] = {}
        self._security_alerts: List[SecurityAlert] = []
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self._handlers[message_type] = handler
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket connection."""
        conn_id = secrets.token_urlsafe(16)
        self.connections.add_connection(conn_id, websocket)
        
        print(f"[WS] New connection: {conn_id} from {websocket.remote_address}")
        
        try:
            await websocket.send(json.dumps({
                "type": WebSocketMessage.AUTH,
                "status": "connected",
                "session_id": conn_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(conn_id, websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": WebSocketMessage.ERROR,
                        "error": "Invalid JSON",
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connections.remove_connection(conn_id)
            print(f"[WS] Connection closed: {conn_id}")
    
    async def _handle_message(self, conn_id: str, websocket: WebSocketServerProtocol, data: dict):
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")
        
        if msg_type == "subscribe":
            channel = data.get("channel")
            self.connections.subscribe(conn_id, channel)
            await websocket.send(json.dumps({
                "type": "subscribed",
                "channel": channel,
            }))
        
        elif msg_type == "unsubscribe":
            channel = data.get("channel")
            self.connections.unsubscribe(conn_id, channel)
            await websocket.send(json.dumps({
                "type": "unsubscribed",
                "channel": channel,
            }))
        
        elif msg_type == WebSocketMessage.TELEMETRY:
            satellite_id = data.get("satellite_id", "SENTRY-01")
            telemetry = self.telemetry.generate_telemetry(satellite_id)
            await websocket.send(json.dumps({
                "type": WebSocketMessage.TELEMETRY,
                "data": asdict(telemetry),
            }))
        
        elif msg_type == WebSocketMessage.COMMAND:
            handler = self._handlers.get(WebSocketMessage.COMMAND)
            if handler:
                result = await handler(data) if asyncio.iscoroutinefunction(handler) else handler(data)
                await websocket.send(json.dumps({
                    "type": "command_result",
                    "result": result,
                }))
        
        elif msg_type == "get_satellites":
            satellites = [
                {"id": s["id"], "regime": s["regime"]}
                for s in self.telemetry.satellites
            ]
            await websocket.send(json.dumps({
                "type": "satellites",
                "data": satellites,
            }))
        
        else:
            handler = self._handlers.get(msg_type)
            if handler:
                result = handler(data)
                await websocket.send(json.dumps(result))
    
    def _broadcast_loop(self):
        """Background thread for broadcasting data."""
        while self._running:
            for sat in self.telemetry.satellites:
                telemetry = self.telemetry.generate_telemetry(sat["id"])
                self.connections.broadcast(WebSocketMessage.TELEMETRY, {
                    "type": WebSocketMessage.TELEMETRY,
                    "data": asdict(telemetry),
                })
            
            metrics = self.telemetry.generate_metrics()
            metrics.active_connections = self.connections.connection_count
            self.connections.broadcast(WebSocketMessage.METRICS, {
                "type": WebSocketMessage.METRICS,
                "data": asdict(metrics),
            })
            
            time.sleep(1)
    
    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            print("WebSocket support not available.")
            return
        
        self._running = True
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._broadcast_thread.start()
        
        print(f"[WS] Starting WebSocket server on {self.host}:{self.port}")
        
        async with serve(self.handle_connection, self.host, self.port):
            await asyncio.Future()
    
    def stop(self):
        """Stop the WebSocket server."""
        self._running = False


def create_demo_server() -> WebSocketServer:
    """Create a configured demo WebSocket server."""
    server = WebSocketServer()
    
    async def handle_command(data: dict):
        cmd = data.get("command")
        print(f"[WS] Command received: {cmd}")
        return {"status": "executed", "command": cmd}
    
    server.register_handler(WebSocketMessage.COMMAND, handle_command)
    return server


if __name__ == "__main__":
    server = create_demo_server()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        server.stop()
