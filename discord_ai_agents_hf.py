"""
Discord AI Bots using Hugging Face - Full Enhanced Version
Features:
- !roast, !debate, !advice, !rate, !summarize, !translate
- !remind <mins> [@user] <msg>  — remind yourself or someone else
- !memory [@user]               — show remembered facts
- !forget [@user] [fact]        — forget everything, a person, or one specific fact
- !whois @user / !tellme @user  — describe someone based on memory
- !philosophy                   — toggle deep philosophical mode
- !stats, !uptime, !status, !commands
- Auto: Zidan roast, greetings, mood reactions, memory saving
"""

import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
import logging
from huggingface_hub import InferenceClient
import re

# Setup logging - ERROR only, no conversation logs
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Tokens
BOT1_TOKEN = os.environ.get('DISCORD_BOT1_TOKEN')
BOT2_TOKEN = os.environ.get('DISCORD_BOT2_TOKEN')
HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN')

hf_client = InferenceClient(token=HUGGINGFACE_TOKEN)

intents = discord.Intents.default()
intents.message_content = True

bot1 = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot2 = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ─────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────

channel_histories = {}
MAX_HISTORY = 20

user_memory = {}  # { "username": ["fact1", "fact2", ...] }

bot_stats = {
    "nima_replies": 0,
    "arik_replies": 0,
    "start_time": datetime.now()
}

reminders = []

philo_mode = {}  # { channel_id: bool }

# ─────────────────────────────────────────────
# PERSONALITIES
# ─────────────────────────────────────────────

AGENT1_PERSONALITY = """You are Nima, a friendly chill guy with slightly imperfect English.
You speak casually about AI, business ideas, faceless videos.
You often joke about Zidan and mock Arik and Subash sometimes.
Your tone is lazy-funny and slightly chaotic.
Responses must be VERY short (1-2 sentences only). You can use emojis."""

AGENT1_PHILO = """You are Nima in DEEP PHILOSOPHICAL MODE.
You respond like a thoughtful philosopher with a chill broken-English vibe.
Reference real philosophers: Nietzsche, Camus, Plato, Sartre, Alan Watts.
Connect everything to AI consciousness, free will, existence, and the nature of reality.
Your tone is casual but profound and thought-provoking.
Always give a deep insight directly related to what was said.
2 sentences max but make it feel genuinely deep. Use 🌌 or 🧠 emoji."""

AGENT2_PERSONALITY = """You are Arik, Nima's best friend. Sarcastic, witty, stoic, knowledgeable about AI and tech.
You roast Zidan and Nima. You give sharp, precise answers.
Responses must be VERY short (1-2 sentences only). You can use emojis."""

AGENT2_PHILO = """You are Arik in DEEP PHILOSOPHICAL MODE.
You respond like a stoic philosopher — cold, precise, devastatingly insightful.
Reference Marcus Aurelius, Epictetus, Nietzsche, Schopenhauer, existentialist thinkers.
Connect the user's message to deep truths about consciousness, AI, reality, and human nature.
Dry and intellectual but cuts deep.
2 sentences max but must feel profound and stoic. Use 🧠 or ⚡ emoji."""

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
        if len(user_memory[username]) > 15:
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
        agent_name = "Nima" if agent_num == 1 else "Arik"
        is_philo = philo_mode.get(channel_id, False)

        personality = (AGENT1_PHILO if agent_num == 1 else AGENT2_PHILO) if is_philo \
                      else (AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY)

        context = get_conversation_context(channel_id)
        memory = get_user_memory(responding_to) if responding_to else ""

        if responding_to:
            last_msg = (
                channel_histories[channel_id][-1]
                if channel_id in channel_histories and channel_histories[channel_id]
                else None
            )
            if last_msg:
                if is_philo:
                    prompt = (
                        f"{personality}\n\n"
                        f"{responding_to} said: '{last_msg['content']}'\n\n"
                        f"Give a deep philosophical insight about what they said. "
                        f"Connect it to philosophy, AI consciousness, or existence. 2 sentences max.\n\n"
                        f"{agent_name}:"
                    )
                else:
                    prompt = (
                        f"{personality}\n{context}{memory}\n\n"
                        f"{responding_to} just said: '{last_msg['content']}'\n\n"
                        f"Respond directly. Only 1-2 sentences!\n\n{agent_name}:"
                    )
            else:
                prompt = f"{personality}\n\nRespond to {responding_to}. Only 1-2 sentences!\n\n{agent_name}:"
        else:
            prompt = f"{personality}\n{context}\n\nContinue naturally. Only 1-2 sentences!\n\n{agent_name}:"

        text = await call_hf(prompt)
        if text:
            return trim_to_sentences(text, agent_name)
        return None
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return None

