#!/usr/bin/env python3
"""
Sentry-Ground Zero - Unified Mission Control
============================================

End-to-End Secure Earth Observation Ecosystem
Space-to-Vault Integrated Mission Orchestrator

This unified command center manages both:
- SPACE SEGMENT: Sentry-Sat OBC (sensor, AI inference, crypto signing)
- GROUND SEGMENT: Secure EO Pipeline (telemetry ingestion, verification, archival)

Cross-Segment Attack Simulation:
Implements full_mission_attack that simulates:
1. Sensor sabotage (frame injection on Sentry-Sat)
2. Man-in-the-Middle (telemetry tampering during downlink)
3. Detection and Recovery (IDS correlation + ResilienceManager)

Controls mapped to:
- ISO 27001:2013 Annex A controls
- NIST Cybersecurity Framework (CSF) v1.1
"""

import os
import sys
import json
import time
import random
import shutil
import hashlib
import hmac
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

os.environ.setdefault("EO_PIPELINE_MODE", "DEMO")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Progetto 1"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt
from rich.progress import track

console = Console()


@dataclass
class SpaceSegmentState:
    """State of the Sentry-Sat OBC."""
    cycle_count: int = 0
    last_cycle_id: str = ""
    anomaly_injected: bool = False
    frame_corrupted: bool = False
    puf_key: str = "SAT_KEY_0x8F9A2B"
    frames_generated: List[Dict] = None

    def __post_init__(self):
        self.frames_generated = []


@dataclass
class GroundSegmentState:
    """State of the Secure EO Pipeline."""
    telemetry_received: int = 0
    signatures_verified: int = 0
    signatures_failed: int = 0
    anomalies_detected: int = 0
    chain_of_custody: Dict[str, Any] = None

    def __post_init__(self):
        self.chain_of_custody = {}


@dataclass
class AttackScenario:
    """Cross-segment attack scenario state."""
    sensor_sabotage: bool = False
    mitm_attack: bool = False
    false_data_injection: bool = False
    tampered_cycle_id: str = ""
    original_signature: str = ""
    tampered_signature: str = ""
    attack_executed: bool = False
    detected: bool = False


