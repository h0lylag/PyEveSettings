"""
Main entry point for py-eve-settings application
"""

from gui import PyEveSettingsGUI


def main():
    """Main entry point"""
    try:
        app = PyEveSettingsGUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
