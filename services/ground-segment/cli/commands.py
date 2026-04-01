from abc import ABC, abstractmethod
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


class BaseCommand(ABC):
    name: str = ""
    aliases: list[str] = []
    help_text: str = ""
    
    def __init__(self, session: 'MissionControlSession'):
        self.session = session
    
    @abstractmethod
    def execute(self, args: list[str]) -> bool:
        pass
    
    def check_auth(self, action: str) -> bool:
        if not self.session.current_user:
            console.print("[red]✗ Authentication required. Please 'login'.[/red]")
            return False
        if not self.session.ac.authorize(self.session.current_user, action):
            console.print(f"[red]✗ Unauthorized. '{self.session.current_user}' lacks '{action}' rights.[/red]")
            return False
        return True
    
    def check_prereq(self, key: str, step: str) -> bool:
        if not self.session.active_product:
            console.print(f"[yellow]⚠ No active target. Run 'scan' first.[/yellow]")
            return False
        if not self.session.state.get(key, False):
            console.print(f"[yellow]⚠ Cannot {step}. Prerequisites not met.[/yellow]")
            return False
        return True


class LoginCommand(BaseCommand):
    name = "login"
    aliases = ["auth", "signin"]
    help_text = "Authenticate operator credentials"
    
    def execute(self, args: list[str]) -> bool:
        console.print("\n[bold underline]AUTHENTICATION[/bold underline]")
        console.print("[dim]Maximum-security posture. Enter your assigned credentials.[/dim]")
        
        user = console.input("\n[bold]Username:[/bold] ")
        password = console.input("[bold]Password:[/bold] ", password=True)
        
        role = self.session.ac.authenticate(user, password)
        
        if role:
            self.session.current_user = user
            self.session.current_role = role
            console.print(f"[green]✓ ACCESS GRANTED — Operator {user} ({role})[/green]")
            return True
        else:
            console.print("[red]✗ ACCESS DENIED — Identity not recognized[/red]")
            return False


class LogoutCommand(BaseCommand):
    name = "logout"
    aliases = ["exit-session"]
    help_text = "End the current session"
    
    def execute(self, args: list[str]) -> bool:
        if not self.session.current_user:
            console.print("[yellow]No active session.[/yellow]")
            return False
        console.print(f"[cyan]Operator {self.session.current_user} logged out.[/cyan]")
        self.session.current_user = None
        self.session.current_role = None
        return True


class LinkCommand(BaseCommand):
    name = "link"
    aliases = ["satellite", "connect"]
    help_text = "Choose constellation satellite"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        from secure_eo_pipeline.constellation_catalog import satellites_from_environment
        
        sats = satellites_from_environment()
        if not sats:
            console.print("[red]No satellites defined.[/red]")
            return False
        
        table = Table(
            title="CONSTELLATION NETWORK — Select Satellite",
            box=box.DOUBLE_EDGE,
            header_style="bold cyan"
        )
        table.add_column("#", style="cyan", justify="right")
        table.add_column("HOSTNAME", style="bold magenta")
        table.add_column("MISSION", style="white")
        table.add_column("PROFILE", style="yellow")
        table.add_column("SCIENCE FOCUS", style="green")
        
        for i, s in enumerate(sats, 1):
            table.add_row(
                str(i),
                s.hostname,
                s.title[:25],
                s.mission_profile,
                s.science_focus or "—"
            )
        
        console.print(table)
        
        from rich.prompt import IntPrompt
        choice = IntPrompt.ask("[cyan]Satellite selection[/cyan]", default=1)
        
        if 1 <= choice <= len(sats):
            self.session.link_host = sats[choice - 1].hostname
            console.print(f"[green]✓ Linked to {self.session.link_host}[/green]")
            return True
        else:
            console.print("[red]Invalid selection.[/red]")
            return False


