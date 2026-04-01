#!/usr/bin/env python3
"""
Sentry-Sat Mission Control  ·  ESOC-style TUI
──────────────────────────────────────────────
ESA / ESOC aesthetic: deep navy background, cold-white text, amber accents
for alerts, crisp monospace layout.  Every panel has a purpose.

Keyboard shortcuts
  b  Build C++ core engine         t  Train autoencoder
  r  Run OBC simulator             e  Export TFLite INT8
  a  Simulate acquisition          f  Export TFLite FP32
  s  SHAP explainability           d  Environment doctor
  v  Verify TFLite model           x  Clean build dir
  ?  Refresh status                q  Quit
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import platform
import shutil
import sys
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static

# ─── Repository layout ────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
CORE     = ROOT / "core_engine"
BUILD    = CORE / "build"
AI       = ROOT / "ai_training"
SIM_NAME = "sentry_sat_sim.exe" if platform.system() == "Windows" else "sentry_sat_sim"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mission_log_path() -> Path:
    override = os.environ.get("SENTRY_MISSION_LOG")
    return Path(override) if override else (ROOT / ".sentry_mission.log")

def _ai_python() -> Path:
    for candidate in [
        AI / "venv" / "bin"     / "python3",
        AI / "venv" / "Scripts" / "python.exe",
    ]:
        if candidate.is_file():
            return candidate
    return Path(sys.executable)

def _cmake() -> str | None:
    return shutil.which("cmake")

def _utc_stamp() -> str:
    return datetime.datetime.utcnow().strftime("%H:%M:%S UTC")

# ─── ASCII sensor-frame renderer ──────────────────────────────────────────────
_RAMP = " ·:;+=xX$&#"   # 11 levels  (space → very bright)

def _frame_to_coloured_ascii(flat: list[float], w: int = 28, h: int = 28) -> str:
    """
    Render a flat float32 list as a Rich-marked ASCII block.
    Each pixel maps to a character from the brightness ramp, coloured by level:
      near-zero  → dim blue   (cold space / dark field)
      mid        → ESA blue   (nominal signal)
      high       → white      (strong signal)
      saturated  → bold red   (anomaly indicator)
    """
    lines: list[str] = []
    for row in range(h):
        chars: list[str] = []
        for col in range(w):
            v   = max(0.0, min(1.0, flat[row * w + col]))
            idx = min(int(v * (len(_RAMP) - 1)), len(_RAMP) - 1)
            ch  = _RAMP[idx] * 2           # ×2 compensates for terminal aspect ratio
            if v == 0.0:
                chars.append(f"[#1e3a5f]{ch}[/]")
            elif v < 0.25:
                chars.append(f"[#2a4a7a]{ch}[/]")
            elif v < 0.55:
                chars.append(f"[#4a8abf]{ch}[/]")
            elif v < 0.80:
                chars.append(f"[#7eb8f7]{ch}[/]")
            elif v < 0.95:
                chars.append(f"[bold #c8e0ff]{ch}[/]")
            else:
                chars.append(f"[bold red]{ch}[/]")   # saturated = anomaly
        lines.append("".join(chars))
    return "\n".join(lines)

# ─── Telemetry parser ─────────────────────────────────────────────────────────

def _parse_telemetry(line: str) -> dict | None:
    stripped = line.strip()
    if not stripped.startswith("[json]"):
        return None
    try:
        return json.loads(stripped[6:].strip())
    except json.JSONDecodeError:
        return None

def _format_telem_log(obj: dict) -> str:
    cid     = obj.get("cycle_id", "?")
    anomaly = obj.get("anomaly", False)
    mse     = obj.get("reconstruction_mse", 0)
    backend = obj.get("inference_backend", "?")
    mac     = (obj.get("signature_hex", "") or "")[:12] + "…"
    status  = "[bold red]⚠ ANOMALY[/]" if anomaly else "[green]✓ NOMINAL[/]"
    return (
        f"  [bold cyan]{cid}[/]  {status}  "
        f"[dim]MSE[/] [yellow]{mse:.5f}[/]  "
        f"[dim]{backend}[/]  [dim]mac {mac}[/]"
    )

# ─── Acquisition modal ────────────────────────────────────────────────────────

class AcquisitionScreen(ModalScreen[dict | None]):
    """ESA-styled modal for sensor acquisition parameters."""

    CSS = """
    AcquisitionScreen { align: center middle; }
    #acq_box {
        width: 64; height: auto;
        border: solid #1e3a5f;
        background: #0b1d3a;
        padding: 1 2;
    }
    #acq_title { color: #7eb8f7; text-style: bold; margin-bottom: 1; }
    #acq_box Label { color: #4a7aaa; margin-top: 1; }
    #acq_box Input { width: 100%; background: #09101f; color: #ccd6f6; border: solid #1e3a5f; }
    #acq_footer { layout: horizontal; height: 3; margin-top: 1; align: right middle; }
    #acq_footer Button { margin-left: 1; min-width: 16; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="acq_box"):
            yield Static("▶  SENSOR ACQUISITION PARAMETERS", id="acq_title")
            yield Label("Image path  (blank = synthetic frame):")
            yield Input(placeholder="/path/to/image.png", id="inp_image")
            yield Label("Synthetic type  [ nominal | anomaly ]:")
            yield Input(value="nominal", id="inp_type")
            yield Label("Inject artifact on loaded image?  [ yes | no ]:")
            yield Input(value="no", id="inp_inject")
            yield Label("Inference backend  [ auto | heuristic | tflite | keras ]:")
            yield Input(value="auto", id="inp_backend")
            yield Label("RNG seed:")
            yield Input(value="42", id="inp_seed")
            with Horizontal(id="acq_footer"):
                yield Button("CONFIRM  [↵]",   id="btn_ok",     variant="primary")
                yield Button("CANCEL   [Esc]", id="btn_cancel", variant="default")

    def on_key(self, event) -> None:
        if event.key == "enter":   self._submit()
        if event.key == "escape":  self.dismiss(None)

    @on(Button.Pressed, "#btn_ok")
    def _submit(self) -> None:
        def v(wid): return self.query_one(wid, Input).value.strip()
        inject = v("#inp_inject").lower() in ("yes","y","true","1")
        self.dismiss({
            "image":          v("#inp_image"),
            "frame_type":     v("#inp_type").lower(),
            "inject_anomaly": inject,
            "backend":        v("#inp_backend").lower(),
            "seed":           v("#inp_seed"),
        })

    @on(Button.Pressed, "#btn_cancel")
    def _cancel(self) -> None:
        self.dismiss(None)

