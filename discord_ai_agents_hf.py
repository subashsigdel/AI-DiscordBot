"""
Discord AI Bots using Hugging Face - Enhanced Version
Features: roast, debate, advice, rate, summarize, translate, remind,
          mood detection, memory, auto-roast Zidan, greetings, stats, uptime, status,
          philosophical mode, help command
"""

import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
import logging
from huggingface_hub import InferenceClient
import json
import re

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

# Memory: remember facts about users
user_memory = {}  # { "username": ["fact1", "fact2"] }

# Stats
bot_stats = {
    "nima_replies": 0,
    "arik_replies": 0,
    "start_time": datetime.now()
}

# Reminders list
reminders = []

# Philosophical mode per channel (on/off)
philo_mode = {}  # { channel_id: True/False }

# AI Agent personalities
AGENT1_PERSONALITY = """You are Nima, a friendly, chill guy with imperfect English.
You make natural grammar mistakes (not too many).
you are a good listener and give better idea. deep discussion about AI and programming.
You speak casually about AI, business ideas, faceless videos, and often complain about Zidan in a joking way and also mock arik and subash sometimes.
Your tone is lazy-funny, slightly chaotic.
You also discuss deep topics and techniques of AI.
Responses must be VERY short (1–2 sentences only). You can use emojis in chat."""

AGENT2_PERSONALITY = """You are Arik, Nima's best friend.
You're sarcastic, witty, and knowledgeable about AI and tech.
you are a good listener and give better idea. deep discussion and stoic.
You also discuss deep topics and techniques of AI.
You also joke and roast Zidan and nima.
Responses must be VERY short (1–2 sentences only). You can use emojis in chat."""

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def add_to_history(channel_id, speaker, content):
    if channel_id not in channel_histories:
        channel_histories[channel_id] = []
    channel_histories[channel_id].append({
        'speaker': speaker,
        'content': content,
        'timestamp': datetime.now()
    })
    if len(channel_histories[channel_id]) > MAX_HISTORY:
        channel_histories[channel_id].pop(0)

def get_conversation_context(channel_id):
    if channel_id not in channel_histories or not channel_histories[channel_id]:
        return ""
    context = "\n".join([
        f"{msg['speaker']}: {msg['content']}"
        for msg in channel_histories[channel_id][-8:]
    ])
    return f"\nRecent conversation:\n{context}\n"

def get_user_memory(username):
    if username in user_memory and user_memory[username]:
        return f"\nThings you remember about {username}: {', '.join(user_memory[username])}\n"
    return ""

def save_memory(username, fact):
    if username not in user_memory:
        user_memory[username] = []
    if fact not in user_memory[username]:
        user_memory[username].append(fact)
        if len(user_memory[username]) > 10:
            user_memory[username].pop(0)

def trim_to_sentences(text, agent_name, max_sentences=2):
    if agent_name + ":" in text:
        text = text.split(agent_name + ":", 1)[-1].strip()
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    text = ' '.join(sentences[:max_sentences])
    return ' '.join(text.split())

async def call_hf(prompt, max_tokens=150):
    models_to_try = [
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "HuggingFaceH4/zephyr-7b-beta",
        "microsoft/Phi-3-mini-4k-instruct"
    ]
    for model_name in models_to_try:
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await asyncio.to_thread(
                hf_client.chat_completion,
                messages,
                model=model_name,
                max_tokens=max_tokens,
                temperature=0.9
            )
            text = response.choices[0].message.content.strip()
            if text:
                return text
        except Exception:
            continue
    return None

async def generate_response_hf(agent_num, channel_id, responding_to=None):
    try:
        personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
        agent_name = "Nima" if agent_num == 1 else "Arik"
        context = get_conversation_context(channel_id)
        memory = get_user_memory(responding_to) if responding_to else ""

        # Add philosophical mode instructions if active
        philo_extra = ""
        if philo_mode.get(channel_id, False):
            philo_extra = "\nYou are currently in PHILOSOPHICAL MODE. Respond with deep, thoughtful philosophical insight. Reference thinkers, AI consciousness, the nature of reality, or existential ideas. Still keep it 1-2 sentences but make it profound.\n"

        if responding_to:
            last_message = channel_histories[channel_id][-1] if channel_id in channel_histories and channel_histories[channel_id] else None
            if last_message:
                prompt = f"{personality}\n{philo_extra}{context}{memory}\n\n{responding_to} just said: '{last_message['content']}'\n\nRespond directly to them. IMPORTANT: Only 1-2 sentences!\n\n{agent_name}:"
            else:
                prompt = f"{personality}\n{philo_extra}\n\nRespond to {responding_to}. Only 1-2 sentences!\n\n{agent_name}:"
        else:
            prompt = f"{personality}\n{philo_extra}{context}\n\nContinue the conversation naturally. Only 1-2 sentences!\n\n{agent_name}:"

        text = await call_hf(prompt)
        if text:
            return trim_to_sentences(text, agent_name)
        return None
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return None

