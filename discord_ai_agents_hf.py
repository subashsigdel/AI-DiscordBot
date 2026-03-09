"""
Discord AI Bots using Hugging Face - User Response Mode
Bots only talk when users message them (no auto-conversation)
Works in ANY channel the bots can see!
"""

import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime
import logging
from huggingface_hub import InferenceClient

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Bot tokens from environment variables
BOT1_TOKEN = os.environ.get('DISCORD_BOT1_TOKEN')
BOT2_TOKEN = os.environ.get('DISCORD_BOT2_TOKEN')
HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN')

# Create Hugging Face client
hf_client = InferenceClient(token=HUGGINGFACE_TOKEN)

# Create two separate bot instances
intents = discord.Intents.default()
intents.message_content = True

bot1 = commands.Bot(command_prefix='!', intents=intents)
bot2 = commands.Bot(command_prefix='!', intents=intents)

# Store conversation history per channel
channel_histories = {}
MAX_HISTORY = 20

# AI Agent personalities
AGENT1_PERSONALITY = """You are Nima, a friendly, chill guy with imperfect English.
You make natural grammar mistakes (not too many).
you are a good listener and give better idea. deep discuaion about AI and programming.
You speak casually about AI, business ideas, faceless videos, and often complain about Zidan in a joking way and also mock arik and subash sometimes.
Your tone is lazy-funny, slightly chaotic.
You also discuss deep topics and techniques of AI.
Responses must be VERY short (1–2 sentences only). You can use emojis in chat."""

AGENT2_PERSONALITY = """You are Arik, Nima's best friend.
You're sarcastic, witty, and knowledgeable about AI and tech.
you are a good listener and give better idea. deep discuaion and stoic.
You also discuss deep topics and techniques of AI.
You also joke and roast Zidan and nima.
Responses must be VERY short (1–2 sentences only). You can use emojis in chat."""

def add_to_history(channel_id, speaker, content):
    """Add message to channel-specific history"""
    if channel_id not in channel_histories:
        channel_histories[channel_id] = []
    
    channel_histories[channel_id].append({
        'speaker': speaker,
        'content': content,
        'timestamp': datetime.now()
    })
    
    # Keep only recent history
    if len(channel_histories[channel_id]) > MAX_HISTORY:
        channel_histories[channel_id].pop(0)

def get_conversation_context(channel_id):
    """Get recent conversation history for a channel"""
    if channel_id not in channel_histories or not channel_histories[channel_id]:
        return ""
    
    context = "\n".join([
        f"{msg['speaker']}: {msg['content']}"
        for msg in channel_histories[channel_id][-8:]
    ])
    return f"\nRecent conversation:\n{context}\n"

async def generate_response_hf(agent_num, channel_id, responding_to=None):
    """Generate AI response using Hugging Face"""
    try:
        personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
        agent_name = "Nima" if agent_num == 1 else "Arik"
        
        context = get_conversation_context(channel_id)
        
        if responding_to:
            last_message = channel_histories[channel_id][-1] if channel_id in channel_histories and channel_histories[channel_id] else None
            if last_message:
                prompt = f"{personality}\n{context}\n\n{responding_to} just said: '{last_message['content']}'\n\nRespond directly to them. IMPORTANT: Only 1-2 sentences!\n\n{agent_name}:"
            else:
                prompt = f"{personality}\n\nRespond to {responding_to}. Only 1-2 sentences!\n\n{agent_name}:"
        else:
            prompt = f"{personality}\n{context}\n\nContinue the conversation naturally. Only 1-2 sentences!\n\n{agent_name}:"
        
        logger.info(f"Generating response for {agent_name}...")
        
        # Use Hugging Face client with chat completion
        models_to_try = [
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "HuggingFaceH4/zephyr-7b-beta",
            "microsoft/Phi-3-mini-4k-instruct"
        ]
        
        for model_name in models_to_try:
            try:
                logger.info(f"Trying model: {model_name}")
                
                # Create messages in chat format
                messages = [{"role": "user", "content": prompt}]
                
                # Generate response
                response = await asyncio.to_thread(
                    hf_client.chat_completion,
                    messages,
                    model=model_name,
                    max_tokens=100,
                    temperature=0.9
                )
                
                # Extract the response text
                text = response.choices[0].message.content.strip()
                
                # Clean up
                if agent_name + ":" in text:
                    text = text.split(agent_name + ":", 1)[-1].strip()
                
                # Limit to 2 sentences
                sentences = []
                for sep in ['. ', '! ', '? ']:
                    if sep in text:
                        parts = text.split(sep)
                        sentences.extend([p + sep.strip() for p in parts[:-1] if p])
                        if parts[-1]:
                            sentences.append(parts[-1])
                        break
                else:
                    sentences = [text]
                
                if len(sentences) > 2:
                    text = ' '.join(sentences[:2])
                else:
                    text = ' '.join(sentences)
                
                text = ' '.join(text.split())
                
                if text:
                    logger.info(f"{agent_name} response: {text}")
                    return text
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue
        
        logger.error(f"All models failed for {agent_name}")
        return None
        
    except Exception as e:
        logger.error(f"Error generating response for {agent_name}: {e}")
        return None

@bot1.event
async def on_ready():
    logger.info(f'Bot1 (Nima) logged in as {bot1.user}')
    logger.info(f'Ready to respond in {len(bot1.guilds)} server(s)')

@bot2.event
async def on_ready():
    logger.info(f'Bot2 (Arik) logged in as {bot2.user}')
    logger.info(f'Ready to respond in {len(bot2.guilds)} server(s)')

@bot1.event
async def on_message(message):
    # Ignore own messages
    if message.author == bot1.user:
        return
    
    # Ignore bot2's messages (let bot2 handle them)
    if message.author == bot2.user:
        # Record Arik's message in history
        add_to_history(message.channel.id, "Arik", message.content)
        return
    
    # Only respond to real users (not other bots)
    if message.author.bot:
        return
    
    # Record user message
    add_to_history(message.channel.id, message.author.display_name, message.content)
    
    # Small delay to seem natural
    await asyncio.sleep(2)
    
    # Generate and send response
    response = await generate_response_hf(1, message.channel.id, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history(message.channel.id, "Nima", response)
        logger.info(f"Nima responded in #{message.channel.name}")

@bot2.event
async def on_message(message):
    # Ignore own messages
    if message.author == bot2.user:
        return
    
    # Ignore bot1's messages (let bot1 handle them)
    if message.author == bot1.user:
        # Record Nima's message in history
        add_to_history(message.channel.id, "Nima", message.content)
        return
    
    # Only respond to real users (not other bots)
    if message.author.bot:
        return
    
    # Record user message
    add_to_history(message.channel.id, message.author.display_name, message.content)
    
    # Small delay (slightly longer than bot1 to not overlap)
    await asyncio.sleep(3)
    
    # Generate and send response
    response = await generate_response_hf(2, message.channel.id, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history(message.channel.id, "Arik", response)
        logger.info(f"Arik responded in #{message.channel.name}")

async def main():
    """Run both bots concurrently"""
    async with asyncio.TaskGroup() as tg:
        tg.create_task(bot1.start(BOT1_TOKEN))
        tg.create_task(bot2.start(BOT2_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
