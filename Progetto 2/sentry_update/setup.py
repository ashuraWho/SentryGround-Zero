#!/usr/bin/env python3
"""
Sentry-Sat  —  one-command setup
Usage:  python setup.py

What it does, in order:
  1. Detects OS and installs system packages (cmake, gcc, libssl-dev)
  2. Copies every updated file from outputs/ into the right project folder
  3. Creates console/.venv  and installs textual
  4. Creates ai_training/venv and installs all ML deps
  5. Builds the C++ simulator with CMake
  6. Prints a final checklist and the single command to launch the TUI
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

# ─── Colours (no dependencies) ───────────────────────────────────────────────
_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")

def _c(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"

def ok(msg):   print(_c("32", "  ✓  ") + msg)
def info(msg): print(_c("36", "  ·  ") + msg)
def warn(msg): print(_c("33", "  ⚠  ") + msg)
def err(msg):  print(_c("31", "  ✗  ") + msg)
def head(msg): print("\n" + _c("1;34", f"══  {msg}"))

def run(cmd: list[str], **kw) -> int:
    """Run a command, stream output, return exit code."""
    info("$ " + " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, **kw)
    return result.returncode

def must(cmd: list[str], msg: str = "", **kw) -> None:
    """Run a command; abort the whole script if it fails."""
    rc = run(cmd, **kw)
    if rc != 0:
        err(f"Command failed (exit {rc}){': ' + msg if msg else ''}")
        sys.exit(rc)

# ─── Paths ────────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent

def _find_root(start):
    current = start
    for _ in range(6):
        if (current / "core_engine").is_dir():
            return current
        current = current.parent
    return None

ROOT = _find_root(HERE)
if ROOT is None:
    err("Cannot find core_engine/ in any parent folder.")
    err("Run: python setup.py  from anywhere inside the Sentry-Sat project.")
    sys.exit(1)

info(f"Project root: {ROOT}")
OUTPUTS = HERE

CORE    = ROOT / "core_engine"
BUILD   = CORE / "build"
AI      = ROOT / "ai_training"
CONSOLE = ROOT / "console"
SEC     = ROOT / "security_enclave" / "src"

OS = platform.system()   # "Linux", "Darwin", "Windows"

# ─── File placement map ───────────────────────────────────────────────────────
# (source_filename_in_outputs_dir, destination_relative_to_ROOT)
FILE_MAP: list[tuple[str, str]] = [
    ("CMakeLists.txt",         "core_engine/CMakeLists.txt"),
    ("main.cpp",               "core_engine/src/main.cpp"),
    ("memory_pool.h",          "core_engine/src/memory_pool.h"),
    ("memory_pool.cpp",        "core_engine/src/memory_pool.cpp"),
    ("inference_engine.h",     "core_engine/src/inference_engine.h"),
    ("inference_engine.cpp",   "core_engine/src/inference_engine.cpp"),
    ("crypto_signer.cpp",      "security_enclave/src/crypto_signer.cpp"),
    ("simulate_acquisition.py","ai_training/simulate_acquisition.py"),
    ("sentry_console.py",      "console/sentry_console.py"),
    ("README.md",              "README.md"),
]

# ─── Step 1: system packages ──────────────────────────────────────────────────
def step_system_packages() -> None:
    head("STEP 1 / 5  —  System packages")

    if OS == "Linux":
        need = []
        for pkg, binary in [
            ("cmake",         "cmake"),
            ("gcc",           "gcc"),
            ("libssl-dev",    None),   # no single binary to check
            ("python3-venv",  None),
        ]:
            if binary and shutil.which(binary):
                ok(f"{pkg} already present")
            else:
                need.append(pkg)

        if need:
            info(f"Installing: {' '.join(need)}")
            must(["sudo", "apt-get", "install", "-y"] + need)
        else:
            ok("All system packages present")

    elif OS == "Darwin":
        if not shutil.which("brew"):
            err("Homebrew not found. Install it from https://brew.sh/ then re-run.")
            sys.exit(1)
        for pkg, binary in [("cmake", "cmake"), ("openssl@3", None)]:
            if binary and shutil.which(binary):
                ok(f"{pkg} already present")
            else:
                must(["brew", "install", pkg])

    elif OS == "Windows":
        warn("Windows detected. Make sure you have:")
        warn("  cmake, Visual Studio 2022 (C++ workload), and OpenSSL on PATH.")
        warn("Skipping automatic system install — continuing.")

    else:
        warn(f"Unknown OS '{OS}' — skipping system package install.")

# ─── Step 2: copy updated files ───────────────────────────────────────────────
def step_copy_files() -> None:
    head("STEP 2 / 5  —  Copy updated files into project")

    copied = 0
    skipped = 0
    for src_name, dst_rel in FILE_MAP:
        dst = ROOT / dst_rel

        # Search for the source file: first next to setup.py, then anywhere
        # inside the project that isn't the destination itself.
        src = OUTPUTS / src_name
        if not src.is_file():
            warn(f"Source not found, skipping: {src_name}")
            skipped += 1
            continue

        # Skip if source and destination are literally the same file.
        try:
            if src.resolve() == dst.resolve():
                ok(f"{src_name}  already in place (skipped self-copy)")
                copied += 1
                continue
        except OSError:
            pass

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        ok(f"{src_name}  →  {dst_rel}")
        copied += 1

    info(f"{copied} files copied, {skipped} skipped")

# ─── Step 3: console venv ─────────────────────────────────────────────────────
def step_console_venv() -> None:
    head("STEP 3 / 5  —  Console virtual environment  (console/.venv)")

    venv_dir = CONSOLE / ".venv"

    # Safety check: if this script is being run from inside the venv we are
    # about to delete, rmtree will fail with ENOTEMPTY on macOS.
    running_from = Path(sys.executable).resolve()
    if str(running_from).startswith(str(venv_dir.resolve())):
        err("You are running setup.py with the Python inside console/.venv.")
        err("That venv is locked while Python is using it — cannot recreate it.")
        err("")
        err("Run setup.py with your system or Anaconda Python instead:")
        err(f"  /opt/anaconda3/bin/python {Path(__file__).resolve()}")
        err("  or")
        err(f"  python3 {Path(__file__).resolve()}")
        sys.exit(1)

    if venv_dir.is_dir():
        info("Removing existing venv (will recreate clean)...")
        if OS == "Windows":
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(venv_dir)])
        else:
            subprocess.run(["rm", "-rf", str(venv_dir)])

    info("Creating venv...")
    must([sys.executable, "-m", "venv", str(venv_dir)])

    venv_py = _venv_bin(venv_dir, "python")
    must([str(venv_py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    must([str(venv_py), "-m", "pip", "install", "--quiet", "textual>=0.47.0"])
    ok("textual installed")

def step_ai_venv() -> None:
    head("STEP 4 / 5  —  AI training virtual environment  (ai_training/venv)")

    venv_dir = AI / "venv"
    py = sys.executable
    req = AI / "requirements.txt"

    venv_py = _venv_bin(venv_dir, "python")
    if venv_dir.is_dir() and not venv_py.is_file():
        warn("venv broken — deleting and recreating...")
        shutil.rmtree(venv_dir)

    if not venv_dir.is_dir():
        info("Creating venv...")
        must([py, "-m", "venv", str(venv_dir)])
    else:
        ok("venv already exists")

    venv_py = _venv_bin(venv_dir, "python")
    must([str(venv_py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])

    if req.is_file():
        info("Installing ai_training/requirements.txt  (may take a few minutes)...")
        must([str(venv_py), "-m", "pip", "install", "--quiet", "-r", str(req)])
        ok("ML dependencies installed")
    else:
        warn("requirements.txt not found — skipping ML deps")

# ─── Step 5: build C++ ────────────────────────────────────────────────────────
def step_build_cpp() -> None:
    head("STEP 5 / 5  —  Build C++ simulator  (CMake)")

    cmake = shutil.which("cmake")
    if not cmake:
        err("cmake not found — skipping C++ build.")
        err("Install cmake and run:  cmake -S core_engine -B core_engine/build && cmake --build core_engine/build --parallel")
        return

    BUILD.mkdir(parents=True, exist_ok=True)

    # Wipe CMakeCache if it was generated from a different source path.
    # This happens when the project folder was moved or renamed.
    cache = BUILD / "CMakeCache.txt"
    if cache.is_file():
        cache_content = cache.read_text(errors="replace")
        if str(CORE) not in cache_content:
            warn("CMakeCache.txt points to wrong source dir — wiping build/...")
            if OS == "Windows":
                subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(BUILD)])
            else:
                subprocess.run(["rm", "-rf", str(BUILD)])
            BUILD.mkdir(parents=True, exist_ok=True)

    info("CMake configure...")
    rc = run([cmake, "-S", str(CORE), "-B", str(BUILD)], cwd=str(ROOT))
    if rc != 0:
        err(f"Configure failed (exit {rc})")
        return

    info("CMake build...")
    rc = run([cmake, "--build", str(BUILD), "--parallel"], cwd=str(ROOT))
    if rc != 0:
        err(f"Build failed (exit {rc})")
        return

    sim = BUILD / ("sentry_sat_sim.exe" if OS == "Windows" else "sentry_sat_sim")
    if sim.is_file():
        ok(f"Binary ready: {sim}")
    else:
        warn("Binary not found after build — check errors above")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _venv_bin(venv: Path, name: str) -> Path:
    if OS == "Windows":
        return venv / "Scripts" / (name + ".exe")
    return venv / "bin" / name

# ─── Final summary ────────────────────────────────────────────────────────────
def summary() -> None:
    head("SETUP COMPLETE")

    console_py = _venv_bin(CONSOLE / ".venv", "python")
    sentry_py  = CONSOLE / "sentry_console.py"

    checks = [
        ("C++ binary",         (BUILD / "sentry_sat_sim").is_file() or
                                (BUILD / "sentry_sat_sim.exe").is_file()),
        ("console venv",       (CONSOLE / ".venv").is_dir()),
        ("ai_training venv",   (AI / "venv").is_dir()),
        ("simulate_acq script",(AI / "simulate_acquisition.py").is_file()),
    ]
    for label, good in checks:
        (ok if good else warn)(label)

    activate = (
        f"source {CONSOLE / '.venv' / 'bin' / 'activate'}"
        if OS != "Windows"
        else f"{CONSOLE / '.venv' / 'Scripts' / 'activate'}"
    )

    print()
    print(_c("1;32", "  ► Launch Mission Control with:"))
    print()
    print(_c("1;37", f"      cd {ROOT}"))
    print(_c("1;37", f"      {activate}"))
    print(_c("1;37", f"      python {sentry_py}"))
    print()
    print(_c("36", "  Or in one line:"))
    print()
    if OS != "Windows":
        print(_c("1;37",
            f'      source {CONSOLE / ".venv" / "bin" / "activate"} && '
            f'python {sentry_py}'
        ))
    else:
        print(_c("1;37",
            f'      {CONSOLE / ".venv" / "Scripts" / "activate"} && '
            f'python {sentry_py}'
        ))
    print()

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(_c("1;34", """
  ╔══════════════════════════════════════════╗
  ║   SENTRY-SAT  ·  Setup & Install        ║
  ╚══════════════════════════════════════════╝"""))

    script_dir = Path(__file__).resolve().parent
    missing = [n for n, _ in FILE_MAP if not (script_dir / n).is_file()]
    if missing:
        err("The following files must be in the SAME folder as setup.py:")
        for m in missing:
            err(f"  {m}")
        err("")
        err(f"setup.py is in:  {script_dir}")
        err("Put ALL downloaded files together in one folder, then run setup.py again.")
        sys.exit(1)

    step_system_packages()
    step_copy_files()
    step_console_venv()
    step_ai_venv()
    step_build_cpp()
    summary()