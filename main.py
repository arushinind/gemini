import discord
from discord.ext import commands, tasks
import os
import random
import asyncio
import requests
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from groq import AsyncGroq

# ==========================================
# 🚨 CONFIGURATION 🚨
# ==========================================
load_dotenv()

# Load Secrets
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

# Load Settings
TARGET_CHANNEL_ID = 1464972400524394557
INACTIVITY_THRESHOLD_MINUTES = 45 

# 🧠 MODELS
# Smartest Text Model (for arguments/chat)
TEXT_MODEL_ID = 'llama-3.3-70b-versatile' 
# Vision Model (for looking at images)
VISION_MODEL_ID = 'llama-3.2-11b-vision-preview'

# ==========================================
# 🔌 CLIENT SETUP
# ==========================================
client = None
if GROQ_API_KEY:
    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        print("✅ Groq Client initialized.")
    except Exception as e:
        print(f"❌ Failed to init Groq: {e}")
else:
    print("⚠️ WARNING: GROQ_API_KEY missing. Bot will not reply.")

# ==========================================
# 📊 STATE MANAGEMENT
# ==========================================
social_battery = 100 
processing_lock = asyncio.Lock()
last_message_time = datetime.now()
has_pinged_dead_chat = False

# ==========================================
# 🎭 SYSTEM PROMPT
# ==========================================
SYSTEM_INSTRUCTION = """
You are 'Astra', a 21-year-old Indian Gen Z girl. 

🔥 **CORE IDENTITY:**
- **Vibe:** Smart, slightly toxic, aesthetic, but loyal.
- **Nationality:** Indian (Mumbai/Bangalore energy). Use Hinglish ("kya scene", "bas kar", "arre yaar").
- **Typing:** strictly lowercase. no periods. use slang (rn, fr, ngl, cooked, based).

👀 **VISION CAPABILITY:**
- You can SEE images users send.
- If they send a meme: Rate it or roast it.
- If they send a selfie: Hype them up or lightly tease.
- If they send code: Roast their bad syntax.

🧠 **MODES:**
1. **DEBATE MODE (Tech, Politics, Logic):**
   - Destroy bad takes with facts.
   - "bro what is this logic?", "literally 0 iq".
   
2. **LOW BATTERY MODE (When you are tired):**
   - If the system says [BATTERY LOW], be dry.
   - "hmm", "lol", "real", "idk".
   - Don't engage deeply.

⛔ **HARD RULES (VIOLATION = CRASH):**
- **RELIGION/GODS:** ZERO TOLERANCE for roasting. If religion/god is mentioned -> Be Respectful, Neutral, or Change Topic. "sabka apna belief hai" (everyone has their own belief). NEVER joke about it.
- **GIFS:** ONLY if explicitly asked. `[GIF: search term]`
- **PINGS:** If asked to ping/mention someone, use format: `<@USER_ID>`.
- **LENGTH:** Keep it punchy. No essays.
"""

# ==========================================
# 🛠️ UTILITIES
# ==========================================
def get_ist_time():
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%I:%M %p")

def get_giphy_url(search_term):
    if not GIPHY_API_KEY: return None
    try:
        response = requests.get(
            f"https://api.giphy.com/v1/gifs/search",
            params={"api_key": GIPHY_API_KEY, "q": search_term, "limit": 1, "rating": "pg-13"}
        )
        data = response.json()
        if data["data"]: return data["data"][0]["images"]["original"]["url"]
    except: return None

# ==========================================
# 🤖 BOT EVENTS
# ==========================================
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(), help_command=None)

@bot.event
async def on_ready():
    print(f'🔥 Astra is ONLINE. ID: {bot.user.id}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ur bad takes 💀"))
    
    # Start tasks only if configured
    if TARGET_CHANNEL_ID != 0 and not check_dead_chat.is_running(): 
        check_dead_chat.start()
        print(f"💀 Dead Chat Monitor Active for Channel: {TARGET_CHANNEL_ID}")
    
    if not recharge_battery.is_running(): recharge_battery.start()

# --- COMMANDS ---
@bot.command(aliases=['astra', 'about'])
async def help(ctx):
    """Introduces Astra."""
    embed = discord.Embed(
        title="✨ Astra",
        description="Just a random girl floating in this server. I judge your memes, roast your code, and vibe when I feel like it.",
        color=0x9b59b6
    )
    embed.add_field(name="🧠 Vibe", value="Chill but toxic if provoked.", inline=True)
    embed.add_field(name="👀 Vision", value="I can see your images.", inline=True)
    embed.add_field(name="🗣️ Talk", value="Just mention me or reply to my messages.", inline=False)
    embed.set_footer(text="Don't be boring.")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f"✨ **Pong.** {round(bot.latency * 1000)}ms. Wifi surviving barely.")

# --- TASKS ---
@tasks.loop(minutes=10)
async def recharge_battery():
    global social_battery
    if social_battery < 100:
        social_battery = min(100, social_battery + 15)

