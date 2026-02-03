#!/usr/bin/env python3
"""
Setup validation script
Checks if all requirements are properly configured
"""

import os
import sys
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists"""
    if not os.path.exists('.env'):
        print(".env file not found")
        print("Copy .env.example to .env and fill in your values")
        return False
    print(".env file found")
    return True

def check_env_variables():
    """Check if all required environment variables are set"""
    load_dotenv()
    
    required_vars = {
        'GEMINI_API_KEY': 'Gemini API key',
        'DISCORD_BOT1_TOKEN': 'Discord Bot 1 token (Alex)',
        'DISCORD_BOT2_TOKEN': 'Discord Bot 2 token (Sam)',
        'DISCORD_CHANNEL_ID': 'Discord channel ID'
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value or value == f'your_{var.lower()}_here':
            print(f"{description} ({var}) not set")
            all_set = False
        else:
            # Show partial value for security
            if 'TOKEN' in var or 'KEY' in var:
                display = value[:10] + '...' if len(value) > 10 else '***'
            else:
                display = value
            print(f" {description} ({var}): {display}")
    
    return all_set

def check_dependencies():
    """Check if required Python packages are installed"""
    packages = ['discord', 'google.generativeai', 'dotenv']
    missing = []
    
    for package in packages:
        try:
            __import__(package.replace('.', '_') if '.' in package else package)
            print(f"{package} installed")
        except ImportError:
            print(f"{package} not installed")
            missing.append(package)
    
    if missing:
        print("\nInstall missing packages with: pip install -r requirements.txt")
        return False
    return True

def main():
    print("Validating Discord AI Bots Setup")
    print("=" * 50)
    
    checks = [
        ("Environment file", check_env_file),
        ("Environment variables", check_env_variables),
        ("Python dependencies", check_dependencies)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("All checks passed! You're ready to run the bots.")
        print("\nRun locally with: python run_local.py")
        print("Or deploy to GitHub Actions (see README.md)")
    else:
        print("Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()