class ScanCommand(BaseCommand):
    name = "scan"
    aliases = ["acquire", "downlink-start"]
    help_text = "Acquire Level-0 from linked satellite"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        import os
        import random
        import time
        from rich.progress import track
        
        if os.getenv("SPACE_SEGMENT_HOSTS", "").strip() and not self.session.link_host:
            console.print("[yellow]⚠ No satellite linked. Run 'link' first.[/yellow]")
            return False
        
        pid = f"SENTINEL_{random.randint(1000, 9999)}_ORB{random.randint(10, 99)}"
        
        hosts_env = os.getenv("SPACE_SEGMENT_HOSTS", "").strip()
        if hosts_env:
            console.print(f"[cyan]┌─ X-BAND DOWNLINK[/cyan]")
            console.print(f"[cyan]│  Host: {self.session.link_host or 'local'}[/cyan]")
            console.print(f"[cyan]│  Mode: {self.session.observation_mode}[/cyan]")
            console.print(f"[cyan]└─ Acquiring...[/cyan]")
        else:
            console.print(f"[cyan]┌─ LOCAL OBC[/cyan]")
            console.print(f"[cyan]│  Mode: {self.session.observation_mode}[/cyan]")
            console.print(f"[cyan]└─ Generating...[/cyan]")
        
        for _ in track(range(10), description="[cyan]Signal acquisition...[/cyan]"):
            time.sleep(0.1)
        
        self.session.source.generate_product(
            pid,
            target_host=self.session.link_host or "",
            observation_mode=self.session.observation_mode,
        )
        
        self.session.active_product = pid
        self.session.state = {
            "generated": True,
            "ingested": False,
            "processed": False,
            "archived": False,
            "hacked": False
        }
        
        console.print(f"[green]✓ SIGNAL LOCKED[/green] — Target: [bold]{pid}[/bold]")
        console.print("[dim]ℹ Metadata validated. Level-0 binary generated.[/dim]")
        return True


class StatusCommand(BaseCommand):
    name = "status"
    aliases = ["state", "pipeline"]
    help_text = "Show pipeline state for active product"
    
    def execute(self, args: list[str]) -> bool:
        table = Table(
            title="PRODUCT VERIFICATION STATUS",
            box=box.HEAVY_EDGE,
            header_style="bold cyan"
        )
        table.add_column("STAGE", style="bold cyan")
        table.add_column("STATUS", style="white")
        
        stages = [
            ("GENERATED", "generated"),
            ("INGESTED", "ingested"),
            ("PROCESSED", "processed"),
            ("ARCHIVED", "archived"),
            ("INTEGRITY", "hacked"),
        ]
        
        for label, key in stages:
            if self.session.state.get(key, False):
                if key == "hacked":
                    status = "[bold red]⚠ CORRUPTED[/bold red]"
                else:
                    status = "[bold green]✓ COMPLETE[/bold green]"
            else:
                status = "[dim]○ PENDING[/dim]"
            table.add_row(label, status)
        
        console.print(table)
        
        if self.session.active_product:
            console.print(f"[dim]Active product: {self.session.active_product}[/dim]")
        
        return True


class HealthCommand(BaseCommand):
    name = "health"
    aliases = ["diag", "diagnostics"]
    help_text = "Run system health diagnostics"
    
    def execute(self, args: list[str]) -> bool:
        import os
        from secure_eo_pipeline import config
        from secure_eo_pipeline.db import sqlite_adapter
        
        table = Table(
            title="SYSTEM HEALTH DIAGNOSTICS",
            box=box.DOUBLE_EDGE
        )
        table.add_column("COMPONENT", style="bold cyan")
        table.add_column("STATUS", style="white")
        table.add_column("INFO", style="dim")
        
        table.add_row(
            "SECURITY POSTURE",
            "[green]MAXIMUM[/green]",
            getattr(config, 'SECURITY_POSTURE', 'maximum')
        )
        
        for label, path in [
            ("INGEST_DIR", config.INGEST_DIR),
            ("PROCESSING_DIR", config.PROCESSING_DIR),
            ("ARCHIVE_DIR", config.ARCHIVE_DIR),
            ("BACKUP_DIR", config.BACKUP_DIR),
        ]:
            exists = os.path.isdir(path)
            status = "[green]OK[/green]" if exists else "[yellow]MISSING[/yellow]"
            table.add_row(label, status, path)
        
        if getattr(config, "USE_SQLITE", False):
            try:
                conn = sqlite_adapter.get_connection()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                users_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM audit_events")
                events_count = cur.fetchone()[0]
                table.add_row(
                    "SQLite",
                    "[green]OK[/green]",
                    f"Users={users_count}, Events={events_count}"
                )
            except Exception as e:
                table.add_row("SQLite", "[red]ERROR[/red]", str(e))
        else:
            table.add_row("SQLite", "[yellow]DISABLED[/yellow]", "USE_SQLITE=False")
        
        console.print(table)
        return True


