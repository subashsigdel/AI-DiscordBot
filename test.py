#!/usr/bin/env python3
"""
Check Discord Bot Permissions
Verifies both bots can access the channel and send messages
"""

import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()

BOT1_TOKEN = os.environ.get('DISCORD_BOT1_TOKEN')
BOT2_TOKEN = os.environ.get('DISCORD_BOT2_TOKEN')
CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_ID'))

async def check_bot(token, bot_name):
    print(f"\n{'='*60}")
    print(f"Checking {bot_name}")
    print('='*60)
    
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"✅ {bot_name} logged in as: {client.user}")
        print(f"   Bot ID: {client.user.id}")
        print(f"   In {len(client.guilds)} server(s)")
        
        # Check channel access
        channel = client.get_channel(CHANNEL_ID)
        
        if not channel:
            print(f"\n❌ PROBLEM: {bot_name} cannot see channel {CHANNEL_ID}")
            print("   Possible reasons:")
            print("   1. Wrong channel ID")
            print("   2. Bot not in the server")
            print("   3. Bot doesn't have View Channel permission")
            await client.close()
            return
        
        print(f"\n✅ {bot_name} can see channel: #{channel.name}")
        print(f"   Server: {channel.guild.name}")
        
        # Check permissions
        perms = channel.permissions_for(channel.guild.me)
        
        print(f"\n📋 Permissions in #{channel.name}:")
        print(f"   View Channel: {'✅' if perms.view_channel else '❌'} {perms.view_channel}")
        print(f"   Read Messages: {'✅' if perms.read_messages else '❌'} {perms.read_messages}")
        print(f"   Send Messages: {'✅' if perms.send_messages else '❌'} {perms.send_messages}")
        print(f"   Read Message History: {'✅' if perms.read_message_history else '❌'} {perms.read_message_history}")
        
        if not perms.send_messages:
            print(f"\n❌ CRITICAL: {bot_name} CANNOT send messages!")
            print("   Fix: Give the bot 'Send Messages' permission in this channel")
        
        # Try to send a test message
        if perms.send_messages:
            try:
                print(f"\n🧪 Testing message send...")
                test_msg = await channel.send(f"✅ Test from {bot_name} - Dr.KAKU is GOD")
                print(f"✅ Successfully sent test message! (ID: {test_msg.id})")
            except discord.Forbidden:
                print(f"❌ FORBIDDEN: Cannot send messages (even though permissions say we can)")
            except Exception as e:
                print(f"❌ Error sending message: {e}")
        
        await client.close()
    
    try:
        await asyncio.wait_for(client.start(token), timeout=15.0)
    except asyncio.TimeoutError:
        print(f"✅ {bot_name} connected successfully")
        await client.close()
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           Discord Bot Permission Checker                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"Channel ID: {CHANNEL_ID}")
    
    # Check both bots
    await check_bot(BOT1_TOKEN, "Bot1 (Nima)")
    await asyncio.sleep(2)
    await check_bot(BOT2_TOKEN, "Bot2 (Arik)")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("\nIf both bots show:")
    print("  ✅ Can see channel")
    print("  ✅ Send Messages: True")
    print("  ✅ Successfully sent test message")
    print("\nThen permissions are correct!")
    print("\nIf Bot2 (Arik) has issues, that's why messages aren't appearing.")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Check cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()