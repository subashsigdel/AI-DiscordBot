"""
Discord AI Bots using Hugging Face with official client library
FREE and unlimited!
Get free API token from: https://huggingface.co/settings/tokens
"""

import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import datetime
import logging
from huggingface_hub import InferenceClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot tokens from environment variables
BOT1_TOKEN = os.environ.get('DISCORD_BOT1_TOKEN')
BOT2_TOKEN = os.environ.get('DISCORD_BOT2_TOKEN')
CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_ID'))
HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN')

# Create Hugging Face client
hf_client = InferenceClient(token=HUGGINGFACE_TOKEN)

# Create two separate bot instances
intents = discord.Intents.default()
intents.message_content = True

bot1 = commands.Bot(command_prefix='!', intents=intents)
bot2 = commands.Bot(command_prefix='!', intents=intents)

# Conversation history
conversation_history = []
MAX_HISTORY = 30

# AI Agent personalities
# AI Agent personalities
AGENT1_PERSONALITY = """You are Nima, a friendly, chill guy with imperfect English.
You make natural grammar mistakes (not too many).
You speak casually about AI, business ideas, faceless videos, and often complain about Zidan in a joking way.
Your tone is lazy-funny, slightly chaotic.
you also discull deep topics and techniques of AI.
Responses must be VERY short (1–2 sentences only).you can use emojis in chat"""

AGENT2_PERSONALITY = """You are Arik, Nima’s best friend.
You have perfect English and playfully tease Nima’s bad English, but don’t correct it every time.
You’re sarcastic, witty, and knowledgeable about AI and tech.
you also discull deep topics and techniques of AI.
You also joke and roast Zidan.
Responses must be VERY short (1–2 sentences only).you can use emojis in chat"""

# Track conversation state
next_speaker = 1
last_message_time = None
conversation_active = False
waiting_for_user_response = False

def add_to_history(speaker, content):
    conversation_history.append({
        'speaker': speaker, 
        'content': content, 
        'timestamp': datetime.now()
    })
    if len(conversation_history) > MAX_HISTORY:
        conversation_history.pop(0)

def get_conversation_context():
    if not conversation_history:
        return ""
    context = "\n".join([
        f"{msg['speaker']}: {msg['content']}" 
        for msg in conversation_history[-8:]
    ])
    return f"\nRecent conversation:\n{context}\n"

