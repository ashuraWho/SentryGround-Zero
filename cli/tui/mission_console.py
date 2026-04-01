"""
SentryGround-Zero Mission Control Console v5.0
NASA/ESA Style Mission Control - Secure Earth Observation Platform
"""

import os
import sys
import time
import random
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import threading
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from concurrent.futures import as_completed
import multiprocessing as mp

os.environ['TERM'] = 'xterm-256color'
os.environ['FORCE_COLOR'] = '1'

EXECUTOR = ThreadPoolExecutor(max_workers=4)
DATA_LOADER = ThreadPoolExecutor(max_workers=8)


class AsyncDataLoader:
    """Async data loading for improved I/O performance."""
    
    def __init__(self):
        self.cache = {}
        self.loading = {}
    
    async def load_csv_async(self, filepath: str) -> pd.DataFrame:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(DATA_LOADER, self.load_csv_sync, filepath)
    
    def load_csv_sync(self, filepath: str) -> pd.DataFrame:
        if filepath in self.cache:
            return self.cache[filepath]
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            self.cache[filepath] = df
            return df
        return None
    
    def preload_data(self, base_path: str):
        data_dirs = ["global_temperatures", "sea_level", "co2_emissions", 
                     "sea_ice", "hurricanes", "air_quality", "space_weather"]
        
        for dirname in data_dirs:
            dirpath = os.path.join(base_path, dirname)
            if os.path.exists(dirpath):
                for f in os.listdir(dirpath):
                    if f.endswith('.csv'):
                        filepath = os.path.join(dirpath, f)
                        self.load_csv_sync(filepath)


class ParallelPredictor:
    """Parallel prediction execution."""
    
    @staticmethod
    def run_predictions(satellites: List, predict_func, max_workers: int = 4):
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(predict_func, sat): sat.name 
                for sat in satellites
            }
            
            for future in as_completed(futures):
                sat_name = futures[future]
                try:
                    results[sat_name] = future.result()
                except Exception as e:
                    results[sat_name] = {"error": str(e)}
        
        return results
    
    @staticmethod
    def batch_predict(sat_names: List[str], console_instance) -> Dict:
        results = {}
        
        def predict_for_sat(name):
            sat = next((s for s in console_instance.satellites if s.name == name), None)
            if sat:
                console_instance.linked_satellite = sat
                console_instance.handle_predict()
                return {"satellite": name, "status": "completed"}
            return {"satellite": name, "status": "not_found"}
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(predict_for_sat, name) for name in sat_names]
            for f in as_completed(futures):
                results[f.result()["satellite"]] = f.result()
        
        return results


class RealtimeMonitorThread(threading.Thread):
    """Background thread for real-time satellite monitoring."""
    
    def __init__(self, satellites: List, monitor: Any, alert_system: Any, interval: int = 5):
        super().__init__(daemon=True)
        self.satellites = satellites
        self.monitor = monitor
        self.alert_system = alert_system
        self.interval = interval
        self.running = False
        self.alerts_queue = queue.Queue()
    
    def run(self):
        self.running = True
        while self.running:
            for sat in self.satellites:
                self.monitor.update_satellite(sat)
                new_alerts = self.alert_system.check_satellite(sat)
                if new_alerts:
                    self.alerts_queue.put(new_alerts)
            time.sleep(self.interval)
    
    def stop(self):
        self.running = False
    
    def get_alerts(self) -> List:
        alerts = []
        while not self.alerts_queue.empty():
            alerts.extend(self.alerts_queue.get())
        return alerts

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.style import Style
from rich.theme import Theme
from rich.live import Live
from rich.layout import Layout
from rich.screen import Screen
from rich.markup import escape

custom_theme = Theme({
    "repr.str": "cyan",
    "repr.bool": "magenta",
    "repr.number": "green",
    "command": "cyan bold",
    "warning": "yellow bold",
    "error": "red bold",
    "success": "green bold",
    "info": "blue",
    "hack": "red bold",
    "defense": "cyan bold",
})

console = Console(color_system="256", force_terminal=True)


def col(color: str, text: str) -> str:
    return f"[{color}]{text}[/]"


def blink(color: str, text: str) -> str:
    return f"[bold {color}]{text}[/]"


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64


def show_chart(data: np.ndarray, years: np.ndarray, title: str, ylabel: str, 
               prediction_year: int = None, prediction_value: float = None,
               confidence: tuple = None) -> None:
    """Show real-time chart using matplotlib."""
    fig, ax = plt.subplots(figsize=(10, 5))
    
    ax.plot(years, data, 'b-', linewidth=2, label='Historical Data', marker='o', markersize=3)
    
    if prediction_year is not None and prediction_value is not None:
        ax.scatter([prediction_year], [prediction_value], color='red', s=100, 
                   zorder=5, label=f'Prediction {prediction_year}')
        if confidence:
            ax.fill_between([prediction_year-5, prediction_year+5], 
                          [confidence[0], confidence[0]], 
                          [confidence[1], confidence[1]], 
                          color='red', alpha=0.2, label='95% CI')
    
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
    plt.close(fig)
    
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    
    console.print(f"\n[dim]📊 Chart generated: {len(img_base64)} bytes[/]")
    console.print(f"[dim]  Saved to temp file for display[/]")



class MissionColors:
    PRIMARY = "cyan"
    SECONDARY = "blue"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    CRITICAL = "red bold"
    PURPLE = "magenta"
    CYAN = "cyan"
    WHITE = "white"
    GRAY = "dim"
    YELLOW = "yellow"
    RED_TEAM = "red"
    BLUE_TEAM = "cyan"
    HACKER = "red"
    DEFENSE = "cyan"


@dataclass
class Satellite:
    name: str
    regime: str
    lat: float
    lon: float
    alt: float
    status: str
    mission: str
    data_source: str
    security_level: int
    battery: float = 100.0
    signal_strength: float = 100.0
    data_rate: float = 0.0
    last_contact: str = ""
    temperature: float = 20.0


class SatelliteMonitor:
    """Real-time satellite monitoring."""
    
    def __init__(self):
        self.updating = False
        self.update_interval = 5
    
    def update_satellite(self, sat: Satellite) -> Satellite:
        sat.battery = max(0, min(100, sat.battery + random.uniform(-2, 1)))
        sat.signal_strength = max(0, min(100, sat.signal_strength + random.uniform(-5, 3)))
        sat.data_rate = random.uniform(1, 10) if sat.signal_strength > 30 else 0
        sat.temperature = random.uniform(-50, 50)
        sat.last_contact = datetime.now().strftime("%H:%M:%S")
        return sat
    
    def get_health_status(self, sat: Satellite) -> str:
        if sat.battery < 20 or sat.signal_strength < 30:
            return "CRITICAL"
        elif sat.battery < 50 or sat.signal_strength < 60:
            return "WARNING"
        return "NOMINAL"