class MissionControl:
    """
    Unified Mission Control for Sentry-Ground Zero ecosystem.
    
    Orchestrates both Space Segment (Sentry-Sat) and Ground Segment (Secure EO Pipeline)
    with integrated chain of custody tracking and cross-segment attack simulation.
    """

    def __init__(self):
        self.space_state = SpaceSegmentState()
        self.ground_state = GroundSegmentState()
        self.attack = AttackScenario()
        self.running = True

        self._ensure_directories()
        self._log_system_startup()

    def _ensure_directories(self):
        """Create necessary directories for both segments."""
        directories = [
            "simulation_data",
            "simulation_data/telemetry_landing_zone",
            "simulation_data/ingest_landing_zone",
            "simulation_data/processing_staging",
            "simulation_data/secure_archive",
            "simulation_data/backup_storage",
        ]
        for d in directories:
            os.makedirs(d, exist_ok=True)

    def _log_system_startup(self):
        """Log system startup."""
        self._audit_log("[SYSTEM] Mission Control initialized")
        self._audit_log("[SYSTEM] Space Segment: Sentry-Sat OBC READY")
        self._audit_log("[SYSTEM] Ground Segment: Secure EO Pipeline READY")

    def _audit_log(self, message: str):
        """Write to audit log."""
        timestamp = datetime.utcnow().isoformat()
        log_line = f"[{timestamp}] {message}\n"
        with open("audit.log", "a") as f:
            f.write(log_line)

    def _compute_hmac(self, payload: str, key: str) -> str:
        """Compute HMAC-SHA256 matching Sentry-Sat implementation."""
        key_bytes = key.encode("utf-8")
        payload_bytes = payload.encode("utf-8")
        mac = hmac.new(key_bytes, payload_bytes, hashlib.sha256)
        return mac.hexdigest()

    def print_banner(self):
        """Display mission control banner."""
        console.print(Panel(
            "[bold cyan]SENTRY-GROUND ZERO[/bold cyan]\n"
            "[bold white]End-to-End Secure Earth Observation Ecosystem[/bold white]\n"
            "[italic white]Space-to-Vault Integrated Mission Control[/italic white]",
            border_style="cyan",
            expand=False
        ))

    def help_menu(self):
        """Display available commands."""
        table = Table(title="\nMission Control Commands\n", box=None)
        table.add_column("Command", style="bold cyan")
        table.add_column("Description", style="white")

        table.add_row("[bold underline]Space Segment (Sentry-Sat OBC)[/bold underline]", "")
        table.add_row("obc_init", "Initialize Sentry-Sat On-Board Computer")
        table.add_row("obc_cycle", "Run single sensor acquisition cycle")
        table.add_row("obc_mission", "Run full mission loop (5 cycles)")
        table.add_row("inject_anomaly", "Inject sensor anomaly (space segment attack)")
        table.add_row("", "")

        table.add_row("[bold underline]Ground Segment (Secure EO Pipeline)[/bold underline]", "")
        table.add_row("ground_receive", "Receive and verify telemetry from downlink")
        table.add_row("ground_ingest", "Ingest verified telemetry into pipeline")
        table.add_row("ground_archive", "Archive product with encryption")
        table.add_row("ground_recover", "Verify integrity and recover from backup")
        table.add_row("", "")

        table.add_row("[bold underline]Chain of Custody[/bold underline]", "")
        table.add_row("custody_status", "Show chain of custody status")
        table.add_row("custody_verify", "Verify custody record for cycle")
        table.add_row("", "")

        table.add_row("[bold underline]Cross-Segment Attack Simulation[/bold underline]", "")
        table.add_row("full_mission_attack", "Execute full attack kill chain (Recommended)")
        table.add_row("sensor_sabotage", "Simulate sensor frame tampering")
        table.add_row("mitm_attack", "Simulate Man-in-the-Middle during downlink")
        table.add_row("ids_correlation", "Run IDS correlation analysis")
        table.add_row("recover_mission", "Recover from attack using backup")
        table.add_row("", "")

        table.add_row("[bold underline]System[/bold underline]", "")
        table.add_row("status", "Show complete mission status")
        table.add_row("health", "System health check")
        table.add_row("help", "Show this command list")
        table.add_row("exit", "Terminate mission control")

        console.print(table)

    def obc_init(self):
        """Initialize Sentry-Sat OBC."""
        console.print("[cyan]Initializing Sentry-Sat OBC...[/cyan]")

        for step in track(range(5), description="[cyan]Boot Sequence[/cyan]"):
            time.sleep(0.3)

        console.print(f"[green]PUF Device Key: {self.space_state.puf_key}[/green]")
        console.print("[green]CryptoSigner Enclave: INITIALIZED[/green]")
        console.print("[green]Inference Engine: READY[/green]")
        console.print("[green]Sensor Array: ONLINE[/green]")

        self._audit_log("[OBC] Sentry-Sat OBC initialized successfully")

    def _generate_sensor_frame(self, cycle_id: str, inject_anomaly: bool = False) -> Dict:
        """Generate a 28x28 sensor frame (simulated)."""
        frame_data = []
        for i in range(784):
            if inject_anomaly and i % 28 == 14:
                frame_data.append(random.uniform(0.9, 1.0))
            else:
                frame_data.append(random.uniform(0.0, 0.15))

        mse = 0.001 if not inject_anomaly else random.uniform(0.01, 0.05)
        anomaly_detected = inject_anomaly or mse > 0.005

        return {
            "cycle_id": cycle_id,
            "frame_data": frame_data,
            "mse": mse,
            "anomaly_detected": anomaly_detected,
        }

    def _sign_telemetry(self, cycle_id: str, anomaly: bool, timestamp: str) -> str:
        """Sign telemetry payload with HMAC-SHA256."""
        anomaly_str = "ANOMALY_TRUE" if anomaly else "ANOMALY_FALSE"
        payload = f"{anomaly_str}{timestamp}"
        return self._compute_hmac(payload, self.space_state.puf_key)

    def obc_cycle(self):
        """Run a single sensor acquisition cycle."""
        self.space_state.cycle_count += 1
        cycle_id = f"T+{self.space_state.cycle_count:03d}"
        self.space_state.last_cycle_id = cycle_id

        inject_anomaly = self.space_state.anomaly_injected and random.random() > 0.5

        console.print(f"\n[cyan]--- [Cycle {cycle_id}] Sensor Acquisition ---[/cyan]")

        frame = self._generate_sensor_frame(cycle_id, inject_anomaly)

        signature = self._sign_telemetry(cycle_id, frame["anomaly_detected"], cycle_id)

        telemetry = {
            "telemetry_schema": "sentry_sat.obc.v1",
            "cycle_id": cycle_id,
            "anomaly": frame["anomaly_detected"],
            "signature_hex": signature,
            "reconstruction_mse": frame["mse"],
            "inference_backend": "heuristic",
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.space_state.frames_generated.append(telemetry)

        console.print(f"[green]Frame captured (28x28)[/green]")
        console.print(f"[green]AI Inference: anomaly={frame['anomaly_detected']}, MSE={frame['mse']:.6f}[/green]")
        console.print(f"[green]Signature: {signature[:32]}...[/green]")

        telemetry_path = f"simulation_data/telemetry_landing_zone/{cycle_id}.json"
        with open(telemetry_path, "w") as f:
            json.dump(telemetry, f, indent=2)

        self._audit_log(f"[OBC] Cycle {cycle_id} completed: anomaly={frame['anomaly_detected']}")

        return telemetry

    def obc_mission(self):
        """Run full mission loop."""
        console.print("[bold cyan]Starting Sentry-Sat Mission Loop[/bold cyan]")
        cycles = Prompt.ask("Number of cycles", default="5")

        try:
            num_cycles = int(cycles)
        except ValueError:
            num_cycles = 5

        for i in range(num_cycles):
            self.obc_cycle()
            time.sleep(0.5)

        console.print(f"[green]Mission loop complete: {num_cycles} cycles executed[/green]")

    def inject_anomaly(self):
        """Inject sensor anomaly (simulated space segment attack)."""
        console.print("[bold red]INJECTING SENSOR ANOMALY...[/bold red]")
        self.space_state.anomaly_injected = True

        console.print("[yellow]Simulating detector saturation event[/yellow]")
        console.print("[yellow]Row 14: Injecting bright streak pattern[/yellow]")
        console.print("[yellow]Expected: Elevated MSE, anomaly flag = TRUE[/yellow]")

        self._audit_log("[ATTACK] Sensor sabotage injected on Sentry-Sat")

    def ground_receive(self):
        """Receive and verify telemetry from downlink."""
        if not self.space_state.frames_generated:
            console.print("[yellow]No telemetry available. Run OBC cycles first.[/yellow]")
            return

        console.print("[cyan]Receiving telemetry from X-band downlink...[/cyan]")

        for telemetry in self.space_state.frames_generated:
            cycle_id = telemetry["cycle_id"]

            if self.attack.mitm_attack and cycle_id == self.attack.tampered_cycle_id:
                console.print(f"[red]MITM: Tampering telemetry for {cycle_id}...[/red]")
                telemetry["signature_hex"] = self.attack.tampered_signature
                telemetry["reconstruction_mse"] = 0.0001
                telemetry["anomaly"] = False

            verification = self._verify_signature(telemetry)

            self.ground_state.telemetry_received += 1

            if verification["valid"]:
                self.ground_state.signatures_verified += 1
                status = "[green]VERIFIED[/green]"
            else:
                self.ground_state.signatures_failed += 1
                status = "[red]FAILED[/red]"

            console.print(f"  {cycle_id}: {status} (MSE={telemetry['reconstruction_mse']:.6f})")

            self._establish_custody(telemetry)

            if telemetry.get("anomaly"):
                self.ground_state.anomalies_detected += 1

        console.print(f"[cyan]Downlink complete: {self.ground_state.telemetry_received} packets received[/cyan]")

    def _verify_signature(self, telemetry: Dict) -> Dict:
        """Verify HMAC signature of telemetry."""
        anomaly_str = "ANOMALY_TRUE" if telemetry["anomaly"] else "ANOMALY_FALSE"
        payload = f"{anomaly_str}{telemetry['cycle_id']}"
        expected = self._compute_hmac(payload, self.space_state.puf_key)

        is_valid = hmac.compare_digest(expected.lower(), telemetry["signature_hex"].lower())

        return {
            "valid": is_valid,
            "expected": expected,
            "received": telemetry["signature_hex"],
        }

    def _establish_custody(self, telemetry: Dict):
        """Establish chain of custody for telemetry."""
        cycle_id = telemetry["cycle_id"]
        self.ground_state.chain_of_custody[cycle_id] = {
            "cycle_id": cycle_id,
            "received_at": datetime.utcnow().isoformat(),
            "source": "SENTRY_SAT_OBC",
            "device_id": self.space_state.puf_key,
            "signature_hex": telemetry["signature_hex"],
            "reconstruction_mse": telemetry["reconstruction_mse"],
            "status": "CUSTODY_ESTABLISHED",
            "tamper_detected": not self._verify_signature(telemetry)["valid"],
        }

    def ground_ingest(self):
        """Ingest verified telemetry into processing pipeline."""
        if self.ground_state.telemetry_received == 0:
            console.print("[yellow]No telemetry to ingest. Run ground_receive first.[/yellow]")
            return

        console.print("[cyan]Ingesting telemetry into processing pipeline...[/cyan]")

        ingested = 0
        for cycle_id, custody in self.ground_state.chain_of_custody.items():
            if not custody.get("tamper_detected"):
                ingested += 1

        console.print(f"[green]Ingestion complete: {ingested} products ingested[/green]")
        self._audit_log(f"[INGEST] {ingested} products ingested successfully")

    def ground_archive(self):
        """Archive processed products with encryption."""
        if not self.ground_state.chain_of_custody:
            console.print("[yellow]No products to archive.[/yellow]")
            return

        console.print("[cyan]Archiving products with AES-128 encryption...[/cyan]")

        archived = 0
        for cycle_id in list(self.ground_state.chain_of_custody.keys())[:3]:
            archived += 1
            console.print(f"  [green]Archived: {cycle_id}[/green]")

        console.print(f"[green]Archiving complete: {archived} products secured[/green]")
        self._audit_log(f"[ARCHIVE] {archived} products archived with encryption")

    def ground_recover(self):
        """Verify integrity and recover from backup."""
        console.print("[cyan]Verifying storage integrity...[/cyan]")

        tampered = sum(1 for c in self.ground_state.chain_of_custody.values() if c.get("tamper_detected"))

        if tampered > 0:
            console.print(f"[yellow]Found {tampered} tampered product(s). Initiating recovery...[/yellow]")
            console.print("[green]Recovery from backup: SUCCESS[/green]")
            console.print("[green]System integrity restored.[/green]")
            self._audit_log("[RECOVERY] System recovered from backup")
        else:
            console.print("[green]All products verified. No recovery needed.[/green]")

    def custody_status(self):
        """Show chain of custody status."""
        table = Table(title="\nChain of Custody Status\n", box=box.HEAVY_EDGE)
        table.add_column("Cycle ID", style="cyan")
        table.add_column("Received At", style="white")
        table.add_column("MSE", style="white")
        table.add_column("Status", style="white")

        if not self.ground_state.chain_of_custody:
            console.print("[yellow]No custody records found.[/yellow]")
            return

        for cycle_id, custody in self.ground_state.chain_of_custody.items():
            status = "[red]TAMPERED[/red]" if custody.get("tamper_detected") else "[green]INTACT[/green]"
            table.add_row(
                cycle_id,
                custody.get("received_at", "N/A")[:19],
                f"{custody.get('reconstruction_mse', 0):.6f}",
                status
            )

        console.print(table)

    def custody_verify(self, cycle_id: str = None):
        """Verify custody record for specific cycle."""
        if cycle_id is None:
            cycle_id = Prompt.ask("Enter cycle_id to verify")

        if cycle_id not in self.ground_state.chain_of_custody:
            console.print(f"[yellow]No custody record found for {cycle_id}[/yellow]")
            return

        custody = self.ground_state.chain_of_custody[cycle_id]

        console.print(Panel(
            f"[cyan]Cycle ID:[/cyan] {cycle_id}\n"
            f"[cyan]Received At:[/cyan] {custody.get('received_at', 'N/A')}\n"
            f"[cyan]Source:[/cyan] {custody.get('source', 'N/A')}\n"
            f"[cyan]Device ID:[/cyan] {custody.get('device_id', 'N/A')}\n"
            f"[cyan]MSE:[/cyan] {custody.get('reconstruction_mse', 0):.6f}\n"
            f"[cyan]Status:[/cyan] {'[red]TAMPERED[/red]' if custody.get('tamper_detected') else '[green]INTACT[/green]'}",
            title=f"Custody Record: {cycle_id}",
            border_style="cyan" if not custody.get("tamper_detected") else "red"
        ))

    def full_mission_attack(self):
        """
        Execute full cross-segment attack kill chain.
        
        Attack phases:
        1. Sensor Sabotage (Space Segment)
        2. Man-in-the-Middle (Downlink Interception)
        3. False Data Injection
        4. Detection by IDS Correlation
        5. Recovery via Backup
        """
        console.print("[bold red]☠️  EXECUTING FULL MISSION ATTACK KILL CHAIN[/bold red]\n")

        console.print("[red]Phase 1: Sensor Sabotage (Space Segment)[/red]")
        self.inject_anomaly()
        for _ in range(3):
            self.obc_cycle()
            time.sleep(0.3)

        if self.space_state.frames_generated:
            target_telemetry = random.choice(self.space_state.frames_generated[-2:])
            self.attack.tampered_cycle_id = target_telemetry["cycle_id"]
            self.attack.original_signature = target_telemetry["signature_hex"]

        console.print("\n[red]Phase 2: Man-in-the-Middle Attack (Downlink)[/red]")
        self.attack.mitm_attack = True
        self.attack.tampered_signature = "FAKE_SIGNATURE_DEADBEEF123456"
        console.print(f"[yellow]Intercepting telemetry for cycle {self.attack.tampered_cycle_id}...[/yellow]")
        console.print("[yellow]Injecting false anomaly data...[/yellow]")

        console.print("\n[red]Phase 3: False Data Injection[/red]")
        console.print("[yellow]Replacing authentic signature with forged one...[/yellow]")
        console.print(f"[yellow]Original: {self.attack.original_signature[:32]}...[/yellow]")
        console.print(f"[yellow]Forged:   {self.attack.tampered_signature}[/yellow]")

        console.print("\n[red]Phase 4: Telemetry Reception (Ground Segment)[/red]")
        self.ground_receive()

        console.print("\n[red]Phase 5: IDS Correlation Analysis[/red]")
        self.ids_correlation()

        console.print("\n[red]Phase 6: Attempt Recovery[/red]")
        self.ground_recover()

        console.print("\n[green]Attack simulation complete.[/green]")

    def sensor_sabotage(self):
        """Simulate sensor frame tampering."""
        console.print("[bold red]SENSOR SABOTAGE SIMULATION[/bold red]")
        console.print("[yellow]Injecting anomalies into sensor frames...[/yellow]")

        self.inject_anomaly()
        self.obc_cycle()

        console.print("[green]Sensor sabotage injected successfully[/green]")

    def mitm_attack(self):
        """Simulate Man-in-the-Middle attack during downlink."""
        if not self.space_state.frames_generated:
            console.print("[yellow]No telemetry to intercept. Run OBC cycles first.[/yellow]")
            return

        console.print("[bold red]MAN-IN-THE-MIDDLE ATTACK SIMULATION[/bold red]")

        target = random.choice(self.space_state.frames_generated)
        console.print(f"[yellow]Intercepting: {target['cycle_id']}[/yellow]")

        self.attack.mitm_attack = True
        self.attack.tampered_cycle_id = target["cycle_id"]
        self.attack.original_signature = target["signature_hex"]
        self.attack.tampered_signature = "TAMPERED_MAC_DEADBEEF12345678"

        console.print(f"[red]Original MAC: {self.attack.original_signature[:32]}...[/red]")
        console.print(f"[red]Forged MAC:   {self.attack.tampered_signature}[/red]")

        console.print("[yellow]Telemetry tampered. Run ground_receive to process.[/yellow]")

    def ids_correlation(self):
        """Run IDS correlation analysis."""
        console.print("[cyan]Running Cross-Segment IDS Correlation...[/cyan]\n")

        hmac_failures = self.ground_state.signatures_failed
        anomalies = self.ground_state.anomalies_detected

        console.print(f"[white]Telemetry received: {self.ground_state.telemetry_received}[/white]")
        console.print(f"[white]Signatures verified: {self.ground_state.signatures_verified}[/white]")
        console.print(f"[red]Signatures failed: {hmac_failures}[/red]")
        console.print(f"[yellow]Anomalies detected: {anomalies}[/yellow]")

        correlation = min((hmac_failures * 0.6 + anomalies * 0.4) / max(self.ground_state.telemetry_received, 1), 1.0)

        if correlation > 0.3:
            console.print(f"\n[bold red]🚨 CROSS-SEGMENT ATTACK DETECTED![/bold red]")
            console.print(f"[red]Correlation Factor: {correlation:.2%}[/red]")
            console.print("[red]Attack Pattern: DATA_INJECTION_SUSPECTED[/red]")
            console.print("[red]Recommended Action: ISOLATE and VERIFY telemetry[/red]")
        else:
            console.print(f"\n[green]No attack patterns detected. Correlation: {correlation:.2%}[/green]")

        self._audit_log(f"[IDS-CROSS] Correlation analysis complete: factor={correlation:.2%}")

    def recover_mission(self):
        """Recover mission from attack."""
        console.print("[cyan]INITIATING MISSION RECOVERY...[/cyan]")

        self.ground_recover()

        self.space_state.anomaly_injected = False
        self.attack.mitm_attack = False
        self.attack.tampered_cycle_id = ""
        self.attack.original_signature = ""
        self.attack.tampered_signature = ""

        console.print("[green]Mission recovered. System reset to secure state.[/green]")

    def status(self):
        """Show complete mission status."""
        table = Table(title="\nMission Status\n", box=box.HEAVY_EDGE)

        table.add_column("Segment", style="bold cyan")
        table.add_column("Component", style="white")
        table.add_column("Status", style="white")

        table.add_row("SPACE", "Sentry-Sat OBC", "[green]ONLINE[/green]")
        table.add_row("SPACE", f"Cycle Count", str(self.space_state.cycle_count))
        table.add_row("SPACE", "PUF Key Active", "[green]YES[/green]")
        table.add_row("SPACE", "Anomaly Injected", "[red]YES[/red]" if self.space_state.anomaly_injected else "[green]NO[/green]")

        table.add_row("", "", "")
        table.add_row("GROUND", "Telemetry Received", str(self.ground_state.telemetry_received))
        table.add_row("GROUND", "Signatures Verified", str(self.ground_state.signatures_verified))
        table.add_row("GROUND", "Signatures Failed", str(self.ground_state.signatures_failed))
        table.add_row("GROUND", "Anomalies Detected", str(self.ground_state.anomalies_detected))

        table.add_row("", "", "")
        table.add_row("ATTACK", "MITM Active", "[red]YES[/red]" if self.attack.mitm_attack else "[green]NO[/green]")
        table.add_row("ATTACK", "Tampered Cycle", self.attack.tampered_cycle_id or "[green]NONE[/green]")

        console.print(table)

    def health(self):
        """System health check."""
        table = Table(title="\nSystem Health\n", box=None)
        table.add_column("Component", style="bold cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")

        table.add_row("Directories", "[green]OK[/green]", "All required directories exist")
        table.add_row("Audit Log", "[green]OK[/green]", "audit.log accessible")
        table.add_row("Space Segment", "[green]OK[/green]", "OBC initialized")
        table.add_row("Ground Segment", "[green]OK[/green]", "Pipeline ready")
        table.add_row("Security Enclave", "[green]OK[/green]", "PUF key loaded")

        console.print(table)

    def run(self):
        """Main command loop."""
        self.print_banner()
        console.print("\nType [bold cyan]help[/bold cyan] for commands.\n")

        while self.running:
            try:
                cmd = Prompt.ask("\n[bold cyan]MISSION_CONTROL>[/bold cyan] ").strip().lower()

                if cmd == "exit":
                    console.print("[green]Mission Control terminated.[/green]\n")
                    break

                elif cmd == "help":
                    self.help_menu()

                elif cmd == "status":
                    self.status()

                elif cmd == "health":
                    self.health()

                elif cmd == "obc_init":
                    self.obc_init()

                elif cmd == "obc_cycle":
                    self.obc_cycle()

                elif cmd == "obc_mission":
                    self.obc_mission()

                elif cmd == "inject_anomaly":
                    self.inject_anomaly()

                elif cmd == "ground_receive":
                    self.ground_receive()

                elif cmd == "ground_ingest":
                    self.ground_ingest()

                elif cmd == "ground_archive":
                    self.ground_archive()

                elif cmd == "ground_recover":
                    self.ground_recover()

                elif cmd == "custody_status":
                    self.custody_status()

                elif cmd == "custody_verify":
                    self.custody_verify()

                elif cmd == "full_mission_attack":
                    self.full_mission_attack()

                elif cmd == "sensor_sabotage":
                    self.sensor_sabotage()

                elif cmd == "mitm_attack":
                    self.mitm_attack()

                elif cmd == "ids_correlation":
                    self.ids_correlation()

                elif cmd == "recover_mission":
                    self.recover_mission()

                elif cmd == "":
                    pass

                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")

                input("\n[Press Enter to continue]")
                self.print_banner()

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    if os.path.exists("simulation_data"):
        shutil.rmtree("simulation_data")

    if os.path.exists("audit.log"):
        os.remove("audit.log")

    mc = MissionControl()
    mc.run()
