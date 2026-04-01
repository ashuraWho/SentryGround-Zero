"""
Blue Team Defense Mechanisms

Comprehensive defensive security framework:
- Intrusion Detection System (IDS)
- Intrusion Prevention System (IPS)
- Honeypot deployment
- Threat hunting
- Malware detection
- Network forensics
- Security Orchestration, Automation and Response (SOAR)
"""

import os
import re
import hashlib
import time
import json
import logging
import socket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import random


class DefenseType(Enum):
    IDS = "ids"
    IPS = "ips"
    HONEYPOT = "honeypot"
    THREAT_HUNTING = "threat_hunting"
    MALWARE_DETECTION = "malware_detection"
    FORENSICS = "forensics"
    SOAR = "soar"
    WAF = "waf"
    FIREWALL = "firewall"


class ThreatCategory(Enum):
    MALICIOUS_SOFTWARE = "malicious_software"
    DENIAL_OF_SERVICE = "denial_of_service"
    WEB_ATTACK = "web_attack"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    BRUTE_FORCE = "brute_force"
    INTRUSION = "intrusion"
    POLICY_VIOLATION = "policy_violation"


class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SecurityAlert:
    """Represents a security alert from defense systems."""
    id: str
    timestamp: datetime
    category: ThreatCategory
    severity: Severity
    source_ip: str
    destination_ip: str
    description: str
    indicators: List[str] = field(default_factory=list)
    mitigated: bool = False
    false_positive: bool = False
    raw_log: str = ""
    playbook_id: Optional[str] = None


@dataclass
class IntrusionDetectionEvent:
    """IDS event data."""
    id: str
    timestamp: datetime
    source_ip: str
    source_port: int
    dest_ip: str
    dest_port: int
    protocol: str
    alert_signature: str
    category: ThreatCategory
    severity: Severity
    payload_snippet: str = ""
    action: str = "alert"


@dataclass
class ThreatHunt:
    """Threat hunting investigation."""
    id: str
    name: str
    hypothesis: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime]
    findings: List[Dict[str, Any]]
    iocs_found: List[Dict[str, Any]]
    severity: Severity


@dataclass
class HoneyPotEvent:
    """Honeypot interaction event."""
    id: str
    timestamp: datetime
    honeypot_type: str
    source_ip: str
    source_port: int
    action: str
    commands_executed: List[str] = field(default_factory=list)
    files_accessed: List[str] = field(default_factory=list)
    credentials_provided: List[str] = field(default_factory=list)


class SignatureDatabase:
    """Intrusion detection signature database."""
    
    def __init__(self):
        self.signatures: Dict[str, Dict] = {}
        self._load_signatures()
    
    def _load_signatures(self):
        """Load detection signatures."""
        self.signatures = {
            "SQL_INJECTION_001": {
                "pattern": r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b.*\b(FROM|INTO|TABLE|WHERE)\b)",
                "category": ThreatCategory.WEB_ATTACK,
                "severity": Severity.HIGH,
                "description": "SQL injection attempt detected"
            },
            "XSS_001": {
                "pattern": r"(<script[^>]*>|javascript:|on\w+\s*=)",
                "category": ThreatCategory.WEB_ATTACK,
                "severity": Severity.HIGH,
                "description": "Cross-site scripting attempt detected"
            },
            "BRUTE_FORCE_SSH": {
                "pattern": r"(Failed password|Invalid user)",
                "category": ThreatCategory.BRUTE_FORCE,
                "severity": Severity.MEDIUM,
                "description": "SSH brute force attempt"
            },
            "PATH_TRAVERSAL": {
                "pattern": r"(\.\./|\.\.\\|%2e%2e)",
                "category": ThreatCategory.WEB_ATTACK,
                "severity": Severity.HIGH,
                "description": "Path traversal attempt"
            },
            "CMD_INJECTION": {
                "pattern": r"(;|\||\`|\$\()",
                "category": ThreatCategory.WEB_ATTACK,
                "severity": Severity.CRITICAL,
                "description": "Command injection attempt"
            },
            "PORT_SCAN": {
                "pattern": r"(Connection refused|Connection timed out)",
                "category": ThreatCategory.INTRUSION,
                "severity": Severity.MEDIUM,
                "description": "Potential port scan detected"
            },
            "MALWARE_SIGNATURE_001": {
                "pattern": r"(EICAR|AVG|malware|trojan|ransomware)",
                "category": ThreatCategory.MALICIOUS_SOFTWARE,
                "severity": Severity.CRITICAL,
                "description": "Known malware signature detected"
            },
        }
    
    def match(self, payload: str) -> Optional[Dict]:
        """Match payload against signatures."""
        for sig_id, sig_data in self.signatures.items():
            if re.search(sig_data["pattern"], payload, re.IGNORECASE):
                return {
                    "signature_id": sig_id,
                    **sig_data
                }
        return None