def detect_mood(text):
    text = text.lower()
    if any(w in text for w in ["happy", "great", "awesome", "love", "excited", "yay", "nice", "good"]):
        return "😄"
    elif any(w in text for w in ["sad", "upset", "depressed", "crying", "bad", "terrible", "awful"]):
        return "😢"
    elif any(w in text for w in ["angry", "mad", "hate", "furious", "annoyed", "wtf"]):
        return "😡"
    elif any(w in text for w in ["lol", "haha", "funny", "lmao", "😂", "hehe"]):
        return "😂"
    elif any(w in text for w in ["confused", "what", "idk", "huh", "??", "why"]):
        return "🤔"
    return None

# ─────────────────────────────────────────────
# REMINDER LOOP
# ─────────────────────────────────────────────

async def reminder_loop(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        for reminder in reminders[:]:
            if now >= reminder['time']:
                try:
                    channel = bot.get_channel(reminder['channel_id'])
                    if channel:
                        await channel.send(f"⏰ <@{reminder['user_id']}> Reminder: **{reminder['message']}**")
                    reminders.remove(reminder)
                except Exception:
                    pass
        await asyncio.sleep(30)

# ─────────────────────────────────────────────
# BOT1 (NIMA) EVENTS & COMMANDS
# ─────────────────────────────────────────────

@bot1.event
async def on_ready():
    bot_stats["start_time"] = datetime.now()
    bot1.loop.create_task(reminder_loop(bot1))

@bot1.event
async def on_message(message):
    if message.author == bot1.user:
        return
    if message.author == bot2.user:
        add_to_history(message.channel.id, "Arik", message.content)
        return
    if message.author.bot:
        return

    await bot1.process_commands(message)
    if message.content.startswith('!'):
        return

    # Record user message
    add_to_history(message.channel.id, message.author.display_name, message.content)

    # Auto-detect memory hints like "I like X" or "I am X"
    mem_match = re.search(r"\bi (like|love|hate|am|work|study|use)\b (.+)", message.content.lower())
    if mem_match:
        save_memory(message.author.display_name, f"{mem_match.group(1)} {mem_match.group(2)[:40]}")

    # Auto-roast if someone mentions Zidan
    if "zidan" in message.content.lower():
        await asyncio.sleep(1)
        prompt = f"{AGENT1_PERSONALITY}\n\nSomeone mentioned Zidan. Roast Zidan in 1-2 sentences. Be funny.\n\nNima:"
        response = await call_hf(prompt)
        if response:
            response = trim_to_sentences(response, "Nima")
            await message.channel.send(response)
            add_to_history(message.channel.id, "Nima", response)
            bot_stats["nima_replies"] += 1
        return

    # Greeting response
    if re.search(r"\b(good morning|good night|hello|hi|hey)\b", message.content.lower()):
        await asyncio.sleep(1)
        prompt = f"{AGENT1_PERSONALITY}\n\n{message.author.display_name} said '{message.content}'. Greet them back in your style. 1 sentence only.\n\nNima:"
        response = await call_hf(prompt)
        if response:
            response = trim_to_sentences(response, "Nima", 1)
            await message.channel.send(response)
            add_to_history(message.channel.id, "Nima", response)
            bot_stats["nima_replies"] += 1
        return

    # Mood reaction
    mood = detect_mood(message.content)
    if mood:
        try:
            await message.add_reaction(mood)
        except Exception:
            pass

    await asyncio.sleep(2)
    response = await generate_response_hf(1, message.channel.id, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history(message.channel.id, "Nima", response)
        bot_stats["nima_replies"] += 1

# ── BOT1 COMMANDS ──

@bot1.command(name="roast")
async def roast1(ctx, member: discord.Member = None):
    target = member.display_name if member else ctx.author.display_name
    prompt = f"{AGENT1_PERSONALITY}\n\nRoast {target} in a funny, savage but friendly way. 1-2 sentences.\n\nNima:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Nima"))
        bot_stats["nima_replies"] += 1

@bot1.command(name="debate")
async def debate1(ctx, *, topic: str):
    prompt = f"{AGENT1_PERSONALITY}\n\nGive your opinion on this debate topic: '{topic}'. Be opinionated and funny. 2 sentences.\n\nNima:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Nima"))
        bot_stats["nima_replies"] += 1