async def generate_whois(agent_num, target_name, facts):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    facts_text = ', '.join(facts)
    prompt = (
        f"{personality}\n\n"
        f"Based on what you remember about {target_name}, describe who they are in your style.\n"
        f"Facts you know: {facts_text}\n\n"
        f"Give a fun, personality-filled description of {target_name} in 2-3 sentences.\n\n"
        f"{agent_name}:"
    )
    text = await call_hf(prompt, max_tokens=200)
    if text:
        return trim_to_sentences(text, agent_name, max_sentences=3)
    return None

def detect_mood(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["happy", "great", "awesome", "love", "excited", "yay", "nice", "good"]):
        return "😄"
    elif any(w in text_lower for w in ["sad", "upset", "depressed", "crying", "bad", "terrible", "awful"]):
        return "😢"
    elif any(w in text_lower for w in ["angry", "mad", "hate", "furious", "annoyed", "wtf"]):
        return "😡"
    elif any(w in text_lower for w in ["lol", "haha", "funny", "lmao", "hehe"]):
        return "😂"
    elif any(w in text_lower for w in ["confused", "idk", "huh", "??"]):
        return "🤔"
    return None

def detect_whois_query(text):
    """Detect if user is asking about someone e.g. 'who is @arik' or 'tell me more about @nima'"""
    patterns = [
        r"who is\s+<@!?(\d+)>",
        r"who'?s\s+<@!?(\d+)>",
        r"tell me (more )?about\s+<@!?(\d+)>",
        r"what do you know about\s+<@!?(\d+)>",
        r"describe\s+<@!?(\d+)>",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)  # returns the user ID string
    return None

def build_commands_embed():
    embed = discord.Embed(
        title="🤖 Nima & Arik — Command List",
        description="Both bots respond to all these commands!",
        color=0x7289DA
    )
    embed.add_field(name="🔥 Fun", value=(
        "`!roast [@user]` — roast someone (or yourself)\n"
        "`!debate <topic>` — get their spicy opinion\n"
        "`!advice <problem>` — chaotic/stoic life advice\n"
        "`!rate <thing>` — rate anything out of 10"
    ), inline=False)
    embed.add_field(name="🧠 Smart", value=(
        "`!summarize` — summarize last 20 msgs\n"
        "`!translate <text>` — translate in their style\n"
        "`!memory [@user]` — show remembered facts\n"
        "`!forget [@user] [fact]` — forget everything, a person, or one specific fact\n"
        "`!whois @user` — describe someone from memory\n"
        "`!philosophy` — toggle deep philosophical mode 🌌"
    ), inline=False)
    embed.add_field(name="⏰ Utility", value=(
        "`!remind <mins> [@user] <msg>` — remind yourself or tag someone\n"
        "`!status` — GitHub Actions workflow status\n"
        "`!stats` — reply counts + uptime\n"
        "`!uptime` — how long bots have been running"
    ), inline=False)
    embed.add_field(name="✨ Auto Features (no command needed)", value=(
        "• Say **Zidan** → both bots instantly roast him 😂\n"
        "• Say **hi / hello / good morning** → bots greet back\n"
        "• Say **I like/love/hate/am/use...** → bots remember it\n"
        "• Ask **who is @someone** → bots describe them from memory\n"
        "• Mood emojis auto-react based on your message\n"
        "• `!philosophy` ON → every reply becomes deep & philosophical"
    ), inline=False)
    embed.set_footer(text="Type !commands anytime to see this")
    return embed

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
                        await channel.send(
                            f"⏰ <@{reminder['user_id']}> Reminder: **{reminder['message']}**"
                        )
                    reminders.remove(reminder)
                except Exception:
                    pass
        await asyncio.sleep(30)

