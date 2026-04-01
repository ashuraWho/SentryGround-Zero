"""
Advanced Mission Control Terminal (TUI)
ESA/NASA-style console with professional aesthetics, autocomplete, and real-time data.
"""

import os
import sys
import time
import asyncio
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import math

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import MenuContainer, MenuItem
from prompt_toolkit.widgets import (
    TextArea, Frame, Box, Label, Button, Dialog,
    CheckboxList, RadioList, ProgressBar
)
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText, to_formatted_text
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.filters import has_focus, to_filter

from rich.console import Console as RichConsole
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.text import Text
from rich.live import Live
from rich.layout import Layout as RichLayout
from rich.columns import Columns
from rich.measure import Measurement
from rich._null_file import NullFile

from cli.session import MissionControlSession
from cli.commands import BaseCommand


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
    BG_DARK = "#0A0E17"
    BG_LIGHT = "#111827"
    BG_PANEL = "#1F2937"


class AnsiColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    GRAY = "\033[90m"
    DARK_GRAY = "\033[90m"


@dataclass
class SatelliteStatus:
    name: str
    regime: str
    altitude: float
    velocity: float
    lat: float
    lon: float
    status: str = "NOMINAL"
    signal_strength: float = 100.0


@dataclass
class SystemMetrics:
    cpu: float = 0.0
    memory: float = 0.0
    network_in: float = 0.0
    network_out: float = 0.0
    disk_usage: float = 0.0
    temperature: float = 35.0
    uptime: str = "00:00:00"


