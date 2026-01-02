"""
Setup script for Steel Parser
"""
import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Requirements installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)

def create_database():
    """Create database structure"""
    print("Creating database...")
    try:
        import database_schema
        database_schema.create_database()
        print("Database created successfully!")
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

def main():
    print("Setting up Steel Parser...")
    install_requirements()
    create_database()
    print("\nSetup complete! Now you can:")
    print("1. Run 'python parser.py' to parse the steel chart")
    print("2. Run 'python app.py' to start the web application")

if __name__ == "__main__":
    main()


