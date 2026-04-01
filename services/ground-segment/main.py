import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.session import MissionControlSession


def main():
    if os.path.exists("simulation_data"):
        import shutil
        try:
            shutil.rmtree("simulation_data")
        except OSError:
            for root_dir, dirs, files in os.walk("simulation_data", topdown=False):
                for name in files:
                    os.remove(os.path.join(root_dir, name))
                for name in dirs:
                    os.rmdir(os.path.join(root_dir, name))
    
    session = MissionControlSession()
    session.run()


if __name__ == "__main__":
    main()