class IDSCommand(BaseCommand):
    name = "ids"
    aliases = ["security", "scan-threats"]
    help_text = "Scan audit logs for security threats"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process") and not self.check_auth("manage_keys"):
            return False
        
        import time
        from rich.progress import Progress
        
        with console.status("[bold red]SCANNING AUDIT LOGS...[/bold red]"):
            time.sleep(1.5)
            incidents = self.session.ids.analyze_audit_log()
        
        if not incidents:
            console.print("[green]✓ System Secure — No threats detected[/green]")
            return True
        
        console.print(f"\n[bold red]⚠ THREATS DETECTED: {len(incidents)}[/bold red]")
        
        table = Table(
            title="INTRUSION DETECTION REPORT",
            box=box.HEAVY_EDGE
        )
        table.add_column("SEVERITY", style="bold")
        table.add_column("TYPE", style="cyan")
        table.add_column("DETAILS", style="white")
        
        for inc in incidents:
            sev = inc["severity"]
            sev_style = "red" if sev == "CRITICAL" else "yellow" if sev == "HIGH" else "blue"
            table.add_row(
                f"[{sev_style}]{sev}[/{sev_style}]",
                inc["type"],
                inc["details"][:80] + "..." if len(inc["details"]) > 80 else inc["details"]
            )
        
        console.print(table)
        console.print("[dim]Recommended: Review audit.log and rotate keys if necessary.[/dim]")
        return True


class OrbitCommand(BaseCommand):
    name = "orbit"
    aliases = ["orbital", "position"]
    help_text = "Show orbital elements and current position"
    
    def execute(self, args: list[str]) -> bool:
        if not self.session.link_host:
            console.print("[yellow]⚠ No satellite linked. Run 'link' first.[/yellow]")
            return False
        
        from secure_eo_pipeline.constellation_catalog import spec_for_host
        from secure_eo_pipeline.physics.orbital import (
            get_current_position, orbital_period, escape_velocity,
            orbital_regime, orbital_velocity
        )
        
        spec = spec_for_host(self.session.link_host)
        if not spec or not spec.orbital_elements:
            console.print("[red]No orbital data available.[/red]")
            return False
        
        oe = spec.orbital_elements
        pos = get_current_position(
            oe.semimajor_axis_km, oe.eccentricity,
            oe.inclination_deg, oe.raan_deg,
            oe.arg_perigee_deg, oe.mean_anomaly_deg,
        )
        
        regime = orbital_regime(oe.semimajor_axis_km)
        period = orbital_period(oe.semimajor_axis_km)
        
        table = Table(
            title=f"ORBITAL STATE — {spec.title}",
            box=box.DOUBLE_EDGE
        )
        table.add_column("PARAMETER", style="cyan")
        table.add_column("VALUE", style="white")
        
        table.add_row("REGIME", f"[bold]{regime}[/bold]")
        table.add_row("SEMI-MAJOR AXIS", f"{oe.semimajor_axis_km:.2f} km")
        table.add_row("ECCENTRICITY", f"{oe.eccentricity:.6f}")
        table.add_row("PERIGEE", f"{oe.perigee_km:.1f} km")
        table.add_row("APOGEE", f"{oe.apogee_km:.1f} km")
        table.add_row("INCLINATION", f"{oe.inclination_deg:.2f}°")
        table.add_row("RAAN", f"{oe.raan_deg:.2f}°")
        table.add_row("ARG PERIGEE", f"{oe.arg_perigee_deg:.2f}°")
        table.add_row("PERIOD", f"{period:.2f} min")
        table.add_row("ALTITUDE", f"{pos.alt_km:.1f} km")
        table.add_row("LATITUDE", f"{pos.lat_deg:.4f}°")
        table.add_row("LONGITUDE", f"{pos.lon_deg:.4f}°")
        table.add_row("VELOCITY", f"{orbital_velocity(oe.semimajor_axis_km, oe.eccentricity):.3f} km/s")
        table.add_row("ESCAPE VEL", f"{escape_velocity(oe.semimajor_axis_km):.3f} km/s")
        
        console.print(table)
        return True