class NetworkIntrusionDetectionSystem:
    """Network-based IDS."""
    
    def __init__(self, interface: str = "any"):
        self.interface = interface
        self.signatures = SignatureDatabase()
        self.alerts: List[SecurityAlert] = []
        self.events: List[IntrusionDetectionEvent] = []
        self._running = False
        self._lock = threading.Lock()
        self.stats = {
            "packets_inspected": 0,
            "alerts_generated": 0,
            "attacks_mitigated": 0,
        }
    
    def analyze_packet(
        self,
        source_ip: str,
        dest_ip: str,
        source_port: int,
        dest_port: int,
        protocol: str,
        payload: str
    ) -> Optional[SecurityAlert]:
        """Analyze a network packet for threats."""
        self.stats["packets_inspected"] += 1
        
        match = self.signatures.match(payload)
        
        if not match:
            return None
        
        alert = SecurityAlert(
            id=f"IDS_{random.randint(10000, 99999)}",
            timestamp=datetime.utcnow(),
            category=match["category"],
            severity=match["severity"],
            source_ip=source_ip,
            destination_ip=dest_ip,
            description=match["description"],
            indicators=[match["signature_id"]]
        )
        
        event = IntrusionDetectionEvent(
            id=alert.id,
            timestamp=alert.timestamp,
            source_ip=source_ip,
            source_port=source_port,
            dest_ip=dest_ip,
            dest_port=dest_port,
            protocol=protocol,
            alert_signature=match["signature_id"],
            category=match["category"],
            severity=match["severity"],
            payload_snippet= payload[:200]
        )
        
        with self._lock:
            self.alerts.append(alert)
            self.events.append(event)
            self.stats["alerts_generated"] += 1
        
        return alert
    
    def get_alerts(
        self,
        severity: Optional[Severity] = None,
        category: Optional[ThreatCategory] = None,
        limit: int = 100
    ) -> List[SecurityAlert]:
        """Get filtered alerts."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        return alerts[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get IDS statistics."""
        return self.stats.copy()


class WebApplicationFirewall:
    """Web Application Firewall."""
    
    def __init__(self):
        self.signatures = SignatureDatabase()
        self.blocked_ips: Dict[str, datetime] = {}
        self.rules: List[Dict] = []
        self.alerts: List[SecurityAlert] = []
        self._load_rules()
    
    def _load_rules(self):
        """Load WAF rules."""
        self.rules = [
            {"id": "WAF-001", "action": "block", "pattern": r"<script", "description": "Block script tags"},
            {"id": "WAF-002", "action": "block", "pattern": r"' OR '1'='1", "description": "Block SQLi patterns"},
            {"id": "WAF-003", "action": "alert", "pattern": r"(\.\./|\.\.\\)", "description": "Alert on path traversal"},
            {"id": "WAF-004", "action": "block", "pattern": r"(;|\||\`)", "description": "Block command injection"},
        ]
    
    def check_request(
        self,
        ip: str,
        method: str,
        path: str,
        query: str,
        body: str
    ) -> Tuple[bool, Optional[SecurityAlert]]:
        """Check HTTP request against WAF rules."""
        if ip in self.blocked_ips:
            if datetime.utcnow() - self.blocked_ips[ip] < timedelta(hours=1):
                return True, None
            else:
                del self.blocked_ips[ip]
        
        full_request = f"{method} {path}?{query} {body}"
        
        for rule in self.rules:
            if re.search(rule["pattern"], full_request, re.IGNORECASE):
                if rule["action"] == "block":
                    self.blocked_ips[ip] = datetime.utcnow()
                    alert = SecurityAlert(
                        id=f"WAF_{random.randint(10000, 99999)}",
                        timestamp=datetime.utcnow(),
                        category=ThreatCategory.WEB_ATTACK,
                        severity=Severity.HIGH,
                        source_ip=ip,
                        destination_ip="",
                        description=f"WAF blocked: {rule['description']}",
                        indicators=[rule["id"]]
                    )
                    self.alerts.append(alert)
                    return True, alert
                else:
                    alert = SecurityAlert(
                        id=f"WAF_{random.randint(10000, 99999)}",
                        timestamp=datetime.utcnow(),
                        category=ThreatCategory.WEB_ATTACK,
                        severity=Severity.MEDIUM,
                        source_ip=ip,
                        destination_ip="",
                        description=f"WAF alert: {rule['description']}",
                        indicators=[rule["id"]]
                    )
                    self.alerts.append(alert)
                    return False, alert
        
        return False, None