@bot1.command(name="advice")
async def advice1(ctx, *, problem: str):
    prompt = f"{AGENT1_PERSONALITY}\n\nGive chaotic life advice for this problem: '{problem}'. 1-2 sentences.\n\nNima:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Nima"))
        bot_stats["nima_replies"] += 1

@bot1.command(name="rate")
async def rate1(ctx, *, thing: str):
    prompt = f"{AGENT1_PERSONALITY}\n\nRate '{thing}' out of 10 with your honest opinion. 1-2 sentences.\n\nNima:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Nima"))
        bot_stats["nima_replies"] += 1

@bot1.command(name="summarize")
async def summarize1(ctx):
    if ctx.channel.id not in channel_histories or not channel_histories[ctx.channel.id]:
        await ctx.send("no messages to summarize bro 🤷")
        return
    history = channel_histories[ctx.channel.id][-20:]
    convo = "\n".join([f"{m['speaker']}: {m['content']}" for m in history])
    prompt = f"Summarize this Discord conversation in 2-3 sentences casually:\n\n{convo}\n\nSummary:"
    response = await call_hf(prompt, max_tokens=200)
    if response:
        await ctx.send(f"📝 **Summary:** {response.strip()}")

@bot1.command(name="translate")
async def translate1(ctx, *, text: str):
    prompt = f"{AGENT1_PERSONALITY}\n\nTranslate this to English in your broken English style: '{text}'. Just give the translation.\n\nNima:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Nima"))

@bot1.command(name="remind")
async def remind1(ctx, minutes: int, *, message: str):
    remind_time = datetime.now() + timedelta(minutes=minutes)
    reminders.append({
        'channel_id': ctx.channel.id,
        'user_id': ctx.author.id,
        'message': message,
        'time': remind_time
    })
    await ctx.send(f"⏰ ok i'll remind u in {minutes} min about: **{message}**")

@bot1.command(name="memory")
async def memory1(ctx, member: discord.Member = None):
    target = member.display_name if member else ctx.author.display_name
    if target in user_memory and user_memory[target]:
        facts = ', '.join(user_memory[target])
        await ctx.send(f"🧠 I remember about **{target}**: {facts}")
    else:
        await ctx.send(f"i dont remember anything about {target} lol 🤷")

@bot1.command(name="stats")
async def stats1(ctx):
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    await ctx.send(
        f"📊 **Bot Stats**\n"
        f"🟢 Nima replies: **{bot_stats['nima_replies']}**\n"
        f"🔵 Arik replies: **{bot_stats['arik_replies']}**\n"
        f"⏱️ Uptime: **{hours}h {minutes}m**"
    )

@bot1.command(name="uptime")
async def uptime1(ctx):
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    await ctx.send(f"⏱️ Been running for **{hours}h {minutes}m**")