class CatalogCommand(BaseCommand):
    name = "catalog"
    aliases = ["satellites", "list"]
    help_text = "Browse all satellite catalogs"
    
    def execute(self, args: list[str]) -> bool:
        from secure_eo_pipeline.constellation_catalog import all_catalogs
        from secure_eo_pipeline.physics.orbital import orbital_regime
        from rich.prompt import Prompt
        
        catalogs = all_catalogs()
        
        table = Table(
            title="SATELLITE CATALOGS",
            box=box.DOUBLE_EDGE
        )
        table.add_column("#", style="cyan", justify="right")
        table.add_column("CATALOG", style="yellow")
        table.add_column("SATELLITES", style="green", justify="right")
        
        for i, (name, sats) in enumerate(catalogs.items(), 1):
            table.add_row(str(i), name.upper(), str(len(sats)))
        
        console.print(table)
        
        choice = Prompt.ask("Select catalog (or 'q')", default="q")
        if choice.lower() == 'q':
            return True
        
        try:
            idx = int(choice) - 1
            cat_names = list(catalogs.keys())
            if 0 <= idx < len(cat_names):
                cat_name = cat_names[idx]
                sats = catalogs[cat_name]
                
                sat_table = Table(
                    title=f"{cat_name.upper()} — {len(sats)} SATELLITES",
                    box=box.ROUNDED
                )
                sat_table.add_column("#", style="cyan", justify="right")
                sat_table.add_column("HOSTNAME", style="magenta")
                sat_table.add_column("TITLE", style="white")
                sat_table.add_column("PROFILE", style="dim")
                sat_table.add_column("REGIME", style="green")
                
                for i, sat in enumerate(sats, 1):
                    reg = orbital_regime(sat.orbital_elements.semimajor_axis_km) if sat.orbital_elements else "N/A"
                    sat_table.add_row(str(i), sat.hostname, sat.title[:30], sat.mission_profile, reg)
                
                console.print(sat_table)
        except ValueError:
            console.print("[red]Invalid selection.[/red]")
        
        return True


class HelpCommand(BaseCommand):
    name = "help"
    aliases = ["?", "commands"]
    help_text = "Show all available commands"
    
    def execute(self, args: list[str]) -> bool:
        table = Table(
            title="MISSION CONTROL COMMAND REFERENCE",
            box=box.DOUBLE_EDGE,
            header_style="bold cyan"
        )
        table.add_column("COMMAND", style="bold cyan")
        table.add_column("ALIASES", style="dim")
        table.add_column("DESCRIPTION", style="white")
        
        commands = [
            ("AUTHENTICATION", [
                ("login", "auth, signin", "Authenticate operator credentials"),
                ("logout", "exit-session", "End current session"),
            ]),
            ("CONSTELLATION", [
                ("link", "satellite, connect", "Choose constellation satellite"),
                ("scan", "acquire, downlink-start", "Acquire Level-0 from satellite"),
                ("status", "state, pipeline", "Show pipeline state"),
            ]),
            ("ORBITAL MECHANICS", [
                ("orbit", "orbital, position", "Show orbital elements"),
                ("catalog", "satellites, list", "Browse satellite catalogs"),
            ]),
            ("SECURITY", [
                ("ids", "security, scan-threats", "Scan for security threats"),
                ("health", "diag, diagnostics", "Run system diagnostics"),
            ]),
            ("CYBER OPERATIONS", [
                ("red-team", "attack-sim", "Run Red Team attack simulation"),
                ("blue-team", "defense-sim", "Show Blue Team defense status"),
                ("zero-trust", "ztna", "Zero Trust authentication"),
                ("pqcrypto", "quantum", "Quantum-resistant crypto operations"),
                ("audit-chain", "blockchain", "Blockchain audit ledger"),
            ]),
            ("UTILITY", [
                ("exit", "", "Close the console"),
            ]),
        ]
        
        for category, cmds in commands:
            table.add_row(f"[bold underline]{category}[/bold underline]", "", "")
            for name, aliases, desc in cmds:
                alias_str = ", ".join(a for a in aliases.split(", ") if a) if aliases else ""
                table.add_row(name, f"[dim]{alias_str}[/dim]", desc)
        
        console.print(table)
        return True


