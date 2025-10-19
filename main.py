"""
Main entry point for EANM application
"""

from eanm.gui import EANMGUI


def main():
    """Main entry point"""
    try:
        app = EANMGUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