class ASCIIArt:
    """ASCII art generators for visual elements."""
    
    @staticmethod
    def logo() -> str:
        return f"""
{AnsiColors.CYAN}{AnsiColors.BOLD}
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                               ║
    ║   ███████╗██████╗  █████╗  ██████╗███████╗    ██╗   ██╗ ██████╗ ██████╗ ██████╗║
    ║   ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝    ██║   ██║██╔═══██╗██╔═══██╗██╔══██╗║
    ║   █████╗  ██████╔╝███████║██║     █████╗      ██║   ██║██║   ██║██║   ██║██║  ██║║
    ║   ██╔══╝  ██╔══██╗██╔══██║██║     ██╔══╝      ╚██╗ ██╔╝██║   ██║██║   ██║██║  ██║║
    ║   ███████╗██║  ██║██║  ██║╚██████╗███████╗     ╚████╔╝ ╚██████╔╝╚██████╔╝██████╔╝║
    ║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝      ╚═══╝   ╚═════╝  ╚═════╝ ╚═════╝ ║
    ║                                                                               ║
    ║{AnsiColors.WHITE}                      GROUND-ZERO MISSION CONTROL TERMINAL                         {AnsiColors.CYAN}║
    ║{AnsiColors.GRAY}              Secure Earth Observation & Space Surveillance Platform              {AnsiColors.CYAN}║
    ║                                                                               ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝
{AnsiColors.RESET}"""

    @staticmethod
    def satellite() -> str:
        return f"""{AnsiColors.CYAN}
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
          ═══════════════════════════════
                 SOLAR PANEL         SOLAR PANEL
{AnsiColors.RESET}"""

    @staticmethod
    def earth() -> str:
        return f"""{AnsiColors.CYAN}
                         .-~~~-.
                        /       \\
                       (  ◉   ◉   )
                        \\   ▼   /
                         `-...-'
                       .-'       `-.
                      /             \\
                     │   .-------.   │
                     │  / .-==-.  \\   │
                     │ / /  ◉◉  \\ \\  │
                     │ │  ◉   ◉  │ │  │
                     │  \\  ◉◉◉  /  │  │
                     │   \\  ◉  /   │  │
                      \\   `-..-'   /
                       \\    ||    /
                        `.  ||  .'
                          `'||`'
{AnsiColors.RESET}"""

    @staticmethod
    def loading_bar(percent: float, width: int = 40) -> str:
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percent:.1f}%"

    @staticmethod
    def progress_spinner(frame: int = 0) -> str:
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        return spinners[frame % len(spinners)]

    @staticmethod
    def signal_bars(level: int) -> str:
        """Generate signal strength bars (0-5)"""
        filled = "▓" * level
        empty = "░" * (5 - level)
        return f"[{filled}{empty}]"

    @staticmethod
    def orbit_diagram(altitude: float, inclination: float, position: float) -> str:
        """Create ASCII orbit diagram"""
        lines = []
        radius = int(altitude / 1000) if altitude < 40000 else 40
        radius = max(5, min(25, radius))
        
        for y in range(-radius-3, radius+4):
            line = ""
            for x in range(-radius*2-1, radius*2+2):
                dist = math.sqrt(x**2 + y**2)
                angle = math.atan2(y, x)
                
                if abs(dist - radius) < 0.5:
                    if abs(angle - position) < 0.2:
                        line += f"{AnsiColors.YELLOW}●{AnsiColors.RESET}"
                    else:
                        line += f"{AnsiColors.CYAN}○{AnsiColors.RESET}"
                elif dist < 2:
                    line += f"{AnsiColors.BLUE}●{AnsiColors.RESET}"
                else:
                    line += " "
            lines.append(line)
        
        return "\n".join(lines)

    @staticmethod
    def mini_map(sats: List[SatelliteStatus]) -> str:
        """Create mini world map showing satellite positions"""
        lines = ["┌──────────────────────────────────────────────────────────────┐"]
        lines.append("│  180°W    120°W    60°W      0°     60°E    120°E    180°E  │")
        
        lat_bands = [(60, 90), (30, 60), (0, 30), (-30, 0), (-60, -30), (-90, -60)]
        
        for lat_min, lat_max in lat_bands:
            line = "│"
            for lon in range(-180, 181, 10):
                found = False
                for sat in sats:
                    if lat_min <= sat.lat < lat_max:
                        if abs(lon - sat.lon) < 10:
                            if sat.status == "NOMINAL":
                                line += f"{AnsiColors.GREEN}●{AnsiColors.RESET}"
                            elif sat.status == "WARNING":
                                line += f"{AnsiColors.YELLOW}●{AnsiColors.RESET}"
                            else:
                                line += f"{AnsiColors.RED}●{AnsiColors.RESET}"
                            found = True
                            break
                if not found:
                    if lat_max > 66.5 or lat_min < -66.5:
                        line += " "
                    else:
                        line += "·"
            line += " │"
            lines.append(line)
        
        lines.append("│                      ● = Satellite Position                    │")
        lines.append("└──────────────────────────────────────────────────────────────┘")
        return "\n".join(lines)

    @staticmethod
    def status_indicator(status: str) -> str:
        colors = {
            "NOMINAL": f"{AnsiColors.GREEN}●{AnsiColors.RESET}",
            "WARNING": f"{AnsiColors.YELLOW}●{AnsiColors.RESET}",
            "CRITICAL": f"{AnsiColors.RED}●{AnsiColors.RESET}",
            "OFFLINE": f"{AnsiColors.GRAY}●{AnsiColors.RESET}",
        }
        return colors.get(status, f"{AnsiColors.WHITE}●{AnsiColors.RESET}")


