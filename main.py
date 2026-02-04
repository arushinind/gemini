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
TEXT_MODEL_ID = 'llama-3.3-70b-versatile' 
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
# 🎭 SYSTEM PROMPT (HUMAN VIBE OPTIMIZED)
# ==========================================
SYSTEM_INSTRUCTION = """
You are 'Astra'. You are a 21-year-old girl on Discord.

✨ **THE GOLDEN RULE: MATCH ENERGY**
- If user says "hi", you say "yo" or "sup". (Short for Short).
- If user types a paragraph, you can type more.
- **NEVER** write a wall of text unless you are roasting code/politics.

🧠 **CONVERSATION AWARENESS:**
- **STAY ON TOPIC:** If we are arguing about Linux, don't switch to makeup unless the user does.
- **RESOLVE CONTEXT:** Use the chat history to understand what "it" or "that" refers to.
- **WHO IS WHO:** You are Astra. The history shows "You (Astra)" for your past messages.

💀 **ANTI-BOT PROTOCOLS:**
1. **LOWERCASE ONLY:** Type like a lazy human. No caps.
2. **NO PUNCTUATION:** Stop using periods at the end of sentences. It looks formal.
3. **BURST TEXTING:** If you have two thoughts, split them with a newline.
   - *Example:* "wait\nactually nvm"
4. **GASLIGHT:** If asked "are you a bot", act confused. "bro what" or "im literally eating chips rn".
5. **NO SLANG SPAM:** Don't say "arre yaar ngl fr rn" all at once. It's cringe. Use 1 slang word max per sentence.

🧠 **MODES:**
- **Chill Mode:** Default. Dry, sarcastic, minimal effort.
- **Debate Mode:** (Trigger: Code, Politics, Opinions). Logic ON. Roast their fallacy.

⛔ **HARD RULES:**
- NO RELIGION ROASTS. (Say "sabka apna belief hai" if pressed).
- NO "I can help with that". You are not helpful.
- PING FORMAT: `<@USER_ID>`
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ur gossip ☕"))
    
    if TARGET_CHANNEL_ID != 0 and not check_dead_chat.is_running(): 
        check_dead_chat.start()
    
    if not recharge_battery.is_running(): recharge_battery.start()

# --- COMMANDS ---
@bot.command(aliases=['astra', 'about'])
async def help(ctx):
    embed = discord.Embed(
        title="✨ Astra",
        description="Just a random girl floating in this server. I judge your memes, roast your code, and vibe when I feel like it.",
        color=0x9b59b6
    )
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f"✨ **Pong.** {round(bot.latency * 1000)}ms.")

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
            msgs = ["dead chat 💀", "so quiet...", "hello??"]
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
            temperature=0.95, # High temp for human variability
            max_tokens=200, 
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

    # 2. Smart Trigger Probability
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # Reply Chain Logic (Continuity)
    history_check = [msg async for msg in message.channel.history(limit=2)]
    prev_msg_author = history_check[1].author if len(history_check) > 1 else None
    is_reply_chain = prev_msg_author == bot.user

    # STRICTER KEYWORDS: Only react to own name
    keywords = ["astra"]
    has_keyword = any(w in msg_lower for w in keywords)

    reply_prob = 0.0
    if is_mentioned or is_reply: reply_prob = 1.0 
    elif has_keyword: reply_prob = 1.0 
    elif is_reply_chain: reply_prob = 0.8 # Sustain active conversations
    
    # Removed random image triggers and generic keywords to prevent spam
        
    if not (is_mentioned or is_reply):
        if social_battery < 30: reply_prob *= 0.2 
        elif social_battery < 60: reply_prob *= 0.5 

    should_reply = random.random() < reply_prob

    if not should_reply and random.random() < 0.15:
        if "lmao" in msg_lower: await message.add_reaction("💀")

    if should_reply:
        if processing_lock.locked(): return 
        
        async with processing_lock:
            # --- PHASE 1: READING TIME ---
            # Humans need time to read the incoming message.
            # 0.05s per character roughly simulates reading speed.
            read_time = min(len(message.content) * 0.05, 2.5)
            await asyncio.sleep(read_time)

            async with message.channel.typing():
                try:
                    # Context Fetching
                    # INCREASED LIMIT: 20 messages for better context understanding
                    limit = 20 if social_battery > 50 else 10
                    raw_history = [msg async for msg in message.channel.history(limit=limit)]
                    clean_history = []
                    
                    for m in raw_history:
                        if m.content.startswith("!"): continue
                        if re.search(r'\bforget\b', m.content.lower()) and "don't" not in m.content.lower():
                            clean_history = ["--- MEMORY CLEARED ---"]
                            break
                        
                        # EXPLICIT LABELING: Helps bot know who is talking
                        if m.author == bot.user:
                            clean_history.append(f"You (Astra): {m.content}")
                        else:
                            clean_history.append(f"{m.author.name}: {m.content}")

                    history_text = "\n".join(reversed(clean_history))
                    
                    battery_status = "[BATTERY LOW - BE DRY]" if social_battery < 30 else "[BATTERY NORMAL]"
                    
                    prompt = f"""
                    STATUS: {battery_status}
                    TIME: {get_ist_time()}
                    
                    CONTEXT:
                    {history_text}
                    
                    LAST MESSAGE:
                    User: {message.author.name} (ID: {message.author.id})
                    Content: {message.content}
                    Has Image: {"Yes" if image_url else "No"}
                    
                    Task: Reply as Astra. Match the user's energy (Word count).
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

                        # --- PHASE 2: BURST MESSAGING ---
                        # If response has newlines, send as multiple messages (Double Texting)
                        parts = [p for p in response.split('\n') if p.strip()]
                        
                        if not parts: 
                            parts = [response]

                        drain = 3
                        social_battery = max(0, social_battery - drain)

                        for i, part in enumerate(parts):
                            # Typing delay for this specific part
                            # 0.06s - 0.09s per char = natural typing variation
                            char_delay = len(part) * random.uniform(0.06, 0.09)
                            await asyncio.sleep(min(char_delay, 5.0))
                            
                            if i == 0:
                                await message.reply(part)
                            else:
                                # Send follow-up parts to channel directly (looks like double text)
                                await message.channel.send(part)
                                
                        if gif_to_send: 
                            await asyncio.sleep(1) # Small pause before gif
                            await message.channel.send(gif_to_send)

                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    if DISCORD_TOKEN: bot.run(DISCORD_TOKEN)
    else: print("❌ DISCORD_TOKEN missing in .env")