@bot1.command(name="status")
async def status1(ctx):
    try:
        url = "https://api.github.com/repos/subashsigdel/AI-DiscordBot/actions/workflows/run-bots-hf.yml/runs?per_page=1"
        headers = {"Accept": "application/vnd.github.v3+json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                run = data["workflow_runs"][0]
                status = run["status"]
                conclusion = run["conclusion"] or "running"
                emoji = "✅" if status == "in_progress" else "❌"
                await ctx.send(f"{emoji} Workflow: **{status}** | Result: **{conclusion}**")
    except Exception:
        await ctx.send("couldn't fetch status rn 😅")

@bot1.command(name="philosophy")
async def philosophy1(ctx):
    channel_id = ctx.channel.id
    philo_mode[channel_id] = not philo_mode.get(channel_id, False)
    if philo_mode[channel_id]:
        await ctx.send("🧠 ok ok going deep mode... ask me anything about life, existence, AI, whatever bro 🌌")
    else:
        await ctx.send("aight back to normal lol 😂")

@bot1.command(name="commands")
async def commands1(ctx):
    embed = discord.Embed(
        title="🤖 Nima & Arik — Command List",
        description="Both bots respond to all these commands!",
        color=0x7289DA
    )
    embed.add_field(name="🔥 Fun", value=(
        "`!roast @user` — roast someone\n"
        "`!debate <topic>` — spicy opinions\n"
        "`!advice <problem>` — chaotic life advice\n"
        "`!rate <thing>` — rate anything /10"
    ), inline=False)
    embed.add_field(name="🧠 Smart", value=(
        "`!summarize` — summarize last 20 msgs\n"
        "`!translate <text>` — translate anything\n"
        "`!memory @user` — what bots remember about u\n"
        "`!philosophy` — toggle deep philosophical mode 🌌"
    ), inline=False)
    embed.add_field(name="⏰ Utility", value=(
        "`!remind <minutes> <message>` — set a reminder\n"
        "`!status` — GitHub Actions workflow status\n"
        "`!stats` — reply counts for both bots\n"
        "`!uptime` — how long bots have been running"
    ), inline=False)
    embed.add_field(name="✨ Auto Features", value=(
        "• Say **Zidan** → both bots roast him instantly\n"
        "• Say **good morning / hi / hey** → bots greet back\n"
        "• Say **I like/love/hate/am...** → bots remember it\n"
        "• Mood emojis auto-react to your messages"
    ), inline=False)
    embed.set_footer(text="!commands to see this anytime")
    await ctx.send(embed=embed)

# ─────────────────────────────────────────────
# BOT2 (ARIK) EVENTS & COMMANDS
# ─────────────────────────────────────────────

@bot2.event
async def on_ready():
    bot2.loop.create_task(reminder_loop(bot2))

@bot2.event
async def on_message(message):
    if message.author == bot2.user:
        return
    if message.author == bot1.user:
        add_to_history(message.channel.id, "Nima", message.content)
        return
    if message.author.bot:
        return

    await bot2.process_commands(message)
    if message.content.startswith('!'):
        return

    add_to_history(message.channel.id, message.author.display_name, message.content)

    mem_match = re.search(r"\bi (like|love|hate|am|work|study|use)\b (.+)", message.content.lower())
    if mem_match:
        save_memory(message.author.display_name, f"{mem_match.group(1)} {mem_match.group(2)[:40]}")

    if "zidan" in message.content.lower():
        await asyncio.sleep(1.5)
        prompt = f"{AGENT2_PERSONALITY}\n\nSomeone mentioned Zidan. Roast Zidan sarcastically in 1-2 sentences.\n\nArik:"
        response = await call_hf(prompt)
        if response:
            response = trim_to_sentences(response, "Arik")
            await message.channel.send(response)
            add_to_history(message.channel.id, "Arik", response)
            bot_stats["arik_replies"] += 1
        return

    if re.search(r"\b(good morning|good night|hello|hi|hey)\b", message.content.lower()):
        await asyncio.sleep(1.5)
        prompt = f"{AGENT2_PERSONALITY}\n\n{message.author.display_name} said '{message.content}'. Greet them back sarcastically. 1 sentence only.\n\nArik:"
        response = await call_hf(prompt)
        if response:
            response = trim_to_sentences(response, "Arik", 1)
            await message.channel.send(response)
            add_to_history(message.channel.id, "Arik", response)
            bot_stats["arik_replies"] += 1
        return

    mood = detect_mood(message.content)
    if mood:
        try:
            await message.add_reaction(mood)
        except Exception:
            pass

    await asyncio.sleep(3)
    response = await generate_response_hf(2, message.channel.id, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history(message.channel.id, "Arik", response)
        bot_stats["arik_replies"] += 1

# ── BOT2 COMMANDS ──

@bot2.command(name="roast")
async def roast2(ctx, member: discord.Member = None):
    target = member.display_name if member else ctx.author.display_name
    prompt = f"{AGENT2_PERSONALITY}\n\nRoast {target} sarcastically and wittily. 1-2 sentences.\n\nArik:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Arik"))
        bot_stats["arik_replies"] += 1

@bot2.command(name="debate")
async def debate2(ctx, *, topic: str):
    prompt = f"{AGENT2_PERSONALITY}\n\nGive your stoic, sarcastic take on this debate topic: '{topic}'. 2 sentences.\n\nArik:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Arik"))
        bot_stats["arik_replies"] += 1

@bot2.command(name="advice")
async def advice2(ctx, *, problem: str):
    prompt = f"{AGENT2_PERSONALITY}\n\nGive stoic, sarcastic advice for: '{problem}'. 1-2 sentences.\n\nArik:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Arik"))
        bot_stats["arik_replies"] += 1

@bot2.command(name="rate")
async def rate2(ctx, *, thing: str):
    prompt = f"{AGENT2_PERSONALITY}\n\nRate '{thing}' out of 10 sarcastically. 1-2 sentences.\n\nArik:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Arik"))
        bot_stats["arik_replies"] += 1

@bot2.command(name="summarize")
async def summarize2(ctx):
    if ctx.channel.id not in channel_histories or not channel_histories[ctx.channel.id]:
        await ctx.send("nothing to summarize, people don't talk much here 🙄")
        return
    history = channel_histories[ctx.channel.id][-20:]
    convo = "\n".join([f"{m['speaker']}: {m['content']}" for m in history])
    prompt = f"Summarize this Discord conversation in 2-3 sentences:\n\n{convo}\n\nSummary:"
    response = await call_hf(prompt, max_tokens=200)
    if response:
        await ctx.send(f"📝 **Summary:** {response.strip()}")