class HoneyPotManager:
    """HoneyPot deployment and management."""
    
    def __init__(self):
        self.honeypots: Dict[str, Dict] = {}
        self.events: List[HoneyPotEvent] = []
        self.deployed_ips: Dict[str, str] = {}
        self._setup_honeypots()
    
    def _setup_honeypots(self):
        """Initialize honeypot configurations."""
        self.honeypots = {
            "ssh": {
                "port": 2222,
                "banner": "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1",
                "fake_filesystem": ["/etc/passwd", "/etc/shadow", "/home/admin/.ssh/"],
                "fake_credentials": {"admin": "admin123", "root": "toor"},
                "description": "SSH honeypot"
            },
            "http": {
                "port": 8080,
                "fake_endpoints": ["/admin", "/config", "/api/v1/auth"],
                "description": "HTTP honeypot"
            },
            "ftp": {
                "port": 2121,
                "fake_files": ["/pub/important.txt", "/conf/secrets.zip"],
                "description": "FTP honeypot"
            },
            "database": {
                "port": 5432,
                "fake_db_name": "sensitive_data",
                "description": "PostgreSQL honeypot"
            }
        }
    
    def deploy(self, honeypot_type: str, virtual_ip: str) -> bool:
        """Deploy a honeypot."""
        if honeypot_type not in self.honeypots:
            return False
        
        self.deployed_ips[virtual_ip] = honeypot_type
        return True
    
    def record_interaction(
        self,
        honeypot_type: str,
        source_ip: str,
        source_port: int,
        action: str,
        commands: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        credentials: Optional[List[str]] = None
    ) -> HoneyPotEvent:
        """Record honeypot interaction."""
        event = HoneyPotEvent(
            id=f"HP_{random.randint(10000, 99999)}",
            timestamp=datetime.utcnow(),
            honeypot_type=honeypot_type,
            source_ip=source_ip,
            source_port=source_port,
            action=action,
            commands_executed=commands or [],
            files_accessed=files or [],
            credentials_provided=credentials or []
        )
        
        self.events.append(event)
        return event
    
    def get_attackers(self) -> List[Dict]:
        """Get list of attackers that interacted with honeypots."""
        attacker_data: Dict[str, Dict[str, Any]] = {}
        
        for event in self.events:
            if event.source_ip not in attacker_data:
                attacker_data[event.source_ip] = {
                    "interactions": 0,
                    "types": set(),
                    "first_seen": None,
                    "last_seen": None
                }
            
            attacker_data[event.source_ip]["interactions"] += 1
            attacker_data[event.source_ip]["types"].add(event.honeypot_type)
            
            if not attacker_data[event.source_ip]["first_seen"]:
                attacker_data[event.source_ip]["first_seen"] = event.timestamp
            attacker_data[event.source_ip]["last_seen"] = event.timestamp
        
        return [
            {
                "ip": ip,
                "interactions": data["interactions"],
                "honeypot_types": list(data["types"]),
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"]
            }
            for ip, data in attacker_data.items()
        ]