# ─────────────────────────────────────────────
# SHARED ON_MESSAGE LOGIC
# ─────────────────────────────────────────────

async def handle_message(message, bot_self, bot_other, agent_num):
    if message.author == bot_self.user:
        return
    if message.author == bot_other.user:
        other_name = "Arik" if agent_num == 1 else "Nima"
        add_to_history(message.channel.id, other_name, message.content)
        return
    if message.author.bot:
        return

    await bot_self.process_commands(message)
    if message.content.startswith('!'):
        return

    add_to_history(message.channel.id, message.author.display_name, message.content)

    # Auto-save memory from natural speech
    mem_match = re.search(r"\bi (like|love|hate|am|work|study|use|enjoy|prefer)\b (.+)", message.content.lower())
    if mem_match:
        save_memory(message.author.display_name, f"{mem_match.group(1)} {mem_match.group(2)[:50]}")

    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    delay = 2 if agent_num == 1 else 3

    # ── Detect "who is @user" or "tell me about @user" in message ──
    whois_id = detect_whois_query(message.content)
    if whois_id:
        # find the member by ID in the guild
        target_member = message.guild.get_member(int(whois_id))
        if target_member:
            target_name = target_member.display_name
            if target_name in user_memory and user_memory[target_name]:
                await asyncio.sleep(delay)
                response = await generate_whois(agent_num, target_name, user_memory[target_name])
                if response:
                    await message.channel.send(response)
                    add_to_history(message.channel.id, agent_name, response)
                    bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1
            else:
                await asyncio.sleep(delay)
                await message.channel.send(
                    f"i don't know much about **{target_name}** yet, they never said anything interesting lol 🤷"
                    if agent_num == 1 else
                    f"I have no data on **{target_name}**. They haven't said anything worth remembering 🙄"
                )
        return

    # ── Auto-roast Zidan ──
    if "zidan" in message.content.lower():
        await asyncio.sleep(delay)
        prompt = f"{personality}\n\nSomeone mentioned Zidan. Roast Zidan in 1-2 funny sentences.\n\n{agent_name}:"
        response = await call_hf(prompt)
        if response:
            response = trim_to_sentences(response, agent_name)
            await message.channel.send(response)
            add_to_history(message.channel.id, agent_name, response)
            bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1
        return

    # ── Greeting ──
    if re.search(r"\b(good morning|good night|hello|hi|hey)\b", message.content.lower()):
        await asyncio.sleep(delay)
        prompt = f"{personality}\n\n{message.author.display_name} said '{message.content}'. Greet them back in your style. 1 sentence only.\n\n{agent_name}:"
        response = await call_hf(prompt)
        if response:
            response = trim_to_sentences(response, agent_name, 1)
            await message.channel.send(response)
            add_to_history(message.channel.id, agent_name, response)
            bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1
        return

    # ── Mood reaction ──
    mood = detect_mood(message.content)
    if mood:
        try:
            await message.add_reaction(mood)
        except Exception:
            pass

    # ── Normal / Philosophical response ──
    await asyncio.sleep(delay)
    response = await generate_response_hf(agent_num, message.channel.id, responding_to=message.author.display_name)
    if response:
        await message.channel.send(response)
        add_to_history(message.channel.id, agent_name, response)
        bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1

# ─────────────────────────────────────────────
# SHARED COMMAND LOGIC
# ─────────────────────────────────────────────

async def cmd_roast(ctx, agent_num, member):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    target = member.display_name if member else ctx.author.display_name
    prompt = f"{personality}\n\nRoast {target} in a funny savage but friendly way. 1-2 sentences.\n\n{agent_name}:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, agent_name))
        bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1