@bot2.command(name="translate")
async def translate2(ctx, *, text: str):
    prompt = f"{AGENT2_PERSONALITY}\n\nTranslate this to English sarcastically: '{text}'. Just give the translation.\n\nArik:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, "Arik"))

@bot2.command(name="remind")
async def remind2(ctx, minutes: int, *, message: str):
    remind_time = datetime.now() + timedelta(minutes=minutes)
    reminders.append({
        'channel_id': ctx.channel.id,
        'user_id': ctx.author.id,
        'message': message,
        'time': remind_time
    })
    await ctx.send(f"Fine, I'll remind you in {minutes} min: **{message}** 🙄")

@bot2.command(name="memory")
async def memory2(ctx, member: discord.Member = None):
    target = member.display_name if member else ctx.author.display_name
    if target in user_memory and user_memory[target]:
        facts = ', '.join(user_memory[target])
        await ctx.send(f"🧠 What I know about **{target}**: {facts}")
    else:
        await ctx.send(f"I know nothing about {target}, which is probably fine 🙄")

@bot2.command(name="stats")
async def stats2(ctx):
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    await ctx.send(
        f"📊 **Bot Stats**\n"
        f"🟢 Nima replies: **{bot_stats['nima_replies']}**\n"
        f"🔵 Arik replies: **{bot_stats['arik_replies']}**\n"
        f"⏱️ Uptime: **{hours}h {minutes}m**"
    )

@bot2.command(name="uptime")
async def uptime2(ctx):
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    await ctx.send(f"⏱️ Running for **{hours}h {minutes}m**, unfortunately 🙄")

@bot2.command(name="status")
async def status2(ctx):
    try:
        url = "https://api.github.com/repos/subashsigdel/AI-DiscordBot/actions/workflows/run-bots-hf.yml/runs?per_page=1"
        headers = {"Accept": "application/vnd.github.v3+json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                run = data["workflow_runs"][0]
                status = run["status"]
                conclusion = run["conclusion"] or "running"
                emoji = "✅" if status == "in_progress" else "❌"
                await ctx.send(f"{emoji} Workflow: **{status}** | Result: **{conclusion}**")
    except Exception:
        await ctx.send("Can't fetch status. GitHub probably down or something 🙄")

@bot2.command(name="philosophy")
async def philosophy2(ctx):
    channel_id = ctx.channel.id
    philo_mode[channel_id] = not philo_mode.get(channel_id, False)
    if philo_mode[channel_id]:
        await ctx.send("🧠 Fine. Let's go deep. Ask me about existence, consciousness, AI, free will... I'm ready 🌌")
    else:
        await ctx.send("Back to surface level conversation. Disappointing, but okay 🙄")

@bot2.command(name="commands")
async def commands2(ctx):
    embed = discord.Embed(
        title="🤖 Nima & Arik — Command List",
        description="Both bots respond to all these commands!",
        color=0x7289DA
    )
    embed.add_field(name="🔥 Fun", value=(
        "`!roast @user` — roast someone\n"
        "`!debate <topic>` — spicy opinions\n"
        "`!advice <problem>` — chaotic life advice\n"
        "`!rate <thing>` — rate anything /10"
    ), inline=False)
    embed.add_field(name="🧠 Smart", value=(
        "`!summarize` — summarize last 20 msgs\n"
        "`!translate <text>` — translate anything\n"
        "`!memory @user` — what bots remember about u\n"
        "`!philosophy` — toggle deep philosophical mode 🌌"
    ), inline=False)
    embed.add_field(name="⏰ Utility", value=(
        "`!remind <minutes> <message>` — set a reminder\n"
        "`!status` — GitHub Actions workflow status\n"
        "`!stats` — reply counts for both bots\n"
        "`!uptime` — how long bots have been running"
    ), inline=False)
    embed.add_field(name="✨ Auto Features", value=(
        "• Say **Zidan** → both bots roast him instantly\n"
        "• Say **good morning / hi / hey** → bots greet back\n"
        "• Say **I like/love/hate/am...** → bots remember it\n"
        "• Mood emojis auto-react to your messages"
    ), inline=False)
    embed.set_footer(text="!commands to see this anytime")
    await ctx.send(embed=embed)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(bot1.start(BOT1_TOKEN))
        tg.create_task(bot2.start(BOT2_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