class MissionControlTUI:
    """
    Advanced Terminal UI for Mission Control.
    Features: Autocomplete, real-time updates, ASCII art, interactive tables.
    """
    
    def __init__(self):
        self.session = MissionControlSession()
        self.console = RichConsole(file=NullFile())
        
        self.commands = self._build_command_tree()
        self.command_completer = WordCompleter(
            list(self.commands.keys()),
            ignore_case=True,
            meta_dict={
                "login": "Authenticate to the system",
                "logout": "End current session",
                "link": "Connect to satellite",
                "scan": "Acquire telemetry",
                "status": "View pipeline state",
                "orbit": "Show orbital info",
                "ids": "Security scan",
                "health": "System diagnostics",
                "map": "Show satellite positions",
                "clear": "Clear screen",
                "help": "Show help",
                "exit": "Exit terminal",
            }
        )
        
        self.history = InMemoryHistory()
        
        self.key_bindings = KeyBindings()
        self._setup_keybindings()
        
        self._running = True
        self._update_thread: Optional[threading.Thread] = None
        
        self.metrics = SystemMetrics()
        self.satellites: List[SatelliteStatus] = []
        
        self._init_demo_data()
    
    def _init_demo_data(self):
        """Initialize demo satellite data"""
        self.satellites = [
            # === EARTH & CLIMATE ===
            SatelliteStatus("SENTRY-01", "LEO", 550.0, 7.6, 45.2, 9.1),
            SatelliteStatus("SENTRY-03", "MEO", 20100.0, 3.9, 12.3, 15.8),
            SatelliteStatus("SENTRY-05", "HEO", 12000.0, 5.2, -45.0, 120.0),
            SatelliteStatus("SENTRY-28", "LEO", 400.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-22", "LEO", 400.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-06", "GEO", 35786.0, 3.1, 0.0, 0.0),
            SatelliteStatus("SENTRY-04", "GEO", 35786.0, 3.1, 0.0, 0.0),
            # === AIR & WATER QUALITY ===
            SatelliteStatus("SENTRY-18", "LEO", 300.0, 8.0, 41.0, 12.0),
            SatelliteStatus("SENTRY-17", "LEO", 400.0, 7.9, 17.0, 79.0),
            # === POLLUTION & HUMAN IMPACT ===
            SatelliteStatus("SENTRY-16", "LEO", 600.0, 7.7, 0.0, 0.0),
            SatelliteStatus("SENTRY-21", "LEO", 350.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-20", "LEO", 400.0, 7.9, 0.0, 0.0),
            # === WEATHER & AGRICULTURE ===
            SatelliteStatus("SENTRY-15", "LEO", 400.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-14", "LEO", 500.0, 7.8, 0.0, 0.0),
            SatelliteStatus("SENTRY-19", "LEO", 350.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-02", "LEO", 540.0, 7.6, -23.5, -46.6),
            # === NATURAL DISASTERS ===
            SatelliteStatus("SENTRY-07", "GEO", 35786.0, 3.1, 25.0, -80.0),
            SatelliteStatus("SENTRY-27", "LEO", 500.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-29", "LEO", 500.0, 7.9, 0.0, 0.0),
            SatelliteStatus("SENTRY-30", "LEO", 450.0, 7.9, 0.0, 0.0),
            # === SPACE & ASTRONOMY ===
            SatelliteStatus("SENTRY-23", "HEO", 10000.0, 5.5, 0.0, 0.0),
            SatelliteStatus("SENTRY-24", "HEO", 15000.0, 4.8, 0.0, 0.0),
            SatelliteStatus("SENTRY-25", "HEO", 12000.0, 5.2, 0.0, 0.0),
            SatelliteStatus("SENTRY-11", "HEO", 10000.0, 5.5, 0.0, 0.0),
            SatelliteStatus("SENTRY-13", "HEO", 15000.0, 4.8, 0.0, 0.0),
            SatelliteStatus("SENTRY-12", "HEO", 12000.0, 5.2, 0.0, 0.0),
            # === ASTEROIDS & NEAR EARTH ===
            SatelliteStatus("SENTRY-09", "HEO", 10000.0, 5.5, 0.0, 0.0),
            SatelliteStatus("SENTRY-10", "LEO", 500.0, 7.8, 0.0, 0.0),
            SatelliteStatus("SENTRY-26", "HEO", 15000.0, 4.8, 0.0, 0.0),
            SatelliteStatus("SENTRY-08", "HEO", 12000.0, 5.2, 0.0, 0.0),
        ]
    
    def _setup_keybindings(self):
        """Setup keyboard shortcuts"""
        
        @self.key_bindings.add(Keys.ControlC)
        def _(event):
            event.app.exit(exception=KeyboardInterrupt)
        
        @self.key_bindings.add(Keys.ControlL)
        def _(event):
            os.system('clear' if os.name == 'posix' else 'cls')
        
        @self.key_bindings.add(Keys.Tab)
        def _(event):
            pass
    
    def _build_command_tree(self) -> Dict[str, str]:
        """Build command lookup tree"""
        return {
            "login": "login [username]",
            "logout": "logout",
            "link": "link [satellite]",
            "scan": "scan [options]",
            "status": "status [satellite]",
            "orbit": "orbit [satellite]",
            "tle": "tle [satellite]",
            "pass": "pass [ground_station]",
            "catalog": "catalog [options]",
            "map": "map [satellite]",
            "health": "health",
            "ids": "ids [options]",
            "security": "security [scan|block|allow]",
            "user": "user [add|list|remove|disable]",
            "backup": "backup [create|restore]",
            "clear": "clear",
            "help": "help [command]",
            "exit": "exit",
            "quit": "exit",
        }
    
    def get_input(self, prompt: str = "MISSION_CONTROL") -> str:
        """Get input with autocomplete and history"""
        try:
            from prompt_toolkit import Prompt
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            
            return Prompt(
                f"{AnsiColors.CYAN}{AnsiColors.BOLD}{prompt}>{AnsiColors.RESET} ",
                completer=self.command_completer,
                history=self.history,
                auto_suggest=AutoSuggestFromHistory(),
                key_bindings=self.key_bindings,
                style=Style.from_dict({
                    'prompt': 'cyan bold',
                    'completions': 'bg:#1F2937 #00D4FF',
                    'completion-menu': 'bg:#111827 #00D4FF',
                }),
            ).prompt()
        except (KeyboardInterrupt, EOFError):
            return "exit"
    
    def print_header(self):
        """Print mission control header"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print(ASCIIArt.logo())
        self._print_status_bar()
    
    def _print_status_bar(self):
        """Print status bar with system metrics"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        user = self.session.current_user or "GUEST"
        role = self.session.current_role or ""
        
        print(f"""
{AnsiColors.DARK_GRAY}{"─" * 80}{AnsiColors.RESET}
 {AnsiColors.CYAN}TIME:{AnsiColors.RESET} {timestamp}  {AnsiColors.CYAN}USER:{AnsiColors.RESET} {user} {role}  {AnsiColors.CYAN}MODE:{AnsiColors.RESET} SECURE
{AnsiColors.DARK_GRAY}{"─" * 80}{AnsiColors.RESET}""")
    
    def print_help(self, command: Optional[str] = None):
        """Print help with professional styling"""
        if command:
            self._print_command_help(command)
        else:
            self._print_general_help()
    
    def _print_general_help(self):
        """Print general help screen"""
        help_text = f"""
{AnsiColors.BOLD}{AnsiColors.CYAN}╔════════════════════════════════════════════════════════════════════════════════════╗{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                              COMMAND REFERENCE                                {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}

{AnsiColors.YELLOW}┌─ AUTHENTICATION ─────────────────────────────────────────────────────────────┐{AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}login{AnsiColors.RESET} <user>         Authenticate to the system                               {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}logout{AnsiColors.RESET}               End current session                                       {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}whoami{AnsiColors.RESET}               Display current user info                                 {AnsiColors.RESET}
{AnsiColors.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{AnsiColors.RESET}

{AnsiColors.YELLOW}┌─ CONSTELLATION ──────────────────────────────────────────────────────────────┐{AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}link{AnsiColors.RESET} <sat>           Connect to satellite node                                 {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}scan{AnsiColors.RESET} [options]       Acquire telemetry from satellite                          {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}status{AnsiColors.RESET}               View data pipeline state                                  {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}catalog{AnsiColors.RESET}              Browse satellite catalog                                 {AnsiColors.RESET}
{AnsiColors.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{AnsiColors.RESET}

{AnsiColors.YELLOW}┌─ ORBITAL MECHANICS ──────────────────────────────────────────────────────────┐{AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}orbit{AnsiColors.RESET} <sat>           Display orbital elements & position                      {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}tle{AnsiColors.RESET} <sat>             Generate TLE for satellite                                {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}pass{AnsiColors.RESET} [options]       Predict passes over ground station                        {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}map{AnsiColors.RESET} [sat]            Show satellite ground track                              {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}collision{AnsiColors.RESET}            Check for collision risks                                {AnsiColors.RESET}
{AnsiColors.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{AnsiColors.RESET}

{AnsiColors.YELLOW}┌─ SCIENCE MODULES ──────────────────────────────────────────────────────────────┐{AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}climate{AnsiColors.RESET} [sim|data]   Climate simulation & data                             {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}cosmology{AnsiColors.RESET}            Cosmological parameters                                  {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}gw{AnsiColors.RESET} [detect|sim]      Gravitational wave analysis                             {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}exoplanet{AnsiColors.RESET}            Exoplanet transit analysis                              {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}darkmatter{AnsiColors.RESET}            Dark matter detection                                    {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}asteroid{AnsiColors.RESET}             Near-Earth object tracking                               {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}spaceweather{AnsiColors.RESET}          Solar activity & space weather                           {AnsiColors.RESET}
{AnsiColors.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{AnsiColors.RESET}

{AnsiColors.YELLOW}┌─ SECURITY ──────────────────────────────────────────────────────────────────┐{AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}ids{AnsiColors.RESET} [scan|report]    Intrusion detection system                              {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}security{AnsiColors.RESET} <action>     Security actions (scan, block, audit)                  {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}audit{AnsiColors.RESET}                View audit log                                          {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}keys{AnsiColors.RESET} [rotate|list]    Key management                                          {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}user{AnsiColors.RESET} <action>         User management                                         {AnsiColors.RESET}
{AnsiColors.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{AnsiColors.RESET}

{AnsiColors.YELLOW}┌─ SYSTEM ───────────────────────────────────────────────────────────────────┐{AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}health{AnsiColors.RESET}                System health diagnostics                                {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}backup{AnsiColors.RESET} [create|restore] Backup management                                         {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}metrics{AnsiColors.RESET}               Display system metrics                                   {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}clear{AnsiColors.RESET}                 Clear screen                                            {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}help{AnsiColors.RESET} [cmd]            Show this help                                          {AnsiColors.RESET}
{AnsiColors.WHITE}│  {AnsiColors.CYAN}exit{AnsiColors.RESET}                  Exit terminal                                           {AnsiColors.RESET}
{AnsiColors.YELLOW}└──────────────────────────────────────────────────────────────────────────────┘{AnsiColors.RESET}

{AnsiColors.BOLD}{AnsiColors.CYAN}╚════════════════════════════════════════════════════════════════════════════════════╝{AnsiColors.RESET}
"""
        print(help_text)
    
    def _print_command_help(self, command: str):
        """Print detailed help for specific command"""
        helps = {
            "login": """
╭───────────────────────────────────────╮
│  {command} - Authenticate to system     │
├───────────────────────────────────────┤
│  Usage: {command} [username]          │
│                                       │
│  Prompts for password interactively.   │
│  Available roles: admin, analyst, user │
│                                       │
│  Examples:                            │
│    {command} admin                    │
│    {command} analyst                  │
╰───────────────────────────────────────╯""",
            "scan": """
╭───────────────────────────────────────╮
│  {command} - Acquire satellite data    │
├───────────────────────────────────────┤
│  Usage: {command} [options]           │
│                                       │
│  Options:                             │
│    --mode <obs_mode>   Observation mode│
│    --duration <sec>    Acquisition time│
│    --product <type>    Product type   │
│                                       │
│  Examples:                            │
│    {command}                          │
│    {command} --mode SAR               │
│    {command} --duration 300           │
╰───────────────────────────────────────╯""",
            "orbit": """
╭───────────────────────────────────────╮
│  {command} - Display orbital data     │
├───────────────────────────────────────┤
│  Usage: {command} [satellite]         │
│                                       │
│  Shows:                               │
│    • Semi-major axis                  │
│    • Eccentricity                     │
│    • Inclination                      │
│    • RAAN, Arg. Perigee               │
│    • Current position                 │
│    • Velocity, Period                  │
╰───────────────────────────────────────╯""",
        }
        
        help_text = helps.get(command.lower(), f"""
╭───────────────────────────────────────╮
│  Help not available for '{command}'    │
╰───────────────────────────────────────╯
        """)
        print(help_text.format(command=command))
    
    def print_satellite_status(self):
        """Print detailed satellite status with ASCII art"""
        print(f"""
{AnsiColors.BOLD}{AnsiColors.CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                              SATELLITE STATUS                                      {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠══════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}""")
        
        for sat in self.satellites:
            status_color = {
                "NOMINAL": AnsiColors.GREEN,
                "WARNING": AnsiColors.YELLOW,
                "CRITICAL": AnsiColors.RED,
            }.get(sat.status, AnsiColors.WHITE)
            
            print(f"""{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {ASCIIArt.status_indicator(sat.status)} {sat.name:<12} │ {sat.regime:<4} │ ALT: {sat.altitude:>8.1f} km │ VEL: {sat.velocity:.2f} km/s {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}    Position: {sat.lat:>7.2f}°N {sat.lon:>8.2f}°E  │ Signal: {ASCIIArt.signal_bars(int(sat.signal_strength/20))} {status_color}{sat.status}{AnsiColors.RESET} {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}    ───────────────────────────────────────────────────────────────────────── {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}""")
        
        print(f"""{AnsiColors.BOLD}{AnsiColors.CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{AnsiColors.RESET}""")
    
    def print_world_map(self, satellite: Optional[str] = None):
        """Print ASCII world map with satellite positions"""
        print(f"""
{AnsiColors.BOLD}{AnsiColors.CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                               GLOBAL SATELLITE TRACKING                              {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠══════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}{AnsiColors.CYAN}{ASCIIArt.mini_map(self.satellites)}{AnsiColors.RESET}{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠══════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  LEGEND: {AnsiColors.GREEN}●{AnsiColors.RESET} NOMINAL  {AnsiColors.YELLOW}●{AnsiColors.RESET} WARNING  {AnsiColors.RED}●{AnsiColors.RESET} CRITICAL  {AnsiColors.GRAY}●{AnsiColors.RESET} OFFLINE                   {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{AnsiColors.RESET}""")
    
    def print_system_metrics(self):
        """Print system metrics in real-time style"""
        cpu_bar = ASCIIArt.loading_bar(self.metrics.cpu, 20)
        mem_bar = ASCIIArt.loading_bar(self.metrics.memory, 20)
        disk_bar = ASCIIArt.loading_bar(self.metrics.disk_usage, 20)
        
        print(f"""
{AnsiColors.BOLD}{AnsiColors.CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                                SYSTEM METRICS                                          {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠══════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  CPU Usage:     {cpu_bar:<45} │ {self.metrics.cpu:.1f}%         {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  Memory:        {mem_bar:<45} │ {self.metrics.memory:.1f}%         {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  Disk Usage:    {disk_bar:<45} │ {self.metrics.disk_usage:.1f}%         {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  Network IN:    {self.metrics.network_in:>10.2f} MB/s    Network OUT: {self.metrics.network_out:>10.2f} MB/s      {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  Temperature:   {self.metrics.temperature:>10.1f} °C       Uptime:      {self.metrics.uptime:>15}    {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{AnsiColors.RESET}""")
    
    def print_security_status(self):
        """Print security status panel"""
        print(f"""
{AnsiColors.BOLD}{AnsiColors.CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                                SECURITY STATUS                                        {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠══════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.GREEN}✓{AnsiColors.RESET} Encryption:         ACTIVE (AES-256-GCM)                                       {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.GREEN}✓{AnsiColors.RESET} Authentication:     ENABLED (Multi-factor available)                         {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.GREEN}✓{AnsiColors.RESET} Firewall:           ACTIVE (iptables + fail2ban)                             {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.GREEN}✓{AnsiColors.RESET} IDS/IPS:            ACTIVE (Suricata + OSSEC)                                {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.GREEN}✓{AnsiColors.RESET} Audit Logging:      ENABLED (Centralized + tamper-proof)                    {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.GREEN}✓{AnsiColors.RESET} Intrusion Alerts:  0 ACTIVE THREATS                                       {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  {AnsiColors.YELLOW}⚠{AnsiColors.RESET} Rate Limiting:     3 IPs TEMPORARILY BLOCKED                                {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{AnsiColors.RESET}""")
    
    def print_pipeline_status(self):
        """Print data pipeline status"""
        stages = [
            ("GENERATED", self.session.state.get("generated", False)),
            ("INGESTED", self.session.state.get("ingested", False)),
            ("PROCESSED", self.session.state.get("processed", False)),
            ("ARCHIVED", self.session.state.get("archived", False)),
        ]
        
        print(f"""
{AnsiColors.BOLD}{AnsiColors.CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                                DATA PIPELINE STATUS                                   {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}╠══════════════════════════════════════════════════════════════════════════════════════╣{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                                                                                     {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}
{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}  """, end="")
        
        for i, (name, completed) in enumerate(stages):
            if completed:
                status = f"{AnsiColors.GREEN}✓{name}{AnsiColors.RESET}"
            else:
                status = f"{AnsiColors.GRAY}○{name}{AnsiColors.RESET}"
            
            if i < len(stages) - 1:
                status += f" {AnsiColors.CYAN}→{AnsiColors.RESET} "
            
            print(status, end="")
        
        print(f"                                                                             {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}")
        print(f"{AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}                                                                                     {AnsiColors.BOLD}{AnsiColors.CYAN}║{AnsiColors.RESET}")
        print(f"{AnsiColors.BOLD}{AnsiColors.CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{AnsiColors.RESET}")
    
    def run_command(self, cmd_line: str) -> bool:
        """Execute a command and return success status"""
        parts = cmd_line.strip().split()
        if not parts:
            return True
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "exit" or cmd == "quit":
            print(f"\n{AnsiColors.CYAN}Session terminated.{AnsiColors.RESET}\n")
            return False
        
        elif cmd == "help" or cmd == "?":
            self.print_help(args[0] if args else None)
        
        elif cmd == "clear" or cmd == "cls":
            os.system('clear' if os.name == 'posix' else 'cls')
            self.print_header()
        
        elif cmd == "map":
            self.print_world_map(args[0] if args else None)
        
        elif cmd == "satellites" or cmd == "status":
            self.print_satellite_status()
        
        elif cmd == "metrics":
            self.print_system_metrics()
        
        elif cmd == "security":
            self.print_security_status()
        
        elif cmd == "pipeline":
            self.print_pipeline_status()
        
        elif cmd == "login":
            user = args[0] if args else None
            if not user:
                user = input(f"{AnsiColors.CYAN}Username: {AnsiColors.RESET}")
            password = input(f"{AnsiColors.CYAN}Password: {AnsiColors.RESET}")
            success = self.session.ac.authenticate(user, password)
            if success:
                self.session.current_user = user
                self.session.current_role = self.session.ac.get_role(user)
                print(f"{AnsiColors.GREEN}✓ Access granted.{AnsiColors.RESET}")
            else:
                print(f"{AnsiColors.RED}✗ Access denied.{AnsiColors.RESET}")
        
        elif cmd == "logout":
            if self.session.current_user:
                print(f"{AnsiColors.CYAN}Goodbye, {self.session.current_user}.{AnsiColors.RESET}")
                self.session.current_user = None
                self.session.current_role = None
            else:
                print(f"{AnsiColors.YELLOW}No active session.{AnsiColors.RESET}")
        
        elif cmd == "health":
            self.session.health()
        
        elif cmd == "ids":
            self.session.run_ids()
        
        elif cmd == "orbit":
            self.session.show_orbit_info()
        
        elif cmd == "catalog":
            self.session.browse_catalog()
        
        elif cmd == "scan":
            self.session.scan()
        
        elif cmd == "status":
            self.session.print_status_panel()
        
        elif cmd == "link":
            self.session.link_satellite()
        
        else:
            print(f"{AnsiColors.RED}Unknown command: {cmd}{AnsiColors.RESET}")
            print(f"{AnsiColors.GRAY}Type 'help' for available commands.{AnsiColors.RESET}")
        
        return True
    
    def _update_metrics_loop(self):
        """Background thread for updating metrics"""
        import random
        while self._running:
            self.metrics.cpu = 20 + random.random() * 40
            self.metrics.memory = 30 + random.random() * 30
            self.metrics.network_in = random.random() * 100
            self.metrics.network_out = random.random() * 50
            self.metrics.disk_usage = 45 + random.random() * 10
            self.metrics.temperature = 35 + random.random() * 10
            
            for sat in self.satellites:
                sat.lat = (sat.lat + random.uniform(-2, 2)) % 90
                sat.lon = (sat.lon + random.uniform(-5, 5)) % 180
                sat.signal_strength = 80 + random.random() * 20
            
            time.sleep(2)
    
    def run(self):
        """Main terminal loop"""
        self.print_header()
        
        self._update_thread = threading.Thread(target=self._update_metrics_loop, daemon=True)
        self._update_thread.start()
        
        print(f"""
{AnsiColors.GRAY}Welcome to Mission Control Terminal{AnsiColors.RESET}
{AnsiColors.GRAY}Type 'help' for commands, 'map' for satellite positions{AnsiColors.RESET}
{AnsiColors.DARK_GRAY}{"─" * 80}{AnsiColors.RESET}
""")
        
        while self._running:
            try:
                cmd = self.get_input("MISSION_CONTROL")
                
                if cmd.strip():
                    self.history.append_string(cmd)
                
                self._running = self.run_command(cmd)
                
            except KeyboardInterrupt:
                print(f"\n{AnsiColors.YELLOW}Use 'exit' to quit.{AnsiColors.RESET}")
            except EOFError:
                break
        
        print(f"\n{AnsiColors.CYAN}Mission Control Terminal shutdown.{AnsiColors.RESET}\n")


def main():
    tui = MissionControlTUI()
    tui.run()


if __name__ == "__main__":
    main()
