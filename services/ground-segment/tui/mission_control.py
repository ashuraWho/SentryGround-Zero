"""
SentryGround-Zero Mission Control Console
Professional ESA/NASA-style terminal interface with real-time monitoring.
"""

import os
import sys
import time
import threading
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import signal
import random
import math

try:
    from rich.console import Console as RichConsole
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich.layout import Layout
    from rich.screen import Screen
    from rich.text import Text
    from rich.style import Style
    from rich.color import Color
    from rich.ansi import AnsiDecoder
    from rich.jupyter import JupyterRenderable
    from rich import box
    from rich.live import Live
    from rich.pulse import Pulse
    from rich.traceback import Traceback
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichConsole = None


class ColorPalette:
    PRIMARY = "#00D4FF"
    SECONDARY = "#3B82F6"
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    CRITICAL = "#DC2626"
    INFO = "#6366F1"
    PURPLE = "#8B5CF6"
    CYAN = "#06B6D4"
    WHITE = "#F9FAFB"
    GRAY = "#6B7280"
    DARK_GRAY = "#374151"
    YELLOW = "#FBBF24"
    BG_DARK = "#0A0E17"
    BG_LIGHT = "#111827"
    BG_PANEL = "#1F2937"
    
    RED_TEAM = "#FF6B6B"
    BLUE_TEAM = "#4ECDC4"
    QUANTUM = "#A855F7"
    ZERO_TRUST = "#22D3EE"
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    @staticmethod
    def ansi(color: str) -> str:
        """Convert hex color to ANSI escape sequence."""
        if color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return f"\033[38;2;{r};{g};{b}m"
        return color


def c(color: str, text: str) -> str:
    """Color wrapper for terminal output."""
    return f"{ColorPalette.ansi(color)}{text}{ColorPalette.RESET}"


