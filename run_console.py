#!/usr/bin/env python3
"""
SentryGround-Zero Unified Mission Control Console
Professional ESA/NASA-style terminal interface with Rich UI.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description="SentryGround-Zero Mission Control Console",
    )
    
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    parser.add_argument("--dark", action="store_true", default=True, help="Use dark theme")
    
    args = parser.parse_args()
    
    from cli.tui.mission_console import MissionConsole
    
    console = MissionConsole()
    console.run()


if __name__ == "__main__":
    main()