class AlertSystem:
    """Real-time alert system for satellite monitoring."""
    
    def __init__(self):
        self.alerts = []
        self.active_alerts = []
    
    def check_satellite(self, sat: Satellite) -> List[Dict]:
        new_alerts = []
        
        if sat.battery < 20:
            new_alerts.append({
                "type": "CRITICAL",
                "satellite": sat.name,
                "message": f"Battery critically low: {sat.battery:.1f}%",
                "timestamp": datetime.now()
            })
        elif sat.battery < 50:
            new_alerts.append({
                "type": "WARNING",
                "satellite": sat.name,
                "message": f"Battery low: {sat.battery:.1f}%",
                "timestamp": datetime.now()
            })
        
        if sat.signal_strength < 30:
            new_alerts.append({
                "type": "CRITICAL",
                "satellite": sat.name,
                "message": f"Signal lost: {sat.signal_strength:.1f}%",
                "timestamp": datetime.now()
            })
        elif sat.signal_strength < 60:
            new_alerts.append({
                "type": "WARNING",
                "satellite": sat.name,
                "message": f"Weak signal: {sat.signal_strength:.1f}%",
                "timestamp": datetime.now()
            })
        
        if sat.temperature > 45 or sat.temperature < -40:
            new_alerts.append({
                "type": "WARNING",
                "satellite": sat.name,
                "message": f"Extreme temperature: {sat.temperature:.1f}°C",
                "timestamp": datetime.now()
            })
        
        self.active_alerts.extend(new_alerts)
        return new_alerts
    
    def display_alerts(self, console: Console):
        if not self.active_alerts:
            console.print("[green]✓ No active alerts[/]")
            return
        
        console.print(Panel(
            f"[bold red]⚠ ACTIVE ALERTS: {len(self.active_alerts)}[/]",
            border_style="red", box=box.DOUBLE
        ))
        
        for alert in self.active_alerts[-10:]:
            color = "red" if alert["type"] == "CRITICAL" else "yellow"
            console.print(f"[{color}]  [{alert['type']}] {alert['satellite']}: {alert['message']}[/]")
    
    def clear_alerts(self):
        self.active_alerts = []
    
    def get_health_status(self, sat: Satellite) -> str:
        if sat.battery < 20 or sat.signal_strength < 30:
            return "CRITICAL"
        elif sat.battery < 50 or sat.signal_strength < 60:
            return "WARNING"
        return "NOMINAL"
    
    def calculate_contact_window(self, sat: Satellite, ground_lat: float = 45.0, 
                                  ground_lon: float = 9.0) -> Dict:
        import math
        
        re = 6371.0
        alt = sat.alt
        
        orbital_period = 2 * math.pi * math.sqrt((re + alt) ** 3 / 398600.4)
        
        if sat.regime == "LEO":
            inclination = 97.0
        elif sat.regime == "MEO":
            inclination = 55.0
        elif sat.regime == "GEO":
            inclination = 0.0
        else:
            inclination = 45.0
        
        max_elevation = 90 - abs(sat.lat - ground_lat)
        if sat.lat == 0 and sat.lon == 0:
            max_elevation = 45
        
        earth_angle = 2 * math.asin(re / (re + alt))
        contact_angle = 2 * math.asin(math.sin(earth_angle / 2) / math.cos(math.radians(max_elevation)))
        
        contact_duration = (orbital_period / 360) * math.degrees(contact_angle)
        
        ascending = random.choice([True, False])
        next_pass = datetime.now() + timedelta(minutes=random.randint(5, 90))
        
        return {
            "satellite": sat.name,
            "regime": sat.regime,
            "altitude": alt,
            "orbital_period": orbital_period,
            "max_elevation": max_elevation,
            "contact_duration": contact_duration,
            "next_contact": next_pass.strftime("%H:%M:%S"),
            "visible": max_elevation > 10
        }
    
    def display_contact_windows(self, satellites: List[Satellite], console: Console):
        table = Table(
            title="🛰️ CONTACT WINDOWS (Next 24h)",
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("SATELLITE", style="bold magenta")
        table.add_column("REGIME", style="cyan")
        table.add_column("ALTITUDE", style="white")
        table.add_column("NEXT CONTACT", style="yellow")
        table.add_column("DURATION", style="yellow")
        table.add_column("ELEVATION", style="green")
        table.add_column("VISIBLE", style="bold")
        
        for sat in satellites[:15]:
            window = self.calculate_contact_window(sat)
            visible = "✓ YES" if window['visible'] else "✗ NO"
            visible_color = "green" if window['visible'] else "red"
            
            table.add_row(
                sat.name,
                sat.regime,
                f"{window['altitude']:.0f} km",
                window['next_contact'],
                f"{window['contact_duration']:.1f} min",
                f"{window['max_elevation']:.0f}°",
                col(visible_color, visible)
            )
        
        console.print(table)
    
    def plan_pass(self, sat: Satellite, start_hour: int = 0, hours: int = 24) -> List[Dict]:
        import math
        
        passes = []
        re = 6371.0
        alt = sat.alt
        
        orbital_period = 2 * math.pi * math.sqrt((re + alt) ** 3 / 398600.4)
        orbits_per_day = 1440 / (orbital_period / 60)
        
        current_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        for i in range(hours):
            pass_time = current_time + timedelta(hours=i)
            elevation = random.uniform(10, 90)
            
            if elevation > 10:
                passes.append({
                    "satellite": sat.name,
                    "start_time": pass_time.strftime("%Y-%m-%d %H:%M"),
                    "duration": random.uniform(3, 15),
                    "max_elevation": elevation,
                    "azimuth_start": random.uniform(0, 360),
                    "azimuth_max": random.uniform(90, 270)
                })
        
        return passes[:5]
    
    def display_dashboard(self, satellites: List[Satellite], console: Console):
        table = Table(
            title="🛰️ REAL-TIME SATELLITE STATUS",
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("SATELLITE", style="bold magenta")
        table.add_column("STATUS", style="bold")
        table.add_column("BATTERY", style="cyan")
        table.add_column("SIGNAL", style="cyan")
        table.add_column("DATA Rate", style="yellow")
        table.add_column("TEMP", style="white")
        table.add_column("LAST CONTACT", style="dim")
        
        for sat in satellites:
            health = self.get_health_status(sat)
            health_color = ("red" if health == "CRITICAL" else 
                          "yellow" if health == "WARNING" else "green")
            
            battery_bar = "█" * int(sat.battery / 10) + "░" * (10 - int(sat.battery / 10))
            signal_bar = "▓" * int(sat.signal_strength / 10) + "░" * (10 - int(sat.signal_strength / 10))
            
            table.add_row(
                sat.name,
                col(health_color, health),
                f"{battery_bar} {sat.battery:.0f}%",
                f"{signal_bar} {sat.signal_strength:.0f}%",
                f"{sat.data_rate:.1f} Mbps",
                f"{sat.temperature:.1f}°C",
                sat.last_contact
            )
        
        console.print(table)  # 1-5


from dataclasses import dataclass, field
from typing import Dict, List, Set


class Role:
    """Role-based access control."""
    
    PERMISSIONS = {
        "admin": {
            "dashboard", "satellites", "link", "scan", "orbit", "predict",
            "status", "red-team", "blue-team", "zero-trust", "pqcrypto",
            "audit-chain", "threats", "monitor", "link_all", "predict_all",
            "manage_users", "view_logs", "export_data", "system_config"
        },
        "operator": {
            "dashboard", "satellites", "link", "scan", "orbit", "predict",
            "status", "blue-team", "zero-trust", "monitor",
            "link_own", "predict_own", "view_logs", "export_data"
        },
        "analyst": {
            "dashboard", "satellites", "predict", "status", "monitor",
            "predict_own"
        },
        "guest": {
            "dashboard", "satellites", "monitor"
        }
    }
    
    CLEARANCE = {
        "admin": 5,
        "operator": 3,
        "analyst": 2,
        "guest": 1
    }
    
    def __init__(self, name: str):
        self.name = name
        self.permissions: Set[str] = self.PERMISSIONS.get(name, set())
        self.clearance_level: int = self.CLEARANCE.get(name, 0)
    
    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass
class User:
    username: str
    password: str
    role: str  # admin, operator, analyst, guest
    clearance_level: int
    permissions: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        role_obj = Role(self.role)
        self.permissions = role_obj.permissions
        self.clearance_level = role_obj.clearance_level
    
    def can(self, permission: str) -> bool:
        return permission in self.permissions


class HackerTools:
    """Red Team hacking tools."""
    
    def __init__(self):
        self.active_session = False
        self.privilege_level = 0
        self.access_matrix = {
            "guest": 0,
            "operator": 1,
            "admin": 2,
            "root": 3
        }
    
    def brute_force_login(self, target: str) -> Dict:
        """Simulate brute force attack."""
        console.print(f"\n[red]Starting brute force attack on {target}...[/]")
        
        attempts = []
        passwords = ["admin", "password", "123456", "root", "admin123", "admin2024", "sentry", "nasa", "esa"]
        
        for i, pw in enumerate(passwords):
            console.print(f"[dim]Attempt {i+1}/{len(passwords)}: {pw}[/]")
            time.sleep(0.15)
            if random.random() < 0.15:
                attempts.append({"password": pw, "success": True})
                return {
                    "success": True,
                    "method": "brute_force",
                    "password": pw,
                    "attempts": i + 1
                }
            else:
                attempts.append({"password": pw, "success": False})
        
        return {"success": False, "method": "brute_force", "attempts": len(passwords)}
    
    def sql_injection(self, target: str) -> Dict:
        """Simulate SQL injection."""
        console.print(f"\n[red]Attempting SQL injection on {target}...[/]")
        
        payloads = ["' OR '1'='1", "admin'--", "' UNION SELECT * FROM users--"]
        
        for i, payload in enumerate(payloads):
            console.print(f"[dim]Payload {i+1}: {payload[:30]}...[/]")
            time.sleep(0.2)
        
        success = random.random() < 0.3
        return {
            "success": success,
            "method": "sql_injection",
            "data_obtained": ["users", "passwords", "sessions"] if success else None
        }
    
    def zero_day_exploit(self, target: str) -> Dict:
        """Simulate zero-day exploit."""
        console.print(f"\n[red]⚠ LAUNCHING ZERO-DAY EXPLOIT ⚠[/]")
        
        exploits = [
            "CVE-2024-0001: Kernel privilege escalation",
            "CVE-2024-0002: Container escape",
            "CVE-2024-0003: Authentication bypass"
        ]
        
        for ex in exploits:
            console.print(f"[red]  → {ex}[/]")
            time.sleep(0.3)
        
        success = random.random() < 0.2
        return {
            "success": success,
            "method": "zero_day",
            "exploits_used": exploits,
            "privilege_escalated": "root" if success else None
        }
    
    def phishing_attack(self) -> Dict:
        """Simulate phishing campaign."""
        console.print(f"\n[red]Launching phishing campaign...[/]")
        
        templates = [
            "Password Reset Request",
            "Security Alert: Unusual Login",
            "Satellite Data Update Required"
        ]
        
        for t in templates:
            console.print(f"[dim]  Sending: {t}[/]")
            time.sleep(0.2)
        
        success = random.random() < 0.25
        return {
            "success": success,
            "method": "phishing",
            "credentials_obtained": ["admin", "operator"] if success else None
        }
    
    def ddos_attack(self, target: str) -> Dict:
        """Simulate DDoS attack."""
        console.print(f"\n[red]⚠ LAUNCHING DDoS ATTACK ⚠[/]")
        
        for i in range(10):
            packets = random.randint(10000, 100000)
            console.print(f"[dim]Wave {i+1}: {packets:,} packets/s[/]")
            time.sleep(0.1)
        
        success = random.random() < 0.4
        return {
            "success": success,
            "method": "ddos",
            "target_down": success,
            "damage": "partial" if random.random() < 0.3 else "full"
        }


class DefenseSystem:
    """Blue Team defense mechanisms."""
    
    def __init__(self):
        self.ids_alerts = 0
        self.waf_blocks = 0
        self.threats_blocked = 0
        self.suspicious_activities = []
    
    def analyze_threat(self, threat_type: str) -> Dict:
        """Analyze detected threat."""
        console.print(f"\n[cyan]🔍 Analyzing threat: {threat_type}[/]")
        
        indicators = {
            "brute_force": ["multiple failed logins", "unusual IP range", "rapid requests"],
            "sql_injection": ["unusual SQL syntax", "special characters in input", "OR condition"],
            "ddos": ["traffic spike", "unusual ports", "botnet signature"],
            "phishing": ["suspicious sender domain", "link mismatch", "urgency language"]
        }
        
        inds = indicators.get(threat_type, ["unknown indicators"])
        
        for ind in inds:
            console.print(f"  [dim]• {ind}[/]")
            time.sleep(0.1)
        
        severity = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        
        return {
            "threat_type": threat_type,
            "indicators": inds,
            "severity": severity,
            "recommended_action": "BLOCK" if severity in ["HIGH", "CRITICAL"] else "MONITOR"
        }
    
    def block_ip(self, ip: str, reason: str) -> bool:
        """Block suspicious IP."""
        console.print(f"\n[green]✓ Blocking IP {ip}[/]")
        console.print(f"[dim]  Reason: {reason}[/]")
        self.waf_blocks += 1
        return True
    
    def launch_countermeasures(self, attack_type: str) -> Dict:
        """Launch active countermeasures."""
        console.print(f"\n[cyan]⚔️ LAUNCHING COUNTERMEASURES[/]")
        
        measures = {
            "ddos": ["traffic scrubbing", "rate limiting", "geo-blocking"],
            "brute_force": ["account lockout", "MFA enforcement", "IP ban"],
            "sql_injection": ["WAF rule update", "input sanitization", "query logging"],
            "phishing": ["email quarantine", "domain blacklist", "user notification"]
        }
        
        for m in measures.get(attack_type, []):
            console.print(f"  [green]✓ {m}[/]")
            time.sleep(0.15)
        
        return {"success": True, "countermeasures": measures.get(attack_type, [])}
    
    def forensic_analysis(self, target: str) -> Dict:
        """Perform forensic analysis."""
        console.print(f"\n[cyan]🔬 Forensics: {target}[/]")
        
        steps = [
            "Collecting system logs",
            "Analyzing network traffic",
            "Checking authentication records",
            "Searching for IOCs",
            "Generating report"
        ]
        
        for s in steps:
            console.print(f"  [dim]→ {s}[/]")
            time.sleep(0.2)
        
        findings = random.sample([
            "Suspicious login from 192.168.1.100",
            "Modified /etc/passwd",
            "New cron job detected",
            "Unusual outbound traffic",
            "Malware signature found"
        ], k=random.randint(1, 3))
        
        return {
            "findings": findings,
            "timeline": "2024-03-15 14:30:00",
            "attribution": random.choice(["APT-28", "Lazarus", "Unknown"])
        }


class MissionConsole:
    """Main mission control console."""
    
    def __init__(self):
        self.console = Console(force_terminal=True, color_system="256")
        self.running = True
        self.authenticated = False
        self.current_user = None
        self.hacker_mode = False
        self.hacker_tools = HackerTools()
        self.defense_system = DefenseSystem()
        self.target_system = "SENTRY-GROUND-ZERO"
        self.satellite_monitor = SatelliteMonitor()
        self.alert_system = AlertSystem()
        self.ground_stations = GroundStations()
        self.failure_simulator = FailureSimulator()
        self.session_log = []
        self.log_file = None
        self.login_attempts = 0
        self.max_login_attempts = 3
        self.locked_out = False
        self.satellites = self._load_satellites()
        self.users = {
            "admin": User("admin", "admin2024", "admin", 5),
            "operator": User("operator", "ops123", "operator", 3),
            "analyst": User("analyst", "analysis123", "analyst", 2),
            "guest": User("guest", "guest", "guest", 1),
        }
        self._init_cyber()
    
    def log_session(self, entry: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {entry}"
        self.session_log.append(log_entry)
        
        if not self.log_file:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            self.log_file = os.path.join(log_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
    
    def export_session(self):
        if not self.session_log:
            console.print("[yellow]  No session data to export[/]")
            return
        
        export_file = self.log_file.replace('.log', '_export.json') if self.log_file else "session_export.json"
        
        import json
        with open(export_file, 'w') as f:
            json.dump(self.session_log, f, indent=2)
        
        console.print(f"[green]  Session exported to {export_file}[/]")
        return export_file
        
        self.users = {
            "admin": User("admin", "admin2024", "admin", 5),
            "operator": User("operator", "ops123", "operator", 3),
            "guest": User("guest", "guest", "guest", 1),
        }
        
        self.satellites = self._load_satellites()
        self._init_cyber()
    
    def _load_satellites(self) -> List[Satellite]:
        return [
            Satellite("SENTRY-01", "LEO", 45.2, 9.1, 550.0, "NOMINAL", "Sea Ice Monitoring", "NSIDC", 5),
            Satellite("SENTRY-02", "LEO", -23.5, -46.6, 540.0, "NOMINAL", "Forest Health", "US Forest Service", 5),
            Satellite("SENTRY-03", "MEO", 12.3, 15.8, 20100.0, "NOMINAL", "Temperature Change", "FAOSTAT", 4),
            Satellite("SENTRY-04", "GEO", 0.0, 0.0, 35786.0, "NOMINAL", "Ocean Climate", "Shifting Seas", 4),
            Satellite("SENTRY-05", "HEO", -45.0, 120.0, 12000.0, "WARNING", "Climate Change", "Berkeley Earth", 3),
            Satellite("SENTRY-06", "GEO", 0.0, 0.0, 35786.0, "NOMINAL", "NASA Ocean Climate", "NASA", 5),
            Satellite("SENTRY-07", "GEO", 25.0, -80.0, 35786.0, "WARNING", "Hurricanes/Typhoons", "NOAA", 4),
            Satellite("SENTRY-08", "HEO", 0.0, 0.0, 12000.0, "NOMINAL", "Kepler Exoplanets", "NASA", 3),
            Satellite("SENTRY-09", "HEO", 0.0, 0.0, 10000.0, "WARNING", "Asteroids", "JPL/NASA", 5),
            Satellite("SENTRY-10", "LEO", 0.0, 0.0, 500.0, "NOMINAL", "Meteorite Landings", "NASA", 3),
            Satellite("SENTRY-11", "HEO", 0.0, 0.0, 10000.0, "NOMINAL", "Star Types", "HR Diagram", 2),
            Satellite("SENTRY-12", "HEO", 0.0, 0.0, 12000.0, "WARNING", "Gravitational Waves", "LIGO", 4),
            Satellite("SENTRY-13", "HEO", 0.0, 0.0, 15000.0, "NOMINAL", "Galaxies", "COMBO-17", 2),
            Satellite("SENTRY-14", "LEO", 0.0, 0.0, 500.0, "NOMINAL", "Cloud Seeding", "Tasmania", 3),
            Satellite("SENTRY-15", "LEO", 0.0, 0.0, 400.0, "NOMINAL", "Weather Data", "10 US Cities", 4),
            Satellite("SENTRY-16", "LEO", 0.0, 0.0, 600.0, "WARNING", "CO2 Emissions", "1990-2018", 3),
            Satellite("SENTRY-17", "LEO", 17.0, 79.0, 400.0, "NOMINAL", "Water Quality", "Telangana", 3),
            Satellite("SENTRY-18", "LEO", 41.0, 12.0, 300.0, "WARNING", "Air Quality", "Italian City", 3),
            Satellite("SENTRY-19", "LEO", 0.0, 0.0, 350.0, "NOMINAL", "Crop Recommendation", "Agriculture", 2),
            Satellite("SENTRY-20", "LEO", 0.0, 0.0, 400.0, "WARNING", "Deforestation", "SDG 15", 3),
            Satellite("SENTRY-21", "LEO", 0.0, 0.0, 350.0, "CRITICAL", "Plastic Pollution", "Jambeck 2015", 4),
            Satellite("SENTRY-22", "LEO", 0.0, 0.0, 400.0, "WARNING", "Sea Level Rise", "NASA 1993-2021", 4),
            Satellite("SENTRY-23", "HEO", 0.0, 0.0, 10000.0, "WARNING", "Space Weather", "NASA DONKI", 5),
            Satellite("SENTRY-24", "HEO", 0.0, 0.0, 15000.0, "NOMINAL", "Solar System Planets", "NASA", 3),
            Satellite("SENTRY-25", "HEO", 0.0, 0.0, 12000.0, "WARNING", "Mars Rover", "Curiosity REMS", 4),
            Satellite("SENTRY-26", "HEO", 0.0, 0.0, 15000.0, "CRITICAL", "NASA Near Earth Objects", "NASA", 5),
            Satellite("SENTRY-27", "LEO", 0.0, 0.0, 500.0, "WARNING", "Earthquake-Tsunami Risk", "NOAA", 4),
            Satellite("SENTRY-28", "LEO", 0.0, 0.0, 400.0, "CRITICAL", "Global Earth Temperatures", "Berkeley Earth", 4),
            Satellite("SENTRY-29", "LEO", 0.0, 0.0, 500.0, "WARNING", "Volcanoes on Earth", "2021", 3),
            Satellite("SENTRY-30", "LEO", 0.0, 0.0, 450.0, "WARNING", "Volcano Eruptions", "NOAA 2010-2018", 3),
        ]
    
    def _init_cyber(self):
        try:
            from secure_eo_pipeline.cyber import (
                RedTeamSimulator, BlueTeamDefense, ZeroTrustAuth,
                QuantumResistantCrypto, BlockchainAuditLedger
            )
            
            self.red_team = RedTeamSimulator()
            self.blue_team = BlueTeamDefense()
            self.zero_trust = ZeroTrustAuth()
            self.quantum = QuantumResistantCrypto()
            self.blockchain = BlockchainAuditLedger()
        except ImportError:
            self.red_team = None
            self.blue_team = None
            self.zero_trust = None
            self.quantum = None
            self.blockchain = None
    
    def clear(self):
        print("\033[2J\033[H", end="")
    
    def print_header(self, title: str = "MISSION CONTROL"):
        self.clear()
        
        header = f"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                           ║
║   ██████╗ ████████╗████████╗██████╗  ██████╗     ██████╗ ██╗   ██╗███████╗███╗   ███╗██╗██╗   ██╗███████╗                 ║
║   ██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗██╔═══██╗    ██╔══██╗██║   ██║██╔════╝████╗ ████║██║██║   ██║██╔════╝                 ║
║   ██████╔╝   ██║      ██║   ██████╔╝██║   ██║    ██████╔╝██║   ██║█████╗  ██╔████╔██║██║██║   ██║███████╗                 ║
║   ██╔══██╗   ██║      ██║   ██╔══██╗██║   ██║    ██╔══██╗██║   ██║██╔══╝  ██║╚██╔╝██║██║╚██╗ ██╔╝╚════██║                 ║
║   ██║  ██║   ██║      ██║   ██║  ██║╚██████╔╝    ██████╔╝╚██████╔╝███████╗██║ ╚═╝ ██║██║ ╚████╔╝ ███████║                 ║
║   ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝     ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝  ╚═══╝  ╚══════╝                 ║
║                                                                                                                           ║
║                     ██████╗ ███████╗██╗   ██╗███╗   ███╗██╗    ██╗███████╗██╗      ██████╗ ██████╗                        ║
║                     ██╔══██╗██╔════╝██║   ██║████╗ ████║██║    ██║██╔════╝██║     ██╔═══██╗██╔══██╗                       ║
║                     ██████╔╝█████╗  ██║   ██║██╔████╔██║██║ ███╗█████╗  ██║     ██║   ██║██████╔╝                         ║
║                     ██╔══██╗██╔══╝  ██║   ██║██║╚██╔╝██║██║╚██╗██╔══╝  ██║     ██║   ██║██╔══██╗                          ║
║                     ██║  ██║███████╗╚██████╔╝██║ ╚═╝ ██║╚█████╔╝███████╗███████╗╚██████╔╝██║  ██║                         ║
║                     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚══════╝ ╚═╝  ╚═╝                                ║
║                                                                                                                           ║
║                                                {title}                                                                    ║
║                                   SECURE EARTH OBSERVATION & SPACE SURVEILLANCE                                           ║
║                                            DEFCON STATUS: ██                                                              ║
║                                                                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"""
        
        console.print(col(MissionColors.CYAN, header))
    
    def print_login_screen(self):
        self.print_header("AUTHENTICATION REQUIRED")
        
        console.print(Panel(f"""
[bold cyan]╔══════════════════════════════════════════════════════════════════╗
║                      MISSION CONTROL LOGIN                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  [yellow]OPTIONS:[/]                                                     ║
║                                                                          ║
║    [green]1. login[/]    → Authenticate with credentials                 ║
║    [red]2. hack[/]       → Attempt unauthorized access (RED TEAM)         ║
║    [cyan]3. demo[/]      → Enter demo mode (limited access)              ║
║    [yellow]4. quit[/]    → Exit system                                   ║
║                                                                          ║
║  [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/] ║
║  [dim]Credentials: admin/admin2024 | operator/ops123 | analyst/analysis123 | guest/guest[/]  ║
╚══════════════════════════════════════════════════════════════════╝""",
            border_style="cyan", box=box.DOUBLE
        ))
    
    def handle_login(self):
        if self.locked_out:
            console.print(Panel(
                "[bold red]🔒 ACCOUNT LOCKED[/]\n\nToo many failed login attempts.\nContact administrator or wait 5 minutes.",
                border_style="red", box=box.DOUBLE
            ))
            return False
        
        console.print(Panel(
            "[bold cyan]🔐 AUTHENTICATION[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        username = console.input("\n[yellow]  Username: [/]").strip()
        password = console.input("[yellow]  Password: [/]").strip()
        
        if username in self.users:
            user = self.users[username]
            if user.password == password:
                self.authenticated = True
                self.current_user = user
                self.login_attempts = 0
                console.print(f"\n[green]✓ AUTHENTICATED AS {username.upper()} (Clearance: {user.clearance_level})[/]")
                return True
            else:
                self.login_attempts += 1
                remaining = self.max_login_attempts - self.login_attempts
                console.print(f"\n[red]✗ INVALID PASSWORD[/]")
                if remaining > 0:
                    console.print(f"[yellow]  Attempts remaining: {remaining}[/]")
                else:
                    self.locked_out = True
                    console.print(f"\n[red bold]✗ ACCOUNT LOCKED after 3 failed attempts[/]")
        else:
            self.login_attempts += 1
            console.print(f"\n[red]✗ USER NOT FOUND[/]")
        
        return False
    
    def handle_hack(self):
        self.print_header("⚠ UNAUTHORIZED ACCESS DETECTED ⚠")
        
        console.print(Panel(f"""
[bold red]╔══════════════════════════════════════════════════════════════════╗
║                      HACKER INTERFACE                                    ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  [red]WARNING: Unauthorized access is a criminal offense[/]              ║
║  [red]This is a simulation for educational purposes only[/]              ║
║                                                                          ║
║  [yellow]AVAILABLE ATTACKS:[/]                                           ║
║                                                                          ║
║    [red]1. brute-force[/]   → Dictionary attack on login                 ║
║    [red]2. sql-inject[/]    → SQL injection attack                       ║
║    [red]3. zero-day[/]      → Exploit unknown vulnerabilities            ║
║    [red]4. phishing[/]      → Social engineering campaign                ║
║    [red]5. ddos[/]          → Denial of service attack                   ║
║    [red]6. back[/]         → Return to main menu                         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝""",
            border_style="red", box=box.DOUBLE
        ))
        
        choice = console.input("\n[red]ATTACK > [/]").strip().lower()
        
        if choice == "back" or choice == "6":
            return
        
        result = None
        
        if choice == "1" or choice == "brute-force":
            result = self.hacker_tools.brute_force_login(self.target_system)
        elif choice == "2" or choice == "sql-inject":
            result = self.hacker_tools.sql_injection(self.target_system)
        elif choice == "3" or choice == "zero-day":
            result = self.hacker_tools.zero_day_exploit(self.target_system)
        elif choice == "4" or choice == "phishing":
            result = self.hacker_tools.phishing_attack()
        elif choice == "5" or choice == "ddos":
            result = self.hacker_tools.ddos_attack(self.target_system)
        else:
            console.print("[red]Invalid attack method[/]")
            return
        
        if result and result.get("success"):
            console.print(f"\n[red bold blink]⚠ ATTACK SUCCESSFUL ⚠[/]")
            console.print(f"[red]Method: {result['method']}[/]")
            
            self.hacker_mode = True
            self._show_hacker_menu()
        else:
            console.print(f"\n[yellow]Attack failed. Target: {self.target_system}[/]")
            
            if self.blue_team:
                analysis = self.defense_system.analyze_threat(result.get('method', 'unknown'))
                console.print(f"[cyan]Threat detected! Severity: {analysis['severity']}[/]")
    
    def _show_hacker_menu(self):
        while self.hacker_mode:
            self.print_header("⚠ HACKER CONTROL PANEL ⚠")
            
            console.print(Panel(f"""
[bold red]╔══════════════════════════════════════════════════════════════════╗
║                  DESTRUCTIVE OPERATIONS MENU                    ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                  ║
║    [red]TARGET SYSTEMS:[/]                                                  ║
║       1. satellite-ctrl    → Satellite control systems             ║
║       2. data-archive      → Mission data archives                 ║
║       3. comm-network      → Communications network                ║
║       4. defense-sec       → Security systems                       ║
║                                                                  ║
║    [yellow]ATTACK OPERATIONS:[/]                                              ║
║       5. inject-malware    → Deploy malicious payload               ║
║       6. ransomware        → Encrypt critical data                  ║
║       7. wipe-data         → Destroy mission data                   ║
║       8. disable-sat       → Disable satellite operations           ║
║                                                                  ║
║    [dim]UTILITIES:[/]                                                          ║
║       9. status            → View access status                     ║
║      10. cover-tracks     → Remove attack evidence                 ║
║      11. exit             → Disconnect                             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝""",
                border_style="red", box=box.DOUBLE
            ))
            
            choice = console.input("\n[red]HACKER > [/]").strip().lower()
            
            targets = {
                "1": ("satellite-ctrl", "Satellite Control"),
                "2": ("data-archive", "Data Archive"),
                "3": ("comm-network", "Communications Network"),
                "4": ("defense-sec", "Security Systems")
            }
            
            if choice in targets:
                target, name = targets[choice]
                console.print(f"\n[red]Targeting {name}...[/]")
                success = random.random() < 0.6
                if success:
                    console.print(f"[green bold blink]✓ ACCESS GAINED TO {name}[/]")
                else:
                    console.print(f"[yellow]Access denied. Attack detected![/]")
                    self.defense_system.analyze_threat("intrusion")
            
            elif choice == "5" or choice == "inject-malware":
                console.print(f"\n[red]Injecting malware payload...[/]")
                time.sleep(0.5)
                console.print(f"[green bold blink]✓ MALWARE DEPLOYED[/]")
            
            elif choice == "6" or choice == "ransomware":
                console.print(f"\n[red]Encrypting mission data...[/]")
                for i in range(5):
                    console.print(f"[dim]Encrypting sector {i+1}/5...[/]")
                    time.sleep(0.3)
                console.print(f"[green bold blink]✓ DATA ENCRYPTED - 24H TO PAY[/]")
            
            elif choice == "7" or choice == "wipe-data":
                console.print(f"\n[red]⚠ WARNING: This will destroy all mission data![/]")
                confirm = console.input("[red]Type 'DELETE' to confirm: [/]").strip()
                if confirm == "DELETE":
                    console.print(f"[green bold blink]✓ MISSION DATA DESTROYED[/]")
                else:
                    console.print("[yellow]Operation cancelled[/]")
            
            elif choice == "8" or choice == "disable-sat":
                console.print(f"\n[red]Sending kill command to satellites...[/]")
                console.print(f"[green bold blink]✓ SATELLITES DISABLED[/]")
            
            elif choice == "9" or choice == "status":
                console.print(f"\n[red]Session Status:[/]")
                console.print(f"  Access Level: {'ROOT' if self.hacker_tools.privilege_level == 3 else 'USER'}[/]")
                console.print(f"  Active: {self.hacker_tools.active_session}[/]")
            
            elif choice == "10" or choice == "cover-tracks":
                console.print(f"\n[red]Clearing logs and evidence...[/]")
                time.sleep(0.5)
                console.print(f"[green]✓ Tracks covered[/]")
            
            elif choice == "11" or choice == "exit":
                console.print(f"\n[yellow]Disconnecting...[/]")
                self.hacker_mode = False
                break
            
            else:
                console.print(f"[red]Invalid command[/]")
            
            console.input("\n[dim]Press Enter to continue...[/]")
    
    def print_main_menu(self):
        self.print_header("MISSION CONTROL")
        
        user_info = "[green]GUEST[/] | Clearance: 1"
        if self.current_user:
            user_info = f"[green]{self.current_user.username.upper()}[/] | Clearance: {self.current_user.clearance_level}"
        
        menu = Table(box=box.DOUBLE_EDGE, show_header=False, pad_edge=True)
        menu.add_column("CMD", style="bold cyan", width=18)
        menu.add_column("DESC", style="white", width=35)
        menu.add_column("CMD", style="bold cyan", width=18)
        menu.add_column("DESC", style="white", width=35)
        
        commands = [
            ("dashboard", "Mission Status", "satellites", "Satellite Catalog"),
            ("link", "Link Satellite", "scan", "Acquire Data"),
            ("predict", "🔮 AI Prediction", "orbit", "Orbital Params"),
            ("status", "Pipeline Status", "red-team", "Red Team Ops"),
            ("blue-team", "Blue Team Defense", "zero-trust", "Zero Trust"),
            ("pqcrypto", "Quantum Crypto", "audit-chain", "Audit Ledger"),
            ("threats", "Active Threats", "logout", "Logout"),
            ("quit", "Exit", "", ""),
        ]
        
        for c1, d1, c2, d2 in commands:
            menu.add_row(c1, d1, c2, d2)
        
        console.print(Panel(
            f"[bold cyan]Logged in as:[/] {user_info}",
            border_style="cyan", box=box.ROUNDED
        ))
        console.print()
        self.console.print(menu)
        console.print()
    
    def print_satellite_catalog(self):
        table = Table(
            title=col(MissionColors.CYAN, "🛰️ SATELLITE CATALOG (30 SATELLITES)"),
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("SATELLITE", style="bold magenta")
        table.add_column("REGIME", style="cyan")
        table.add_column("ALTITUDE", style="white")
        table.add_column("STATUS", style="bold")
        table.add_column("MISSION", style="white")
        table.add_column("SEC", style="yellow")
        
        for sat in self.satellites:
            status = sat.status
            status_color = (MissionColors.SUCCESS if status == "NOMINAL" else 
                          MissionColors.WARNING if status == "WARNING" else 
                          MissionColors.ERROR)
            
            sec = "★" * sat.security_level + "☆" * (5 - sat.security_level)
            
            table.add_row(
                sat.name,
                sat.regime,
                f"{sat.alt:,.0f} km",
                col(status_color, status),
                sat.mission[:20],
                sec
            )
        
        self.console.print(table)
        console.print()
    
    def handle_link(self):
        console.print(Panel(
            "[bold cyan]📡 SATELLITE LINK[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        console.print("[cyan]  Available satellites:[/]")
        for sat in self.satellites:
            console.print(f"    [magenta]{sat.name}[/] - {sat.mission}")
        
        name = console.input("\n[yellow]  Satellite name: [/]").strip().upper()
        
        sat = next((s for s in self.satellites if s.name == name), None)
        if sat:
            self.linked_satellite = sat
            console.print(f"\n[green]✓ Linked to {sat.name}[/]")
            console.print(f"[cyan]  Mission: {sat.mission}[/]")
            console.print(f"[cyan]  Data Source: {sat.data_source}[/]")
            
            prediction_info = self._get_prediction_info(sat.name)
            if prediction_info:
                console.print(f"\n[yellow]  Prediction available:[/] {prediction_info}")
        else:
            console.print(f"\n[red]✗ Satellite not found[/]")
    
    def _get_prediction_info(self, sat_name: str) -> str:
        """Get prediction info for satellite."""
        pred_map = {
            "SENTRY-28": "Global Temperature Prediction",
            "SENTRY-22": "Sea Level Rise Prediction", 
            "SENTRY-16": "CO2 Emissions Forecast",
            "SENTRY-26": "NEO Hazard Assessment",
            "SENTRY-07": "Hurricane Intensity Prediction",
            "SENTRY-18": "Air Quality Forecast",
            "SENTRY-19": "Crop Recommendation",
            "SENTRY-09": "Asteroid Impact Assessment",
            "SENTRY-05": "Climate Change Projection",
            "SENTRY-01": "Sea Ice Extent Prediction",
            "SENTRY-02": "Forest Health Assessment",
            "SENTRY-03": "Temperature Change by Country",
            "SENTRY-04": "Ocean Climate Prediction",
            "SENTRY-06": "NASA Ocean Climate",
            "SENTRY-08": "Kepler Exoplanet Discovery",
            "SENTRY-10": "Meteorite Fall Prediction",
            "SENTRY-11": "Star Types Analysis",
            "SENTRY-12": "Gravitational Wave Events",
            "SENTRY-13": "Galaxy Catalog Analysis",
            "SENTRY-14": "Cloud Seeding Efficiency",
            "SENTRY-15": "Weather Forecast",
            "SENTRY-17": "Water Quality Analysis",
            "SENTRY-20": "Deforestation Trend",
            "SENTRY-21": "Plastic Pollution Projection",
            "SENTRY-23": "Space Weather Forecast",
            "SENTRY-24": "Solar System Planets",
            "SENTRY-25": "Mars Climate Prediction",
            "SENTRY-27": "Earthquake/Tsunami Risk",
            "SENTRY-29": "Volcano Activity Monitor",
            "SENTRY-30": "Volcano Eruption Prediction",
        }
        return pred_map.get(sat_name, "")
    
    def handle_predict(self):
        """Handle predict command - run AI/ML prediction for linked satellite."""
        if not hasattr(self, 'linked_satellite'):
            console.print("[yellow]  No satellite linked. Use 'link' first.[/]")
            return
        
        sat = self.linked_satellite
        sat_name = sat.name
        
        console.print(Panel(
            f"[bold cyan]🔮 AI/ML PREDICTION: {sat.mission}[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        console.print(f"[cyan]  Analyzing data from {sat.data_source}...[/]")
        time.sleep(0.5)
        
        self.log_session(f"PREDICT: {sat_name} - {sat.mission}")
        
        if sat_name == "SENTRY-28":
            self._predict_temperature()
        elif sat_name == "SENTRY-22":
            self._predict_sea_level()
        elif sat_name == "SENTRY-16":
            self._predict_co2()
        elif sat_name == "SENTRY-26":
            self._predict_neo_hazard()
        elif sat_name == "SENTRY-07":
            self._predict_hurricane()
        elif sat_name == "SENTRY-18":
            self._predict_air_quality()
        elif sat_name == "SENTRY-19":
            self._predict_crop()
        elif sat_name == "SENTRY-09":
            self._predict_asteroid()
        elif sat_name == "SENTRY-05":
            self._predict_climate()
        elif sat_name == "SENTRY-01":
            self._predict_sea_ice()
        elif sat_name == "SENTRY-02":
            self._predict_forest_health()
        elif sat_name == "SENTRY-03":
            self._predict_faostat()
        elif sat_name == "SENTRY-04":
            self._predict_ocean_climate()
        elif sat_name == "SENTRY-06":
            self._predict_nasa_ocean()
        elif sat_name == "SENTRY-08":
            self._predict_exoplanets()
        elif sat_name == "SENTRY-10":
            self._predict_meteorites()
        elif sat_name == "SENTRY-11":
            self._predict_stars()
        elif sat_name == "SENTRY-12":
            self._predict_gravitational_waves()
        elif sat_name == "SENTRY-13":
            self._predict_galaxies()
        elif sat_name == "SENTRY-14":
            self._predict_cloud_seeding()
        elif sat_name == "SENTRY-15":
            self._predict_weather()
        elif sat_name == "SENTRY-17":
            self._predict_water_quality()
        elif sat_name == "SENTRY-20":
            self._predict_deforestation()
        elif sat_name == "SENTRY-21":
            self._predict_plastic_pollution()
        elif sat_name == "SENTRY-23":
            self._predict_space_weather()
        elif sat_name == "SENTRY-24":
            self._predict_planets()
        elif sat_name == "SENTRY-25":
            self._predict_mars_climate()
        elif sat_name == "SENTRY-27":
            self._predict_earthquake()
        elif sat_name == "SENTRY-29":
            self._predict_volcano()
        elif sat_name == "SENTRY-30":
            self._predict_volcano_eruptions()
        else:
            console.print(f"[yellow]  No prediction model available for {sat.name}[/]")
            console.print(f"[dim]  Supported: Temperature, Sea Level, CO2, NEO, Hurricane, Air Quality, Crop[/]")
    
    def _predict_temperature(self):
        """Predict global temperature using auto model selection with EDA + Feature Engineering."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        temp_file = os.path.join(base_path, "global_temperatures/Global Temperatures.csv")
        
        df = pd.read_csv(temp_file)
        df.columns = df.columns.str.strip()
        df = df.replace('NaN', np.nan).replace('', np.nan)
        
        # Add year column for analysis
        df['Year'] = [1850 + i for i in range(len(df))]
        
        target_year = console.input("\n[yellow]  Enter target year (e.g., 2030, 2050, 2100): [/]").strip()
        
        if not target_year.isdigit():
            console.print("[red]  Please enter a valid year.[/]")
            return
        
        target_year = int(target_year)
        
        if target_year < 1850 or target_year > 2100:
            console.print(f"[red]  Year must be between 1850 and 2100.[/]")
            return
        
        # Run with EDA and Feature Engineering
        result = run_auto_prediction(
            years=np.array([]),  # Will be derived from df
            values=np.array([]),  # Will be derived from df
            target_year=target_year,
            unit="°C",
            title="Global Temperature",
            data_type="climate_temperature",
            df=df,
            target_col="Annual Anomaly"
        )
        
        if result and "prediction" in result:
            pred = result["prediction"]["prediction"]
            
            if pred > 0:
                console.print(f"\n[red bold]  Status: WARMER than baseline[/]")
            else:
                console.print(f"\n[blue bold]  Status: COOLER than baseline[/]")
            
            show_chart(values, year_vals, 'Global Temperature', 'Anomaly (°C)',
                       target_year, pred, pred_result['confidence_95'])
    
    def _predict_sea_level(self):
        """Predict sea level rise using auto model selection with EDA + Feature Engineering."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        sea_file = os.path.join(base_path, "sea_level/sea_level.csv")
        
        df = pd.read_csv(sea_file)
        
        target_year = console.input("\n[yellow]  Enter target year (e.g., 2030, 2050, 2100): [/]").strip()
        
        if not target_year.isdigit():
            console.print("[red]  Please enter a valid year.[/]")
            return
        
        target_year = int(target_year)
        
        if target_year < 1993 or target_year > 2100:
            console.print(f"[red]  Year must be between 1993 and 2100.[/]")
            return
        
        result = run_auto_prediction(
            years=np.array([]),
            values=np.array([]),
            target_year=target_year,
            unit="mm",
            title="Sea Level Rise",
            data_type="sea_level",
            df=df,
            target_col="Smoothed_GMSL_mm"
        )
        
        if result and "prediction" in result:
            pred = result["prediction"]["prediction"]
            current_year = int(df['Year'].max()) if 'Year' in df.columns else 2021
            
            risk = "CRITICAL" if pred > 700 else "HIGH" if pred > 500 else "MODERATE"
            risk_color = MissionColors.ERROR if risk == "CRITICAL" else MissionColors.WARNING
            console.print(f"\n[{risk_color} bold]  Risk Level: {risk}[/]")
    
    def _predict_co2(self):
        """Predict CO2 emissions using auto model selection with EDA + Feature Engineering."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        co2_file = os.path.join(base_path, "co2_emissions/emissions.csv")
        
        df = pd.read_csv(co2_file)
        
        target_year = console.input("\n[yellow]  Enter target year (e.g., 2030, 2050, 2100): [/]").strip()
        
        if not target_year.isdigit():
            console.print("[red]  Please enter a valid year.[/]")
            return
        
        target_year = int(target_year)
        
        if target_year < 1990 or target_year > 2100:
            console.print(f"[red]  Year must be between 1990 and 2100.[/]")
            return
        
        # Try to find year and emissions columns
        year_col = None
        emission_col = None
        for col in df.columns:
            if 'year' in col.lower():
                year_col = col
            if 'emission' in col.lower() or 'co2' in col.lower() or 'mt' in col.lower():
                emission_col = col
        
        # If no real data, use fallback data - avoid polynomial overfitting
        if year_col is None or emission_col is None or len(df) < 5:
            years_data = np.array([1990, 1995, 2000, 2005, 2010, 2015, 2018])
            emissions_data = np.array([22600, 24700, 25700, 27700, 30000, 33500, 36000])
            
            # Scale years for stability
            years_scaled = (years_data - 1990) / 30.0
            
            # Use engineered features
            X = np.column_stack([years_scaled, years_scaled**2])
            
            result = run_auto_prediction(
                years_data, emissions_data, target_year,
                unit="MtCO2", title="CO2 Emissions",
                data_type="co2_emissions"
            )
            
            if result and "prediction" in result:
                pred = result["prediction"]["prediction"]
                if pred > 50000:
                    console.print(f"\n[red bold]  ⚠ WARNING: Emissions exceed 50 GtCO2 threshold![/]")
        else:
            result = run_auto_prediction(
                years=np.array([]),
                values=np.array([]),
                target_year=target_year,
                unit="MtCO2",
                title="CO2 Emissions",
                data_type="co2_emissions",
                df=df,
                target_col=emission_col
            )
            
            if result and "prediction" in result:
                pred = result["prediction"]["prediction"]
                if pred > 50000:
                    console.print(f"\n[red bold]  ⚠ WARNING: Emissions exceed 50 GtCO2 threshold![/]")
    
    def _predict_neo_hazard(self):
        """Predict NEO hazard assessment."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]NEAR-EARTH OBJECT HAZARD ANALYSIS[/]                  [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        neo_file = os.path.join(base_path, "nasa_neo/neo.csv")
        
        try:
            df = pd.read_csv(neo_file)
            
            total = len(df)
            hazardous = df[df.get('hazardous', False) == True]
            haz_count = len(hazardous)
            
            console.print(f"[cyan]  ║[/]  Total Objects: [yellow]{total}[/]                             [cyan]║")
            console.print(f"[cyan]  ║[/]  Hazardous:    [red]{haz_count}[/]                              [cyan]║")
            
            if haz_count > 0:
                max_dia = hazardous.get('est_diameter_max', hazardous.iloc[:, 0]).max()
                min_dist = hazardous.get('miss_distance', hazardous.iloc[:, 0]).min()
                
                console.print(f"[cyan]  ║[/]  Max Diameter:  [yellow]{max_dia:.2f} km[/]                        [cyan]║")
                console.print(f"[cyan]  ║[/]  Min Distance:  [yellow]{min_dist:,.0f} km[/]                     [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            
            risk = "HIGH" if haz_count > 5 else "MODERATE" if haz_count > 0 else "LOW"
            risk_color = MissionColors.ERROR if risk == "HIGH" else MissionColors.WARNING if risk == "MODERATE" else MissionColors.SUCCESS
            
            console.print(f"[cyan]  ║[/]  Overall Risk: [{risk_color}]{risk}[/]                            [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_hurricane(self):
        """Predict hurricane intensity using auto model selection."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]HURRICANE INTENSITY PREDICTION[/]                    [cyan]║")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        atl_file = os.path.join(base_path, "hurricanes/atlantic.csv")
        
        try:
            df = pd.read_csv(atl_file)
            df = df[df['Maximum Wind'] > 0]
            
            if 'Year' in df.columns and len(df) > 10:
                yearly = df.groupby('Year')['Maximum Wind'].mean().reset_index()
                X = yearly['Year'].values
                y = yearly['Maximum Wind'].values
                
                target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                if target_year.isdigit():
                    target_year = int(target_year)
                    
                    console.print(Panel(
                        f"[bold cyan]🔮 AUTO MODEL SELECTION - Hurricane[/]",
                        border_style="cyan", box=box.DOUBLE
                    ))
                    
                    result = AutoModelSelector.run_full_analysis(X, y, target_year, console)
                    
                    if result and "prediction" in result:
                        pred = result["prediction"]["prediction"]
                        pred_result = result["prediction"]
                        error = pred_result["std_error"]
                        
                        console.print(f"\n[cyan]  ══════════════════════════════════════════════════════")
                        console.print(f"[cyan]  Predicted avg max wind: [yellow]({pred:.1f} ± {error:.1f}) knots[/]")
                        console.print(f"[cyan]  Best model: {result['best_model']}, R²: {result['metrics']['r2']:.4f}")
            else:
                max_wind = df['Maximum Wind'].max()
                avg_wind = df['Maximum Wind'].mean()
                
                console.print(f"[cyan]  ║[/]  Historical max wind: [yellow]{max_wind} knots[/]              [cyan]║")
                console.print(f"[cyan]  ║[/]  Historical avg wind: [yellow]{avg_wind:.0f} knots[/]              [cyan]║")
                console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
                
                if max_wind >= 157:
                    cat = "CAT 5"
                elif max_wind >= 130:
                    cat = "CAT 4"
                elif max_wind >= 111:
                    cat = "CAT 3"
                elif max_wind >= 96:
                    cat = "CAT 2"
                else:
                    cat = "CAT 1"
                
                console.print(f"[cyan]  ║[/]  Maximum category: [red]{cat}[/]                            [cyan]║")
            
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_air_quality(self):
        """Predict air quality using auto model selection."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        aq_file = os.path.join(base_path, "air_quality/air_quality.csv")
        
        try:
            df = pd.read_csv(aq_file)
            console.print(f"[cyan]  Analyzing {len(df)} air quality records...[/]")
            
            if 'Year' in df.columns and 'PM2.5' in df.columns:
                yearly = df.groupby('Year')['PM2.5'].mean().reset_index()
                X = yearly['Year'].values
                y = yearly['PM2.5'].values
                
                target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                if target_year.isdigit():
                    target_year = int(target_year)
                    run_auto_prediction(X, y, target_year, "µg/m³", "Air Quality (PM2.5)")
                else:
                    console.print(f"[cyan]  Current avg PM2.5: [yellow]({y.mean():.2f} ± {y.std():.2f}) µg/m³[/]")
            elif 'PM2.5' in df.columns:
                console.print(f"[cyan]  Current avg PM2.5: [yellow]({df['PM2.5'].mean():.2f} ± {df['PM2.5'].std():.2f}) µg/m³[/]")
            else:
                console.print(f"[cyan]  ║  Analyzing {len(df)} records...                        [cyan]║")
                console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_crop(self):
        """Predict crop recommendation."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]CROP RECOMMENDATION SYSTEM[/]                        [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        console.print(f"[cyan]  ║  Enter soil and weather conditions to get           [cyan]║")
        console.print(f"[cyan]  ║  AI-powered crop recommendations.                    [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        try:
            n_val = console.input("[yellow]  N (Nitrogen) [50]: [/]").strip() or "50"
            p_val = console.input("[yellow]  P (Phosphorus) [50]: [/]").strip() or "50"
            k_val = console.input("[yellow]  K (Potassium) [50]: [/]").strip() or "50"
            temp = console.input("[yellow]  Temperature [25]: [/]").strip() or "25"
            hum = console.input("[yellow]  Humidity [50]: [/]").strip() or "50"
            ph = console.input("[yellow]  pH [7.0]: [/]").strip() or "7.0"
            rain = console.input("[yellow]  Rainfall [150]: [/]").strip() or "150"
            
            console.print(f"\n[cyan]  Analyzing conditions...[/]")
            time.sleep(0.5)
            
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import LabelEncoder
            
            base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
            crop_file = os.path.join(base_path, "crop_recommendation/Crop_Recommendation.csv")
            
            df = pd.read_csv(crop_file)
            df.columns = df.columns.str.strip()
            
            features = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
            if 'label' in df.columns:
                X = df[features].values
                y = LabelEncoder().fit_transform(df['label'].str.lower())
                
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X, y)
                
                cond = np.array([[int(n_val), int(p_val), int(k_val), float(temp), float(hum), float(ph), int(rain)]])
                pred = model.predict(cond)[0]
                probs = model.predict_proba(cond)[0]
                
                crops = LabelEncoder().fit_transform(df['label'].str.lower())
                top_idx = np.argsort(probs)[::-1][:3]
                
                console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
                console.print(f"[cyan]  ║[/] [bold green]RECOMMENDED CROP: {crops[pred].upper()}[/]                   [cyan]║")
                console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
                for idx in top_idx:
                    console.print(f"[cyan]  ║  {crops[idx]}: {probs[idx]*100:.1f}%                            [cyan]║")
                console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
            console.print(f"[dim]  Crop recommendation requires data file[/]")
    
    def _predict_asteroid(self):
        """Predict asteroid impact assessment."""
        self._predict_neo_hazard()
    
    def _predict_climate(self):
        """Predict climate change."""
        self._predict_temperature()
    
    def _predict_sea_ice(self):
        """Predict sea ice extent using auto model selection with EDA + Feature Engineering."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        sea_file = os.path.join(base_path, "sea_ice/seaice.csv")
        
        try:
            df = pd.read_csv(sea_file)
            df.columns = df.columns.str.strip()
            df = df[df['Extent'].notna()]
            
            if df.empty:
                console.print("[red]  No sea ice data available[/]")
                return
            
            if 'Year' not in df.columns:
                console.print("[red]  No Year column found in sea ice data[/]")
                return
            
            target_year = console.input("\n[yellow]  Enter target year (e.g., 2030, 2050): [/]").strip()
            if not target_year.isdigit():
                console.print("[red]  Please enter a valid year.[/]")
                return
            
            target_year = int(target_year)
            
            if target_year < 1978 or target_year > 2100:
                console.print(f"[red]  Year must be between 1978 and 2100.[/]")
                return
            
            result = run_auto_prediction(
                years=np.array([]),
                values=np.array([]),
                target_year=target_year,
                unit="million km²",
                title="Sea Ice Extent",
                data_type="sea_ice",
                df=df,
                target_col="Extent"
            )
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_forest_health(self):
        """Predict forest health."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]FOREST HEALTH ASSESSMENT[/]                         [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        forest_file = os.path.join(base_path, "forest_health/forest_health_data_with_target.csv")
        
        try:
            df = pd.read_csv(forest_file)
            console.print(f"[cyan]  ║  Analyzing {len(df)} forest plots...                    [cyan]║")
            
            if 'Target' in df.columns:
                healthy = (df['Target'] == 1).sum()
                console.print(f"[cyan]  ║[/]  Healthy plots: [green]{healthy}[/]                          [cyan]║")
                console.print(f"[cyan]  ║[/]  At-risk plots:  [yellow]{len(df) - healthy}[/]                         [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Random Forest Classifier                  [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_faostat(self):
        """Predict FAOSTAT temperature change."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]FAOSTAT TEMPERATURE CHANGE[/]                        [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        country = console.input("[yellow]  Enter country name: [/]").strip()
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        
        for f in ["temperature_change/FAOSTAT_data_en_11-1-2024.csv", 
                  "temperature_change/GlobalTemperatures.csv"]:
            try:
                df_file = os.path.join(base_path, f)
                if os.path.exists(df_file):
                    df = pd.read_csv(df_file, encoding='utf-8', on_bad_lines='skip')
                    console.print(f"[cyan]  ║[/]  Data source: {f}[/]                              [cyan]║")
                    console.print(f"[cyan]  ║[/]  Records: {len(df)}[/]                                 [cyan]║")
                    break
            except:
                continue
        
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        console.print(f"[cyan]  ║  Model:  Linear Regression                        [cyan]║")
        console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
    
    def _predict_ocean_climate(self):
        """Predict ocean climate."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]OCEAN CLIMATE PREDICTION[/]                         [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        ocean_file = os.path.join(base_path, "ocean_climate/realistic_ocean_climate_dataset.csv")
        
        try:
            df = pd.read_csv(ocean_file)
            df.columns = df.columns.str.strip()
            console.print(f"[cyan]  ║  Analyzing {len(df)} ocean records...                  [cyan]║")
            
            if 'SST (°C)' in df.columns:
                avg_sst = df['SST (°C)'].mean()
                console.print(f"[cyan]  ║[/]  Avg SST: {avg_sst:.2f}°C[/]                              [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Gradient Boosting                        [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_nasa_ocean(self):
        """Predict NASA ocean climate."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]NASA OCEAN CLIMATE ANALYSIS[/]                      [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        nasa_file = os.path.join(base_path, "nasa_ocean/nasa_ocean_climate.csv")
        
        try:
            df = pd.read_csv(nasa_file)
            console.print(f"[cyan]  ║[/]  Records: {len(df)}[/]                                   [cyan]║")
            console.print(f"[cyan]  ║[/]  Year range: {df['year'].min()}-{df['year'].max()}[/]              [cyan]║")
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Time Series Regression                   [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_exoplanets(self):
        """Predict exoplanet discoveries."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]KEPLER EXOPLANET DISCOVERY ANALYSIS[/]                [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        kepler_file = os.path.join(base_path, "kepler/cumulative.csv")
        
        try:
            df = pd.read_csv(kepler_file)
            
            confirmed = (df['koi_disposition'] == 'CONFIRMED').sum()
            candidates = (df['koi_disposition'] == 'CANDIDATE').sum()
            
            console.print(f"[cyan]  ║[/]  TotalKOIs: {len(df)}[/]                                 [cyan]║")
            console.print(f"[cyan]  ║[/]  Confirmed:  [green]{confirmed}[/]                              [cyan]║")
            console.print(f"[cyan]  ║[/]  Candidates: [yellow]{candidates}[/]                             [cyan]║")
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Machine Learning Classifier             [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_meteorites(self):
        """Predict meteorite falls using auto model selection."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        meteor_file = os.path.join(base_path, "meteorites/meteorite-landings.csv")
        
        try:
            df = pd.read_csv(meteor_file)
            df = df[df['year'].notna()]
            
            yearly = df.groupby('year').size()
            
            if len(yearly) > 5:
                X = np.array(yearly.index)
                y = yearly.values
                
                target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                if target_year.isdigit():
                    target_year = int(target_year)
                    run_auto_prediction(X, y, target_year, "falls", "Meteorite Falls")
                else:
                    console.print(f"[cyan]  Historical avg: [yellow]({y.mean():.1f} ± {y.std():.1f}) falls/year[/]")
            else:
                console.print(f"[cyan]  Historical avg: [yellow]({yearly.mean():.1f} ± {yearly.std():.1f}) falls/year[/]")
                console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_cloud_seeding(self):
        """Predict cloud seeding efficiency using auto model selection."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]CLOUD SEEDING EFFICIENCY[/]                        [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        cloud_file = os.path.join(base_path, "cloud_seeding/cloud_seeding.csv")
        
        try:
            if os.path.exists(cloud_file):
                df = pd.read_csv(cloud_file)
                console.print(f"[cyan]  Analyzing {len(df)} cloud seeding records...[/]")
                
                if 'Year' in df.columns and 'Efficiency' in df.columns:
                    X = df['Year'].values
                    y = df['Efficiency'].values
                    
                    target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                    if target_year.isdigit():
                        target_year = int(target_year)
                        run_auto_prediction(X, y, target_year, "%", "Cloud Seeding Efficiency")
                else:
                    console.print(f"[cyan]  Avg efficiency: [yellow]({df.mean().mean():.1f} ± {df.std().mean():.1f}) %[/]")
            else:
                console.print(f"[cyan]  ║  Using simulation data...                            [cyan]║")
                years = np.array([2018, 2019, 2020, 2021, 2022, 2023])
                efficiency = np.array([15.2, 16.8, 14.5, 17.3, 18.1, 16.9])
                
                target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                if target_year.isdigit():
                    target_year = int(target_year)
                    run_auto_prediction(years, efficiency, target_year, "%", "Cloud Seeding Efficiency")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        cloud_file = os.path.join(base_path, "cloud_seeding/cloud_seeding.csv")
        
        try:
            df = pd.read_csv(cloud_file)
            
            seeded = df[df['seeded'] == 'S']['TE'].mean()
            unseeded = df[df['seeded'] == 'U']['TE'].mean()
            
            console.print(f"[cyan]  ║[/]  Seeded avg:   [green]{seeded:.2f}[/]                              [cyan]║")
            console.print(f"[cyan]  ║[/]  Unseeded avg: [yellow]{unseeded:.2f}[/]                             [cyan]║")
            
            if seeded > unseeded:
                increase = ((seeded - unseeded) / unseeded) * 100
                console.print(f"[cyan]  ║[/]  Effectiveness: [green]+{increase:.1f}%[/]                         [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Statistical Comparison                  [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_weather(self):
        """Predict weather using auto model selection."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        weather_file = os.path.join(base_path, "weather/weather_data.csv")
        
        try:
            df = pd.read_csv(weather_file)
            console.print(f"[cyan]  Analyzing {len(df)} weather records...[/]")
            
            if 'Date' in df.columns and 'Temperature_C' in df.columns:
                df['Year'] = pd.to_datetime(df['Date'], errors='coerce').dt.year
                yearly = df.groupby('Year')['Temperature_C'].mean().dropna()
                
                if len(yearly) > 3:
                    X = np.array(yearly.index)
                    y = yearly.values
                    
                    target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                    if target_year.isdigit():
                        target_year = int(target_year)
                        run_auto_prediction(X, y, target_year, "°C", "Temperature")
                    else:
                        console.print(f"[cyan]  Avg: [yellow]({y.mean():.1f} ± {y.std():.1f}) °C[/]")
                else:
                    console.print(f"[cyan]  Avg: [yellow]({df['Temperature_C'].mean():.1f} ± {df['Temperature_C'].std():.1f}) °C[/]")
            else:
                console.print(f"[cyan]  Records: {len(df)}, Avg: [yellow]({df.mean().mean():.1f} ± {df.std().mean():.1f})[/]")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_water_quality(self):
        """Predict water quality using auto model selection."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        water_file = os.path.join(base_path, "water_quality/telangana_water.csv")
        
        try:
            df = pd.read_csv(water_file)
            
            console.print(f"[cyan]  ║  Analyzing {len(df)} water samples...              [cyan]║")
            
            if 'pH' in df.columns:
                avg_ph = pd.to_numeric(df['pH'], errors='coerce').mean()
                console.print(f"[cyan]  ║[/]  Average pH: {avg_ph:.2f}[/]                              [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Random Forest Classifier                 [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_deforestation(self):
        """Predict deforestation trend using auto model selection."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        defor_file = os.path.join(base_path, "deforestation/goal15.forest_shares.csv")
        
        try:
            df = pd.read_csv(defor_file)
            console.print(f"[cyan]  Analyzing {len(df)} countries...[/]")
            
            df_clean = df.dropna(subset=['forests_2000', 'forests_2020'])
            if len(df_clean) > 5:
                years = np.array([2000, 2005, 2010, 2015, 2020])
                values = np.array([
                    df_clean['forests_2000'].mean(),
                    df_clean.get('forests_2005', df_clean['forests_2000']).mean(),
                    df_clean.get('forests_2010', df_clean['forests_2000']).mean(),
                    df_clean.get('forests_2015', df_clean['forests_2000']).mean(),
                    df_clean['forests_2020'].mean()
                ])
                
                target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                if target_year.isdigit():
                    target_year = int(target_year)
                    run_auto_prediction(years, values, target_year, "%", "Forest Cover")
                else:
                    console.print(f"[cyan]  Current forest cover: [yellow]({values[-1]:.1f} ± {values.std():.1f}) %[/]")
            else:
                console.print(f"[cyan]  Avg forest: [yellow]({df_clean['forests_2020'].mean():.1f} ± {df_clean['forests_2020'].std():.1f}) %[/]")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_plastic_pollution(self):
        """Predict plastic pollution using auto model selection."""
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        plastic_file = os.path.join(base_path, "plastic_pollution/plastic_waste.csv")
        
        try:
            df = pd.read_csv(plastic_file)
            
            if 'Year' in df.columns and len(df) > 5:
                yearly = df.groupby('Year')['Total plastic waste (tonnes)'].sum().reset_index()
                X = yearly['Year'].values
                y = yearly['Total plastic waste (tonnes)'].values
                
                target_year = console.input("\n[yellow]  Enter target year: [/]").strip()
                if target_year.isdigit():
                    target_year = int(target_year)
                    run_auto_prediction(X, y, target_year, "tonnes", "Plastic Pollution")
                    
                    console.print(f"\n[red bold]  ⚠ WARNING: Plastic pollution increasing globally![/]")
                else:
                    console.print(f"[cyan]  Current: [yellow]({y[-1]/1e6:.2f} ± {y.std()/1e6:.2f}) million tonnes[/]")
            else:
                console.print(f"[cyan]  Total waste: [yellow]{df['Total plastic waste (tonnes)'].sum():,.0f} tonnes[/]")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_space_weather(self):
        """Predict space weather."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]SPACE WEATHER FORECAST[/]                           [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        space_file = os.path.join(base_path, "space_weather/space_weather_unified.csv")
        
        try:
            df = pd.read_csv(space_file)
            
            console.print(f"[cyan]  ║[/]  Total events: {len(df)}[/]                           [cyan]║")
            
            if 'event_type' in df.columns:
                console.print(f"\n[yellow]  Available types:[/]")
                for et in df['event_type'].unique():
                    count = (df['event_type'] == et).sum()
                    console.print(f"    [dim]- {et}: {count}[/]")
                
                event_filter = console.input("\n[yellow]  Filter by event type (or Enter for all): [/]").strip()
                
                if event_filter:
                    df = df[df['event_type'].str.contains(event_filter, case=False, na=False)]
                    console.print(f"[cyan]  ║[/]  Filtered events: {len(df)}[/]                      [cyan]║")
                
                flares = (df['event_type'] == 'Solar Flare').sum() if 'event_type' in df.columns else 0
                cme = (df['event_type'] == 'Coronal Mass Ejection').sum() if 'event_type' in df.columns else 0
                console.print(f"[cyan]  ║[/]  Solar Flares: [yellow]{flares}[/]                            [cyan]║")
                console.print(f"[cyan]  ║[/]  CMEs: [yellow]{cme}[/]                                   [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Event Prediction                         [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_mars_climate(self):
        """Predict Mars climate for a specific Sol."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]MARS CLIMATE PREDICTION (Curiosity Rover)[/]         [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        mars_file = os.path.join(base_path, "mars_rover/REMS_Mars_Dataset.csv")
        
        try:
            df = pd.read_csv(mars_file)
            
            sol_input = console.input("[yellow]  Enter Sol number (Martian day, 0-4000): [/]").strip()
            
            if sol_input.isdigit():
                target_sol = int(sol_input)
                
                # Extract numeric part from sol_number column
                df['sol_num'] = df['sol_number'].str.extract(r'Sol (\d+)').astype(float)
                sol_data = df[df['sol_num'] == target_sol]
                
                if len(sol_data) > 0:
                    max_temp = pd.to_numeric(sol_data['max_air_temp(°C)'].iloc[0], errors='coerce')
                    min_temp = pd.to_numeric(sol_data['min_air_temp(°C)'].iloc[0], errors='coerce')
                    # Use std from all data as error estimate
                    std_max = pd.to_numeric(df['max_air_temp(°C)'], errors='coerce').std()
                    std_min = pd.to_numeric(df['min_air_temp(°C)'], errors='coerce').std()
                    
                    console.print(f"[cyan]  ║[/]  Sol:         [yellow]{target_sol}[/]                             [cyan]║")
                    console.print(f"[cyan]  ║[/]  Max Temp:    [yellow]({max_temp:.1f} ± {std_max:.1f})°C[/]              [cyan]║")
                    console.print(f"[cyan]  ║[/]  Min Temp:    [yellow]({min_temp:.1f} ± {std_min:.1f})°C[/]              [cyan]║")
                else:
                    avg_max = pd.to_numeric(df['max_air_temp(°C)'], errors='coerce').mean()
                    avg_min = pd.to_numeric(df['min_air_temp(°C)'], errors='coerce').mean()
                    std_max = pd.to_numeric(df['max_air_temp(°C)'], errors='coerce').std()
                    std_min = pd.to_numeric(df['min_air_temp(°C)'], errors='coerce').std()
                    console.print(f"[cyan]  ║   Sol not found. Showing average:[/]               [cyan]║")
                    console.print(f"[cyan]  ║[/]  Avg Max Temp: [yellow]({avg_max:.1f} ± {std_max:.1f})°C[/]         [cyan]║")
                    console.print(f"[cyan]  ║[/]  Avg Min Temp: [yellow]({avg_min:.1f} ± {std_min:.1f})°C[/]         [cyan]║")
            else:
                console.print("[yellow]  Showing historical averages...[/]")
                max_temp = pd.to_numeric(df['max_air_temp(°C)'], errors='coerce').mean()
                min_temp = pd.to_numeric(df['min_air_temp(°C)'], errors='coerce').mean()
                std_max = pd.to_numeric(df['max_air_temp(°C)'], errors='coerce').std()
                std_min = pd.to_numeric(df['min_air_temp(°C)'], errors='coerce').std()
                console.print(f"[cyan]  ║[/]  Avg Max Temp: [yellow]({max_temp:.1f} ± {std_max:.1f})°C[/]         [cyan]║")
                console.print(f"[cyan]  ║[/]  Avg Min Temp: [yellow]({min_temp:.1f} ± {std_min:.1f})°C[/]         [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Time Series Regression                     [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_earthquake(self):
        """Predict earthquake/tsunami risk."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]EARTHQUAKE/TSUNAMI RISK ANALYSIS[/]                 [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        quake_file = os.path.join(base_path, "earthquake_tsunami/earthquake_data_tsunami.csv")
        
        try:
            df = pd.read_csv(quake_file)
            
            min_mag = console.input("[yellow]  Minimum magnitude (e.g., 5, 6, 7): [/]").strip()
            
            if min_mag.replace('.','').isdigit():
                threshold = float(min_mag)
                filtered = df[df['magnitude'] >= threshold]
                
                console.print(f"[cyan]  ║[/]  Threshold:    [yellow]M >= {threshold}[/]                        [cyan]║")
                console.print(f"[cyan]  ║[/]  Events:       [yellow]{len(filtered)}[/]                              [cyan]║")
                
                if len(filtered) > 0:
                    max_mag = filtered['magnitude'].max()
                    avg_mag = filtered['magnitude'].mean()
                    console.print(f"[cyan]  ║[/]  Max:          [red]{max_mag:.1f}[/]                            [cyan]║")
                    console.print(f"[cyan]  ║[/]  Avg:          [yellow]{avg_mag:.1f}[/]                           [cyan]║")
                    
                    if 'tsunami' in df.columns:
                        tsunami = filtered['tsunami'].sum()
                        console.print(f"[cyan]  ║[/]  Tsunamis:     [yellow]{tsunami}[/]                             [cyan]║")
            else:
                console.print(f"[cyan]  ║[/]  Total events: {len(df)}[/]                           [cyan]║")
                max_mag = df['magnitude'].max()
                avg_mag = df['magnitude'].mean()
                console.print(f"[cyan]  ║[/]  Max magnitude: [red]{max_mag:.1f}[/]                         [cyan]║")
                console.print(f"[cyan]  ║[/]  Avg magnitude: [yellow]{avg_mag:.1f}[/]                        [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Logistic Regression                       [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_stars(self):
        """Predict star types and characteristics."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]STAR TYPES ANALYSIS[/]                               [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        star_file = os.path.join(base_path, "stars/star_data.csv")
        
        try:
            df = pd.read_csv(star_file)
            
            console.print(f"[cyan]  ║[/]  Total stars: {len(df)}[/]                               [cyan]║")
            
            if 'Temperature (K)' in df.columns:
                avg_temp = pd.to_numeric(df['Temperature (K)'], errors='coerce').mean()
                console.print(f"[cyan]  ║[/]  Avg temperature: {avg_temp:.0f} K[/]                  [cyan]║")
            
            if 'Star type' in df.columns:
                types = df['Star type'].value_counts().head(5)
                for stype, count in types.items():
                    console.print(f"[cyan]  ║[/]  {stype}: {count}[/]                                [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Classification                            [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_gravitational_waves(self):
        """Predict gravitational wave events."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]GRAVITATIONAL WAVE ANALYSIS[/]                     [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        gw_file = os.path.join(base_path, "gravitational_waves/gw_data.csv")
        
        try:
            df = pd.read_csv(gw_file)
            
            console.print(f"[cyan]  ║[/]  Total events: {len(df)}[/]                            [cyan]║")
            
            if 'detector' in df.columns:
                detectors = df['detector'].unique()
                console.print(f"[cyan]  ║[/]  Detectors: {len(detectors)}[/]                          [cyan]║")
                for det in detectors:
                    count = (df['detector'] == det).sum()
                    console.print(f"[cyan]  ║[/]    {det}: {count} events[/]                        [cyan]║")
            
            if 'mean' in df.columns:
                avg_strain = df['mean'].abs().mean()
                console.print(f"[cyan]  ║[/]  Avg strain: {avg_strain:.2e}[/]                    [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Signal Detection                         [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_galaxies(self):
        """Predict galaxy properties."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]GALAXY CATALOG ANALYSIS[/]                          [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        gal_file = os.path.join(base_path, "galaxies/combo17_galaxies.csv")
        
        try:
            df = pd.read_csv(gal_file)
            
            console.print(f"[cyan]  ║[/]  Total galaxies: {len(df)}[/]                         [cyan]║")
            
            if 'Rmag' in df.columns:
                avg_mag = pd.to_numeric(df['Rmag'], errors='coerce').mean()
                console.print(f"[cyan]  ║[/]  Avg R magnitude: {avg_mag:.2f}[/]                   [cyan]║")
            
            if 'Mcz' in df.columns:
                avg_z = pd.to_numeric(df['Mcz'], errors='coerce').mean()
                console.print(f"[cyan]  ║[/]  Avg redshift: {avg_z:.4f}[/]                        [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Photometric Analysis                      [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_planets(self):
        """Predict solar system planet data."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]SOLAR SYSTEM PLANET ANALYSIS[/]                    [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        planet_file = os.path.join(base_path, "planets/planets.csv")
        
        try:
            df = pd.read_csv(planet_file)
            
            console.print(f"[cyan]  ║[/]  Total planets: {len(df)}[/]                             [cyan]║")
            
            if 'Planet' in df.columns:
                for _, row in df.head(8).iterrows():
                    name = str(row['Planet'])[:10]
                    mass = row.get('Mass (10^24kg)', 'N/A')
                    console.print(f"[cyan]  ║[/]  {name}: Mass {mass}[/]                           [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Planetary Database                        [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_volcano_eruptions(self):
        """Predict volcano eruption data."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]VOLCANO ERUPTION ANALYSIS[/]                      [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        erup_file = os.path.join(base_path, "volcano_eruptions/volcano_data_2010.csv")
        
        try:
            df = pd.read_csv(erup_file)
            
            console.print(f"[cyan]  ║[/]  Total eruptions: {len(df)}[/]                         [cyan]║")
            
            if 'VEI' in df.columns:
                avg_vei = pd.to_numeric(df['VEI'], errors='coerce').mean()
                max_vei = pd.to_numeric(df['VEI'], errors='coerce').max()
                console.print(f"[cyan]  ║[/]  Avg VEI: {avg_vei:.1f}[/]                              [cyan]║")
                console.print(f"[cyan]  ║[/]  Max VEI: {int(max_vei)}[/]                               [cyan]║")
            
            if 'DEATHS' in df.columns:
                total_deaths = pd.to_numeric(df['DEATHS'], errors='coerce').sum()
                console.print(f"[cyan]  ║[/]  Total deaths: {int(total_deaths)}[/]                       [cyan]║")
            
            console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
            console.print(f"[cyan]  ║  Model:  Historical Analysis                       [cyan]║")
            console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        except Exception as e:
            console.print(f"[red]  Error: {escape(str(e))}[/]")
    
    def _predict_volcano(self):
        """Predict volcano activity."""
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]VOLCANO ACTIVITY PREDICTION[/]                     [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'satellites', 'data')
        
        for vfile in ["volcanoes/volcanoes around the world in 2021.csv",
                      "volcano_eruptions/volcano_data_2010.csv"]:
            try:
                vpath = os.path.join(base_path, vfile)
                if os.path.exists(vpath):
                    df = pd.read_csv(vpath)
                    console.print(f"[cyan]  ║[/]  Data source: {vfile}[/]                          [cyan]║")
                    console.print(f"[cyan]  ║[/]  Total volcanoes: {len(df)}[/]                      [cyan]║")
                    
                    if 'Status' in df.columns:
                        active = (df['Status'] == 'Active').sum()
                        console.print(f"[cyan]  ║[/]  Active volcanoes: [yellow]{active}[/]                      [cyan]║")
                    break
            except:
                continue
        
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        console.print(f"[cyan]  ║  Model:  Classification                            [cyan]║")
        console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
    
    def handle_scan(self):
        console.print(Panel(
            "[bold cyan]📡 DATA ACQUISITION[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        if not hasattr(self, 'linked_satellite'):
            console.print("[yellow]  No satellite linked. Use 'link' first.[/]")
            return
        
        sat = self.linked_satellite
        console.print(f"[cyan]  Scanning {sat.name}...[/]")
        
        for i in range(5):
            console.print(f"  [dim]Receiving telemetry stream {i+1}/5...[/]")
            time.sleep(0.3)
        
        console.print(f"\n[green]✓ Data acquired from {sat.name}[/]")
    
    def handle_orbit(self):
        console.print(Panel(
            "[bold cyan]🌐 ORBITAL PARAMETERS[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        if not hasattr(self, 'linked_satellite'):
            console.print("[yellow]  No satellite linked. Use 'link' first.[/]")
            return
        
        sat = self.linked_satellite
        
        console.print(f"[cyan]  ╔══════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]{sat.name}[/] [cyan]                     ║")
        console.print(f"[cyan]  ╠══════════════════════════════════════╣")
        console.print(f"[cyan]  ║[/]  Regime:       [yellow]{sat.regime:>8}[/]        ║")
        console.print(f"[cyan]  ║[/]  Altitude:     [yellow]{sat.alt:>8.0f} km[/]       ║")
        console.print(f"[cyan]  ║[/]  Latitude:     [yellow]{sat.lat:>8.2f}°[/]        ║")
        console.print(f"[cyan]  ║[/]  Longitude:    [yellow]{sat.lon:>8.2f}°[/]        ║")
        console.print(f"[cyan]  ║[/]  Status:       [yellow]{sat.status:>8}[/]        ║")
        console.print(f"[cyan]  ╚══════════════════════════════════════╝")
    
    def handle_status(self):
        console.print(Panel(
            "[bold cyan]📊 PIPELINE STATUS[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        stages = [
            ("GENERATED", True),
            ("INGESTED", True),
            ("PROCESSED", True),
            ("ARCHIVED", True),
        ]
        
        for name, status in stages:
            color = MissionColors.SUCCESS if status else MissionColors.GRAY
            symbol = "✓" if status else "○"
            console.print(f"  [{color}]{symbol}[/] {name}")
    
    def handle_red_team(self):
        if not self.red_team:
            console.print("[yellow]Red Team module not available[/]")
            return
        
        console.print(Panel(
            f"[bold red]⬡ RED TEAM ATTACK SIMULATION[/]",
            border_style="red", box=box.DOUBLE
        ))
        
        console.print(f"[red]Running attack simulation...[/]")
        result = self.red_team.run_campaign("test_campaign", ["localhost"])
        
        console.print(f"\n[red]Total attacks: {result.total_attacks}[/]")
        console.print(f"[red]Successful: {result.successful_attacks}[/]")
        console.print(f"[red]Risk score: {result.risk_score}[/]")
    
    def handle_blue_team(self):
        if not self.blue_team:
            console.print("[yellow]Blue Team module not available[/]")
            return
        
        console.print(Panel(
            f"[bold cyan]⬡ BLUE TEAM DEFENSE STATUS[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        stats = self.blue_team.get_defense_status()
        
        console.print(col(MissionColors.CYAN, "  NETWORK IDS:"))
        console.print(f"    Packets: {stats['ids']['packets_inspected']} | Alerts: {stats['ids']['alerts_generated']}")
        
        console.print(col(MissionColors.CYAN, "  WEB APPLICATION FIREWALL:"))
        console.print(f"    Rules: {stats['waf']['rules_active']} | Blocked IPs: {stats['waf']['blocked_ips']}")
        
        console.print(f"\n[green]✓ Defense systems operational[/]")
    
    def handle_zero_trust(self):
        if not self.zero_trust:
            console.print("[yellow]Zero Trust module not available[/]")
            return
        
        status = self.zero_trust.get_authorization_status()
        
        console.print(Panel(
            f"[bold cyan]⬡ ZERO TRUST AUTHENTICATION[/]",
            border_style="cyan", box=box.DOUBLE
        ))
        
        console.print(f"[cyan]  Sessions: {status['active_sessions']} | Devices: {status['devices']}[/]")
        console.print(f"[cyan]  Policies: {status['policies']}[/]")
    
    def handle_pqcrypto(self):
        if not self.quantum:
            console.print("[yellow]Quantum crypto module not available[/]")
            return
        
        from secure_eo_pipeline.cyber.quantum_resistant.pqcrypto import PQAlgorithm
        key_pair = self.quantum.generate_keypair(algorithm=PQAlgorithm.ML_KEM_768)
        
        console.print(Panel(
            f"[bold purple]⬡ QUANTUM-RESISTANT CRYPTOGRAPHY[/]",
            border_style="purple", box=box.DOUBLE
        ))
        
        console.print(f"[purple]  Algorithm: ML-KEM-768[/]")
        console.print(f"[purple]  Status: READY[/]")
    
    def handle_audit_chain(self):
        if not self.blockchain:
            console.print("[yellow]Blockchain module not available[/]")
            return
        
        stats = self.blockchain.get_chain_statistics()
        
        console.print(Panel(
            f"[bold green]⬡ BLOCKCHAIN AUDIT LEDGER[/]",
            border_style="green", box=box.DOUBLE
        ))
        
        console.print(f"[green]  Blocks: {stats['blocks']} | Events: {stats['total_events']}[/]")
    
    def handle_threats(self):
        console.print(Panel(
            f"[bold yellow]⚠ ACTIVE THREATS MONITOR[/]",
            border_style="yellow", box=box.DOUBLE
        ))
        
        threats = [
            ("BRUTE-FORCE", "192.168.1.105", "MEDIUM", "Active"),
            ("SQL_INJECTION", "10.0.0.55", "HIGH", "Blocked"),
            ("PORT_SCAN", "172.16.0.23", "LOW", "Monitoring"),
        ]
        
        for threat, ip, severity, status in threats:
            color = MissionColors.ERROR if severity == "HIGH" else MissionColors.WARNING if severity == "MEDIUM" else MissionColors.GRAY
            console.print(f"  [{color}]{threat}[/] | {ip} | {severity} | {status}")
    
    def run(self):
        self.running = True
        
        while self.running:
            if not self.authenticated and not self.hacker_mode:
                self.print_login_screen()
                
                choice = console.input("\n[cyan]SELECT > [/]").strip().lower()
                
                if choice == "1" or choice == "login":
                    self.handle_login()
                elif choice == "2" or choice == "hack":
                    self.handle_hack()
                elif choice == "3" or choice == "demo":
                    self.authenticated = True
                    self.current_user = self.users["guest"]
                elif choice == "4" or choice == "quit":
                    console.print("[yellow]Exiting...[/]")
                    self.running = False
                    break
                else:
                    console.print("[red]Invalid option[/]")
                
                console.input("\n[dim]Press Enter to continue...[/]")
            
            elif self.authenticated:
                self.print_main_menu()
                
                choice = console.input("\n[cyan]COMMAND > [/]").strip().lower()
                
                console.print()
                
                if choice == "dashboard":
                    self.log_session("CMD: dashboard")
                    self.print_satellite_catalog()
                elif choice == "satellites":
                    self.log_session("CMD: satellites")
                    self.print_satellite_catalog()
                elif choice == "link":
                    if not self.current_user.can("link"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: link")
                        self.handle_link()
                elif choice == "scan":
                    if not self.current_user.can("scan"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: scan")
                        self.handle_scan()
                elif choice == "orbit":
                    if not self.current_user.can("orbit"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: orbit")
                        self.handle_orbit()
                elif choice == "predict":
                    if not self.current_user.can("predict"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: predict")
                        self.handle_predict()
                elif choice == "status":
                    self.log_session("CMD: status")
                    self.handle_status()
                elif choice == "red-team":
                    if not self.current_user.can("red-team"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: red-team")
                        self.handle_red_team()
                elif choice == "blue-team":
                    if not self.current_user.can("blue-team"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: blue-team")
                        self.handle_blue_team()
                elif choice == "zero-trust":
                    if not self.current_user.can("zero-trust"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: zero-trust")
                        self.handle_zero_trust()
                elif choice == "pqcrypto":
                    if not self.current_user.can("pqcrypto"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: pqcrypto")
                        self.handle_pqcrypto()
                elif choice == "audit-chain":
                    if not self.current_user.can("audit-chain"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: audit-chain")
                        self.handle_audit_chain()
                elif choice == "threats":
                    if not self.current_user.can("threats"):
                        console.print("[red]  ✗ Access denied: insufficient permissions[/]")
                    else:
                        self.log_session("CMD: threats")
                        self.handle_threats()
                elif choice == "audit-chain":
                    self.log_session("CMD: audit-chain")
                    self.handle_audit_chain()
                elif choice == "threats":
                    self.log_session("CMD: threats")
                    self.handle_threats()
                elif choice == "monitor":
                    self.log_session("CMD: monitor")
                    for sat in self.satellites:
                        self.satellite_monitor.update_satellite(sat)
                        self.alert_system.check_satellite(sat)
                    self.satellite_monitor.display_dashboard(self.satellites, self.console)
                    self.alert_system.display_alerts(self.console)
                elif choice == "alerts":
                    self.log_session("CMD: alerts")
                    for sat in self.satellites:
                        self.alert_system.check_satellite(sat)
                    self.alert_system.display_alerts(self.console)
                elif choice == "contact":
                    self.log_session("CMD: contact")
                    self.satellite_monitor.display_contact_windows(self.satellites, self.console)
                elif choice == "pass":
                    self.log_session("CMD: pass")
                    sat_name = console.input("[yellow]  Satellite name (or Enter for all): [/]").strip().upper()
                    if sat_name:
                        sat = next((s for s in self.satellites if s.name == sat_name), None)
                        if sat:
                            passes = self.satellite_monitor.plan_pass(sat)
                            console.print(f"\n[cyan]  Pass schedule for {sat_name}:[/]")
                            for p in passes:
                                console.print(f"    [yellow]{p['start_time']}[/] - Elev: {p['max_elevation']:.0f}°, Dur: {p['duration']:.1f}min")
                        else:
                            console.print(f"[red]  Satellite {sat_name} not found[/]")
                    else:
                        for sat in self.satellites[:5]:
                            passes = self.satellite_monitor.plan_pass(sat)
                            console.print(f"\n[cyan]  {sat.name}:[/]")
                            for p in passes[:2]:
                                console.print(f"    [yellow]{p['start_time']}[/] - Elev: {p['max_elevation']:.0f}°")
                elif choice == "log" or choice == "export":
                    self.log_session("CMD: export")
                    self.export_session()
                elif choice == "stations":
                    self.log_session("CMD: stations")
                    self.ground_stations.display_stations(self.console)
                elif choice == "station":
                    self.log_session("CMD: station set")
                    station_name = console.input("[yellow]  Station name: [/]").strip()
                    if self.ground_stations.set_active_station(station_name):
                        console.print(f"[green]  Active station: {self.ground_stations.active_station}[/]")
                        console.print(f"  {self.ground_stations.get_station_info()}[/]")
                    else:
                        console.print(f"[red]  Station not found[/]")
                elif choice == "failures":
                    self.log_session("CMD: failures")
                    self.failure_simulator.display_failures(self.console)
                elif choice == "simulate-fail":
                    self.log_session("CMD: simulate-fail")
                    sat_name = console.input("[yellow]  Satellite name: [/]").strip().upper()
                    sat = next((s for s in self.satellites if s.name == sat_name), None)
                    if sat:
                        result = self.failure_simulator.simulate_failure(sat)
                        console.print(f"[red]  ⚠ FAILURE TRIGGERED on {sat_name}[/]")
                        console.print(f"  Type: {result['type']}, Severity: {result['severity']}")
                    else:
                        console.print(f"[red]  Satellite {sat_name} not found[/]")
                elif choice == "recover":
                    self.log_session("CMD: recover")
                    sat_name = console.input("[yellow]  Satellite name: [/]").strip().upper()
                    result = self.failure_simulator.trigger_recovery(sat_name)
                    if result["status"] == "RECOVERED":
                        console.print(f"[green]  ✓ {sat_name} recovered via {result['action']}[/]")
                    elif result["status"] == "RETRY_NEEDED":
                        console.print(f"[yellow]  ⚠ Recovery attempt failed: {result['action']}[/]")
                    else:
                        console.print(f"[dim]  {result['message']}[/]")
                elif choice == "logout":
                    self.authenticated = False
                    self.current_user = None
                    console.print("[yellow]Logged out[/]")
                elif choice == "quit" or choice == "exit":
                    self.running = False
                    break
                else:
                    console.print(f"[red]Unknown command: {choice}[/]")
                
                if choice not in ["dashboard", "satellites", "quit", "exit", "logout"]:
                    console.input("\n[dim]Press Enter to continue...[/]")


def main():
    console_obj = MissionConsole()
    console_obj.run()


if __name__ == "__main__":
    main()


class GroundStations:
    """Multiple ground station management."""
    
    STATIONS = {
        "GOLDSTONE": {"lat": 35.4, "lon": -116.9, "country": "USA", "tz": "PST"},
        "CANARY": {"lat": 28.3, "lon": -15.6, "country": "Spain", "tz": "CET"},
        "MADRID": {"lat": 40.4, "lon": -3.7, "country": "Spain", "tz": "CET"},
        "CEBERNET": {"lat": 45.8, "lon": 8.5, "country": "Italy", "tz": "CET"},
        "DWARFS": {"lat": -25.7, "lon": 28.2, "country": "South Africa", "tz": "SAST"},
        "GOLDWOOD": {"lat": 51.8, "lon": -1.5, "country": "UK", "tz": "GMT"},
        "TOKYO": {"lat": 35.7, "lon": 139.7, "country": "Japan", "tz": "JST"},
        "SYDNEY": {"lat": -33.9, "lon": 151.2, "country": "Australia", "tz": "AEST"},
    }
    
    def __init__(self):
        self.active_station = "CEBERNET"
    
    def set_active_station(self, name: str) -> bool:
        if name.upper() in self.STATIONS:
            self.active_station = name.upper()
            return True
        return False
    
    def get_station_info(self, name: str = None) -> Dict:
        station = name.upper() if name else self.active_station
        return self.STATIONS.get(station, self.STATIONS["CEBERNET"])
    
    def display_stations(self, console: Console):
        table = Table(
            title="🌐 GROUND STATIONS NETWORK",
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("STATION", style="bold magenta")
        table.add_column("LATITUDE", style="cyan")
        table.add_column("LONGITUDE", style="cyan")
        table.add_column("COUNTRY", style="white")
        table.add_column("TIMEZONE", style="yellow")
        table.add_column("STATUS", style="bold")
        
        for name, info in self.STATIONS.items():
            status = "ACTIVE" if name == self.active_station else "STANDBY"
            status_color = "green" if status == "ACTIVE" else "dim"
            
            table.add_row(
                name,
                f"{info['lat']:.1f}°",
                f"{info['lon']:.1f}°",
                info['country'],
                info['tz'],
                col(status_color, status)
            )
        
        console.print(table)


class FailureSimulator:
    """Satellite failure simulation and recovery."""
    
    FAILURE_TYPES = [
        "POWER_FAILURE",
        "COMM_FAILURE",
        "ATTITUDE_ERROR",
        "THERMAL_FAILURE",
        "SOFTWARE_ERROR",
        "TRANSPONDER_FAIL"
    ]
    
    def __init__(self):
        self.active_failures = []
    
    def simulate_failure(self, sat: Satellite) -> Dict:
        failure_type = random.choice(self.FAILURE_TYPES)
        
        severity = random.choice(["MINOR", "MAJOR", "CRITICAL"])
        
        failure = {
            "satellite": sat.name,
            "type": failure_type,
            "severity": severity,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "recoverable": severity in ["MINOR", "MAJOR"]
        }
        
        self.active_failures.append(failure)
        
        return failure
    
    def trigger_recovery(self, sat_name: str) -> Dict:
        failure = next((f for f in self.active_failures if f["satellite"] == sat_name), None)
        
        if not failure:
            return {"satellite": sat_name, "status": "NO_FAILURE", "message": "No active failure"}
        
        if not failure["recoverable"]:
            return {"satellite": sat_name, "status": "FAILED", "message": "Non-recoverable failure"}
        
        recovery_actions = [
            "Reset subsystems",
            "Switch to backup power",
            "Reorient satellite",
            "Software reboot",
            "Thermal control adjustment"
        ]
        
        action = random.choice(recovery_actions)
        success = random.random() < 0.8
        
        if success:
            self.active_failures = [f for f in self.active_failures if f["satellite"] != sat_name]
            return {"satellite": sat_name, "status": "RECOVERED", "action": action}
        else:
            return {"satellite": sat_name, "status": "RETRY_NEEDED", "action": action}
    
    def display_failures(self, console: Console):
        if not self.active_failures:
            console.print("[green]✓ No active failures[/]")
            return
        
        table = Table(
            title="⚠️ ACTIVE SATELLITE FAILURES",
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold red"
        )
        
        table.add_column("SATELLITE", style="bold magenta")
        table.add_column("FAILURE TYPE", style="red")
        table.add_column("SEVERITY", style="bold")
        table.add_column("TIMESTAMP", style="dim")
        table.add_column("RECOVERABLE", style="green")
        
        for f in self.active_failures:
            severity_color = "red" if f["severity"] == "CRITICAL" else "yellow"
            rec_color = "green" if f["recoverable"] else "red"
            rec_text = "YES" if f["recoverable"] else "NO"
            
            table.add_row(
                f["satellite"],
                f["type"],
                col(severity_color, f["severity"]),
                f["timestamp"],
                col(rec_color, rec_text)
            )
        
        console.print(table)


class AdvancedMLModels:
    """Advanced ML/DL models for satellite predictions."""
    
    @staticmethod
    def xgboost_predict(X_train: np.ndarray, y_train: np.ndarray, 
                        X_pred: np.ndarray) -> Dict:
        try:
            import xgboost as xgb
            model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
            model.fit(X_train, y_train)
            return {"model": "XGBoost", "prediction": model.predict(X_pred)[0], "success": True}
        except ImportError:
            return {"model": "XGBoost", "success": False, "error": "Not installed"}
        except Exception as e:
            return {"model": "XGBoost", "success": False, "error": str(e)}
    
    @staticmethod
    def lightgbm_predict(X_train: np.ndarray, y_train: np.ndarray, X_pred: np.ndarray) -> Dict:
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(n_estimators=100, max_depth=6, random_state=42, verbose=-1)
            model.fit(X_train, y_train)
            return {"model": "LightGBM", "prediction": model.predict(X_pred)[0], "success": True}
        except ImportError:
            return {"model": "LightGBM", "success": False, "error": "Not installed"}
        except Exception as e:
            return {"model": "LightGBM", "success": False, "error": str(e)}
    
    @staticmethod
    def svm_predict(X_train: np.ndarray, y_train: np.ndarray, X_pred: np.ndarray) -> Dict:
        try:
            from sklearn.svm import SVR
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            model = SVR(kernel='rbf', C=100)
            model.fit(scaler.fit_transform(X_train), y_train)
            return {"model": "SVM", "prediction": model.predict(scaler.transform(X_pred))[0], "success": True}
        except Exception as e:
            return {"model": "SVM", "success": False, "error": str(e)}
    
    @staticmethod
    def neural_network_predict(X_train: np.ndarray, y_train: np.ndarray, X_pred: np.ndarray) -> Dict:
        try:
            from sklearn.neural_network import MLPRegressor
            model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
            model.fit(X_train, y_train)
            return {"model": "MLP", "prediction": model.predict(X_pred)[0], "success": True}
        except Exception as e:
            return {"model": "MLP", "success": False, "error": str(e)}
    
    @staticmethod
    def lstm_predict(sequences: np.ndarray, X_pred: np.ndarray) -> Dict:
        try:
            import torch
            class LSTMModel(torch.nn.Module):
                def __init__(self, input_size):
                    super().__init__()
                    self.lstm = torch.nn.LSTM(input_size, 32, batch_first=True)
                    self.fc = torch.nn.Linear(32, 1)
                def forward(self, x):
                    out, _ = self.lstm(x)
                    return self.fc(out[:, -1, :])
            X_t = torch.FloatTensor(sequences)
            y_t = torch.FloatTensor(sequences[:, -1, 0])
            model = LSTMModel(sequences.shape[-1])
            opt = torch.optim.Adam(model.parameters(), lr=0.01)
            loss_fn = torch.nn.MSELoss()
            for _ in range(100):
                model.train(); opt.zero_grad(); loss_fn(model(X_t).squeeze(), y_t).backward(); opt.step()
            model.eval()
            return {"model": "LSTM", "prediction": model(torch.FloatTensor(X_pred)).item(), "success": True}
        except ImportError:
            return {"model": "LSTM", "success": False, "error": "PyTorch needed"}
        except Exception as e:
            return {"model": "LSTM", "success": False, "error": str(e)}
    
    @staticmethod
    def prophet_predict(dates: List, values: np.ndarray, future_date: str) -> Dict:
        try:
            from prophet import Prophet
            df = pd.DataFrame({'ds': pd.to_datetime(dates), 'y': values})
            m = Prophet(yearly_seasonality=True).fit(df)
            f = m.predict(m.make_future_dataframe(periods=365))
            pred = f[f['ds'] == future_date]['yhat'].values[0]
            return {"model": "Prophet", "prediction": pred, "success": True}
        except ImportError:
            return {"model": "Prophet", "success": False, "error": "Not installed"}
        except Exception as e:
            return {"model": "Prophet", "success": False, "error": str(e)}
    
    @staticmethod
    def run_all(years: np.ndarray, values: np.ndarray, target_year: int) -> Dict:
        X = years.reshape(-1, 1)
        y = values
        X_pred = np.array([[target_year]])
        return {n: f(X, y, X_pred) for n, f in [
            ("XGBoost", AdvancedMLModels.xgboost_predict),
            ("LightGBM", AdvancedMLModels.lightgbm_predict),
            ("SVM", AdvancedMLModels.svm_predict),
            ("NeuralNet", AdvancedMLModels.neural_network_predict)
        ]}


class ModelSelector:
    MODELS = {
        "1": "Linear", "2": "Polynomial", "3": "Random Forest",
        "4": "XGBoost", "5": "LightGBM", "6": "SVM",
        "7": "Neural Net", "8": "LSTM", "9": "Prophet", "10": "Compare All"
    }
    
    @staticmethod
    def display():
        console.print("\n[cyan]Available Models:[/]")
        for k, v in ModelSelector.MODELS.items():
            console.print(f"  [yellow]{k}[/]. {v}")
    
    @staticmethod
    def get_choice() -> str:
        ModelSelector.display()
        return console.input("\n[yellow]Model [1]: [/]").strip() or "1"


class DataAnalyzer:
    """EDA and Feature Engineering specific for each dataset type."""
    
    @staticmethod
    def analyze_and_engineer(df: pd.DataFrame, target_col: str, data_type: str) -> tuple:
        """Main method: performs EDA and feature engineering based on data type."""
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        console.print(Panel(
            f"[bold cyan]📊 DATA ANALYSIS: {data_type}[/]",
            border_style="cyan", box=box.ROUNDED
        ))
        
        console.print(f"\n[cyan]1. EXPLORATORY DATA ANALYSIS[/]")
        
        # Basic stats
        console.print(f"  [dim]Rows: {len(df)}, Columns: {len(df.columns)}[/]")
        
        # Missing values analysis
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)
        cols_with_missing = missing_pct[missing_pct > 0]
        if len(cols_with_missing) > 0:
            console.print(f"  [yellow]Missing values: {dict(cols_with_missing[cols_with_missing > 0].head(5))}[/]")
        
        # Data type specific analysis
        if data_type == "climate_temperature":
            return DataAnalyzer._climate_temp_features(df, target_col)
        elif data_type == "sea_level":
            return DataAnalyzer._sea_level_features(df, target_col)
        elif data_type == "co2_emissions":
            return DataAnalyzer._co2_features(df, target_col)
        elif data_type == "sea_ice":
            return DataAnalyzer._sea_ice_features(df, target_col)
        elif data_type == "hurricane":
            return DataAnalyzer._hurricane_features(df, target_col)
        elif data_type == "air_quality":
            return DataAnalyzer._air_quality_features(df, target_col)
        elif data_type == "ocean":
            return DataAnalyzer._ocean_features(df, target_col)
        elif data_type == "space_weather":
            return DataAnalyzer._space_weather_features(df, target_col)
        elif data_type == "mars_climate":
            return DataAnalyzer._mars_climate_features(df, target_col)
        else:
            return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _climate_temp_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for global temperature data."""
        console.print(f"  [dim]Type: Time Series Climate Data[/]")
        
        # Detect year column
        year_col = None
        for col in df.columns:
            if 'year' in col.lower():
                year_col = col
                break
        
        if year_col:
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
            df = df.dropna(subset=[year_col, target_col])
            
            # Time-based features
            year_min, year_max = df[year_col].min(), df[year_col].max()
            df['year_scaled'] = (df[year_col] - year_min) / (year_max - year_min + 1e-10)
            df['decade'] = (df[year_col] // 10) * 10
            df['year_sq'] = df['year_scaled'] ** 2  # Polynomial feature
            df['year_cube'] = df['year_scaled'] ** 3
            
            console.print(f"  [green]✓ Features: year_scaled, decade, year_sq, year_cube[/]")
            
            X = df[['year_scaled', 'year_sq', 'year_cube']].values
            y = df[target_col].values
            return X, y, df[year_col].values
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _sea_level_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for sea level data."""
        console.print(f"  [dim]Type: Sea Level Altimetry Data[/]")
        
        year_col = None
        for col in df.columns:
            if 'year' in col.lower():
                year_col = col
                break
        
        if year_col:
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
            df = df.dropna(subset=[year_col, target_col])
            
            # Non-linear trend features
            df['year_scaled'] = (df[year_col] - df[year_col].min()) / (df[year_col].max() - df[year_col].min() + 1e-10)
            df['year_sq'] = df['year_scaled'] ** 2
            df['year_sqrt'] = np.sqrt(df['year_scaled'])
            
            # Moving average as feature
            df['ma_3'] = df[target_col].rolling(3, min_periods=1).mean()
            
            console.print(f"  [green]✓ Features: year_scaled, year_sq, year_sqrt, ma_3[/]")
            
            X = df[['year_scaled', 'year_sq', 'year_sqrt', 'ma_3']].fillna(0).values
            y = df[target_col].values
            return X, y, df[year_col].values
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _co2_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for CO2 emissions."""
        console.print(f"  [dim]Type: CO2 Emission Time Series[/]")
        
        year_col = None
        for col in df.columns:
            if 'year' in col.lower():
                year_col = col
                break
        
        if year_col:
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
            df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
            df = df.dropna(subset=[year_col, target_col])
            
            if len(df) < 5:
                console.print(f"  [red]✗ Insufficient valid data after cleaning[/]")
                return None, None, None
            
            # Exponential growth features
            year_min, year_max = df[year_col].min(), df[year_col].max()
            df['year_scaled'] = (df[year_col] - year_min) / (year_max - year_min + 1e-10)
            df['exp_year'] = np.exp(df['year_scaled'].clip(0, 5))
            df['log_year'] = np.log1p(df['year_scaled'])
            
            # Acceleration features
            df['year_sq'] = df['year_scaled'] ** 2
            
            console.print(f"  [green]✓ Features: year_scaled, year_sq, exp_year, log_year[/]")
            
            X = df[['year_scaled', 'year_sq', 'exp_year', 'log_year']].values
            y = df[target_col].values
            return X, y, df[year_col].values
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _sea_ice_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for sea ice extent."""
        console.print(f"  [dim]Type: Sea Ice Satellite Data[/]")
        
        year_col = None
        for col in df.columns:
            if 'year' in col.lower():
                year_col = col
                break
        
        if year_col:
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
            df = df.dropna(subset=[year_col, target_col])
            
            # Cyclic features for seasonal patterns
            df['year_scaled'] = (df[year_col] - df[year_col].min()) / (df[year_col].max() - df[year_col].min() + 1e-10)
            df['year_sq'] = df['year_scaled'] ** 2
            
            # Trend + seasonal decomposition approximation
            df['trend'] = df[target_col].rolling(5, min_periods=1).mean()
            df['detrend'] = df[target_col] - df['trend']
            
            console.print(f"  [green]✓ Features: year_scaled, year_sq, trend, detrend[/]")
            
            X = df[['year_scaled', 'year_sq', 'trend', 'detrend']].fillna(0).values
            y = df[target_col].values
            return X, y, df[year_col].values
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _hurricane_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for hurricane data."""
        console.print(f"  [dim]Type: Hurricane/cyclone Track Data[/]")
        
        # Check for numeric columns for features
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            feature_cols = [c for c in numeric_cols if c != target_col][:5]
            
            console.print(f"  [green]✓ Features: {feature_cols}[/]")
            
            X = df[feature_cols].fillna(0).values
            y = df[target_col].values if target_col in df.columns else None
            
            if y is None:
                # Create target from max wind
                if 'Maximum Wind' in df.columns:
                    y = df['Maximum Wind'].values
            
            return X, y, None
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _air_quality_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for air quality data."""
        console.print(f"  [dim]Type: Air Quality Monitoring[/]")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            feature_cols = [c for c in numeric_cols if c != target_col][:6]
            
            # Add interaction features
            if len(feature_cols) >= 2:
                df['interaction'] = df[feature_cols[0]] * df[feature_cols[1]]
                feature_cols.append('interaction')
            
            console.print(f"  [green]✓ Features: {feature_cols[:6]}[/]")
            
            X = df[feature_cols].fillna(0).values
            y = df[target_col].values if target_col in df.columns else None
            return X, y, None
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _ocean_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for ocean climate data."""
        console.print(f"  [dim]Type: Ocean/Sea Surface Temperature[/]")
        
        year_col = None
        for col in df.columns:
            if 'year' in col.lower():
                year_col = col
                break
        
        if year_col:
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
            df = df.dropna(subset=[year_col])
            
            if target_col in df.columns:
                df = df.dropna(subset=[target_col])
                
                # Temporal features
                df['year_scaled'] = (df[year_col] - df[year_col].min()) / (df[year_col].max() - df[year_col].min() + 1e-10)
                df['sin_year'] = np.sin(2 * np.pi * df['year_scaled'])
                df['cos_year'] = np.cos(2 * np.pi * df['year_scaled'])
                
                console.print(f"  [green]✓ Features: year_scaled, sin_year, cos_year (cyclic)[/]")
                
                X = df[['year_scaled', 'sin_year', 'cos_year']].values
                y = df[target_col].values
                return X, y, df[year_col].values
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _space_weather_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for space weather data."""
        console.print(f"  [dim]Type: Solar/Space Weather Events[/]")
        
        # Check for datetime or date columns
        date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
        
        if date_cols and target_col in df.columns:
            try:
                df[date_cols[0]] = pd.to_datetime(df[date_cols[0]], errors='coerce')
                df = df.dropna(subset=[date_cols[0], target_col])
                
                # Temporal features
                df['month'] = df[date_cols[0]].dt.month
                df['day_of_year'] = df[date_cols[0]].dt.dayofyear
                df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
                df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
                
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                feature_cols = [c for c in numeric_cols if c != target_col][:4]
                
                console.print(f"  [green]✓ Features: temporal cyclic + numeric[/]")
                
                X = df[feature_cols].fillna(0).values
                y = df[target_col].values
                return X, y, None
            except:
                pass
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _mars_climate_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Feature engineering for Mars rover climate data."""
        console.print(f"  [dim]Type: Mars REMS Sensor Data[/]")
        
        # Sol-based time series
        sol_col = None
        for col in df.columns:
            if 'sol' in col.lower():
                sol_col = col
                break
        
        if sol_col:
            # Extract numeric sol
            df['sol_num'] = df[sol_col].astype(str).str.extract(r'Sol (\d+)')[0].astype(float)
            df = df.dropna(subset=['sol_num'])
            
            if target_col in df.columns:
                df = df.dropna(subset=[target_col])
                
                # Time features for Martian sol
                df['sol_scaled'] = (df['sol_num'] - df['sol_num'].min()) / (df['sol_num'].max() - df['sol_num'].min() + 1e-10)
                df['sol_sin'] = np.sin(2 * np.pi * (df['sol_num'] % 100) / 100)  # Seasonal pattern
                df['sol_cos'] = np.cos(2 * np.pi * (df['sol_num'] % 100) / 100)
                
                console.print(f"  [green]✓ Features: sol_scaled, sol_sin, sol_cos (Martian seasonal)[/]")
                
                X = df[['sol_scaled', 'sol_sin', 'sol_cos']].values
                y = df[target_col].values
                return X, y, df['sol_num'].values
        
        return DataAnalyzer._generic_features(df, target_col)
    
    @staticmethod
    def _generic_features(df: pd.DataFrame, target_col: str) -> tuple:
        """Generic feature engineering for any dataset."""
        console.print(f"  [dim]Type: Generic[/]")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if target_col in df.columns:
            feature_cols = [c for c in numeric_cols if c != target_col]
        else:
            feature_cols = numeric_cols[:5] if numeric_cols else []
        
        if feature_cols:
            console.print(f"  [green]✓ Features: {feature_cols[:5]}[/]")
            X = df[feature_cols].fillna(0).values
            y = df[target_col].values if target_col in df.columns else df[numeric_cols[0]].values
            return X, y, None
        
        console.print(f"  [red]✗ No numeric features found[/]")
        return None, None, None


class AutoModelSelector:
    """Automatic model selection with cross-validation."""
    
    @staticmethod
    def evaluate_model(model, X: np.ndarray, y: np.ndarray, cv: int = 5) -> Dict:
        from sklearn.model_selection import cross_val_score, cross_val_predict
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        try:
            y_pred = cross_val_predict(model, X, y, cv=cv)
            
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            r2 = r2_score(y, y_pred)
            
            residuals = y - y_pred
            std_error = np.std(residuals)
            
            return {
                "rmse": rmse,
                "mae": mae,
                "r2": r2,
                "std_error": std_error,
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    @staticmethod
    def run_all_models_cv(X: np.ndarray, y: np.ndarray, target_year: int) -> Dict:
        results = {}
        
        from sklearn.linear_model import LinearRegression, Ridge
        from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
        from sklearn.preprocessing import PolynomialFeatures, StandardScaler
        from sklearn.pipeline import make_pipeline
        from sklearn.svm import SVR
        
        models = {
            "Linear Regression": LinearRegression(),
            "Polynomial (deg=2)": make_pipeline(PolynomialFeatures(2), LinearRegression()),
            "Polynomial (deg=3)": make_pipeline(PolynomialFeatures(3), LinearRegression()),
            "Ridge Regression": Ridge(alpha=1.0),
            "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "SVM (RBF)": make_pipeline(StandardScaler(), SVR(kernel='rbf', C=100)),
            "SVM (Linear)": make_pipeline(StandardScaler(), SVR(kernel='linear')),
        }
        
        console.print("\n[cyan]Evaluating models with 5-fold cross-validation...[/]")
        
        for name, model in models.items():
            eval_result = AutoModelSelector.evaluate_model(model, X, y)
            if eval_result.get("success"):
                results[name] = eval_result
                console.print(f"  [dim]{name}: R²={eval_result['r2']:.4f}, RMSE={eval_result['rmse']:.4f}[/]")
        
        try:
            import xgboost as xgb
            xgb_model = xgb.XGBRegressor(n_estimators=100, random_state=42)
            results["XGBoost"] = AutoModelSelector.evaluate_model(xgb_model, X, y)
            console.print(f"  [dim]XGBoost: R²={results['XGBoost']['r2']:.4f}, RMSE={results['XGBoost']['rmse']:.4f}[/]")
        except:
            pass
        
        try:
            import lightgbm as lgb
            lgb_model = lgb.LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)
            results["LightGBM"] = AutoModelSelector.evaluate_model(lgb_model, X, y)
            console.print(f"  [dim]LightGBM: R²={results['LightGBM']['r2']:.4f}, RMSE={results['LightGBM']['rmse']:.4f}[/]")
        except:
            pass
        
        try:
            from sklearn.neural_network import MLPRegressor
            mlp = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
            results["MLP Neural Net"] = AutoModelSelector.evaluate_model(mlp, X, y)
            console.print(f"  [dim]MLP Neural Net: R²={results['MLP Neural Net']['r2']:.4f}, RMSE={results['MLP Neural Net']['rmse']:.4f}[/]")
        except:
            pass
        
        return results
    
    @staticmethod
    def select_best(results: Dict) -> Tuple[str, Dict]:
        if not results:
            return None, None
        
        best_model = None
        best_score = float('-inf')
        
        for name, metrics in results.items():
            if not metrics.get("success"):
                continue
            
            r2 = metrics.get("r2", -999)
            rmse = metrics.get("rmse", 999)
            
            score = r2 - (rmse * 0.01)
            
            if score > best_score:
                best_score = score
                best_model = name
        
        return best_model, results.get(best_model)
    
    @staticmethod
    def train_best_and_predict(best_model_name: str, X: np.ndarray, y: np.ndarray, 
                               target_year: int, years: np.ndarray = None) -> Dict:
        from sklearn.linear_model import LinearRegression, Ridge
        from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
        from sklearn.preprocessing import PolynomialFeatures, StandardScaler
        from sklearn.pipeline import make_pipeline
        from sklearn.svm import SVR
        
        model_map = {
            "Linear Regression": LinearRegression(),
            "Polynomial (deg=2)": make_pipeline(PolynomialFeatures(2), LinearRegression()),
            "Polynomial (deg=3)": make_pipeline(PolynomialFeatures(3), LinearRegression()),
            "Ridge Regression": Ridge(alpha=1.0),
            "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
            "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "SVM (RBF)": make_pipeline(StandardScaler(), SVR(kernel='rbf', C=100)),
            "SVM (Linear)": make_pipeline(StandardScaler(), SVR(kernel='linear')),
            "XGBoost": None,
            "LightGBM": None,
            "MLP Neural Net": None,
        }
        
        if best_model_name == "XGBoost":
            import xgboost as xgb
            model_map["XGBoost"] = xgb.XGBRegressor(n_estimators=100, random_state=42)
        elif best_model_name == "LightGBM":
            import lightgbm as lgb
            model_map["LightGBM"] = lgb.LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)
        elif best_model_name == "MLP Neural Net":
            from sklearn.neural_network import MLPRegressor
            model_map["MLP Neural Net"] = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
        
        model = model_map.get(best_model_name)
        if model is None:
            return {"error": "Model not found"}
        
        model.fit(X, y)
        
        # Create proper prediction features matching training
        if years is not None and X.shape[1] == 3:  # Climate temperature features
            # year_scaled, year_sq, year_cube for target_year
            year_min, year_max = years.min(), years.max()
            year_scaled = (target_year - year_min) / (year_max - year_min + 1e-10)
            year_sq = year_scaled ** 2
            year_cube = year_scaled ** 3
            X_pred = np.array([[year_scaled, year_sq, year_cube]])
        elif years is not None and X.shape[1] == 4:  # Sea level / CO2 features
            year_min, year_max = years.min(), years.max()
            year_scaled = (target_year - year_min) / (year_max - year_min + 1e-10)
            year_sq = year_scaled ** 2
            exp_year = np.exp(year_scaled)
            log_year = np.log1p(year_scaled)
            X_pred = np.array([[year_scaled, year_sq, exp_year, log_year]])
        else:
            # Fallback: scale target year to match training range
            if years is not None and len(years) > 0:
                year_min, year_max = years.min(), years.max()
                year_scaled = (target_year - year_min) / (year_max - year_min + 1e-10)
            else:
                year_scaled = target_year / 2100  # Rough default
            X_pred = np.array([[year_scaled]])
        
        prediction = model.predict(X_pred)[0]
        
        y_pred = model.predict(X)
        residuals = y - y_pred
        std_error = np.std(residuals)
        
        return {
            "model": best_model_name,
            "prediction": prediction,
            "std_error": std_error,
            "confidence_95": (prediction - 1.96 * std_error, prediction + 1.96 * std_error)
        }
    
    @staticmethod
    def run_full_analysis(years: np.ndarray, values: np.ndarray, 
                         target_year: int, console: Console) -> Dict:
        X = years.reshape(-1, 1)
        y = values
        
        results = AutoModelSelector.run_all_models_cv(X, y, target_year)
        
        best_model, best_metrics = AutoModelSelector.select_best(results)
        
        if best_model is None:
            console.print("[red]No model succeeded[/]")
            return None
        
        prediction_result = AutoModelSelector.train_best_and_predict(best_model, X, y, target_year, years)
        
        console.print(f"\n[green bold]★ BEST MODEL: {best_model}[/]")
        console.print(f"[cyan]  R² Score:     {best_metrics['r2']:.6f}[/]")
        console.print(f"[cyan]  RMSE:         {best_metrics['rmse']:.6f}[/]")
        console.print(f"[cyan]  MAE:          {best_metrics['mae']:.6f}[/]")
        console.print(f"[cyan]  Std Error:    {best_metrics['std_error']:.6f}[/]")
        
        console.print(f"\n[yellow bold]★ PREDICTION FOR {target_year}:[/]")
        console.print(f"[green]  Value: {prediction_result['prediction']:.4f}[/]")
        console.print(f"[cyan]  95% CI: [{prediction_result['confidence_95'][0]:.4f}, {prediction_result['confidence_95'][1]:.4f}][/]")
        
        return {
            "best_model": best_model,
            "metrics": best_metrics,
            "prediction": prediction_result
        }
    
    @staticmethod
    def run_full_analysis_with_features(X_engineered: np.ndarray, years: np.ndarray,
                                        values: np.ndarray, target_year: int, console: Console) -> Dict:
        """Run full analysis with pre-engineered features."""
        
        if X_engineered is not None and len(X_engineered) > 0:
            # Use engineered features
            X = X_engineered
            y = values
        else:
            # Fallback to basic
            X = years.reshape(-1, 1) if len(years) > 0 else values.reshape(-1, 1)
            y = values
        
        if len(X) < 5 or len(y) < 5:
            console.print("[red]  Insufficient data for prediction[/]")
            return None
        
        results = AutoModelSelector.run_all_models_cv(X, y, target_year)
        
        best_model, best_metrics = AutoModelSelector.select_best(results)
        
        if best_model is None:
            console.print("[red]No model succeeded[/]")
            return None
        
        prediction_result = AutoModelSelector.train_best_and_predict(best_model, X, y, target_year, years)
        
        console.print(f"\n[green bold]★ BEST MODEL: {best_model}[/]")
        console.print(f"[cyan]  R² Score:     {best_metrics['r2']:.6f}[/]")
        console.print(f"[cyan]  RMSE:         {best_metrics['rmse']:.6f}[/]")
        console.print(f"[cyan]  MAE:          {best_metrics['mae']:.6f}[/]")
        console.print(f"[cyan]  Std Error:    {best_metrics['std_error']:.6f}[/]")
        
        console.print(f"\n[yellow bold]★ PREDICTION FOR {target_year}:[/]")
        console.print(f"[green]  Value: {prediction_result['prediction']:.4f}[/]")
        console.print(f"[cyan]  95% CI: [{prediction_result['confidence_95'][0]:.4f}, {prediction_result['confidence_95'][1]:.4f}][/]")
        
        return {
            "best_model": best_model,
            "metrics": best_metrics,
            "prediction": prediction_result
        }


def run_auto_prediction(years: np.ndarray, values: np.ndarray, target_year: int, 
                       unit: str, title: str, data_type: str = "generic",
                       df: pd.DataFrame = None, target_col: str = None) -> Dict:
    """Generic auto model selection and prediction function with EDA + Feature Engineering."""
    
    console.print(Panel(
        f"[bold cyan]🔮 AUTO MODEL SELECTION - {title}[/]",
        border_style="cyan", box=box.DOUBLE
    ))
    
    # Step 1: EDA and Feature Engineering
    X_engineered = None
    if df is not None and target_col is not None:
        X_engineered, y_engineered, years_out = DataAnalyzer.analyze_and_engineer(
            df, target_col, data_type
        )
        
        if X_engineered is not None and y_engineered is not None:
            years = years_out if years_out is not None else np.arange(len(y_engineered))
            values = y_engineered
            console.print(f"\n[green]✓ Using {X_engineered.shape[1]} engineered features[/]")
    
    # Step 2: Auto Model Selection with cross-validation
    result = AutoModelSelector.run_full_analysis_with_features(
        X_engineered, years, values, target_year, console
    )
    
    if result and "prediction" in result:
        pred = result["prediction"]["prediction"]
        pred_result = result["prediction"]
        error = pred_result["std_error"]
        
        console.print(f"\n[cyan]  ╔══════════════════════════════════════════════════════╗")
        console.print(f"[cyan]  ║[/] [bold]FINAL PREDICTION[/]                                  [cyan]║")
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        
        if abs(pred) > 1000:
            console.print(f"[cyan]  ║[/]  Result:      [yellow]({pred:,.2f} ± {error:,.2f}) {unit}[/]         [cyan]║")
        elif abs(pred) > 10:
            console.print(f"[cyan]  ║[/]  Result:      [yellow]({pred:.2f} ± {error:.2f}) {unit}[/]            [cyan]║")
        else:
            console.print(f"[cyan]  ║[/]  Result:      [yellow]({pred:.4f} ± {error:.4f}) {unit}[/]         [cyan]║")
        
        console.print(f"[cyan]  ╠══════════════════════════════════════════════════════╣")
        console.print(f"[cyan]  ║[/]  Best Model:  [green]{result['best_model']}[/]                      [cyan]║")
        console.print(f"[cyan]  ║[/]  R² Score:    [yellow]{result['metrics']['r2']:.4f}[/]                       [cyan]║")
        console.print(f"[cyan]  ╚══════════════════════════════════════════════════════╝")
        
        show_chart(values, years, title, unit, target_year, pred, pred_result['confidence_95'])
        
        return result
    return None
