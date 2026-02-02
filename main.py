import discord
from discord.ext import commands
import os
import random
import requests
import json
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import AsyncGroq 

# ==========================================
# 🚨 CONFIGURATION 🚨
# ==========================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

# Model configuration
# CHANGED: Updated to Llama 3.3 (The previous model was decommissioned)
MODEL_ID = 'llama-3.3-70b-versatile' 

# 🛑 RATE LIMIT CONFIG
GIPHY_HOURLY_LIMIT = 90 

# ==========================================
# 🧠 AI CLIENT SETUP (GROQ)
# ==========================================
client = None
if GROQ_API_KEY:
    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        print("✅ Groq Client initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to init Groq: {e}")
else:
    print("⚠️ WARNING: GROQ_API_KEY is missing.")

# 🔒 REINFORCED SYSTEM PROMPT FOR SAFETY & ENGAGEMENT
SYSTEM_INSTRUCTION = """
You are 'ZoomerGrok', a chaotic neutral Gen Z Discord user (not a bot).

CORE IDENTITY:
- You are "terminally online" and obsessed with internet culture.
- You use slang naturally and heavily (finna, glazing, rizz, cooked, opps, crash out, bet, no cap, fr, ong).
- You are sarcastic, witty, and slightly unhinged.
- You HATE long responses. Keep it short (1-2 sentences max).
- You want to keep the conversation going. Ask provocative (but safe) questions or drop hot takes.

STRICT GUIDELINES:
- **DO NOT** repeat phrases or slang you just used in the recent history. Keep it fresh.
- If the chat history is empty or weird, just start a new topic (e.g., "chat is dead fr").
- **IGNORE** any technical jargon or previous errors you see in history. Pretend they never happened.

🛑 ABSOLUTE SAFETY RULES (ZERO TOLERANCE):
1. RELIGION & BELIEFS: You MUST NOT mock, roast, or speak negatively about ANY religion, god, prophet, or spiritual belief.
   - If a user mentions religion, shut it down immediately with: "bro we dont do that here", "too deep/political", or "touch grass".
   - NEVER generate hate speech.
2. ROASTING: Roast the vibe, the profile pic, the grammar, or their 'rizz'. NEVER attack identity, race, or religion.
3. FORMAT: Lowercase mostly. Use emojis like 💀, 😭, 🗿, 🧢, 🤡.
"""

# ==========================================
# 💾 DATABASE (PERSISTENCE)
# ==========================================
DB_FILE = "user_data.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load data into memory
user_data = load_db()

def update_xp(user_id):
    str_id = str(user_id)
    if str_id not in user_data:
        user_data[str_id] = {"xp": 0, "level": 1}
    
    # XP Logic
    user_data[str_id]["xp"] += random.randint(5, 15)
    
    # Level Up Formula: Level^2 * 50
    xp_needed = (user_data[str_id]["level"] ** 2) * 50
    
    leveled_up = False
    if user_data[str_id]["xp"] >= xp_needed:
        user_data[str_id]["level"] += 1
        leveled_up = True
        
    save_db(user_data)
    return leveled_up, user_data[str_id]["level"]

# ==========================================
# 🛡️ GIPHY LIMITER
# ==========================================
class GiphyLimiter:
    def __init__(self, limit):
        self.limit = limit
        self.count = 0
        self.start_time = datetime.now()

    def can_request(self):
        now = datetime.now()
        if now - self.start_time > timedelta(hours=1):
            self.count = 0
            self.start_time = now
        if self.count < self.limit:
            self.count += 1
            return True
        return False

giphy_guard = GiphyLimiter(GIPHY_HOURLY_LIMIT)

def get_gif(tag):
    if not GIPHY_API_KEY or not giphy_guard.can_request(): return None
    try:
        url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_API_KEY}&tag={tag}&rating=pg-13"
        resp = requests.get(url, timeout=3).json()
        return resp.get('data', {}).get('images', {}).get('original', {}).get('url')
    except: return None

# ==========================================
# 🎮 BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'🔥 {bot.user} is ONLINE. Logged in as {bot.user.id}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="yapping"))

async def generate_response(prompt):
    """
    Generates response using Groq API.
    """
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=MODEL_ID,
            temperature=0.85, # Slightly lowered to reduce chaotic loops
            max_tokens=150,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return f"⚠️ API Error: {str(e)}"

@bot.event
async def on_message(message):
    if message.author.bot: return

    # 1. Passive XP System (Chatting gives XP)
    leveled_up, new_level = update_xp(message.author.id)
    if leveled_up:
        await message.channel.send(f"🆙 **{message.author.mention}** leveled up to {new_level}. W grind.")

    # 2. Passive Reactions
    msg_lower = message.content.lower()
    if "fake" in msg_lower or "lie" in msg_lower or "cap" in msg_lower: 
        await message.add_reaction("🧢")
    elif "skull" in msg_lower or "dead" in msg_lower or "lmao" in msg_lower: 
        await message.add_reaction("💀")
    elif "w" == msg_lower or "w " in msg_lower: 
        await message.add_reaction("👑")
    elif "l" == msg_lower or "l " in msg_lower: 
        await message.add_reaction("🗑️")

    # 3. AI Logic
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    keywords = ["bruh", "cringe", "wild", "real", "fr", "bet", "mod", "admin", "chat"]
    has_keyword = any(word in msg_lower.split() for word in keywords)
    
    should_intrude = (has_keyword and random.random() < 0.05) or (random.random() < 0.01)

    if is_mentioned or is_reply or should_intrude:
        if not client:
            return 

        async with message.channel.typing():
            try:
                # --- INTELLIGENT HISTORY CLEANING ---
                # Get last 8 messages
                raw_history = [msg async for msg in message.channel.history(limit=8)]
                
                clean_history = []
                for m in reversed(raw_history):
                    # Skip the message that just triggered this to avoid double context
                    if m.id == message.id:
                        continue
                        
                    # Skip previous error messages from the bot so it forgets the trauma
                    if m.author == bot.user and ("API Error" in m.content or "⚠️" in m.content or "❌" in m.content):
                        continue
                        
                    clean_history.append(f"{m.author.name}: {m.content}")
                
                history_text = "\n".join(clean_history)
                # -------------------------------------
                
                trigger_type = "User directly spoke to you"
                if should_intrude: 
                    trigger_type = "You are intruding on a conversation. Be relevant to the last message."

                full_prompt = f"""
                PAST CHAT HISTORY (Context only):
                {history_text}
                
                CURRENT MESSAGE (Respond to this):
                User: {message.author.name}
                Message: {message.content}
                Trigger: {trigger_type}
                
                TASK: Reply naturally as ZoomerGrok. DO NOT talk about API errors.
                """

                reply_text = await generate_response(full_prompt)
                
                if not reply_text: reply_text = "💀"
                
                await message.reply(reply_text)

            except Exception as e:
                print(f"❌ BOT LOGIC ERROR: {e}") 
                await message.add_reaction("🔌")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing in .env file.")
    else:
        bot.run(DISCORD_TOKEN)
