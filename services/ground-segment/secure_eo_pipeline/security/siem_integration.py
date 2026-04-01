"""
SIEM Integration Module for SentryGround-Zero
Provides integration with Security Information and Event Management systems.
Supports: Elastic Security, Splunk, Microsoft Sentinel, and generic syslog.
"""

import os
import json
import time
import logging
import threading
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import hashlib
import uuid


class ThreatLevel(Enum):
    UNKNOWN = 0
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5
    EMERGENCY = 6


class EventType(Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    FILE_OPERATION = "file_operation"
    NETWORK_CONNECTION = "network_connection"
    NETWORK_TRAFFIC = "network_traffic"
    PROCESS_START = "process_start"
    PROCESS_END = "process_end"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_ALERT = "security_alert"
    SYSTEM_ERROR = "system_error"
    PHYSICAL_ACCESS = "physical_access"


@dataclass
class SecurityEvent:
    id: str
    timestamp: datetime
    event_type: EventType
    threat_level: ThreatLevel
    source_ip: str
    source_port: int
    dest_ip: str
    dest_port: int
    user: Optional[str]
    action: str
    resource: str
    outcome: str
    details: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    raw: Optional[str] = None
    processed: bool = False
    enrichment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatIntel:
    indicator: str
    indicator_type: str
    threat_type: str
    confidence: float
    severity: ThreatLevel
    source: str
    first_seen: datetime
    last_seen: datetime
    tags: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Alert:
    id: str
    title: str
    description: str
    severity: ThreatLevel
    status: str
    source: str
    events: List[str]
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    notes: List[Dict] = field(default_factory=list)


@dataclass
class Incident:
    id: str
    title: str
    description: str
    severity: ThreatLevel
    status: str
    alerts: List[str]
    owner: Optional[str] = None
    timeline: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


class ThreatIntelligenceFeed:
    """Threat intelligence feed management."""
    
    def __init__(self):
        self.feeds: Dict[str, List[ThreatIntel]] = {}
        self._indicators: Dict[str, ThreatIntel] = {}
    
    def add_feed(self, name: str, intel_list: List[ThreatIntel]):
        """Add a threat intelligence feed."""
        self.feeds[name] = intel_list
        for intel in intel_list:
            self._indicators[intel.indicator] = intel
    
    def lookup(self, indicator: str) -> Optional[ThreatIntel]:
        """Look up an indicator."""
        return self._indicators.get(indicator)
    
    def check_ip(self, ip: str) -> Optional[ThreatIntel]:
        """Check if IP is in threat intel."""
        return self._indicators.get(ip)
    
    def check_hash(self, hash_value: str) -> Optional[ThreatIntel]:
        """Check if hash is in threat intel."""
        return self._indicators.get(hash_value)
    
    def check_domain(self, domain: str) -> Optional[ThreatIntel]:
        """Check if domain is in threat intel."""
        return self._indicators.get(domain.lower())


class EnrichmentEngine:
    """Enrich security events with additional context."""
    
    def __init__(self, threat_intel: ThreatIntelligenceFeed):
        self.threat_intel = threat_intel
        self._geo_cache: Dict[str, Dict] = {}
        self._asn_cache: Dict[str, Dict] = {}
    
    def enrich(self, event: SecurityEvent) -> SecurityEvent:
        """Enrich a security event."""
        event.enrichment = {}
        
        if event.source_ip:
            event.enrichment['geo'] = self._get_geo(event.source_ip)
            event.enrichment['threat_intel'] = self._check_threat_intel(event.source_ip)
        
        if event.user:
            event.enrichment['user_info'] = self._get_user_info(event.user)
        
        if event.action:
            event.enrichment['action_category'] = self._categorize_action(event.action)
        
        event.enrichment['risk_score'] = self._calculate_risk_score(event)
        
        return event
    
    def _get_geo(self, ip: str) -> Dict:
        """Get geographic information for IP."""
        if ip in self._geo_cache:
            return self._geo_cache[ip]
        
        geo = {
            'country': 'Unknown',
            'country_code': 'XX',
            'city': 'Unknown',
            'latitude': 0.0,
            'longitude': 0.0,
            'asn': None,
            'org': None,
        }
        
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            geo['country'] = 'Private Network'
            geo['country_code'] = 'PRV'
        elif ip == '127.0.0.1' or ip == '::1':
            geo['country'] = 'Localhost'
            geo['country_code'] = 'LOC'
        else:
            geo['country'] = 'United States'
            geo['country_code'] = 'US'
            geo['latitude'] = 37.751
            geo['longitude'] = -97.822
        
        self._geo_cache[ip] = geo
        return geo
    
    def _check_threat_intel(self, indicator: str) -> Optional[Dict]:
        """Check threat intelligence."""
        intel = self.threat_intel.lookup(indicator)
        if intel:
            return {
                'matched': True,
                'threat_type': intel.threat_type,
                'severity': intel.severity.name,
                'confidence': intel.confidence,
                'source': intel.source,
            }
        return {'matched': False}
    
    def _get_user_info(self, username: str) -> Dict:
        """Get user information."""
        return {
            'username': username,
            'account_type': 'human' if not username.startswith('svc_') else 'service',
            'risk_level': 'high' if username in ['admin', 'root'] else 'normal',
        }
    
    def _categorize_action(self, action: str) -> str:
        """Categorize an action."""
        action_lower = action.lower()
        
        if any(x in action_lower for x in ['login', 'auth', 'sign']):
            return 'authentication'
        elif any(x in action_lower for x in ['read', 'view', 'get', 'list']):
            return 'data_access'
        elif any(x in action_lower for x in ['write', 'create', 'update', 'delete', 'modify']):
            return 'data_modification'
        elif any(x in action_lower for x in ['file', 'upload', 'download']):
            return 'file_operation'
        elif any(x in action_lower for x in ['network', 'connect', 'send', 'receive']):
            return 'network_activity'
        else:
            return 'other'
    
    def _calculate_risk_score(self, event: SecurityEvent) -> float:
        """Calculate risk score for event."""
        score = 0.0
        
        score += event.threat_level.value * 20
        
        if event.enrichment.get('threat_intel', {}).get('matched'):
            score += 30
        
        geo = event.enrichment.get('geo', {})
        if geo.get('country_code') in ['CN', 'RU', 'KP', 'IR']:
            score += 10
        
        if event.outcome == 'failure':
            score += 15
        
        if event.action in ['brute_force', 'sql_injection', 'xss', 'csrf']:
            score += 40
        
        return min(100, max(0, score))


class SIEMConnector:
    """
    Base SIEM connector class.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f'siem.{name}')
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to SIEM."""
        raise NotImplementedError
    
    def disconnect(self):
        """Disconnect from SIEM."""
        raise NotImplementedError
    
    def send_event(self, event: SecurityEvent) -> bool:
        """Send event to SIEM."""
        raise NotImplementedError
    
    def send_batch(self, events: List[SecurityEvent]) -> bool:
        """Send batch of events."""
        raise NotImplementedError
    
    def query(self, query: str, time_range: str = "24h") -> List[Dict]:
        """Query events from SIEM."""
        raise NotImplementedError


class ElasticSecurityConnector(SIEMConnector):
    """Elastic Security SIEM connector."""
    
    def __init__(self, hosts: List[str], index: str = "sentryground-*"):
        super().__init__("elastic")
        self.hosts = hosts
        self.index = index
        self._client = None
    
    def connect(self) -> bool:
        try:
            from elasticsearch import Elasticsearch
            self._client = Elasticsearch(self.hosts)
            self._connected = True
            self.logger.info(f"Connected to ElasticSearch: {self.hosts}")
            return True
        except ImportError:
            self.logger.error("elasticsearch package not installed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def send_event(self, event: SecurityEvent) -> bool:
        if not self._connected:
            return False
        
        try:
            doc = {
                '@timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type.value,
                'threat_level': event.threat_level.name,
                'source': {
                    'ip': event.source_ip,
                    'port': event.source_port,
                },
                'destination': {
                    'ip': event.dest_ip,
                    'port': event.dest_port,
                },
                'user': event.user,
                'action': event.action,
                'resource': event.resource,
                'outcome': event.outcome,
                'details': event.details,
                'tags': event.tags,
                'enrichment': event.enrichment,
            }
            
            self._client.index(index=self.index, body=doc)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send event: {e}")
            return False
    
    def query(self, query: str, time_range: str = "24h") -> List[Dict]:
        if not self._connected:
            return []
        
        try:
            body = {
                "query": {
                    "query_string": {"query": query}
                },
                "sort": [{"@timestamp": "desc"}],
            }
            
            result = self._client.search(index=self.index, body=body)
            return [hit['_source'] for hit in result['hits']['hits']]
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return []


class SplunkConnector(SIEMConnector):
    """Splunk SIEM connector."""
    
    def __init__(self, host: str, port: int, token: str, index: str = "sentryground"):
        super().__init__("splunk")
        self.host = host
        self.port = port
        self.token = token
        self.index = index
        self._session = None
    
    def connect(self) -> bool:
        try:
            from splunklib import client
            self._session = client.connect(
                host=self.host,
                port=self.port,
                token=self.token
            )
            self._connected = True
            self.logger.info(f"Connected to Splunk: {self.host}:{self.port}")
            return True
        except ImportError:
            self.logger.error("splunk-sdk package not installed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def send_event(self, event: SecurityEvent) -> bool:
        if not self._connected:
            return False
        
        try:
            body = json.dumps({
                'time': event.timestamp.timestamp(),
                'host': socket.gethostname(),
                'source': f"sentryground/{event.event_type.value}",
                'sourcetype': 'sentryground:security',
                'index': self.index,
                'event': asdict(event),
            })
            
            self._session.post(
                f'/services/collector',
                headers={'Authorization': f'Splunk {self.token}'},
                data=body
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to send event: {e}")
            return False
    
    def query(self, query: str, time_range: str = "24h") -> List[Dict]:
        if not self._connected:
            return []
        
        try:
            kwargs = {
                'search': f'search index={self.index} {query}',
                'earliest_time': f'-{time_range}',
                'latest_time': 'now',
            }
            
            job = self._session.jobs.create(**kwargs)
            results = job.results()
            return list(results)
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return []


class SyslogConnector(SIEMConnector):
    """Syslog connector for generic SIEM integration."""
    
    def __init__(self, host: str = "localhost", port: int = 514, protocol: str = "udp"):
        super().__init__("syslog")
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self._socket = None
        self._formatter = None
    
    def connect(self) -> bool:
        try:
            if self.protocol == "tcp":
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            if self.protocol == "tcp":
                self._socket.connect((self.host, self.port))
            
            self._connected = True
            self.logger.info(f"Connected to syslog: {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    def send_event(self, event: SecurityEvent) -> bool:
        if not self._connected:
            return False
        
        try:
            syslog_msg = self._format_syslog(event)
            
            if self.protocol == "tcp":
                self._socket.sendall(syslog_msg.encode('utf-8') + b'\n')
            else:
                self._socket.sendto(syslog_msg.encode('utf-8'), (self.host, self.port))
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to send event: {e}")
            return False
    
    def _format_syslog(self, event: SecurityEvent) -> str:
        """Format event as syslog message."""
        priority = self._calculate_priority(event)
        
        timestamp = event.timestamp.strftime('%b %d %H:%M:%S')
        hostname = socket.gethostname()
        
        message = (
            f'<{priority}>'
            f'{timestamp} '
            f'{hostname} '
            f'sentryground[{os.getpid()}]: '
            f'{event.event_type.value} '
            f'src={event.source_ip} '
            f'user={event.user or "-"} '
            f'action={event.action} '
            f'result={event.outcome}'
        )
        
        return message
    
    def _calculate_priority(self, event: SecurityEvent) -> int:
        """Calculate syslog priority."""
        facility = 16
        severity_map = {
            ThreatLevel.EMERGENCY: 0,
            ThreatLevel.CRITICAL: 1,
            ThreatLevel.HIGH: 2,
            ThreatLevel.MEDIUM: 3,
            ThreatLevel.LOW: 4,
            ThreatLevel.INFO: 5,
            ThreatLevel.UNKNOWN: 6,
        }
        severity = severity_map.get(event.threat_level, 6)
        return facility * 8 + severity


class SIEMManager:
    """
    Central SIEM management for SentryGround-Zero.
    Coordinates multiple SIEM connectors and event processing.
    """
    
    def __init__(self):
        self.connectors: Dict[str, SIEMConnector] = {}
        self.threat_intel = ThreatIntelligenceFeed()
        self.enrichment_engine: Optional[EnrichmentEngine] = None
        self.alerts: Dict[str, Alert] = {}
        self.incidents: Dict[str, Incident] = {}
        self.event_queue: List[SecurityEvent] = []
        self._processing = False
        self._lock = threading.Lock()
        
        self._setup_default_connectors()
        self._load_threat_intel()
    
    def _setup_default_connectors(self):
        """Setup default SIEM connectors."""
        if os.getenv('ELASTIC_HOSTS'):
            hosts = os.getenv('ELASTIC_HOSTS').split(',')
            connector = ElasticSecurityConnector(hosts)
            self.connectors['elastic'] = connector
        
        if os.getenv('SPLUNK_HOST'):
            connector = SplunkConnector(
                host=os.getenv('SPLUNK_HOST'),
                port=int(os.getenv('SPLUNK_PORT', 8089)),
                token=os.getenv('SPLUNK_TOKEN', ''),
            )
            self.connectors['splunk'] = connector
        
        if os.getenv('SYSLOG_HOST'):
            connector = SyslogConnector(
                host=os.getenv('SYSLOG_HOST'),
                port=int(os.getenv('SYSLOG_PORT', 514)),
                protocol=os.getenv('SYSLOG_PROTO', 'udp'),
            )
            self.connectors['syslog'] = connector
        
        self.enrichment_engine = EnrichmentEngine(self.threat_intel)
    
    def _load_threat_intel(self):
        """Load threat intelligence feeds."""
        demo_intel = [
            ThreatIntel(
                indicator="192.168.1.100",
                indicator_type="ip",
                threat_type="malware",
                confidence=0.8,
                severity=ThreatLevel.HIGH,
                source="demo",
                first_seen=datetime.now() - timedelta(days=30),
                last_seen=datetime.now() - timedelta(hours=1),
                tags=["malware", "c2"],
                description="Known C2 server"
            ),
            ThreatIntel(
                indicator="evil-domain.com",
                indicator_type="domain",
                threat_type="phishing",
                confidence=0.9,
                severity=ThreatLevel.CRITICAL,
                source="demo",
                first_seen=datetime.now() - timedelta(days=7),
                last_seen=datetime.now(),
                tags=["phishing", "credential_theft"],
                description="Known phishing domain"
            ),
        ]
        
        self.threat_intel.add_feed("demo", demo_intel)
    
    def connect_all(self):
        """Connect to all configured SIEM systems."""
        for name, connector in self.connectors.items():
            try:
                if connector.connect():
                    self.logger.info(f"Connected to {name}")
                else:
                    self.logger.warning(f"Failed to connect to {name}")
            except Exception as e:
                self.logger.error(f"Error connecting to {name}: {e}")
    
    def disconnect_all(self):
        """Disconnect from all SIEM systems."""
        for connector in self.connectors.values():
            try:
                connector.disconnect()
            except:
                pass
    
    def log_event(
        self,
        event_type: EventType,
        threat_level: ThreatLevel,
        source_ip: str,
        action: str,
        resource: str,
        outcome: str,
        dest_ip: str = "",
        dest_port: int = 0,
        user: Optional[str] = None,
        details: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Log a security event."""
        event = SecurityEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            threat_level=threat_level,
            source_ip=source_ip,
            source_port=0,
            dest_ip=dest_ip,
            dest_port=dest_port,
            user=user,
            action=action,
            resource=resource,
            outcome=outcome,
            details=details or {},
            tags=tags or [],
        )
        
        with self._lock:
            self.event_queue.append(event)
        
        if threat_level.value >= ThreatLevel.HIGH.value:
            self._create_alert(event)
        
        return event.id
    
    def process_events(self):
        """Process queued events."""
        with self._lock:
            events = self.event_queue[:]
            self.event_queue.clear()
        
        for event in events:
            try:
                if self.enrichment_engine:
                    event = self.enrichment_engine.enrich(event)
                
                for connector in self.connectors.values():
                    try:
                        connector.send_event(event)
                    except:
                        pass
                
                self._check_correlation(event)
                
            except Exception as e:
                self.logger.error(f"Error processing event {event.id}: {e}")
    
    def _create_alert(self, event: SecurityEvent):
        """Create alert from high-priority event."""
        alert = Alert(
            id=str(uuid.uuid4()),
            title=f"{event.event_type.value.upper()}: {event.action}",
            description=f"High-priority security event detected",
            severity=event.threat_level,
            status="open",
            source="sentryground",
            events=[event.id],
            assigned_to=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            closed_at=None,
            notes=[],
        )
        
        self.alerts[alert.id] = alert
    
    def _check_correlation(self, event: SecurityEvent):
        """Check event for correlation rules."""
        pass
    
    def create_incident(
        self,
        title: str,
        description: str,
        severity: ThreatLevel,
        alert_ids: List[str],
        owner: Optional[str] = None
    ) -> str:
        """Create incident from alerts."""
        incident = Incident(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            severity=severity,
            status="open",
            alerts=alert_ids,
            owner=owner,
            timeline=[{
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'created',
                'actor': owner or 'system',
            }],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            resolved_at=None,
        )
        
        self.incidents[incident.id] = incident
        
        for alert_id in alert_ids:
            if alert_id in self.alerts:
                self.alerts[alert_id].status = "in_progress"
        
        return incident.id
    
    def get_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[ThreatLevel] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        return alerts[:limit]
    
    def get_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[ThreatLevel] = None,
        limit: int = 100
    ) -> List[Incident]:
        """Get incidents with optional filtering."""
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        
        incidents.sort(key=lambda x: x.created_at, reverse=True)
        return incidents[:limit]
    
    def start_processing(self, interval: float = 1.0):
        """Start background event processing."""
        if self._processing:
            return
        
        self._processing = True
        
        def process_loop():
            while self._processing:
                self.process_events()
                time.sleep(interval)
        
        thread = threading.Thread(target=process_loop, daemon=True)
        thread.start()
    
    def stop_processing(self):
        """Stop background event processing."""
        self._processing = False
    
    def get_statistics(self) -> Dict:
        """Get SIEM statistics."""
        return {
            'connectors': list(self.connectors.keys()),
            'connected': sum(1 for c in self.connectors.values() if c._connected),
            'queue_size': len(self.event_queue),
            'total_alerts': len(self.alerts),
            'open_alerts': sum(1 for a in self.alerts.values() if a.status == 'open'),
            'total_incidents': len(self.incidents),
            'open_incidents': sum(1 for i in self.incidents.values() if i.status == 'open'),
        }


_siem_manager: Optional[SIEMManager] = None


def get_siem_manager() -> SIEMManager:
    """Get or create SIEM manager singleton."""
    global _siem_manager
    if _siem_manager is None:
        _siem_manager = SIEMManager()
    return _siem_manager