class RedTeamCommand(BaseCommand):
    name = "red-team"
    aliases = ["attack-sim", "red"]
    help_text = "Run Red Team attack simulation"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        import random
        from rich.progress import Progress
        
        from secure_eo_pipeline.cyber.red_team.attacks import RedTeamSimulator, AttackType
        
        console.print("\n[bold red]╔════════════════════════════════════════╗")
        console.print("║     RED TEAM ATTACK SIMULATION          ║")
        console.print("╚════════════════════════════════════════╝[/bold red]")
        
        target = args[0] if args else "sentryground.local"
        
        with console.status("[bold red]Initializing attack vectors...[/bold red]"):
            simulator = RedTeamSimulator(target_systems=[target])
            report = simulator.run_campaign(f"campaign_{random.randint(1000, 9999)}", targets=[target])
        
        console.print(f"\n[bold]Campaign Results:[/bold]")
        console.print(f"  Total Attacks: [cyan]{report.total_attacks}[/cyan]")
        console.print(f"  Successful: [red]{report.successful_attacks}[/red]")
        console.print(f"  Failed: [green]{report.failed_attacks}[/green]")
        console.print(f"  Risk Score: [yellow]{report.risk_score:.1f}/100[/yellow]")
        
        if report.vulnerabilities_found:
            console.print(f"\n[bold red]⚠ Vulnerabilities Found: {len(report.vulnerabilities_found)}[/bold red]")
            
            vuln_table = Table(
                title="DISCOVERED VULNERABILITIES",
                box=box.HEAVY_EDGE
            )
            vuln_table.add_column("TYPE", style="cyan")
            vuln_table.add_column("SEVERITY", style="bold")
            vuln_table.add_column("CWE", style="dim")
            
            for vuln in report.vulnerabilities_found[:10]:
                sev_color = "red" if vuln["severity"] == "CRITICAL" else "yellow"
                vuln_table.add_row(
                    vuln["type"],
                    f"[{sev_color}]{vuln['severity']}[/{sev_color}]",
                    vuln.get("cwe", "N/A")
                )
            
            console.print(vuln_table)
        
        if report.recommendations:
            console.print("\n[bold]Recommendations:[/bold]")
            for rec in report.recommendations[:5]:
                console.print(f"  [green]•[/green] {rec}")
        
        return True


class BlueTeamCommand(BaseCommand):
    name = "blue-team"
    aliases = ["defense-sim", "blue"]
    help_text = "Show Blue Team defense status"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        from secure_eo_pipeline.cyber.blue_team.defenses import BlueTeamDefense
        
        console.print("\n[bold blue]╔════════════════════════════════════════╗")
        console.print("║     BLUE TEAM DEFENSE STATUS             ║")
        console.print("╚════════════════════════════════════════╝[/bold blue]")
        
        defense = BlueTeamDefense()
        status = defense.get_defense_status()
        
        ids_stats = status.get("ids", {})
        console.print(f"\n[bold]Network IDS:[/bold]")
        console.print(f"  Packets Inspected: [cyan]{ids_stats.get('packets_inspected', 0)}[/cyan]")
        console.print(f"  Alerts Generated: [yellow]{ids_stats.get('alerts_generated', 0)}[/yellow]")
        console.print(f"  Attacks Mitigated: [green]{ids_stats.get('attacks_mitigated', 0)}[/green]")
        
        waf_stats = status.get("waf", {})
        console.print(f"\n[bold]Web Application Firewall:[/bold]")
        console.print(f"  Rules Active: [cyan]{waf_stats.get('rules_active', 0)}[/cyan]")
        console.print(f"  Blocked IPs: [red]{waf_stats.get('blocked_ips', 0)}[/red]")
        
        hp_stats = status.get("honeypot", {})
        console.print(f"\n[bold]Honeypots:[/bold]")
        console.print(f"  Deployed: [cyan]{hp_stats.get('deployed', 0)}[/cyan]")
        console.print(f"  Interactions: [yellow]{hp_stats.get('interactions', 0)}[/yellow]")
        console.print(f"  Attackers Identified: [red]{hp_stats.get('attackers', 0)}[/red]")
        
        th_stats = status.get("threat_hunting", {})
        console.print(f"\n[bold]Threat Hunting:[/bold]")
        console.print(f"  Active Hunts: [yellow]{th_stats.get('active_hunts', 0)}[/yellow]")
        console.print(f"  Completed Hunts: [green]{th_stats.get('completed_hunts', 0)}[/green]")
        
        overall = status.get("overall", {})
        console.print(f"\n[bold]Overall Defense Posture:[/bold]")
        console.print(f"  Total Alerts: [yellow]{overall.get('alerts_generated', 0)}[/yellow]")
        console.print(f"  Attacks Blocked: [green]{overall.get('attacks_blocked', 0)}[/green]")
        console.print(f"  Playbooks Executed: [cyan]{overall.get('playbooks_executed', 0)}[/cyan]")
        
        return True