# ─── Main application ─────────────────────────────────────────────────────────

class SentryMissionControl(App[None]):
    """
    ESOC-style Mission Control TUI for the Sentry-Sat OBC pipeline.

    Three-column layout:
      LEFT   narrow operations menu (keyboard shortcuts)
      CENTRE streaming command output log
      RIGHT  live telemetry panel + 28×28 ASCII sensor frame
    """

    TITLE     = "SENTRY-SAT  ·  MISSION CONTROL"
    SUB_TITLE = "Ground Software  v1.1  ·  ESOC"

    CSS = """
    /* ── Global ──────────────────────────────────────────────────────────── */
    Screen {
        layout: vertical;
        background: #09101f;
        color: #ccd6f6;
    }
    Header {
        background: #071428;
        color: #7eb8f7;
        text-style: bold;
    }
    Header.-tall { height: 3; }

    /* ── Status bar ───────────────────────────────────────────────────────── */
    #statusbar {
        height: 3;
        background: #071428;
        border-bottom: solid #1a3050;
        padding: 0 2;
        layout: horizontal;
        align: left middle;
    }

    /* ── Body ─────────────────────────────────────────────────────────────── */
    #body { layout: horizontal; height: 1fr; }

    /* ── Left menu ────────────────────────────────────────────────────────── */
    #menu-panel {
        width: 30;
        min-width: 30;
        background: #071428;
        border-right: solid #1a3050;
        padding: 1 0;
        layout: vertical;
    }
    #menu-title {
        text-align: center;
        color: #7eb8f7;
        text-style: bold;
        padding: 0 1;
        margin-bottom: 1;
        border-bottom: solid #1a3050;
    }
    .menu-section {
        color: #2a4a6a;
        text-style: bold;
        padding: 0 2;
        margin-top: 1;
    }
    #menu-panel Button {
        width: 100%;
        height: 2;
        background: transparent;
        border: none;
        text-align: left;
        padding: 0 2;
        color: #8ab0d0;
        margin: 0;
    }
    #menu-panel Button:hover {
        background: #122040;
        color: #c0d8f0;
    }
    #menu-panel Button:focus {
        background: #0e2040;
        border: none;
        color: #7eb8f7;
    }
    #btn_acquire { color: #f0c850 !important; }
    #btn_acquire:hover { background: #201808 !important; color: #ffd870 !important; }

    /* ── Centre log ───────────────────────────────────────────────────────── */
    #log-panel { width: 1fr; background: #09101f; border-right: solid #1a3050; layout: vertical; }
    #log-label {
        background: #071428;
        color: #7eb8f7;
        text-style: bold;
        padding: 0 2;
        height: 2;
        border-bottom: solid #1a3050;
    }
    #log { height: 1fr; background: #09101f; border: none; padding: 0 1; }

    /* ── Right panel ──────────────────────────────────────────────────────── */
    #right-panel { width: 62; min-width: 62; background: #060e1a; layout: vertical; }

    #telem-label {
        background: #071428;
        color: #7eb8f7;
        text-style: bold;
        padding: 0 2;
        height: 2;
        border-bottom: solid #1a3050;
    }
    #telem-body { height: 11; padding: 1; border-bottom: solid #1a3050; }

    #frame-label {
        background: #071428;
        color: #7eb8f7;
        text-style: bold;
        padding: 0 2;
        height: 2;
        border-bottom: solid #1a3050;
    }
    #frame-body { height: 1fr; padding: 0 1; }

    /* ── Footer ───────────────────────────────────────────────────────────── */
    Footer { background: #071428; color: #2a4a6a; }
    Footer > .footer--key { background: #1a3050; color: #7eb8f7; }
    """

    BINDINGS = [
        Binding("b",             "do_build",   "b Build",       show=True),
        Binding("r",             "do_run",     "r Run OBC",     show=True),
        Binding("t",             "do_train",   "t Train",       show=True),
        Binding("e",             "do_tflite",  "e INT8",        show=True),
        Binding("f",             "do_fp32",    "f FP32",        show=True),
        Binding("a",             "do_acquire", "a Acquire",     show=True),
        Binding("s",             "do_shap",    "s SHAP",        show=True),
        Binding("d",             "do_doctor",  "d Doctor",      show=True),
        Binding("v",             "do_verify",  "v Verify",      show=True),
        Binding("x",             "do_clean",   "x Clean",       show=True),
        Binding("question_mark", "do_status",  "? Status",      show=True),
        Binding("q",             "quit",       "q Quit",        show=True),
    ]

    # ── Compose ───────────────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header()

        # ── Status bar ─────────────────────────────────────────────────────
        with Horizontal(id="statusbar"):
            yield Static("", id="status-inline")

        # ── Body ───────────────────────────────────────────────────────────
        with Horizontal(id="body"):

            # Left: operations menu
            with Vertical(id="menu-panel"):
                yield Static("◈  OPERATIONS", id="menu-title")
                yield Static("── SIMULATION ──", classes="menu-section")
                yield Button("b)  Build core engine",     id="btn_build")
                yield Button("r)  Run OBC simulator",     id="btn_run")
                yield Button("a)  Simulate acquisition",  id="btn_acquire")
                yield Static("── AI PIPELINE ──", classes="menu-section")
                yield Button("t)  Train autoencoder",     id="btn_train")
                yield Button("e)  Export INT8 TFLite",    id="btn_tflite")
                yield Button("f)  Export FP32 TFLite",    id="btn_fp32")
                yield Button("s)  SHAP explainability",   id="btn_shap")
                yield Static("── TOOLS ──", classes="menu-section")
                yield Button("d)  Environment doctor",    id="btn_doctor")
                yield Button("v)  Verify TFLite model",   id="btn_verify")
                yield Button("x)  Clean build dir",       id="btn_clean")
                yield Button("?)  Refresh status",        id="btn_status")

            # Centre: log
            with Vertical(id="log-panel"):
                yield Static(
                    "  ▶  MISSION LOG", id="log-label")
                yield RichLog(id="log", highlight=False, markup=True, wrap=True)

            # Right: telemetry + ASCII frame
            with Vertical(id="right-panel"):
                yield Static("  ◈  LAST TELEMETRY CYCLE", id="telem-label")
                yield Static("  [dim]awaiting data…[/]",  id="telem-body")
                yield Static("  ◈  SENSOR FRAME  28 × 28 px", id="frame-label")
                yield Static("  [dim]no frame acquired[/]",   id="frame-body")

        yield Footer()

    # ── Mount ──────────────────────────────────────────────────────────────────
    def on_mount(self) -> None:
        self._refresh_statusbar()
        self._banner()

    # ── Status bar ────────────────────────────────────────────────────────────
    def _badge(self, path: Path, label: str) -> str:
        ok = path.is_file()
        return f"[{'green' if ok else 'dim #2a4a6a'}]{'●' if ok else '○'}  {label}[/]"

    def _refresh_statusbar(self) -> None:
        cmake_ok = _cmake() is not None
        parts = [
            self._badge(BUILD / SIM_NAME,                 "BUILD"),
            self._badge(AI / "autoencoder.h5",            "MODEL"),
            self._badge(AI / "anomaly_model.tflite",      "INT8"),
            self._badge(AI / "anomaly_model_fp32.tflite", "FP32"),
            self._badge(AI / "obc_model_meta.json",       "META"),
            f"[{'green' if cmake_ok else 'red'}]{'●' if cmake_ok else '○'}  cmake[/]",
            f"[dim #2a4a6a]{_utc_stamp()}[/]",
        ]
        self.query_one("#status-inline", Static).update("    ".join(parts))

    # ── Banner ────────────────────────────────────────────────────────────────
    def _banner(self) -> None:
        log = self.query_one("#log", RichLog)
        ts  = _utc_stamp()
        log.write("")
        log.write("[bold #1a3a6a]╔══════════════════════════════════════════════════╗[/]")
        log.write("[bold #1a3a6a]║[/][bold #7eb8f7]  SENTRY-SAT  MISSION CONTROL  v1.1              [/][bold #1a3a6a]║[/]")
        log.write("[bold #1a3a6a]║[/][#4a7aaa]  European Space Operations Centre  (ESOC)         [/][bold #1a3a6a]║[/]")
        log.write(f"[bold #1a3a6a]║[/][dim]  Session started  {ts:<33}[/][bold #1a3a6a]║[/]")
        log.write("[bold #1a3a6a]╚══════════════════════════════════════════════════╝[/]")
        log.write("")
        log.write(f"[dim]  Root      {ROOT}[/]")
        log.write(f"[dim]  Log file  {_mission_log_path()}[/]")
        log.write("")

    # ── Log helpers ───────────────────────────────────────────────────────────
    def _log(self, msg: str) -> None:
        self.query_one("#log", RichLog).write(msg)

    def _log_plain(self, line: str) -> None:
        try:
            lp = _mission_log_path()
            lp.parent.mkdir(parents=True, exist_ok=True)
            with open(lp, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def _section(self, title: str) -> None:
        ts = _utc_stamp()
        self._log("")
        self._log(f"[#1a3a6a]{'─' * 60}[/]")
        self._log(f"[bold #7eb8f7]  ▶  {title}[/]  [dim]{ts}[/]")
        self._log(f"[#1a3a6a]{'─' * 60}[/]")

    def _ok_line(self, code: int) -> None:
        if code == 0:
            self._log("[bold green]  ✓  COMPLETED  (exit 0)[/]")
        else:
            self._log(f"[bold red]  ✗  FAILED  (exit {code})[/]")

    # ── Telemetry panel ───────────────────────────────────────────────────────
    def _update_telem(self, obj: dict) -> None:
        anomaly = obj.get("anomaly", False)
        mse     = obj.get("reconstruction_mse", 0.0)
        thr     = obj.get("threshold", "—")
        cid     = obj.get("cycle_id", "?")
        backend = obj.get("inference_backend", "?")
        mac     = (obj.get("signature_hex") or "—")
        src     = obj.get("acquisition_source", "")

        sc = "red" if anomaly else "green"
        st = "⚠  ANOMALY DETECTED" if anomaly else "✓  NOMINAL"

        lines = [
            f"  [{sc}]■  STATUS   {st}[/]",
            f"",
            f"  [dim]CYC_ID   [/][cyan]{cid}[/]",
            f"  [dim]MSE      [/][yellow]{mse:.8f}[/]",
            f"  [dim]THRESH   [/]{thr}",
            f"  [dim]BACKEND  [/]{backend}",
            f"  [dim]MAC      [/][dim]{mac[:32]}[/]",
        ]
        if src:
            name = Path(src).name if "/" in src or "\\" in src else src
            lines.append(f"  [dim]SOURCE   [/][dim]{name}[/]")

        self.query_one("#telem-body", Static).update("\n".join(lines))

    # ── Frame panel ───────────────────────────────────────────────────────────
    def _update_frame(self, flat: list[float]) -> None:
        art = _frame_to_coloured_ascii(flat)
        self.query_one("#frame-body", Static).update(art)

    # ── Generic subprocess streamer ───────────────────────────────────────────
    async def _stream(self, argv: list[str], cwd: Path, title: str) -> None:
        self._section(title)
        self._log(f"[dim]  $ {' '.join(str(a) for a in argv)}[/]")
        self._log_plain(f"=== {title} ===")
        self._log_plain(f"$ {' '.join(str(a) for a in argv)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *[str(a) for a in argv],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd),
            )
        except FileNotFoundError as exc:
            self._log(f"[red]  command not found: {exc}[/]")
            return

        assert proc.stdout
        frame_buf: list[float] = []

        async for raw in proc.stdout:
            plain = raw.decode(errors="replace").rstrip()

            # ── Telemetry JSON ────────────────────────────────────────────
            obj = _parse_telemetry(plain)
            if obj:
                self._log(_format_telem_log(obj))
                self._update_telem(obj)
                self._log_plain(plain)
                continue

            # ── Frame row data from simulate_acquisition.py ───────────────
            # The script emits lines like: [FRAME-ROW] 0.12 0.03 … (28 floats)
            if plain.startswith("[FRAME-ROW]"):
                try:
                    vals = [float(x) for x in plain[11:].split()]
                    frame_buf.extend(vals)
                    if len(frame_buf) >= 784:
                        self._update_frame(frame_buf[:784])
                        frame_buf = []
                except ValueError:
                    pass
                self._log_plain(plain)
                continue

            # ── Colour-coded log output ────────────────────────────────────
            lo = plain.lower()
            if any(k in lo for k in ("anomaly","alert","fatal","error","failed")):
                self._log(f"[bold red]  {plain}[/]")
            elif any(k in lo for k in ("✓","completed","saved","ok","nominal")):
                self._log(f"[green]  {plain}[/]")
            elif plain.startswith(("[OBC","[Trust","[ACQ","[ACQU")):
                self._log(f"[#7eb8f7]  {plain}[/]")
            elif plain.strip() == "":
                self._log("")
            else:
                self._log(f"[#8ab0d0]  {plain}[/]")
            self._log_plain(plain)

        code = await proc.wait()
        self._ok_line(code)
        self._log_plain(f"exit {code}")
        self._refresh_statusbar()

    # ── Build ─────────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_build(self) -> None:
        cmake = _cmake()
        if not cmake:
            self._log("[red]  cmake not found on PATH.[/]"); return
        BUILD.mkdir(parents=True, exist_ok=True)
        self._section("CONFIGURE  —  CMake")
        cfg = await asyncio.create_subprocess_exec(
            cmake, "-S", str(CORE), "-B", str(BUILD),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ROOT),
        )
        assert cfg.stdout
        async for raw in cfg.stdout:
            plain = raw.decode(errors="replace").rstrip()
            self._log(f"[dim]  {plain}[/]"); self._log_plain(plain)
        c1 = await cfg.wait()
        if c1 != 0:
            self._log(f"[bold red]  ✗  Configure failed — exit {c1}[/]")
            self._refresh_statusbar(); return
        self._section("COMPILE  —  CMake --build")
        bld = await asyncio.create_subprocess_exec(
            cmake, "--build", str(BUILD), "--parallel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert bld.stdout
        async for raw in bld.stdout:
            plain = raw.decode(errors="replace").rstrip()
            if "error:" in plain.lower():   self._log(f"[red]  {plain}[/]")
            elif "warning:" in plain.lower(): self._log(f"[yellow]  {plain}[/]")
            else:                             self._log(f"[dim]  {plain}[/]")
            self._log_plain(plain)
        self._ok_line(await bld.wait())
        self._refresh_statusbar()

    # ── Run OBC ───────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_run(self) -> None:
        exe = BUILD / SIM_NAME
        if not exe.is_file():
            self._log("[red]  Binary missing — build first.[/]"); return
        await self._stream([str(exe)], BUILD, "OBC SIMULATOR")

    # ── Train ─────────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_train(self) -> None:
        s = AI / "train_model.py"
        if not s.is_file(): self._log("[red]  train_model.py not found.[/]"); return
        await self._stream([str(_ai_python()), str(s)], AI, "AUTOENCODER TRAINING")

    # ── Export INT8 ───────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_tflite(self) -> None:
        if not (AI / "autoencoder.h5").is_file():
            self._log("[yellow]  autoencoder.h5 missing — train first.[/]"); return
        await self._stream([str(_ai_python()), str(AI / "export_tflite.py")], AI, "EXPORT  TFLite INT8")

    # ── Export FP32 ───────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_fp32(self) -> None:
        if not (AI / "autoencoder.h5").is_file():
            self._log("[yellow]  autoencoder.h5 missing — train first.[/]"); return
        await self._stream([str(_ai_python()), str(AI / "export_tflite_fp32.py")], AI, "EXPORT  TFLite FP32")

    # ── SHAP ──────────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_shap(self) -> None:
        if not (AI / "autoencoder.h5").is_file():
            self._log("[yellow]  autoencoder.h5 missing — train first.[/]"); return
        await self._stream([str(_ai_python()), str(AI / "shap_explainer.py")], AI, "SHAP EXPLAINABILITY")

    # ── Doctor ────────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_doctor(self) -> None:
        s = AI / "doctor.py"
        if not s.is_file(): self._log("[red]  doctor.py not found.[/]"); return
        await self._stream([str(_ai_python()), str(s)], AI, "ENVIRONMENT DOCTOR")

    # ── Verify ────────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_verify(self) -> None:
        if not (AI / "anomaly_model.tflite").is_file():
            self._log("[yellow]  anomaly_model.tflite missing.[/]"); return
        await self._stream([str(_ai_python()), str(AI / "verify_tflite.py")], AI, "VERIFY  TFLite MODEL")

    # ── Clean ─────────────────────────────────────────────────────────────────
    @work(exclusive=True, group="proc")
    async def _action_clean(self) -> None:
        self._section("CLEAN  BUILD DIRECTORY")
        if BUILD.exists():
            try:
                await asyncio.to_thread(shutil.rmtree, BUILD)
                self._log(f"[green]  ✓  Removed: {BUILD}[/]")
            except OSError as e:
                self._log(f"[red]  ✗  {e}[/]")
        else:
            self._log("[dim]  Build dir absent.[/]")
        self._refresh_statusbar()

    # ── Status ────────────────────────────────────────────────────────────────
    def _action_status(self) -> None:
        self._section("STATUS REFRESH")
        self._refresh_statusbar()
        checks = [
            ("cmake",         _cmake() is not None,                 shutil.which("cmake") or "—"),
            ("sentry_sat_sim",(BUILD/SIM_NAME).is_file(),           str(BUILD/SIM_NAME)),
            ("autoencoder.h5",(AI/"autoencoder.h5").is_file(),      str(AI/"autoencoder.h5")),
            ("INT8 .tflite",  (AI/"anomaly_model.tflite").is_file(),str(AI/"anomaly_model.tflite")),
            ("FP32 .tflite",  (AI/"anomaly_model_fp32.tflite").is_file(), str(AI/"anomaly_model_fp32.tflite")),
            ("obc_meta.json", (AI/"obc_model_meta.json").is_file(), str(AI/"obc_model_meta.json")),
            ("simulate_acq",  (AI/"simulate_acquisition.py").is_file(), str(AI/"simulate_acquisition.py")),
        ]
        for label, ok, path in checks:
            c = "green" if ok else "dim #2a4a6a"
            i = "●" if ok else "○"
            self._log(f"  [{c}]{i}[/]  [dim]{label:<22}[/] [{c}]{path}[/]")

    # ── Acquisition ───────────────────────────────────────────────────────────
    def _action_acquire(self) -> None:
        self.push_screen(AcquisitionScreen(), self._run_acquisition)

    @work(exclusive=True, group="proc")
    async def _run_acquisition(self, params: dict | None) -> None:
        if params is None:
            self._log("[dim]  Acquisition cancelled.[/]"); return
        script = AI / "simulate_acquisition.py"
        if not script.is_file():
            self._log("[red]  simulate_acquisition.py not found.[/]"); return

        argv: list[str] = [str(_ai_python()), str(script)]

        image = params.get("image", "")
        if image:
            argv += ["--image", image]
            if params.get("inject_anomaly"):
                argv.append("--inject-anomaly")
        else:
            if params.get("frame_type") == "anomaly":
                argv.append("--inject-anomaly")

        backend = params.get("backend", "auto")
        if backend == "heuristic":
            argv.append("--no-model")
        elif backend == "tflite" and (AI / "anomaly_model_fp32.tflite").is_file():
            argv += ["--tflite", str(AI / "anomaly_model_fp32.tflite")]
        elif backend == "keras":
            argv += ["--model", str(AI / "autoencoder.h5")]

        argv += ["--seed", str(params.get("seed", "42"))]
        argv += ["--emit-frame-rows"]   # machine-readable row data for TUI frame panel
        argv += ["--ascii"]             # human-readable preview still goes to log

        await self._stream(argv, AI, "SENSOR ACQUISITION SIMULATION")

    # ── Action routing ────────────────────────────────────────────────────────
    def action_do_build(self)   -> None: self._action_build()
    def action_do_run(self)     -> None: self._action_run()
    def action_do_train(self)   -> None: self._action_train()
    def action_do_tflite(self)  -> None: self._action_tflite()
    def action_do_fp32(self)    -> None: self._action_fp32()
    def action_do_acquire(self) -> None: self._action_acquire()
    def action_do_shap(self)    -> None: self._action_shap()
    def action_do_doctor(self)  -> None: self._action_doctor()
    def action_do_verify(self)  -> None: self._action_verify()
    def action_do_clean(self)   -> None: self._action_clean()
    def action_do_status(self)  -> None: self._action_status()

    # ── Button handlers ────────────────────────────────────────────────────────
    @on(Button.Pressed, "#btn_build")
    def _hb(self, _): self._action_build()

    @on(Button.Pressed, "#btn_run")
    def _hr(self, _): self._action_run()

    @on(Button.Pressed, "#btn_acquire")
    def _ha(self, _): self._action_acquire()

    @on(Button.Pressed, "#btn_train")
    def _ht(self, _): self._action_train()

    @on(Button.Pressed, "#btn_tflite")
    def _he(self, _): self._action_tflite()

    @on(Button.Pressed, "#btn_fp32")
    def _hf(self, _): self._action_fp32()

    @on(Button.Pressed, "#btn_shap")
    def _hs(self, _): self._action_shap()

    @on(Button.Pressed, "#btn_doctor")
    def _hd(self, _): self._action_doctor()

    @on(Button.Pressed, "#btn_verify")
    def _hv(self, _): self._action_verify()

    @on(Button.Pressed, "#btn_clean")
    def _hx(self, _): self._action_clean()

    @on(Button.Pressed, "#btn_status")
    def _hq(self, _): self._action_status()


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    SentryMissionControl().run()

if __name__ == "__main__":
    main()