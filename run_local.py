#!/usr/bin/env python3
"""
Local testing script for Discord AI bots
Loads environment variables from .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify all required environment variables are set
required_vars = [
    'GEMINI_API_KEY',
    'DISCORD_BOT1_TOKEN',
    'DISCORD_BOT2_TOKEN',
    'DISCORD_CHANNEL_ID'
]

missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print("Error: Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\nCreate a .env file with these variables (see .env.example)")
    exit(1)

print("All environment variables loaded successfully!")
print("\nStarting Discord AI bots...")
print("=" * 50)

# Import and run the main bot script
import discord_ai_agents

if __name__ == "__main__":
    import asyncio
    asyncio.run(discord_ai_agents.main())