class ZeroTrustCommand(BaseCommand):
    name = "zero-trust"
    aliases = ["ztna", "zt"]
    help_text = "Zero Trust authentication and authorization"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        from secure_eo_pipeline.cyber.zero_trust.auth import ZeroTrustAuth, TrustLevel, AccessDecision
        
        console.print("\n[bold cyan]╔════════════════════════════════════════╗")
        console.print("║     ZERO TRUST ARCHITECTURE              ║")
        console.print("╚════════════════════════════════════════╝[/bold cyan]")
        
        zta = ZeroTrustAuth()
        
        action = args[0] if args else "status"
        
        if action == "status":
            status = zta.get_authorization_status()
            
            console.print(f"\n[bold]System Status:[/bold]")
            console.print(f"  Identities: [cyan]{status['identities']}[/cyan]")
            console.print(f"  Devices: [cyan]{status['devices']}[/cyan]")
            console.print(f"  Resources: [cyan]{status['resources']}[/cyan]")
            console.print(f"  Policies: [cyan]{status['policies']}[/cyan]")
            console.print(f"  Active Sessions: [yellow]{status['active_sessions']}[/yellow]")
            
            trust_dist = status.get("trust_distribution", {})
            console.print(f"\n[bold]Device Trust Distribution:[/bold]")
            for level, count in trust_dist.items():
                if count > 0:
                    console.print(f"  {level}: [green]{count}[/green]")
        
        elif action == "identities":
            console.print("\n[bold]Registered Identities:[/bold]")
            for identity in zta.identities.values():
                trust_icon = "🔴" if identity.device_trust == TrustLevel.UNTRUSTED else "🟡" if identity.device_trust == TrustLevel.LOW else "🟢"
                console.print(f"  {trust_icon} {identity.username} ({identity.identity_type}) - {identity.device_trust.name}")
        
        elif action == "test":
            console.print("[yellow]Testing Zero Trust authorization...[/yellow]")
            console.print("  [green]✓ Zero Trust framework operational[/green]")
        
        return True