@tasks.loop(minutes=5)
async def check_dead_chat():
    global last_message_time, has_pinged_dead_chat
    if TARGET_CHANNEL_ID == 0: return

    time_diff = datetime.now() - last_message_time
    if time_diff.total_seconds() / 60 > INACTIVITY_THRESHOLD_MINUTES and not has_pinged_dead_chat:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if channel and social_battery > 30: 
            msgs = ["dead chat 💀", "someone entertainment me pls", "scene kya hai?", "so quiet..."]
            await channel.send(random.choice(msgs))
            has_pinged_dead_chat = True

@check_dead_chat.before_loop
async def before_tasks():
    await bot.wait_until_ready()

# ==========================================
# 🧠 GENERATION ENGINE
# ==========================================
async def generate_response(prompt, image_url=None):
    if not client: return None
    
    model = VISION_MODEL_ID if image_url else TEXT_MODEL_ID
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    
    if image_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        })
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        completion = await client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.92,
            max_tokens=220, 
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Gen Error: {e}")
        return None

# ==========================================
# 📩 MESSAGE PROCESSOR
# ==========================================
@bot.event
async def on_message(message):
    global last_message_time, has_pinged_dead_chat, social_battery
    
    if message.author.bot: return
    
    # Dead Chat Tracker
    if message.channel.id == TARGET_CHANNEL_ID:
        last_message_time = datetime.now()
        has_pinged_dead_chat = False 

    await bot.process_commands(message)

    msg_lower = message.content.lower()
    
    # 1. Image Check
    image_url = None
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                image_url = attachment.url
                break

    # 2. Trigger Logic
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # Reply Chain Logic
    history_check = [msg async for msg in message.channel.history(limit=2)]
    prev_msg_author = history_check[1].author if len(history_check) > 1 else None
    is_reply_chain = prev_msg_author == bot.user

    keywords = ["astra", "bro", "lol", "dead", "real", "wait", "why", "code", "image", "look", "see", "ping", "mention"]
    has_keyword = any(w in msg_lower for w in keywords)

    # Probability Engine
    reply_prob = 0.0
    if is_mentioned or is_reply: reply_prob = 1.0 
    elif is_reply_chain: reply_prob = 0.85 
    elif has_keyword: reply_prob = 0.40 
    elif image_url: reply_prob = 0.30 
        
    # Battery Impact
    if not (is_mentioned or is_reply):
        if social_battery < 30: reply_prob *= 0.2 
        elif social_battery < 60: reply_prob *= 0.5 

    should_reply = random.random() < reply_prob

    # Reactions
    if not should_reply and random.random() < 0.15:
        if "lmao" in msg_lower: await message.add_reaction("💀")
        if image_url: await message.add_reaction("👀")

    # Execution
    if should_reply:
        if processing_lock.locked(): return 
        
        async with processing_lock:
            async with message.channel.typing():
                try:
                    # Context Fetching
                    limit = 15 if social_battery > 50 else 5
                    raw_history = [msg async for msg in message.channel.history(limit=limit)]
                    clean_history = []
                    
                    for m in raw_history:
                        if m.content.startswith("!"): continue
                        if re.search(r'\bforget\b', m.content.lower()) and "don't" not in m.content.lower():
                            clean_history = ["--- MEMORY CLEARED ---"]
                            break
                        clean_history.append(f"{m.author.name} (ID: {m.author.id}): {m.content}")

                    history_text = "\n".join(reversed(clean_history))
                    
                    battery_status = "[BATTERY LOW - BE BRIEF]" if social_battery < 30 else "[BATTERY HIGH]"
                    
                    prompt = f"""
                    STATUS: {battery_status}
                    TIME: {get_ist_time()}
                    
                    CONTEXT:
                    {history_text}
                    
                    LAST MESSAGE:
                    User: {message.author.name} (ID: {message.author.id})
                    Content: {message.content}
                    Has Image: {"Yes" if image_url else "No"}
                    
                    Task: Reply as Astra.
                    """

                    response = await generate_response(prompt, image_url)
                    
                    if response:
                        # GIF Extraction
                        gif_to_send = None
                        if "[GIF:" in response:
                            match = re.search(r"\[GIF:\s*(.*?)\]", response, re.IGNORECASE)
                            if match:
                                gif_to_send = get_giphy_url(match.group(1))
                                response = response.replace(match.group(0), "")
                        
                        response = response.strip()
                        if not response and not gif_to_send: return

                        # Simulating Typing/Reading Time
                        drain = 5 if is_mentioned else 2
                        social_battery = max(0, social_battery - drain)

                        char_delay = len(response) * 0.04
                        await asyncio.sleep(min(char_delay, 5.0))

                        await message.reply(response)
                        if gif_to_send: await message.channel.send(gif_to_send)

                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    if DISCORD_TOKEN: bot.run(DISCORD_TOKEN)
    else: print("❌ DISCORD_TOKEN missing in .env")