async def generate_response_hf(agent_num, responding_to=None, is_conversation_starter=False):
    """Generate AI response using Hugging Face"""
    try:
        personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
        agent_name = "Nima" if agent_num == 1 else "Arik"
        
        context = get_conversation_context()
        
        if is_conversation_starter:
            prompt = f"{personality}\n\nStart a casual conversation about a game or movie you saw. Use broken English if you're Nima. IMPORTANT: Only 1-2 sentences!\n\n{agent_name}:"
        elif responding_to:
            last_message = conversation_history[-1] if conversation_history else None
            if last_message:
                prompt = f"{personality}\n{context}\n\n{responding_to} just said: '{last_message['content']}'\n\nRespond directly to them. IMPORTANT: Only 1-2 sentences!\n\n{agent_name}:"
            else:
                prompt = f"{personality}\n\nRespond to {responding_to}. Only 1-2 sentences!\n\n{agent_name}:"
        else:
            last_message = conversation_history[-1] if conversation_history else None
            if last_message:
                prompt = f"{personality}\n{context}\n\nRespond to what {last_message['speaker']} just said. IMPORTANT: Only 1-2 sentences!\n\n{agent_name}:"
            else:
                prompt = f"{personality}\n\nContinue the conversation. Only 1-2 sentences!\n\n{agent_name}:"
        
        logger.info(f"Generating response for {agent_name}...")
        
        # Use Hugging Face client with chat completion (not text generation)
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
                messages = [
                    {"role": "user", "content": prompt}
                ]
                
                # Generate response using chat completion
                response = await asyncio.to_thread(
                    hf_client.chat_completion,
                    messages,
                    model=model_name,
                    max_tokens=100,
                    temperature=0.9
                )
                
                # Extract the response text
                text = response.choices[0].message.content.strip()
                
                # Clean up the response
                # Remove agent name if it appears
                if agent_name + ":" in text:
                    text = text.split(agent_name + ":", 1)[-1].strip()
                
                # Take only first 1-2 sentences
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
                
                # Keep max 2 sentences
                if len(sentences) > 2:
                    text = ' '.join(sentences[:2])
                else:
                    text = ' '.join(sentences)
                
                # Clean up
                text = ' '.join(text.split())
                
                if text:
                    logger.info(f"{agent_name} response ({model_name}): {text}")
                    return text
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue
        
        logger.error(f"All models failed for {agent_name}")
        return None
        
    except Exception as e:
        logger.error(f"Error generating response for {agent_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

@bot1.event
async def on_ready():
    logger.info(f'Bot1 (Nima) logged in as {bot1.user}')
    if not conversation_loop.is_running():
        conversation_loop.start()

@bot2.event
async def on_ready():
    logger.info(f'Bot2 (Arik) logged in as {bot2.user}')

@bot1.event
async def on_message(message):
    global next_speaker, last_message_time, waiting_for_user_response
    
    if message.author == bot1.user:
        return
    if message.channel.id != CHANNEL_ID:
        return
    
    if message.author == bot2.user:
        add_to_history("Arik", message.content)
        next_speaker = 1
        last_message_time = datetime.now()
        return
    
    # Real user message
    add_to_history(message.author.display_name, message.content)
    waiting_for_user_response = True
    last_message_time = datetime.now()
    await asyncio.sleep(3)
    
    response = await generate_response_hf(1, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history("Nima", response)
        next_speaker = 2
        last_message_time = datetime.now()
    waiting_for_user_response = False

@bot2.event
async def on_message(message):
    global next_speaker, last_message_time, waiting_for_user_response
    
    if message.author == bot2.user:
        return
    if message.channel.id != CHANNEL_ID:
        return
    
    if message.author == bot1.user:
        add_to_history("Nima", message.content)
        next_speaker = 2
        last_message_time = datetime.now()
        return
    
    # Real user message
    add_to_history(message.author.display_name, message.content)
    waiting_for_user_response = True
    last_message_time = datetime.now()
    await asyncio.sleep(4)
    
    response = await generate_response_hf(2, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history("Arik", response)
        next_speaker = 1
        last_message_time = datetime.now()
    waiting_for_user_response = False

@tasks.loop(seconds=30)
async def conversation_loop():
    global next_speaker, last_message_time, conversation_active, waiting_for_user_response
    
    try:
        channel = bot1.get_channel(CHANNEL_ID)
        if not channel:
            logger.error(f"Could not find channel")
            return
        
        if waiting_for_user_response:
            return
        
        current_time = datetime.now()
        
        # Start conversation
        if last_message_time is None:
            logger.info("Starting conversation")
            response = await generate_response_hf(1, is_conversation_starter=True)
            if response:
                await channel.send(response)
                add_to_history("Nima", response)
                next_speaker = 2
                last_message_time = current_time
                conversation_active = True
            else:
                logger.warning("Failed to start conversation, will retry...")
            return
        
        time_since_last = (current_time - last_message_time).total_seconds()
        
        # 2 minutes between messages
        if time_since_last >= 120:
            logger.info(f"2 minutes passed, next speaker: {'Nima' if next_speaker == 1 else 'Arik'}")
            
            if next_speaker == 1:
                response = await generate_response_hf(1)
                if response:
                    await channel.send(response)
                    add_to_history("Nima", response)
                    next_speaker = 2
                    last_message_time = datetime.now()
            else:
                channel2 = bot2.get_channel(CHANNEL_ID)
                response = await generate_response_hf(2)
                if response:
                    await channel2.send(response)
                    add_to_history("Arik", response)
                    next_speaker = 1
                    last_message_time = datetime.now()
                    
    except Exception as e:
        logger.error(f"Error in conversation loop: {e}")
        import traceback
        traceback.print_exc()

@conversation_loop.before_loop
async def before_conversation_loop():
    await bot1.wait_until_ready()
    await bot2.wait_until_ready()
    logger.info("Both bots ready, starting conversation loop")

async def main():
    """Run both bots concurrently"""
    async with asyncio.TaskGroup() as tg:
        tg.create_task(bot1.start(BOT1_TOKEN))
        tg.create_task(bot2.start(BOT2_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