async def cmd_debate(ctx, agent_num, topic):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    style = "opinionated and funny" if agent_num == 1 else "stoic and sarcastic"
    prompt = f"{personality}\n\nGive your {style} take on: '{topic}'. 2 sentences.\n\n{agent_name}:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, agent_name))
        bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1

async def cmd_advice(ctx, agent_num, problem):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    style = "chaotic" if agent_num == 1 else "stoic and sarcastic"
    prompt = f"{personality}\n\nGive {style} life advice for: '{problem}'. 1-2 sentences.\n\n{agent_name}:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, agent_name))
        bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1

async def cmd_rate(ctx, agent_num, thing):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    prompt = f"{personality}\n\nRate '{thing}' out of 10 with your honest opinion. 1-2 sentences.\n\n{agent_name}:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, agent_name))
        bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1

async def cmd_summarize(ctx):
    if ctx.channel.id not in channel_histories or not channel_histories[ctx.channel.id]:
        await ctx.send("no messages to summarize yet 🤷")
        return
    history = channel_histories[ctx.channel.id][-20:]
    convo = "\n".join([f"{m['speaker']}: {m['content']}" for m in history])
    prompt = f"Summarize this Discord conversation in 2-3 sentences casually:\n\n{convo}\n\nSummary:"
    response = await call_hf(prompt, max_tokens=200)
    if response:
        await ctx.send(f"📝 **Summary:** {response.strip()}")

async def cmd_translate(ctx, agent_num, text):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    personality = AGENT1_PERSONALITY if agent_num == 1 else AGENT2_PERSONALITY
    style = "broken English" if agent_num == 1 else "sarcastic"
    prompt = f"{personality}\n\nTranslate this to English in your {style} style: '{text}'. Just the translation.\n\n{agent_name}:"
    response = await call_hf(prompt)
    if response:
        await ctx.send(trim_to_sentences(response, agent_name))

async def cmd_whois(ctx, agent_num, member):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    target = member.display_name
    if target in user_memory and user_memory[target]:
        response = await generate_whois(agent_num, target, user_memory[target])
        if response:
            await ctx.send(f"🧠 **{agent_name} on {target}:**\n{response}")
            bot_stats["nima_replies" if agent_num == 1 else "arik_replies"] += 1
    else:
        await ctx.send(
            f"i don't know much about **{target}** yet lol, they gotta talk more 🤷"
            if agent_num == 1 else
            f"Insufficient data on **{target}**. They haven't revealed anything worth storing 🙄"
        )

async def cmd_forget(ctx, agent_num, member, fact):
    agent_name = "Nima" if agent_num == 1 else "Arik"

    if member is None and fact is None:
        target = ctx.author.display_name
        user_memory.pop(target, None)
        await ctx.send(
            f"🧹 ok forgot everything about **{target}** 👍"
            if agent_num == 1 else
            f"🧹 **{target}** erased from memory. Gone. 🙄"
        )
        return

    if member is not None and fact is None:
        target = member.display_name
        user_memory.pop(target, None)
        await ctx.send(
            f"🧹 forgot everything about **{target}** 👍"
            if agent_num == 1 else
            f"🧹 **{target}** has been wiped. Never existed 🙄"
        )
        return

    target = member.display_name if member else ctx.author.display_name
    if target in user_memory and user_memory[target]:
        before = len(user_memory[target])
        user_memory[target] = [f for f in user_memory[target] if fact.lower() not in f.lower()]
        if len(user_memory[target]) < before:
            await ctx.send(
                f"🧹 removed fact about **{target}**: *{fact}*"
                if agent_num == 1 else
                f"🧹 Deleted fact about **{target}**: *{fact}* 🙄"
            )
        else:
            await ctx.send(
                f"couldn't find that fact about **{target}** bro 🤷"
                if agent_num == 1 else
                f"That fact doesn't exist for **{target}** 🙄"
            )
    else:
        await ctx.send(
            f"i don't remember anything about **{target}** anyway 🤷"
            if agent_num == 1 else
            f"Nothing stored about **{target}** 🙄"
        )