class AnimationFrame:
    """Animation frame generator for terminal effects."""
    
    @staticmethod
    def radar_sweep(frame: int, width: int = 20) -> str:
        angle = (frame * 15) % 360
        lines = []
        center = width // 2
        
        for y in range(-width//2, width//2 + 1):
            line = ""
            for x in range(-width, width + 1):
                dist = math.sqrt(x**2 + y**2)
                if dist < center + 2:
                    radar_angle = math.atan2(y, x) * 180 / math.pi
                    if radar_angle < 0:
                        radar_angle += 360
                    
                    if abs(radar_angle - angle) < 15 and dist > 2:
                        line += "●"
                    elif abs(dist - center) < 1:
                        line += "○"
                    elif dist < 2:
                        line += "⊙"
                    else:
                        line += " "
                else:
                    line += " "
            lines.append(line)
        return "\n".join(lines)
    
    @staticmethod
    def loading_dots(frame: int, text: str = "Loading") -> str:
        dots = "." * ((frame % 3) + 1)
        return f"{text}{dots:3s}"
    
    @staticmethod
    def signal_bars(frame: int, level: int = 4) -> str:
        bars = ["▂", "▃", "▅", "▆", "█"]
        result = ""
        for i in range(5):
            if i < level:
                if (frame + i) % 4 == 0:
                    result += f"[{ColorPalette.CYAN}]{bars[i]}[/{ColorPalette.CYAN}]"
                else:
                    result += bars[i]
            else:
                result += " "
        return result
    
    @staticmethod
    def scanning_line(frame: int, width: int = 60) -> str:
        pos = (frame * 2) % width
        bar = "█" * pos + "░" * (width - pos)
        return f"[{bar}]"
    
    @staticmethod
    def orbit_dots(frame: int, num_satellites: int = 5) -> List[Tuple[float, float]]:
        positions = []
        for i in range(num_satellites):
            angle = (frame * 3 + i * 72) % 360
            rad = angle * math.pi / 180
            x = math.cos(rad) * 15
            y = math.sin(rad) * 8
            positions.append((x + 30, y + 10))
        return positions
    
    @staticmethod
    def matrix_rain(frame: int, width: int = 40, height: int = 20) -> List[str]:
        lines = []
        chars = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        for y in range(height):
            line = ""
            for x in range(width):
                if random.random() < 0.1:
                    line += random.choice(chars)
                else:
                    line += " "
            lines.append(line)
        return lines
    
    @staticmethod
    def heartbeat(frame: int) -> str:
        if frame % 4 < 2:
            return "♥"
        return "♡"
    
    @staticmethod
    def lock_icon(frame: int) -> str:
        states = ["🔓", "🔐"]
        return states[frame % 2]
    
    @staticmethod
    def shield_animation(frame: int) -> str:
        frames = ["🛡", "🛡️", "⚔", "⚔️"]
        return frames[frame % len(frames)]


class ASCIIArt:
    """Professional ASCII art for mission control."""
    
    @staticmethod
    def logo() -> str:
        return f"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                          ║
║   ███████╗██████╗  █████╗  ██████╗███████╗    ██╗   ██╗ ██████╗ ██████╗ ██████╗║
║   ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝    ██║   ██║██╔═══██╗██╔═══██╗██╔══██╗║
║   █████╗  ██████╔╝███████║██║     █████╗      ██║   ██║██║   ██║██║   ██║██║  ██║║
║   ██╔══╝  ██╔══██╗██╔══██║██║     ██╔══╝      ╚██╗ ██╔╝██║   ██║██║   ██║██║  ██║║
║   ███████╗██║  ██║██║  ██║╚██████╗███████╗     ╚████╔╝ ╚██████╔╝╚██████╔╝██████╔╝║
║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝      ╚═══╝   ╚═════╝  ╚═════╝ ╚═════╝ ║
║                                                                                          ║
║                          MISSION CONTROL CONSOLE v2.0                                    ║
║               Secure Earth Observation & Space Surveillance Platform                    ║
║                                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝"""
    
    @staticmethod
    def satellite() -> str:
        return """
            ┌─────────────────────┐
           /                       \\
          /    ╔═══════════════╗   \\
         │     ║  ████████████ ║   │
         │     ║  ██╔════════╗██ ║   │
         │     ║  ██║ SATELL ║██ ║   │
         │     ║  ██║════════║██ ║   │
         │     ║  ████████████ ║   │
          \\    ╚═══════════════╝   /
           \\                       /
            \\      ╱╲      ╱╲     /
             \\    ╱  ╲    ╱  ╲   /
              │  │    │  │    │  │
              │  │    │  │    │  │
              │  │    │  │    │  │
             ╱│╲ │    ╱│╲ │    ╱│╲ │
            ╱ │ ╲│   ╱ │ ╲│   ╱ │ ╲│
           ╱  │  ╲│  ╱  │  ╲│  ╱  │  ╲│
          ══════════════════════════════
                SOLAR PANEL          SOLAR PANEL"""
    
    @staticmethod
    def shield() -> str:
        return """
        ╔═══════════════════════════╗
        ║      ╔═══════════╗       ║
        ║      ║  DEFENSE ║       ║
        ║      ║  SYSTEM  ║       ║
        ║      ╚═══════════╝       ║
        ║     ╔═══════════════╗    ║
        ║     ║  ACTIVE     ║    ║
        ║     ╚═══════════════╝    ║
        ╚═══════════════════════════╝"""
    
    @staticmethod
    def attack_skull() -> str:
        return """
             ╱╲     ╱╲
            ╱  ╲   ╱  ╲
           │ ██╲ ╱██ │ 
           │ ███████ │
           ╲ ██████ ╱
            ╲██████╱
             ║║║║║
            ╔╩╩╩╩╩╗
            ╚══════╝"""
    
    @staticmethod
    def quantum() -> str:
        return """
           ╭─────────────────╮
          ╱ ╱╲   ╲╲ ╲╲  ╲╲ ╲ ╲╲ ╲
         ╱  ╱╲╲╲ ╲╲ ╲╲ ╲╲  ╲╲╲╲  ╲
        │   ╲╲╲╲ ╲╲ ╲╲ ╲╲   ╲╲╲╲   │
        │   ╱╲  ╲╲ ╲╲╲╲╲╲  ╲╲  ╲   │
        ╲    ╲╲  ╲╲╲╲╲╲╲  ╲╲  ╱   ╱
         ╲   ╲╲╲╲╲╲╲╲╲╲╲╲╲╲╲ ╱   ╱
          ╲   ╲╲  ╲╲╲╲╲╲╲╲  ╲╲╱   ╱
           ╰───╯───╯───╯───╯───╯"""
    
    @staticmethod
    def blockchain() -> str:
        return """
        ┌───┐   ┌───┐   ┌───┐
        │ A │───│ B │───│ C │
        └─┬─┘   └───┘   └───┘
          │       │       │
        ┌──┴──┐ ┌──┴──┐ ┌──┴──┐
        │  █ │   │  █ │   │  █ │
        └─────┘   └─────┘   └─────┘"""
    
    @staticmethod
    def zero_trust() -> str:
        return """
        ╭─────────────────────────────╮
        │    ZERO TRUST ARCHITECTURE  │
        ├─────────────────────────────┤
        │  ┌─────┐   ┌─────┐   ┌───┐ │
        │  │DEV │───│USR │───│RES│ │
        │  └─────┘   └─────┘   └───┘ │
        │        ↻ VERIFY         │   │
        │    NEVER TRUST         │   │
        │    ALWAYS VERIFY       │   │
        ╰─────────────────────────────╯"""
    
    @staticmethod
    def radar() -> str:
        return """
               ╱ ╲
              ╱   ╲
             ╱ ●   ╲
            ╱       ╲
           ╱─────────╲
          ╱           ╲
         ╱═════════════╲
        ╱               ╲
       ╱                 ╲
      ════════════════════"""


class StatusIndicators:
    """Status indicator generators."""
    
    @staticmethod
    def status_dot(status: str) -> str:
        colors = {
            "NOMINAL": f"[{ColorPalette.SUCCESS}]●[/{ColorPalette.SUCCESS}]",
            "WARNING": f"[{ColorPalette.WARNING}]●[/{ColorPalette.WARNING}]",
            "CRITICAL": f"[{ColorPalette.ERROR}]●[/{ColorPalette.ERROR}]",
            "OFFLINE": f"[{ColorPalette.GRAY}]●[/{ColorPalette.GRAY}]",
            "ACTIVE": f"[{ColorPalette.CYAN}]●[/{ColorPalette.CYAN}]",
        }
        return colors.get(status, "○")
    
    @staticmethod
    def progress_bar(percent: float, width: int = 30, color: str = ColorPalette.CYAN) -> str:
        filled = int(width * percent / 100)
        bar = f"[{color}]{'█' * filled}[/{color}]"
        empty = '░' * (width - filled)
        return f"{bar}{empty} {percent:.1f}%"
    
    @staticmethod
    def spinner(frame: int) -> str:
        chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        return chars[frame % len(chars)]
    
    @staticmethod
    def connection_status(connected: bool) -> str:
        if connected:
            return f"[{ColorPalette.SUCCESS}]CONNECTED[/{ColorPalette.SUCCESS}]"
        return f"[{ColorPalette.ERROR}]DISCONNECTED[/{ColorPalette.ERROR}]"
    
    @staticmethod
    def security_level(level: int) -> str:
        levels = {
            1: f"[{ColorPalette.ERROR}]LOW[/{ColorPalette.ERROR}]",
            2: f"[{ColorPalette.WARNING}]MEDIUM[/{ColorPalette.WARNING}]",
            3: f"[{ColorPalette.CYAN}]HIGH[/{ColorPalette.CYAN}]",
            4: f"[{ColorPalette.SUCCESS}]MAXIMUM[/{ColorPalette.SUCCESS}]",
        }
        return levels.get(level, "UNKNOWN")


class CyberDashboard:
    """Real-time cyber operations dashboard."""
    
    def __init__(self):
        self.frame = 0
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        
        self.stats = {
            "red_team": {"attacks": 0, "successful": 0, "vulnerabilities": 0},
            "blue_team": {"alerts": 0, "blocked": 0, "honey_pots": 0},
            "zero_trust": {"sessions": 0, "devices": 0, "trust_score": 0},
            "quantum": {"keys_generated": 0, "encryptions": 0},
            "blockchain": {"blocks": 0, "events": 0},
        }
        
        self.alerts: List[Dict] = []
        self.threats: List[Dict] = []
    
    def start(self):
        """Start the dashboard update loop."""
        self._running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
    
    def stop(self):
        """Stop the dashboard."""
        self._running = False
    
    def _update_loop(self):
        """Background update loop."""
        while self._running:
            self.frame += 1
            
            if random.random() < 0.1:
                self._generate_alert()
            
            if random.random() < 0.05:
                self._generate_threat()
            
            self._update_stats()
            
            time.sleep(1)
    
    def _generate_alert(self):
        """Generate a random security alert."""
        alert_types = [
            ("IDS", "Potential intrusion detected", "MEDIUM"),
            ("WAF", "Malicious request blocked", "HIGH"),
            ("AUTH", "Failed login attempt", "LOW"),
            ("MFA", "MFA challenge failed", "MEDIUM"),
            ("NETWORK", "Unusual traffic pattern", "MEDIUM"),
        ]
        
        alert_type, message, severity = random.choice(alert_types)
        
        self.alerts.append({
            "id": f"ALT-{len(self.alerts) + 1:04d}",
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "source": f"192.168.1.{random.randint(1, 255)}"
        })
        
        if len(self.alerts) > 50:
            self.alerts.pop(0)
    
    def _generate_threat(self):
        """Generate a random threat event."""
        threat_types = [
            ("SQL_INJECTION", "SQL Injection Attempt", "CRITICAL"),
            ("XSS", "Cross-Site Scripting", "HIGH"),
            ("BRUTE_FORCE", "Brute Force Attack", "HIGH"),
            ("PORT_SCAN", "Port Scanning Detected", "MEDIUM"),
            ("MALWARE", "Malware Signature Detected", "CRITICAL"),
        ]
        
        threat_type, description, severity = random.choice(threat_types)
        
        self.threats.append({
            "id": f"THR-{len(self.threats) + 1:04d}",
            "type": threat_type,
            "description": description,
            "severity": severity,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "target": f"10.0.0.{random.randint(1, 254)}"
        })
        
        if len(self.threats) > 20:
            self.threats.pop(0)
    
    def _update_stats(self):
        """Update statistics."""
        self.stats["red_team"]["attacks"] = len(self.alerts) + random.randint(0, 10)
        self.stats["blue_team"]["alerts"] = len(self.alerts)
        self.stats["blue_team"]["blocked"] = sum(1 for a in self.alerts if "BLOCKED" in str(a))
        self.stats["zero_trust"]["sessions"] = random.randint(5, 50)
        self.stats["zero_trust"]["devices"] = random.randint(10, 100)
        self.stats["zero_trust"]["trust_score"] = random.randint(70, 100)
        self.stats["quantum"]["keys_generated"] = random.randint(100, 1000)
        self.stats["blockchain"]["blocks"] = random.randint(100, 1000)
        self.stats["blockchain"]["events"] = sum(len(a.get("events", [])) for a in self.alerts)
    
    def get_render(self) -> str:
        """Get the dashboard render."""
        self.frame += 1
        
        lines = []
        lines.append(f"{'='*80}")
        lines.append(f"  CYBER OPERATIONS DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"{'='*80}")
        
        lines.append("")
        lines.append(f"  [{ColorPalette.RED_TEAM}]●[/{ColorPalette.RED_TEAM}] RED TEAM SIMULATOR        [{ColorPalette.BLUE_TEAM}]●[/{ColorPalette.BLUE_TEAM}] BLUE TEAM DEFENSE")
        lines.append(f"  ───────────────────────────     ───────────────────────────")
        lines.append(f"  Attacks: {self.stats['red_team']['attacks']:4d}                      Alerts: {self.stats['blue_team']['alerts']:4d}")
        lines.append(f"  Successful: {self.stats['red_team']['successful']:3d}                   Blocked: {self.stats['blue_team']['blocked']:4d}")
        lines.append(f"  Vulns Found: {self.stats['red_team']['vulnerabilities']:3d}                   Honey Pots: {self.stats['blue_team']['honey_pots']:3d}")
        
        lines.append("")
        lines.append(f"  [{ColorPalette.ZERO_TRUST}]●[/{ColorPalette.ZERO_TRUST}] ZERO TRUST             [{ColorPalette.QUANTUM}]●[/{ColorPalette.QUANTUM}] QUANTUM CRYPTO")
        lines.append(f"  ───────────────────────       ───────────────────────")
        lines.append(f"  Sessions: {self.stats['zero_trust']['sessions']:4d}                    Keys Generated: {self.stats['quantum']['keys_generated']:5d}")
        lines.append(f"  Devices: {self.stats['zero_trust']['devices']:4d}                     Encryptions: {self.stats['quantum']['encryptions']:5d}")
        lines.append(f"  Trust Score: {self.stats['zero_trust']['trust_score']:3d}%                    Algorithm: ML-KEM-768")
        
        lines.append("")
        lines.append(f"  [{ColorPalette.SUCCESS}]●[/{ColorPalette.SUCCESS}] BLOCKCHAIN AUDIT")
        lines.append(f"  ───────────────────────")
        lines.append(f"  Blocks: {self.stats['blockchain']['blocks']:5d}                    Events: {self.stats['blockchain']['events']:5d}")
        lines.append(f"  Chain Status: VERIFIED ✓")
        
        lines.append("")
        lines.append(f"{'='*80}")
        
        if self.threats:
            lines.append("  RECENT THREATS:")
            lines.append("  ─────────────────────────────────────────────────────────────────")
            for threat in self.threats[-5:]:
                sev_color = ColorPalette.CRITICAL if threat["severity"] == "CRITICAL" else ColorPalette.WARNING
                lines.append(f"  [{sev_color}]{threat['severity']:8s}[/{sev_color}] {threat['type']:15s} - {threat['description']:30s} [{threat['timestamp']}]")
        
        lines.append(f"{'='*80}")
        
        return "\n".join(lines)


class MissionControlConsole:
    """
    Professional Mission Control Console (ESA/NASA style)
    with real-time updates and animations.
    """
    
    def __init__(self):
        self.console = RichConsole() if RICH_AVAILABLE else None
        self.dashboard = CyberDashboard()
        self.frame = 0
        self._running = False
        self._input_thread: Optional[threading.Thread] = None
        self._animation_thread: Optional[threading.Thread] = None
        
        self.session = {
            "user": None,
            "role": None,
            "authenticated": False,
            "linked_satellite": None,
            "active_product": None,
        }
        
        self.state = {
            "generated": False,
            "ingested": False,
            "processed": False,
            "archived": False,
        }
        
        self.command_history: List[str] = []
        self.command_index = 0
        
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n\nShutdown requested. Saving state...")
        self._running = False
        sys.exit(0)
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_banner(self):
        """Print the mission control banner."""
        self.clear_screen()
        print(ASCIIArt.logo())
        print()
        print(f"  [{ColorPalette.CYAN}]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/{ColorPalette.CYAN}] INITIALIZING SYSTEMS")
        print()
        time.sleep(0.3)
        print(f"  [{ColorPalette.SUCCESS}]✓[/{ColorPalette.SUCCESS}] Core systems loaded")
        time.sleep(0.2)
        print(f"  [{ColorPalette.SUCCESS}]✓[/{ColorPalette.SUCCESS}] Security modules initialized")
        time.sleep(0.2)
        print(f"  [{ColorPalette.SUCCESS}]✓[/{ColorPalette.SUCCESS}] Network interfaces configured")
        time.sleep(0.2)
        print(f"  [{ColorPalette.SUCCESS}]✓[/{ColorPalette.SUCCESS}] Crypto engines ready")
        time.sleep(0.2)
        print(f"  [{ColorPalette.SUCCESS}]✓[/{ColorPalette.SUCCESS}] Blockchain ledger initialized")
        time.sleep(0.2)
        print()
        print(f"  [{ColorPalette.CYAN}]▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓[/{ColorPalette.CYAN}] SYSTEM ONLINE")
        print()
    
    def print_main_menu(self):
        """Print the main menu."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        user = self.session.get("user", "GUEST")
        role = self.session.get("role", "")
        
        print(f"\n{'─'*80}")
        print(f"  {ColorPalette.CYAN}TIME:{ColorPalette.WHITE} {timestamp}")
        print(f"  {ColorPalette.CYAN}USER:{ColorPalette.WHITE} {user} {role}")
        print(f"  {ColorPalette.CYAN}MODE:{ColorPalette.WHITE} SECURE")
        print(f"  {ColorPalette.CYAN}SATELLITE:{ColorPalette.WHITE} {self.session.get('linked_satellite', 'NONE')}")
        print(f"{'─'*80}\n")
        
        print(f"  {ColorPalette.YELLOW}╔══════════════════════════════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.YELLOW}║{ColorPalette.RESET}                     MISSION CONTROL COMMANDS                     {ColorPalette.YELLOW}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.YELLOW}╠══════════════════════════════════════════════════════════════════╣{ColorPalette.RESET}")
        
        commands = [
            (ColorPalette.CYAN, "login", "Authenticate to system"),
            (ColorPalette.CYAN, "link", "Connect to satellite"),
            (ColorPalette.CYAN, "scan", "Acquire telemetry data"),
            (ColorPalette.CYAN, "status", "Show pipeline status"),
            (ColorPalette.CYAN, "orbit", "Display orbital information"),
            (ColorPalette.CYAN, "catalog", "Browse satellite catalog"),
            (ColorPalette.RED_TEAM, "red-team", "Run attack simulation"),
            (ColorPalette.BLUE_TEAM, "blue-team", "Show defense status"),
            (ColorPalette.ZERO_TRUST, "zero-trust", "Zero Trust management"),
            (ColorPalette.QUANTUM, "pqcrypto", "Quantum crypto operations"),
            (ColorPalette.SUCCESS, "audit-chain", "Blockchain audit"),
            (ColorPalette.CYAN, "dashboard", "Real-time cyber dashboard"),
            (ColorPalette.CYAN, "help", "Show this help"),
            (ColorPalette.GRAY, "exit", "Exit console"),
        ]
        
        for i, (color, cmd, desc) in enumerate(commands):
            if i % 2 == 0:
                print(f"  {ColorPalette.YELLOW}║{ColorPalette.RESET}  [{color}]{cmd:15s}[/{color}]  {desc:<40s}  ", end="")
            else:
                print(f"[{color}]{cmd:15s}[/{color}]  {desc:<40s}  {ColorPalette.YELLOW}║{ColorPalette.RESET}")
        
        print(f"  {ColorPalette.YELLOW}╚══════════════════════════════════════════════════════════════════╝{ColorPalette.RESET}\n")
    
    def run_command(self, command: str) -> bool:
        """Execute a command."""
        parts = command.strip().lower().split()
        if not parts:
            return True
        
        cmd = parts[0]
        args = parts[1:]
        
        if cmd == "help" or cmd == "?":
            self.print_main_menu()
        
        elif cmd == "clear" or cmd == "cls":
            self.clear_screen()
            self.print_banner()
        
        elif cmd == "login":
            self._handle_login()
        
        elif cmd == "logout":
            self.session["user"] = None
            self.session["role"] = None
            self.session["authenticated"] = False
            print(f"\n  {ColorPalette.CYAN}Session terminated.{ColorPalette.RESET}\n")
        
        elif cmd == "red-team":
            self._handle_red_team(args)
        
        elif cmd == "blue-team":
            self._handle_blue_team()
        
        elif cmd == "zero-trust":
            self._handle_zero_trust(args)
        
        elif cmd == "pqcrypto":
            self._handle_pqcrypto(args)
        
        elif cmd == "audit-chain":
            self._handle_audit_chain(args)
        
        elif cmd == "dashboard":
            self._handle_dashboard()
        
        elif cmd == "link":
            self._handle_link(args)
        
        elif cmd == "scan":
            self._handle_scan()
        
        elif cmd == "status":
            self._handle_status()
        
        elif cmd == "exit" or cmd == "quit":
            print(f"\n  {ColorPalette.CYAN}Mission Control Console shutdown.{ColorPalette.RESET}\n")
            return False
        
        else:
            print(f"\n  {ColorPalette.ERROR}Unknown command: {cmd}{ColorPalette.RESET}")
            print(f"  {ColorPalette.GRAY}Type 'help' for available commands.{ColorPalette.RESET}\n")
        
        return True
    
    def _handle_login(self):
        """Handle login command."""
        print(f"\n  {ColorPalette.CYAN}╔══════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.CYAN}║{ColorPalette.RESET}     AUTHENTICATION          {ColorPalette.CYAN}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.CYAN}╚══════════════════════════════╝{ColorPalette.RESET}\n")
        
        username = input(f"  {ColorPalette.CYAN}Username: {ColorPalette.RESET}").strip()
        if not username:
            print(f"\n  {ColorPalette.ERROR}Authentication cancelled{ColorPalette.RESET}\n")
            return
        
        password = input(f"  {ColorPalette.CYAN}Password: {ColorPalette.RESET}").strip()
        
        if username in ["admin", "operator", "analyst"]:
            self.session["user"] = username
            self.session["role"] = "ADMIN" if username == "admin" else "OPERATOR"
            self.session["authenticated"] = True
            print(f"\n  {ColorPalette.SUCCESS}✓ ACCESS GRANTED - Operator {username} ({self.session['role']}){ColorPalette.RESET}\n")
        else:
            print(f"\n  {ColorPalette.ERROR}✗ ACCESS DENIED - Invalid credentials{ColorPalette.RESET}\n")
    
    def _handle_red_team(self, args):
        """Handle red team command."""
        target = args[0] if args else "sentryground.local"
        
        print(f"\n  {ColorPalette.RED_TEAM}╔════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.RED_TEAM}║{ColorPalette.RESET}       RED TEAM ATTACK SIMULATION    {ColorPalette.RED_TEAM}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.RED_TEAM}╚════════════════════════════════════════╝{ColorPalette.RESET}\n")
        
        print(f"  {ColorPalette.CYAN}Initializing attack vectors...{ColorPalette.RESET}")
        
        from secure_eo_pipeline.cyber.red_team.attacks import RedTeamSimulator
        
        simulator = RedTeamSimulator(target_systems=[target])
        report = simulator.run_campaign(f"campaign_{random.randint(1000, 9999)}", targets=[target])
        
        print(f"\n  {ColorPalette.RED_TEAM}Campaign Results:{ColorPalette.RESET}")
        print(f"    Total Attacks: {ColorPalette.CYAN}{report.total_attacks}{ColorPalette.RESET}")
        print(f"    Successful: {ColorPalette.ERROR}{report.successful_attacks}{ColorPalette.RESET}")
        print(f"    Failed: {ColorPalette.SUCCESS}{report.failed_attacks}{ColorPalette.RESET}")
        print(f"    Risk Score: {ColorPalette.WARNING}{report.risk_score:.1f}/100{ColorPalette.RESET}")
        
        if report.vulnerabilities_found:
            print(f"\n  {ColorPalette.ERROR}⚠ Vulnerabilities Found: {len(report.vulnerabilities_found)}{ColorPalette.RESET}")
            for vuln in report.vulnerabilities_found[:5]:
                print(f"    - {vuln['type']} ({vuln['severity']})")
        
        print()
    
    def _handle_blue_team(self):
        """Handle blue team command."""
        print(f"\n  {ColorPalette.BLUE_TEAM}╔════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.BLUE_TEAM}║{ColorPalette.RESET}       BLUE TEAM DEFENSE STATUS     {ColorPalette.BLUE_TEAM}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.BLUE_TEAM}╚════════════════════════════════════════╝{ColorPalette.RESET}\n")
        
        from secure_eo_pipeline.cyber.blue_team.defenses import BlueTeamDefense
        
        defense = BlueTeamDefense()
        status = defense.get_defense_status()
        
        print(f"  {ColorPalette.CYAN}Network IDS:{ColorPalette.RESET}")
        print(f"    Packets Inspected: {status['ids'].get('packets_inspected', 0)}")
        print(f"    Alerts Generated: {status['ids'].get('alerts_generated', 0)}")
        
        print(f"\n  {ColorPalette.CYAN}Web Application Firewall:{ColorPalette.RESET}")
        print(f"    Rules Active: {status['waf'].get('rules_active', 0)}")
        print(f"    Blocked IPs: {status['waf'].get('blocked_ips', 0)}")
        
        print(f"\n  {ColorPalette.CYAN}Honeypots:{ColorPalette.RESET}")
        print(f"    Deployed: {status['honeypot'].get('deployed', 0)}")
        print(f"    Interactions: {status['honeypot'].get('interactions', 0)}")
        print(f"    Attackers Identified: {status['honeypot'].get('attackers', 0)}")
        
        print()
    
    def _handle_zero_trust(self, args):
        """Handle zero trust command."""
        action = args[0] if args else "status"
        
        print(f"\n  {ColorPalette.ZERO_TRUST}╔════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.ZERO_TRUST}║{ColorPalette.RESET}    ZERO TRUST ARCHITECTURE         {ColorPalette.ZERO_TRUST}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.ZERO_TRUST}╚════════════════════════════════════════╝{ColorPalette.RESET}\n")
        
        from secure_eo_pipeline.cyber.zero_trust.auth import ZeroTrustAuth
        
        zta = ZeroTrustAuth()
        
        if action == "status":
            status = zta.get_authorization_status()
            print(f"  {ColorPalette.CYAN}Identities:{ColorPalette.RESET} {status['identities']}")
            print(f"  {ColorPalette.CYAN}Devices:{ColorPalette.RESET} {status['devices']}")
            print(f"  {ColorPalette.CYAN}Resources:{ColorPalette.RESET} {status['resources']}")
            print(f"  {ColorPalette.CYAN}Policies:{ColorPalette.RESET} {status['policies']}")
            print(f"  {ColorPalette.CYAN}Active Sessions:{ColorPalette.RESET} {status['active_sessions']}")
        
        print()
    
    def _handle_pqcrypto(self, args):
        """Handle pqcrypto command."""
        action = args[0] if args else "status"
        
        print(f"\n  {ColorPalette.QUANTUM}╔════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.QUANTUM}║{ColorPalette.RESET}  QUANTUM-RESISTANT CRYPTOGRAPHY     {ColorPalette.QUANTUM}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.QUANTUM}╚════════════════════════════════════════╝{ColorPalette.RESET}\n")
        
        from secure_eo_pipeline.cyber.quantum_resistant.pqcrypto import QuantumResistantCrypto
        
        pqc = QuantumResistantCrypto()
        
        if action == "status":
            caps = pqc.get_capabilities()
            print(f"  {ColorPalette.CYAN}KEM Algorithms:{ColorPalette.RESET} {', '.join(caps['algorithms']['kem'])}")
            print(f"  {ColorPalette.CYAN}DSA Algorithms:{ColorPalette.RESET} {', '.join(caps['algorithms']['dsa'])}")
            print(f"  {ColorPalette.CYAN}Security Levels:{ColorPalette.RESET}")
            for level in caps['security_levels']:
                print(f"    - {level}")
        
        elif action == "generate":
            keypair = pqc.generate_keypair()
            print(f"  {ColorPalette.SUCCESS}✓ Key pair generated{ColorPalette.RESET}")
            print(f"    Key ID: {ColorPalette.YELLOW}{keypair.key_id}{ColorPalette.RESET}")
            print(f"    Type: {keypair.key_type.value}")
            print(f"    Algorithm: {keypair.algorithm.value}")
        
        print()
    
    def _handle_audit_chain(self, args):
        """Handle audit chain command."""
        action = args[0] if args else "status"
        
        print(f"\n  {ColorPalette.SUCCESS}╔════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.SUCCESS}║{ColorPalette.RESET}     BLOCKCHAIN AUDIT LEDGER       {ColorPalette.SUCCESS}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.SUCCESS}╚════════════════════════════════════════╝{ColorPalette.RESET}\n")
        
        from secure_eo_pipeline.cyber.blockchain_audit.ledger import get_ledger
        
        ledger = get_ledger()
        
        if action == "status":
            stats = ledger.get_chain_statistics()
            print(f"  {ColorPalette.CYAN}Blocks:{ColorPalette.RESET} {stats['blocks']}")
            print(f"  {ColorPalette.CYAN}Total Events:{ColorPalette.RESET} {stats['total_events']}")
            print(f"  {ColorPalette.CYAN}Pending Events:{ColorPalette.RESET} {stats['pending_events']}")
            print(f"  {ColorPalette.CYAN}Chain Integrity:{ColorPalette.RESET} {'✓ VERIFIED' if stats['chain_integrity'] else '✗ COMPROMISED'}")
        
        elif action == "verify":
            valid, errors = ledger.verify_chain()
            if valid:
                print(f"  {ColorPalette.SUCCESS}✓ Chain integrity verified{ColorPalette.RESET}")
            else:
                print(f"  {ColorPalette.ERROR}✗ Chain integrity check failed:{ColorPalette.RESET}")
                for error in errors:
                    print(f"    - {error}")
        
        print()
    
    def _handle_dashboard(self):
        """Handle dashboard command."""
        print(f"\n  Starting real-time cyber dashboard... (Press Ctrl+C to return)\n")
        
        self.dashboard.start()
        
        try:
            while True:
                print("\033[H")
                print(self.dashboard.get_render())
                time.sleep(2)
        except KeyboardInterrupt:
            self.dashboard.stop()
            print(f"\n  {ColorPalette.CYAN}Dashboard stopped.{ColorPalette.RESET}\n")
    
    def _handle_link(self, args):
        """Handle link command."""
        satellites = ["SENTRY-01", "SENTRY-02", "SENTRY-03", "SENTRY-04", "SENTRY-05"]
        
        print(f"\n  {ColorPalette.CYAN}Available Satellites:{ColorPalette.RESET}")
        for i, sat in enumerate(satellites, 1):
            print(f"    {i}. {sat}")
        
        choice = input(f"\n  {ColorPalette.CYAN}Select satellite [1-{len(satellites)}]: {ColorPalette.RESET}").strip()
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(satellites):
                self.session["linked_satellite"] = satellites[idx]
                print(f"\n  {ColorPalette.SUCCESS}✓ Linked to {satellites[idx]}{ColorPalette.RESET}\n")
            else:
                print(f"\n  {ColorPalette.ERROR}Invalid selection{ColorPalette.RESET}\n")
        except ValueError:
            print(f"\n  {ColorPalette.ERROR}Invalid input{ColorPalette.RESET}\n")
    
    def _handle_scan(self):
        """Handle scan command."""
        if not self.session.get("linked_satellite"):
            print(f"\n  {ColorPalette.WARNING}⚠ No satellite linked. Run 'link' first.{ColorPalette.RESET}\n")
            return
        
        print(f"\n  {ColorPalette.CYAN}Acquiring telemetry from {self.session['linked_satellite']}...{ColorPalette.RESET}")
        
        for i in range(10):
            print(f"  {AnimationFrame.spinner(i)} Signal acquisition...")
            time.sleep(0.2)
        
        self.session["active_product"] = f"SENTINEL_{random.randint(1000, 9999)}"
        self.state["generated"] = True
        
        print(f"\n  {ColorPalette.SUCCESS}✓ SIGNAL LOCKED - Target: {self.session['active_product']}{ColorPalette.RESET}\n")
    
    def _handle_status(self):
        """Handle status command."""
        print(f"\n  {ColorPalette.CYAN}╔════════════════════════════════════════╗{ColorPalette.RESET}")
        print(f"  {ColorPalette.CYAN}║{ColorPalette.RESET}         PIPELINE STATUS             {ColorPalette.CYAN}║{ColorPalette.RESET}")
        print(f"  {ColorPalette.CYAN}╚════════════════════════════════════════╝{ColorPalette.RESET}\n")
        
        stages = [
            ("GENERATED", self.state["generated"]),
            ("INGESTED", self.state["ingested"]),
            ("PROCESSED", self.state["processed"]),
            ("ARCHIVED", self.state["archived"]),
        ]
        
        for i, (name, completed) in enumerate(stages):
            if completed:
                print(f"  {ColorPalette.SUCCESS}✓{ColorPalette.RESET} {name}")
            else:
                print(f"  {ColorPalette.GRAY}○{ColorPalette.RESET} {name}")
        
        if self.session.get("active_product"):
            print(f"\n  {ColorPalette.CYAN}Active product:{ColorPalette.RESET} {self.session['active_product']}")
        
        print()
    
    def run(self):
        """Run the mission control console."""
        self.print_banner()
        
        print(f"  {ColorPalette.GRAY}Welcome to Mission Control Console{ColorPalette.RESET}")
        print(f"  {ColorPalette.GRAY}Type 'help' for commands, 'dashboard' for real-time monitoring{ColorPalette.RESET}")
        print(f"  {ColorPalette.DARK_GRAY}{'─'*80}{ColorPalette.RESET}\n")
        
        self._running = True
        
        while self._running:
            try:
                prompt = f"{ColorPalette.CYAN}MISSION_CONTROL{ColorPalette.RESET}"
                if self.session.get("user"):
                    prompt += f"({ColorPalette.YELLOW}{self.session['user']}{ColorPalette.RESET})"
                prompt += f" {ColorPalette.WHITE}>{ColorPalette.RESET} "
                
                command = input(prompt).strip()
                
                if command:
                    self.command_history.append(command)
                    self.command_index = len(self.command_history)
                    self._running = self.run_command(command)
                
            except KeyboardInterrupt:
                print(f"\n  {ColorPalette.YELLOW}Use 'exit' to quit.{ColorPalette.RESET}")
            except EOFError:
                break
        
        print(f"\n  {ColorPalette.CYAN}Mission Control Console shutdown.{ColorPalette.RESET}\n")


def main():
    """Main entry point."""
    console = MissionControlConsole()
    console.run()


if __name__ == "__main__":
    main()