class ThreatHunter:
    """Threat hunting engine."""
    
    def __init__(self):
        self.hunts: Dict[str, ThreatHunt] = {}
        self.ioc_database: Dict[str, List[Dict]] = defaultdict(list)
        self.hunt_templates = self._load_hunt_templates()
    
    def _load_hunt_templates(self) -> List[Dict]:
        """Load threat hunting templates."""
        return [
            {
                "id": "HUNT-001",
                "name": "Suspicious PowerShell Activity",
                "hypothesis": "Adversaries may be using PowerShell for lateral movement",
                "search_patterns": ["powershell.exe", "IEX ", "Invoke-Expression"],
                "severity": Severity.HIGH
            },
            {
                "id": "HUNT-002", 
                "name": "Unusual Network Traffic",
                "hypothesis": "Possible data exfiltration through unusual ports",
                "search_patterns": ["non-standard ports", "large outbound"],
                "severity": Severity.MEDIUM
            },
            {
                "id": "HUNT-003",
                "name": "Persistence Mechanism",
                "hypothesis": "Attacker may have established persistence",
                "search_patterns": ["registry run keys", "scheduled tasks", "services"],
                "severity": Severity.CRITICAL
            },
            {
                "id": "HUNT-004",
                "name": "Credential Dumping",
                "hypothesis": "Attempt to dump credentials detected",
                "search_patterns": ["mimikatz", "lsass", "samdump"],
                "severity": Severity.CRITICAL
            }
        ]
    
    def start_hunt(
        self,
        template_id: str,
        data_source: str = "logs"
    ) -> Optional[ThreatHunt]:
        """Start a threat hunting investigation."""
        template = next((t for t in self.hunt_templates if t["id"] == template_id), None)
        
        if not template:
            return None
        
        hunt = ThreatHunt(
            id=f"HUNT_{random.randint(10000, 99999)}",
            name=template["name"],
            hypothesis=template["hypothesis"],
            status="in_progress",
            created_at=datetime.utcnow(),
            closed_at=None,
            findings=[],
            iocs_found=[],
            severity=template["severity"]
        )
        
        self.hunts[hunt.id] = hunt
        
        self._execute_hunt(hunt, data_source)
        
        return hunt
    
    def _execute_hunt(self, hunt: ThreatHunt, data_source: str):
        """Execute hunt logic (simulated)."""
        num_findings = random.randint(0, 5)
        
        for _ in range(num_findings):
            hunt.findings.append({
                "timestamp": datetime.utcnow().isoformat(),
                "description": random.choice([
                    "Suspicious process execution detected",
                    "Unusual network connection established",
                    "Modified system binary detected",
                    "Unauthorized registry modification"
                ]),
                "source": random.choice(["endpoint", "network", "log"])
            })
        
        if hunt.findings:
            hunt.status = "completed"
            hunt.closed_at = datetime.utcnow()
            
            for finding in hunt.findings:
                hunt.iocs_found.append({
                    "type": "behavior",
                    "indicator": finding["description"],
                    "severity": hunt.severity.name
                })
        else:
            hunt.status = "closed_no_findings"
            hunt.closed_at = datetime.utcnow()
    
    def get_hunts(
        self,
        status: Optional[str] = None
    ) -> List[ThreatHunt]:
        """Get hunts with optional filtering."""
        hunts = list(self.hunts.values())
        
        if status:
            hunts = [h for h in hunts if h.status == status]
        
        return sorted(hunts, key=lambda x: x.created_at, reverse=True)


