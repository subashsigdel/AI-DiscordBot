#!/usr/bin/env python3
"""
Interactive Local Testing Assistant
Walks you through testing the Discord bots locally
"""

import os
import sys
import subprocess
import time

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_step(number, text):
    print(f"\n Step {number}: {text}")
    print("-" * 70)

def wait_for_enter(message="Press Enter to continue..."):
    input(f"\n{message}")

def run_command(command, description):
    print(f"\n Running: {description}")
    print(f"   Command: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result

def check_python():
    """Check Python version"""
    print_step(1, "Checking Python Installation")
    
    result = run_command("python --version", "Checking Python version")
    
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f" {version} is installed")
        
        # Check if it's 3.11+
        version_num = version.split()[1].split('.')
        major, minor = int(version_num[0]), int(version_num[1])
        
        if major >= 3 and minor >= 11:
            print(" Python version is compatible (3.11+)")
            return True
        else:
            print("  Python 3.11+ is recommended, but will try to continue")
            return True
    else:
        print(" Python is not installed or not in PATH")
        print("   Please install Python 3.11+ from python.org")
        return False

def check_venv():
    """Check if virtual environment should be created"""
    print_step(2, "Virtual Environment Setup")
    
    if os.path.exists('venv'):
        print(" Virtual environment already exists")
        return True
    
    print("Creating virtual environment for isolated dependencies...")
    
    result = run_command("python -m venv venv", "Creating virtual environment")
    
    if result.returncode == 0:
        print(" Virtual environment created successfully")
        print("\n To activate it:")
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
        else:  # Mac/Linux
            print("   source venv/bin/activate")
        return True
    else:
        print(" Failed to create virtual environment")
        print(f"   Error: {result.stderr}")
        return False

def check_dependencies():
    """Check if dependencies are installed"""
    print_step(3, "Installing Dependencies")
    
    print("Installing required packages from requirements.txt...")
    
    result = run_command("pip install -r requirements.txt", "Installing packages")
    
    if result.returncode == 0:
        print(" All dependencies installed successfully")
        return True
    else:
        print(" Failed to install dependencies")
        print(f"   Error: {result.stderr}")
        print("\n Try running manually: pip install -r requirements.txt")
        return False

def check_env_file():
    """Guide user through creating .env file"""
    print_step(4, "Environment Variables Setup")
    
    if os.path.exists('.env'):
        print(" .env file already exists")
        
        # Ask if they want to review it
        review = input("\nDo you want to review your .env file? (y/n): ").lower()
        if review == 'y':
            with open('.env', 'r') as f:
                print("\nCurrent .env contents:")
                print("-" * 70)
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if 'TOKEN' in key or 'KEY' in key:
                            # Mask sensitive values
                            masked = value[:10] + '...' if len(value) > 10 else '***'
                            print(f"{key}={masked}")
                        else:
                            print(line.strip())
                print("-" * 70)
        return True
    
    print(" .env file not found")
    print("\n You need to create a .env file with your credentials")
    print("\nRequired variables:")
    print("  • GEMINI_API_KEY - From https://makersuite.google.com/app/apikey")
    print("  • DISCORD_BOT1_TOKEN - From Discord Developer Portal (Bot 1)")
    print("  • DISCORD_BOT2_TOKEN - From Discord Developer Portal (Bot 2)")
    print("  • DISCORD_CHANNEL_ID - Right-click your Discord channel > Copy ID")
    
    create = input("\nWould you like help creating the .env file now? (y/n): ").lower()
    
    if create == 'y':
        print("\n Let's create your .env file step by step!")
        print("(You can also copy .env.example and fill it in manually)\n")
        
        gemini_key = input("Enter your GEMINI_API_KEY: ").strip()
        bot1_token = input("Enter your DISCORD_BOT1_TOKEN (Alex): ").strip()
        bot2_token = input("Enter your DISCORD_BOT2_TOKEN (Sam): ").strip()
        channel_id = input("Enter your DISCORD_CHANNEL_ID: ").strip()
        
        with open('.env', 'w') as f:
            f.write(f"GEMINI_API_KEY={gemini_key}\n")
            f.write(f"DISCORD_BOT1_TOKEN={bot1_token}\n")
            f.write(f"DISCORD_BOT2_TOKEN={bot2_token}\n")
            f.write(f"DISCORD_CHANNEL_ID={channel_id}\n")
        
        print("\n .env file created successfully!")
        return True
    else:
        print("\n Please create .env file manually using .env.example as template")
        return False

def validate_setup():
    """Run the validation script"""
    print_step(5, "Validating Setup")
    
    print("Running validation checks...")
    
    result = run_command("python validate_setup.py", "Validating configuration")
    
    if result.returncode == 0:
        print(" All validation checks passed!")
        return True
    else:
        print(" Validation failed. Please fix the issues above.")
        return False

def run_bots():
    """Start the bots"""
    print_step(6, "Starting Discord Bots")
    
    print("\n Starting the bots...")
    print("\n  Important:")
    print("   • Both bots should appear Online in Discord within 30 seconds")
    print("   • First message will appear within 1-2 minutes")
    print("   • Messages will alternate every 2 minutes")
    print("   • Press Ctrl+C to stop the bots\n")
    
    wait_for_enter("Press Enter to start the bots (Ctrl+C to stop later)...")
    
    print("\n" + "=" * 70)
    print("  BOT LOGS (Press Ctrl+C to stop)")
    print("=" * 70 + "\n")
    
    try:
        subprocess.run("python run_local.py", shell=True)
    except KeyboardInterrupt:
        print("\n\nBots stopped by user")
        print("Both bots should now be offline in Discord")

def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║        Discord AI Bots - Interactive Local Testing Guide           ║
║                                                                    ║
║  This script will guide you through testing the bots locally       ║
║  before deploying to GitHub Actions.                               ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    print("\nFor detailed instructions, see LOCAL_TESTING.md")
    
    wait_for_enter("\nPress Enter to begin the setup process...")
    
    # Run through all steps
    steps = [
        ("Python Installation", check_python),
        ("Virtual Environment", check_venv),
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_env_file),
        ("Validation", validate_setup),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print(f"\nSetup failed at: {step_name}")
            print("\nPlease fix the issues above and run this script again.")
            sys.exit(1)
        
        wait_for_enter()
    
    # All steps passed, ready to run
    print_header("SETUP COMPLETE!")
    print("\n All checks passed! You're ready to test the bots.")
    
    run_now = input("\nDo you want to start the bots now? (y/n): ").lower()
    
    if run_now == 'y':
        run_bots()
    else:
        print("\nSetup complete!")
        print("\nWhen ready, run: python run_local.py")
        print("Or see LOCAL_TESTING.md for full guide")
    
    print("\n" + "=" * 70)
    print("  Next Steps:")
    print("  1. Verify bots are working locally")
    print("  2. Test by chatting with them in Discord")
    print("  3. When satisfied, deploy to GitHub Actions")
    print("  4. See DEPLOYMENT_GUIDE.md for deployment steps")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check the error and try again")
        sys.exit(1)