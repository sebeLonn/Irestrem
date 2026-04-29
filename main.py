"""
Eye Guardian — screen-proximity eye-strain reminder app.

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt
"""

import sys


def main():
    try:
        from ui import IrestremApp
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run:  pip install -r requirements.txt")
        sys.exit(1)

    app = IrestremApp()
    app.run()


if __name__ == '__main__':
    main()