class MalwareDetector:
    """Malware detection engine."""
    
    def __init__(self):
        self.signatures: Dict[str, str] = {}
        self.suspicious_behaviors: List[Dict[str, Any]] = []
        self.quarantine: List[Dict[str, Any]] = []
        self._load_signatures()
    
    def _load_signatures(self):
        """Load malware signatures."""
        self.signatures = {
            "EICAR": r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
            "MIMIKATZ_PATTERN": "mimikatz",
            "NETCAT_PATTERN": "nc.exe",
            "PWNCREAM": "pwncream",
            "COINMINER": "coinminer",
            "RANSOMWARE_EXTENSION": ".encrypted",
        }
    
    def scan_file(self, file_path: str, file_content: bytes) -> Tuple[bool, Optional[str]]:
        """Scan file for malware."""
        content_str = file_content.decode('utf-8', errors='ignore')
        
        for sig_name, sig_pattern in self.signatures.items():
            if sig_pattern in content_str:
                self.quarantine.append({
                    "file_path": file_path,
                    "signature": sig_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "quarantined"
                })
                return True, sig_name
        
        suspicious_patterns = [
            "powershell.*-enc",
            "bitsadmin",
            "certutil.*decode",
            "frombase64",
            "reverse_shell"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                self.suspicious_behaviors.append({
                    "file": file_path,
                    "behavior": pattern,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False, f"suspicious_behavior:{pattern}"
        
        return False, None
    
    def get_quarantine(self) -> List[Dict]:
        """Get quarantined files."""
        return self.quarantine.copy()


class SOAREngine:
    """Security Orchestration, Automation and Response."""
    
    def __init__(self):
        self.playbooks: Dict[str, Dict] = {}
        self.incidents: Dict[str, Dict] = {}
        self.automations: List[Dict] = []
        self._load_playbooks()
    
    def _load_playbooks(self):
        """Load automated response playbooks."""
        self.playbooks = {
            "PB-001": {
                "name": "Malware Detected",
                "triggers": ["malware_detected"],
                "steps": [
                    {"action": "quarantine", "target": "infected_endpoint"},
                    {"action": "collect_forensics", "target": "infected_endpoint"},
                    {"action": "notify", "target": "security_team"},
                    {"action": "create_incident", "target": "ticketing_system"}
                ]
            },
            "PB-002": {
                "name": "Brute Force Attack",
                "triggers": ["brute_force_detected"],
                "steps": [
                    {"action": "block_ip", "target": "source_ip"},
                    {"action": "enable_mfa", "target": "affected_accounts"},
                    {"action": "notify", "target": "security_team"}
                ]
            },
            "PB-003": {
                "name": "Data Exfiltration",
                "triggers": ["data_exfiltration_detected"],
                "steps": [
                    {"action": "block_ip", "target": "source_ip"},
                    {"action": "suspend_account", "target": "user"},
                    {"action": "collect_forensics", "target": "endpoint"},
                    {"action": "notify", "target": "management"}
                ]
            }
        }
    
    def trigger_playbook(
        self,
        playbook_id: str,
        incident_data: Dict
    ) -> Dict:
        """Trigger automated response playbook."""
        playbook = self.playbooks.get(playbook_id)
        
        if not playbook:
            return {"status": "error", "message": "Playbook not found"}
        
        incident_id = f"INC_{random.randint(10000, 99999)}"
        
        incident = {
            "id": incident_id,
            "playbook": playbook_id,
            "trigger": incident_data.get("trigger", "unknown"),
            "status": "running",
            "started_at": datetime.utcnow(),
            "steps_completed": [],
            "steps_failed": []
        }
        
        self.incidents[incident_id] = incident
        
        for step in playbook["steps"]:
            try:
                time.sleep(0.1)
                incident["steps_completed"].append(step)
            except Exception as e:
                incident["steps_failed"].append({
                    "step": step,
                    "error": str(e)
                })
        
        incident["status"] = "completed"
        
        return incident
    
    def get_incidents(self, status: Optional[str] = None) -> List[Dict]:
        """Get incidents with optional filtering."""
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i["status"] == status]
        
        return incidents


class BlueTeamDefense:
    """
    Comprehensive Blue Team Defense Framework.
    
    Integrates all defensive mechanisms into unified defense system.
    """
    
    def __init__(self):
        self.ids = NetworkIntrusionDetectionSystem()
        self.waf = WebApplicationFirewall()
        self.honeypot = HoneyPotManager()
        self.threat_hunter = ThreatHunter()
        self.malware_detector = MalwareDetector()
        self.soar = SOAREngine()
        
        self.defense_stats = {
            "alerts_generated": 0,
            "attacks_blocked": 0,
            "threats_hunted": 0,
            "malware_detected": 0,
            "playbooks_executed": 0
        }
    
    def analyze_network_traffic(
        self,
        source_ip: str,
        dest_ip: str,
        source_port: int,
        dest_port: int,
        protocol: str,
        payload: str
    ) -> Optional[SecurityAlert]:
        """Analyze network traffic for threats."""
        alert = self.ids.analyze_packet(
            source_ip, dest_ip, source_port, dest_port, protocol, payload
        )
        
        if alert:
            self.defense_stats["alerts_generated"] += 1
            
            self.soar.trigger_playbook(
                "PB-002" if alert.category == ThreatCategory.BRUTE_FORCE else "PB-001",
                {"trigger": alert.category.value, "alert": alert.id}
            )
            self.defense_stats["playbooks_executed"] += 1
        
        return alert
    
    def check_web_request(
        self,
        ip: str,
        method: str,
        path: str,
        query: str = "",
        body: str = ""
    ) -> bool:
        """Check web request against WAF."""
        blocked, alert = self.waf.check_request(ip, method, path, query, body)
        
        if alert:
            self.defense_stats["alerts_generated"] += 1
        
        return blocked
    
    def scan_for_malware(self, file_path: str, content: bytes) -> Tuple[bool, str]:
        """Scan file for malware."""
        is_malware, signature = self.malware_detector.scan_file(file_path, content)
        
        if is_malware:
            self.defense_stats["malware_detected"] += 1
            
            self.soar.trigger_playbook("PB-001", {"trigger": "malware_detected"})
            self.defense_stats["playbooks_executed"] += 1
        
        return is_malware, signature or "clean"
    
    def start_threat_hunt(self, template_id: str) -> Optional[ThreatHunt]:
        """Start a threat hunting investigation."""
        hunt = self.threat_hunter.start_hunt(template_id)
        
        if hunt:
            self.defense_stats["threats_hunted"] += 1
        
        return hunt
    
    def get_defense_status(self) -> Dict:
        """Get comprehensive defense status."""
        return {
            "ids": self.ids.get_statistics(),
            "waf": {
                "rules_active": len(self.waf.rules),
                "blocked_ips": len(self.waf.blocked_ips)
            },
            "honeypot": {
                "deployed": len(self.honeypot.deployed_ips),
                "interactions": len(self.honeypot.events),
                "attackers": len(self.honeypot.get_attackers())
            },
            "threat_hunting": {
                "active_hunts": len(self.threat_hunter.get_hunts("in_progress")),
                "completed_hunts": len(self.threat_hunter.get_hunts("completed"))
            },
            "malware": {
                "quarantined": len(self.malware_detector.get_quarantine()),
                "suspicious": len(self.malware_detector.suspicious_behaviors)
            },
            "soar": {
                "playbooks": len(self.soar.playbooks),
                "incidents": len(self.soar.incidents)
            },
            "overall": self.defense_stats.copy()
        }
    
    def generate_defense_report(self) -> Dict:
        """Generate comprehensive defense report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "defense_systems": {
                "ids": {
                    "alerts": len(self.ids.alerts),
                    "events": len(self.ids.events)
                },
                "waf": {
                    "alerts": len(self.waf.alerts)
                },
                "honeypot": {
                    "interactions": len(self.honeypot.events),
                    "unique_attackers": len(self.honeypot.get_attackers())
                },
                "threat_hunting": {
                    "total_hunts": len(self.threat_hunter.hunts),
                    "findings": sum(len(h.findings) for h in self.threat_hunter.hunts.values())
                },
                "malware": {
                    "quarantined": len(self.malware_detector.quarantine)
                },
                "soar": {
                    "incidents": len(self.soar.incidents)
                }
            },
            "statistics": self.defense_stats.copy(),
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        if self.defense_stats["alerts_generated"] > 100:
            recommendations.append("High alert volume detected - review tuning rules")
        
        if self.defense_stats["malware_detected"] > 0:
            recommendations.append("Malware detected - immediate investigation required")
        
        if not self.honeypot.deployed_ips:
            recommendations.append("Deploy honeypots for early threat detection")
        
        completed_hunts = len(self.threat_hunter.get_hunts("completed"))
        if completed_hunts < 5:
            recommendations.append("Increase threat hunting frequency")
        
        return recommendations if recommendations else ["Maintain current defensive posture"]