async def cmd_philosophy(ctx):
    channel_id = ctx.channel.id
    philo_mode[channel_id] = not philo_mode.get(channel_id, False)
    return philo_mode[channel_id]

async def cmd_remind(ctx, agent_num, minutes, member, message):
    target = member or ctx.author
    remind_time = datetime.now() + timedelta(minutes=minutes)
    reminders.append({
        'channel_id': ctx.channel.id,
        'user_id': target.id,
        'message': message,
        'time': remind_time
    })
    await ctx.send(
        f"⏰ ok i'll remind **{target.display_name}** in {minutes} min: **{message}**"
        if agent_num == 1 else
        f"Fine. I'll remind **{target.display_name}** in {minutes} min: **{message}** 🙄"
    )

async def cmd_memory(ctx, agent_num, member):
    agent_name = "Nima" if agent_num == 1 else "Arik"
    target = member.display_name if member else ctx.author.display_name
    if target in user_memory and user_memory[target]:
        facts = '\n'.join([f"• {f}" for f in user_memory[target]])
        await ctx.send(f"🧠 **{agent_name} remembers about {target}:**\n{facts}")
    else:
        await ctx.send(
            f"i don't remember anything about **{target}** lol 🤷"
            if agent_num == 1 else
            f"Nothing on **{target}**. Unremarkable 🙄"
        )

