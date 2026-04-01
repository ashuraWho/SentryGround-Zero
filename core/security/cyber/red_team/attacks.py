"""
Red Team Attack Simulation Framework

Provides realistic attack simulation scenarios for security posture assessment:
- SQL Injection attacks
- XSS (Cross-Site Scripting)
- CSRF attacks
- Brute force authentication bypass
- Denial of Service (DoS)
- Man-in-the-Middle attacks
- Privilege escalation
- Data exfiltration simulation
"""

import os
import random
import string
import hashlib
import re
import time
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json


class AttackType(Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    BRUTE_FORCE = "brute_force"
    DOS = "denial_of_service"
    MITM = "man_in_the_middle"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    ZERO_DAY = "zero_day"
    SUPPLY_CHAIN = "supply_chain"
    BUFFER_OVERFLOW = "buffer_overflow"
    CODE_INJECTION = "code_injection"


class AttackSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AttackScenario:
    """Represents a single attack scenario."""
    id: str
    attack_type: AttackType
    severity: AttackSeverity
    target: str
    description: str
    success: bool
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    mitigation: str = ""
    ioc: Dict[str, str] = field(default_factory=dict)


@dataclass
class AttackReport:
    """Comprehensive attack simulation report."""
    timestamp: datetime
    total_attacks: int
    successful_attacks: int
    failed_attacks: int
    scenarios: List[AttackScenario]
    vulnerabilities_found: List[Dict[str, Any]]
    risk_score: float
    recommendations: List[str]


class RedTeamSimulator:
    """
    Red Team Attack Simulation Framework.
    
    Provides controlled attack simulations for security testing.
    All attacks are simulated and logged for analysis.
    """
    
    def __init__(self, target_systems: Optional[List[str]] = None):
        self.target_systems = target_systems or ["localhost"]
        self._attack_history: List[AttackScenario] = []
        self._vulnerabilities: List[Dict[str, Any]] = []
        self._active_campaigns: Dict[str, Dict] = {}
        
        self._setup_attack_vectors()
    
    def _setup_attack_vectors(self):
        """Initialize attack vectors and payloads."""
        self.sql_injection_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' /*",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users--",
            "' UNION SELECT null, null, username, password FROM users--",
            "admin'--",
            "' OR '1'='1'",
            "1' AND '1'='1",
            "1' AND '1'='2",
            "' OR ''='",
            "' OR 1=1--",
            "1' ORDER BY 1--",
            "1' ORDER BY 10--",
        ]
        
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<marquee onstart=alert('XSS')>",
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>",
        ]
        
        self.brute_force_credentials = [
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "123456"),
            ("root", "root"),
            ("root", "toor"),
            ("admin", "admin123"),
            ("user", "user"),
            ("administrator", "administrator"),
            ("test", "test"),
            ("guest", "guest"),
        ]
    
    def simulate_sql_injection(
        self,
        target: str,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate SQL injection attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"SQLI_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("sql_injection", 0.3)
        
        payload = random.choice(self.sql_injection_payloads)
        
        details = {
            "target": target,
            "payload": payload,
            "injection_point": "login_form",
            "database_type": "PostgreSQL",
            "tested_params": ["username", "password", "email"],
        }
        
        ioc = {
            "indicator": f"malformed_sql_query_{scenario_id[:8]}",
            "pattern": payload[:20] + "...",
            "signature": hashlib.md5(payload.encode()).hexdigest()[:16],
        }
        
        success = target_vuln and random.random() < 0.7
        
        if success:
            details["data_exposed"] = ["users table", "hashed_passwords"]
            details["privilege_obtained"] = "database_admin"
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.SQL_INJECTION,
            severity=AttackSeverity.CRITICAL if success else AttackSeverity.HIGH,
            target=target,
            description=f"SQL Injection attack on {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            ioc=ioc,
            mitigation="Use parameterized queries, input validation, least privilege DB accounts"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "SQL Injection",
                "severity": "CRITICAL",
                "target": target,
                "cwe": "CWE-89",
                "description": "Unparameterized SQL query allows injection"
            })
        
        return scenario
    
    def simulate_xss_attack(
        self,
        target: str,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate XSS attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"XSS_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("xss", 0.25)
        
        payload = random.choice(self.xss_payloads)
        
        details = {
            "target": target,
            "payload": payload,
            "injection_point": "comment_field",
            "context": "html_body",
            "bypass_filters": random.random() < 0.3,
        }
        
        ioc = {
            "indicator": f"xss_payload_{scenario_id[:8]}",
            "pattern": payload[:30] + "...",
            "signature": hashlib.sha256(payload.encode()).hexdigest()[:16],
        }
        
        success = target_vuln and random.random() < 0.6
        
        if success:
            details["cookies_stolen"] = ["session_id", "auth_token"]
            details["script_executed"] = True
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.XSS,
            severity=AttackSeverity.HIGH if success else AttackSeverity.MEDIUM,
            target=target,
            description=f"XSS attack on {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            ioc=ioc,
            mitigation="Output encoding, Content Security Policy, HttpOnly cookies"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "Cross-Site Scripting",
                "severity": "HIGH",
                "target": target,
                "cwe": "CWE-79",
                "description": "Insufficient output encoding allows XSS"
            })
        
        return scenario
    
    def simulate_brute_force(
        self,
        target: str,
        max_attempts: int = 100,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate brute force authentication attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"BF_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("weak_credentials", 0.4)
        
        attempts = random.randint(10, max_attempts)
        
        details = {
            "target": target,
            "attempts": attempts,
            "target_service": "ssh",
            "username": "admin",
            "password_list_size": len(self.brute_force_credentials),
            "lockout_bypass": random.random() < 0.2,
        }
        
        success = target_vuln and random.random() < 0.5
        
        if success:
            details["credentials_obtained"] = random.choice(self.brute_force_credentials)
        
        ioc = {
            "indicator": f"brute_force_{scenario_id[:8]}",
            "source_ips": [f"192.168.1.{random.randint(50, 150)}"],
            "pattern": "authentication_failure",
        }
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.BRUTE_FORCE,
            severity=AttackSeverity.HIGH if success else AttackSeverity.MEDIUM,
            target=target,
            description=f"Brute force attack on {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            ioc=ioc,
            mitigation="Rate limiting, account lockout, multi-factor authentication, strong passwords"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "Weak Credentials",
                "severity": "HIGH",
                "target": target,
                "cwe": "CWE-307",
                "description": "No rate limiting on authentication endpoint"
            })
        
        return scenario
    
    def simulate_dos_attack(
        self,
        target: str,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate Denial of Service attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"DOS_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("dos_vulnerable", 0.2)
        
        details = {
            "target": target,
            "attack_vector": random.choice(["SYN flood", "HTTP flood", "UDP flood"]),
            "packets_per_second": random.randint(1000, 50000),
            "duration_seconds": random.randint(10, 300),
            "botnet_size": random.randint(100, 10000),
        }
        
        success = target_vuln and random.random() < 0.4
        
        if success:
            details["service_impacted"] = random.choice(["API", "Web UI", "Data Ingestion"])
            details["downtime_seconds"] = random.randint(30, 600)
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.DOS,
            severity=AttackSeverity.HIGH if success else AttackSeverity.MEDIUM,
            target=target,
            description=f"DoS attack on {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            mitigation="Rate limiting, traffic filtering, CDN, redundant infrastructure"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "Denial of Service",
                "severity": "MEDIUM",
                "target": target,
                "cwe": "CWE-400",
                "description": "No DoS protection detected"
            })
        
        return scenario
    
    def simulate_privilege_escalation(
        self,
        target: str,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate privilege escalation attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"PE_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("privilege_escalation", 0.25)
        
        escalation_paths = [
            ("user", "admin"),
            ("admin", "root"),
            ("service_account", "root"),
            ("container", "host"),
            ("kubernetes_pod", "node"),
        ]
        
        path = random.choice(escalation_paths)
        
        details = {
            "target": target,
            "initial_privilege": path[0],
            "target_privilege": path[1],
            "exploitation_method": random.choice([
                "sudo misconfiguration",
                "SUID binary exploitation",
                "container escape",
                "kernel exploit"
            ]),
        }
        
        success = target_vuln and random.random() < 0.4
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.PRIVILEGE_ESCALATION,
            severity=AttackSeverity.CRITICAL if success else AttackSeverity.HIGH,
            target=target,
            description=f"Privilege escalation on {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            mitigation="Least privilege, sudo logging, container isolation, kernel hardening"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "Privilege Escalation",
                "severity": "CRITICAL",
                "target": target,
                "cwe": "CWE-269",
                "description": f"Privilege escalation from {path[0]} to {path[1]}"
            })
        
        return scenario
    
    def simulate_mitm_attack(
        self,
        target: str,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate Man-in-the-Middle attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"MITM_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("weak_tls", 0.35)
        
        details = {
            "target": target,
            "attack_vector": random.choice(["ARP spoofing", "DNS spoofing", "SSL strip"]),
            "certificate_validation": "disabled" if target_vuln else "enabled",
            "traffic_intercepted": target_vuln and random.random() < 0.7,
        }
        
        success = target_vuln and random.random() < 0.5
        
        if success:
            details["data_obtained"] = random.choice([
                "session_tokens",
                "API_keys",
                "personal_data",
                "financial_info"
            ])
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.MITM,
            severity=AttackSeverity.CRITICAL if success else AttackSeverity.HIGH,
            target=target,
            description=f"Man-in-the-Middle attack on {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            mitigation="TLS 1.3, certificate pinning, HSTS, mutual TLS"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "Man-in-the-Middle",
                "severity": "CRITICAL",
                "target": target,
                "cwe": "CWE-295",
                "description": "Insufficient certificate validation"
            })
        
        return scenario
    
    def simulate_data_exfiltration(
        self,
        target: str,
        vulnerability_db: Optional[Dict] = None
    ) -> AttackScenario:
        """Simulate data exfiltration attack."""
        vuln_db = vulnerability_db or self._get_default_vuln_db()
        
        scenario_id = f"EXFIL_{random.randint(10000, 99999)}"
        timestamp = datetime.utcnow()
        
        target_vuln = random.random() < vuln_db.get("data_exposure", 0.3)
        
        data_types = [
            "satellite imagery",
            "customer_data",
            "encryption_keys",
            "telemetry_data",
            "user_credentials"
        ]
        
        details = {
            "target": target,
            "data_type": random.choice(data_types),
            "volume_mb": random.randint(100, 10000),
            "exfiltration_method": random.choice([
                "DNS tunneling",
                "HTTPS exfil",
                "ICMP tunneling",
                "Cloud storage sync"
            ]),
            "destination": random.choice([
                "attacker-server.net",
                "pastebin.com",
                "mega.nz",
                "dark web marketplace"
            ]),
        }
        
        success = target_vuln and random.random() < 0.35
        
        scenario = AttackScenario(
            id=scenario_id,
            attack_type=AttackType.DATA_EXFILTRATION,
            severity=AttackSeverity.CRITICAL,
            target=target,
            description=f"Data exfiltration from {target}",
            success=success,
            timestamp=timestamp,
            details=details,
            mitigation="DLP solutions, network monitoring, encryption at rest, egress filtering"
        )
        
        self._attack_history.append(scenario)
        
        if success:
            self._vulnerabilities.append({
                "type": "Data Exfiltration",
                "severity": "CRITICAL",
                "target": target,
                "cwe": "CWE-306",
                "description": f"Unauthorized data transfer of {details['data_type']}"
            })
        
        return scenario
    
    def run_campaign(
        self,
        campaign_name: str,
        targets: Optional[List[str]] = None,
        attack_types: Optional[List[AttackType]] = None
    ) -> AttackReport:
        """
        Execute a full attack campaign.
        
        Args:
            campaign_name: Name of the campaign
            targets: Target systems (defaults to configured targets)
            attack_types: Types of attacks to run
        
        Returns:
            AttackReport with detailed results
        """
        targets = targets or self.target_systems
        attack_types = attack_types or [
            AttackType.SQL_INJECTION,
            AttackType.XSS,
            AttackType.BRUTE_FORCE,
            AttackType.DOS,
            AttackType.PRIVILEGE_ESCALATION,
            AttackType.MITM,
            AttackType.DATA_EXFILTRATION,
        ]
        
        self._active_campaigns[campaign_name] = {
            "start_time": datetime.utcnow(),
            "targets": targets,
            "attack_types": [a.value for a in attack_types],
        }
        
        scenarios = []
        
        for target in targets:
            for attack_type in attack_types:
                if attack_type == AttackType.SQL_INJECTION:
                    scenario = self.simulate_sql_injection(target)
                elif attack_type == AttackType.XSS:
                    scenario = self.simulate_xss_attack(target)
                elif attack_type == AttackType.BRUTE_FORCE:
                    scenario = self.simulate_brute_force(target)
                elif attack_type == AttackType.DOS:
                    scenario = self.simulate_dos_attack(target)
                elif attack_type == AttackType.PRIVILEGE_ESCALATION:
                    scenario = self.simulate_privilege_escalation(target)
                elif attack_type == AttackType.MITM:
                    scenario = self.simulate_mitm_attack(target)
                elif attack_type == AttackType.DATA_EXFILTRATION:
                    scenario = self.simulate_data_exfiltration(target)
                else:
                    continue
                
                scenarios.append(scenario)
                
                time.sleep(0.1)
        
        self._active_campaigns[campaign_name]["end_time"] = datetime.utcnow()
        
        successful = sum(1 for s in scenarios if s.success)
        failed = len(scenarios) - successful
        
        risk_score = self._calculate_risk_score(scenarios)
        
        recommendations = self._generate_recommendations(scenarios)
        
        return AttackReport(
            timestamp=datetime.utcnow(),
            total_attacks=len(scenarios),
            successful_attacks=successful,
            failed_attacks=failed,
            scenarios=scenarios,
            vulnerabilities_found=self._vulnerabilities.copy(),
            risk_score=risk_score,
            recommendations=recommendations
        )
    
    def _calculate_risk_score(self, scenarios: List[AttackScenario]) -> float:
        """Calculate overall risk score based on successful attacks."""
        if not scenarios:
            return 0.0
        
        severity_weights = {
            AttackSeverity.LOW: 5,
            AttackSeverity.MEDIUM: 15,
            AttackSeverity.HIGH: 30,
            AttackSeverity.CRITICAL: 50,
        }
        
        total_weight = sum(
            severity_weights[s.severity] for s in scenarios if s.success
        )
        
        return min(100, total_weight)
    
    def _generate_recommendations(
        self,
        scenarios: List[AttackScenario]
    ) -> List[str]:
        """Generate security recommendations based on attack results."""
        recommendations = set()
        
        attack_types_present = set(s.attack_type for s in scenarios if s.success)
        
        if AttackType.SQL_INJECTION in attack_types_present:
            recommendations.add("Implement parameterized queries (prepared statements)")
            recommendations.add("Apply input validation and output encoding")
        
        if AttackType.XSS in attack_types_present:
            recommendations.add("Implement Content Security Policy (CSP)")
            recommendations.add("Use HttpOnly and Secure flags on cookies")
        
        if AttackType.BRUTE_FORCE in attack_types_present:
            recommendations.add("Implement account lockout after failed attempts")
            recommendations.add("Enable multi-factor authentication")
        
        if AttackType.DOS in attack_types_present:
            recommendations.add("Configure rate limiting on all endpoints")
            recommendations.add("Deploy DDoS mitigation service")
        
        if AttackType.PRIVILEGE_ESCALATION in attack_types_present:
            recommendations.add("Apply principle of least privilege")
            recommendations.add("Enable sudo logging and audit")
        
        if AttackType.MITM in attack_types_present:
            recommendations.add("Enforce TLS 1.3 for all connections")
            recommendations.add("Implement certificate pinning")
        
        if AttackType.DATA_EXFILTRATION in attack_types_present:
            recommendations.add("Deploy Data Loss Prevention (DLP) solution")
            recommendations.add("Implement egress monitoring and filtering")
        
        if not recommendations:
            recommendations.add("Continue regular security assessments")
            recommendations.add("Maintain current security posture")
        
        return sorted(list(recommendations))
    
    def _get_default_vuln_db(self) -> Dict[str, float]:
        """Get default vulnerability probabilities."""
        return {
            "sql_injection": 0.3,
            "xss": 0.25,
            "weak_credentials": 0.4,
            "dos_vulnerable": 0.2,
            "privilege_escalation": 0.25,
            "weak_tls": 0.35,
            "data_exposure": 0.3,
        }
    
    def get_attack_history(
        self,
        attack_type: Optional[AttackType] = None,
        limit: int = 100
    ) -> List[AttackScenario]:
        """Get attack history with optional filtering."""
        history = self._attack_history
        
        if attack_type:
            history = [s for s in history if s.attack_type == attack_type]
        
        return history[-limit:]
    
    def get_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Get discovered vulnerabilities."""
        return self._vulnerabilities.copy()
    
    def get_campaign(self, campaign_name: str) -> Optional[Dict]:
        """Get campaign details."""
        return self._active_campaigns.get(campaign_name)
    
    def export_report(self, format: str = "json") -> str:
        """Export attack history as JSON or HTML report."""
        if format == "json":
            return json.dumps({
                "attacks": [
                    {
                        "id": s.id,
                        "type": s.attack_type.value,
                        "severity": s.severity.name,
                        "target": s.target,
                        "success": s.success,
                        "timestamp": s.timestamp.isoformat(),
                        "details": s.details,
                        "ioc": s.ioc,
                    }
                    for s in self._attack_history
                ],
                "vulnerabilities": self._vulnerabilities,
                "statistics": {
                    "total_attacks": len(self._attack_history),
                    "successful": sum(1 for s in self._attack_history if s.success),
                    "failed": sum(1 for s in self._attack_history if not s.success),
                }
            }, indent=2)
        
        return ""