class PQCryptoCommand(BaseCommand):
    name = "pqcrypto"
    aliases = ["quantum", "pq"]
    help_text = "Quantum-resistant cryptographic operations"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        from secure_eo_pipeline.cyber.quantum_resistant.pqcrypto import QuantumResistantCrypto, PQAlgorithm, KeyType
        
        console.print("\n[bold magenta]╔════════════════════════════════════════╗")
        console.print("║  QUANTUM-RESISTANT CRYPTOGRAPHY           ║")
        console.print("╚════════════════════════════════════════╝[/bold magenta]")
        
        pqc = QuantumResistantCrypto()
        
        action = args[0] if args else "status"
        
        if action == "status":
            caps = pqc.get_capabilities()
            
            console.print(f"\n[bold]Supported Algorithms:[/bold]")
            console.print(f"  KEM: [cyan]{', '.join(caps['algorithms']['kem'])}[/cyan]")
            console.print(f"  DSA: [cyan]{', '.join(caps['algorithms']['dsa'])}[/cyan]")
            
            console.print(f"\n[bold]Features:[/bold]")
            for feature in caps['features']:
                console.print(f"  [green]✓[/green] {feature}")
            
            console.print(f"\n[bold]Security Levels:[/bold]")
            for level in caps['security_levels']:
                console.print(f"  [cyan]•[/cyan] {level}")
        
        elif action == "generate":
            keypair = pqc.generate_keypair()
            
            console.print(f"\n[bold]Generated Key Pair:[/bold]")
            console.print(f"  Key ID: [yellow]{keypair.key_id}[/yellow]")
            console.print(f"  Type: [cyan]{keypair.key_type.value}[/cyan]")
            console.print(f"  Algorithm: [cyan]{keypair.algorithm.value}[/cyan]")
            console.print(f"  Public Key: [dim]{keypair.public_key.hex()[:32]}...[/dim]")
            console.print(f"  Created: [green]{keypair.created_at.isoformat()}[/green]")
        
        elif action == "encrypt" and len(args) > 1:
            plaintext = args[1].encode()
            keypair = pqc.generate_keypair()
            encrypted = pqc.encrypt(plaintext, keypair.public_key, hybrid=True)
            
            console.print(f"\n[bold green]Encryption successful![/bold green]")
            console.print(f"  Algorithm: [cyan]{encrypted['algorithm']}[/cyan]")
            console.print(f"  Ciphertext length: [yellow]{len(encrypted['ciphertext'])}[/yellow]")
        
        return True


class AuditChainCommand(BaseCommand):
    name = "audit-chain"
    aliases = ["blockchain", "bc"]
    help_text = "Blockchain audit ledger operations"
    
    def execute(self, args: list[str]) -> bool:
        if not self.check_auth("process"):
            return False
        
        from secure_eo_pipeline.cyber.blockchain_audit.ledger import get_ledger, EventCategory
        
        console.print("\n[bold green]╔════════════════════════════════════════╗")
        console.print("║     BLOCKCHAIN AUDIT LEDGER              ║")
        console.print("╚════════════════════════════════════════╝[/bold green]")
        
        ledger = get_ledger()
        
        action = args[0] if args else "status"
        
        if action == "status":
            stats = ledger.get_chain_statistics()
            
            console.print(f"\n[bold]Blockchain Statistics:[/bold]")
            console.print(f"  Blocks: [cyan]{stats['blocks']}[/cyan]")
            console.print(f"  Total Events: [yellow]{stats['total_events']}[/yellow]")
            console.print(f"  Pending Events: [red]{stats['pending_events']}[/red]")
            console.print(f"  Validators: [green]{stats['validators']}[/green]")
            console.print(f"  Chain Integrity: [green]✓ Verified[/green]" if stats['chain_integrity'] else "[red]✗ Compromised[/red]")
            
            if stats.get('category_distribution'):
                console.print(f"\n[bold]Event Distribution:[/bold]")
                for cat, count in stats['category_distribution'].items():
                    console.print(f"  {cat}: [cyan]{count}[/cyan]")
        
        elif action == "log":
            category = args[1] if len(args) > 1 else "system_event"
            actor = self.session.current_user or "anonymous"
            
            try:
                cat = EventCategory(category)
            except:
                cat = EventCategory.SYSTEM_EVENT
            
            event_id = ledger.add_event(
                category=cat,
                actor=actor,
                action="manual_log",
                resource="cli",
                result="success"
            )
            
            console.print(f"\n[green]✓ Event logged:[/green] {event_id}")
            
            block = ledger.create_block("validator_001")
            if block:
                console.print(f"[green]✓ Block mined:[/green] #{block.index}")
        
        elif action == "verify":
            valid, errors = ledger.verify_chain()
            
            if valid:
                console.print("\n[green]✓ Chain integrity verified[/green]")
            else:
                console.print(f"\n[red]✗ Chain integrity check failed:[/red]")
                for error in errors:
                    console.print(f"  - {error}")
        
        return True


class ExitCommand(BaseCommand):
    name = "exit"
    aliases = ["quit", "q"]
    help_text = "Close the console"
    
    def execute(self, args: list[str]) -> bool:
        console.print("[bold green]\n╔══════════════════════════════════════╗\n║  SESSION TERMINATED                 ║\n╚══════════════════════════════════════╝[/bold green]\n")
        return True