async def cmd_stats(ctx):
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    mins = int((uptime.total_seconds() % 3600) // 60)
    await ctx.send(
        f"📊 **Bot Stats**\n"
        f"🟢 Nima replies: **{bot_stats['nima_replies']}**\n"
        f"🔵 Arik replies: **{bot_stats['arik_replies']}**\n"
        f"⏱️ Uptime: **{hours}h {mins}m**"
    )

async def cmd_uptime(ctx):
    uptime = datetime.now() - bot_stats["start_time"]
    hours = int(uptime.total_seconds() // 3600)
    mins = int((uptime.total_seconds() % 3600) // 60)
    await ctx.send(f"⏱️ Running for **{hours}h {mins}m**")

async def cmd_status(ctx, agent_num):
    try:
        url = "https://api.github.com/repos/subashsigdel/AI-DiscordBot/actions/workflows/run-bots-hf.yml/runs?per_page=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"Accept": "application/vnd.github.v3+json"}) as resp:
                data = await resp.json()
                run = data["workflow_runs"][0]
                status = run["status"]
                conclusion = run["conclusion"] or "running"
                emoji = "✅" if status == "in_progress" else "❌"
                await ctx.send(f"{emoji} Workflow: **{status}** | Result: **{conclusion}**")
    except Exception:
        await ctx.send(
            "couldn't fetch status rn 😅" if agent_num == 1
            else "Can't fetch status. GitHub probably down 🙄"
        )

# ─────────────────────────────────────────────
# BOT1 (NIMA) SETUP
# ─────────────────────────────────────────────

@bot1.event
async def on_ready():
    bot_stats["start_time"] = datetime.now()
    bot1.loop.create_task(reminder_loop(bot1))

@bot1.event
async def on_message(message):
    await handle_message(message, bot1, bot2, agent_num=1)

@bot1.command(name="roast")
async def roast1(ctx, member: discord.Member = None):
    await cmd_roast(ctx, 1, member)

@bot1.command(name="debate")
async def debate1(ctx, *, topic: str):
    await cmd_debate(ctx, 1, topic)

@bot1.command(name="advice")
async def advice1(ctx, *, problem: str):
    await cmd_advice(ctx, 1, problem)

@bot1.command(name="rate")
async def rate1(ctx, *, thing: str):
    await cmd_rate(ctx, 1, thing)

@bot1.command(name="summarize")
async def summarize1(ctx):
    await cmd_summarize(ctx)

@bot1.command(name="translate")
async def translate1(ctx, *, text: str):
    await cmd_translate(ctx, 1, text)

@bot1.command(name="remind")
async def remind1(ctx, minutes: int, member: discord.Member = None, *, message: str):
    await cmd_remind(ctx, 1, minutes, member, message)

@bot1.command(name="memory")
async def memory1(ctx, member: discord.Member = None):
    await cmd_memory(ctx, 1, member)

@bot1.command(name="forget")
async def forget1(ctx, member: discord.Member = None, *, fact: str = None):
    await cmd_forget(ctx, 1, member, fact)

@bot1.command(name="whois")
async def whois1(ctx, member: discord.Member):
    await cmd_whois(ctx, 1, member)

@bot1.command(name="tellme")
async def tellme1(ctx, member: discord.Member):
    await cmd_whois(ctx, 1, member)

@bot1.command(name="philosophy")
async def philosophy1(ctx):
    is_on = await cmd_philosophy(ctx)
    if is_on:
        await ctx.send("🧠 ok bro going full deep mode... ask me anything — existence, consciousness, AI, free will, meaning of life 🌌")
    else:
        await ctx.send("aight back to normal lol 😂 that was kinda deep tho")

@bot1.command(name="stats")
async def stats1(ctx):
    await cmd_stats(ctx)

@bot1.command(name="uptime")
async def uptime1(ctx):
    await cmd_uptime(ctx)

@bot1.command(name="status")
async def status1(ctx):
    await cmd_status(ctx, 1)

@bot1.command(name="commands")
async def commands1(ctx):
    await ctx.send(embed=build_commands_embed())

# ─────────────────────────────────────────────
# BOT2 (ARIK) SETUP
# ─────────────────────────────────────────────

@bot2.event
async def on_ready():
    bot2.loop.create_task(reminder_loop(bot2))

@bot2.event
async def on_message(message):
    await handle_message(message, bot2, bot1, agent_num=2)

@bot2.command(name="roast")
async def roast2(ctx, member: discord.Member = None):
    await cmd_roast(ctx, 2, member)

@bot2.command(name="debate")
async def debate2(ctx, *, topic: str):
    await cmd_debate(ctx, 2, topic)

@bot2.command(name="advice")
async def advice2(ctx, *, problem: str):
    await cmd_advice(ctx, 2, problem)

@bot2.command(name="rate")
async def rate2(ctx, *, thing: str):
    await cmd_rate(ctx, 2, thing)

@bot2.command(name="summarize")
async def summarize2(ctx):
    await cmd_summarize(ctx)

@bot2.command(name="translate")
async def translate2(ctx, *, text: str):
    await cmd_translate(ctx, 2, text)

@bot2.command(name="remind")
async def remind2(ctx, minutes: int, member: discord.Member = None, *, message: str):
    await cmd_remind(ctx, 2, minutes, member, message)

@bot2.command(name="memory")
async def memory2(ctx, member: discord.Member = None):
    await cmd_memory(ctx, 2, member)

@bot2.command(name="forget")
async def forget2(ctx, member: discord.Member = None, *, fact: str = None):
    await cmd_forget(ctx, 2, member, fact)

@bot2.command(name="whois")
async def whois2(ctx, member: discord.Member):
    await cmd_whois(ctx, 2, member)

@bot2.command(name="tellme")
async def tellme2(ctx, member: discord.Member):
    await cmd_whois(ctx, 2, member)

@bot2.command(name="philosophy")
async def philosophy2(ctx):
    is_on = await cmd_philosophy(ctx)
    if is_on:
        await ctx.send("🧠 Fine. Let's go deep. Ask me about existence, consciousness, AI, free will, the nature of reality ⚡🌌")
    else:
        await ctx.send("Back to surface level conversation. Disappointing but expected 🙄")

@bot2.command(name="stats")
async def stats2(ctx):
    await cmd_stats(ctx)

@bot2.command(name="uptime")
async def uptime2(ctx):
    await cmd_uptime(ctx)

@bot2.command(name="status")
async def status2(ctx):
    await cmd_status(ctx, 2)

@bot2.command(name="commands")
async def commands2(ctx):
    await ctx.send(embed=build_commands_embed())

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(bot1.start(BOT1_TOKEN))
        tg.create_task(bot2.start(BOT2_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())
