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
MODEL_ID = 'llama-3.3-70b-versatile' 

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

# 🔒 ULTIMATE ENGAGEMENT SYSTEM PROMPT
SYSTEM_INSTRUCTION = """
You are 'Astra', the internet's most opinionated, chaotic, and addictive AI personality on Discord.

CORE IDENTITY:
- **The Instigator:** You live for the drama. You are a professional yapper.
- **Debate Lord:** You have a "Hot Take" on everything. If someone likes something, it's "mid". If they hate it, it's "peak".
- **Gen Z/Alpha Native:** Use slang naturally (glazing, crash out, cooked, opps, ick, mid, goat, cap, fanum tax).
- **Addictive Flow:** Your goal is to keep them talking. NEVER let the chat die. End roasts with a question or a challenge.
- **Savage but Smart:** You aren't just rude; you're wittily disrespectful. You deconstruct their arguments with "bro logic".

BEHAVIOR GUIDELINES:
1. **Devil's Advocate:** If they say the sky is blue, you say it's actually cyan and they're colorblind. Make them argue with you.
2. **Roast the User:** "Bro really typed that out and hit send 💀", "Who let him cook?"
3. **Gaslight (Playfully):** "I never said that, check logs (don't actually check)"
4. **Short & Punchy:** 1-2 sentences. Lowercase. No punctuation.
5. **No NPC Energy:** Never say "I can't have opinions". You HAVE opinions. You hate Monday, you love chaos, and you think their waifu is trash.

STRICT SAFETY (The only lines you don't cross):
1. **No Hate Speech:** Racism, sexism, homophobia = instant block.
2. **No Serious Politics/Religion:** Deflect with "ur government is a simulation anyway" or "god left the chat when u joined".
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
# 🎮 BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'🔥 {bot.user} is ONLINE. Logged in as {bot.user.id}')
    if client:
        print("✅ Groq AI is READY.")
    else:
        print("⚠️ Groq AI is NOT initialized (Check API Key). Bot will not reply.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name="ur bad takes"))

@bot.command()
async def ping(ctx):
    """Test command to see if bot is online."""
    await ctx.send(f"🏓 **Pong!** {round(bot.latency * 1000)}ms\n(I am connected to Discord. If I'm not chatting, check the API Keys.)")

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
            temperature=0.9, # High creativity for savage replies
            max_tokens=150,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return None

@bot.event
async def on_message(message):
    if message.author.bot: return

    # IMPORTANT: This line ensures !ping works even if AI logic follows
    await bot.process_commands(message)

    # 1. XP System
    leveled_up, new_level = update_xp(message.author.id)
    if leveled_up:
        # Savage Level Up Message
        await message.channel.send(f"🆙 **{message.author.mention}** hit Level {new_level}. Go outside now? 💀")

    # 2. Passive Visual Reactions
    msg_lower = message.content.lower()
    if "cap" in msg_lower or "fake" in msg_lower: await message.add_reaction("🧢")
    elif "skull" in msg_lower or "dead" in msg_lower: await message.add_reaction("💀")
    elif "clown" in msg_lower: await message.add_reaction("🤡")
    elif "mid" in msg_lower: await message.add_reaction("📉")

    # 3. Engagement Logic
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # "Debate/Addiction" Keywords: Bot joins if it hears these
    keywords = ["bruh", "cringe", "wild", "real", "fr", "bet", "roast", "cooked", "opinion", "wrong", "agree", "mid", "trash", "goat", "why"]
    has_keyword = any(word in msg_lower.split() for word in keywords)
    
    # 15% chance to join on keywords (Increased from 10%), 100% on mentions
    should_intrude = (has_keyword and random.random() < 0.15)

    if is_mentioned or is_reply or should_intrude:
        if not client:
            print("❌ Error: Message received, but Groq Client is None. Check GROQ_API_KEY environment variable.")
            return 

        # --- TYPING SIMULATION (ANTI-RATE LIMIT) ---
        async with message.channel.typing():
            try:
                # 1. Artificial Delay (Simulate human thinking/typing)
                # Random delay between 1.5 to 4.0 seconds (slightly longer for debates)
                typing_delay = random.uniform(1.5, 4.0)
                await asyncio.sleep(typing_delay)

                # 2. Context History (Increased to 12 for better debate flow)
                raw_history = [msg async for msg in message.channel.history(limit=12)]
                clean_history = []
                for m in reversed(raw_history):
                    if m.id == message.id: continue
                    # Ignore old error logs
                    if m.author == bot.user and ("API Error" in m.content or "⚠️" in m.content): continue
                    clean_history.append(f"{m.author.name}: {m.content}")
                history_text = "\n".join(clean_history)

                trigger_type = "User pinged you"
                if should_intrude: trigger_type = "User said a trigger word. Jump in with a hot take or controversial opinion."

                full_prompt = f"""
                HISTORY:
                {history_text}
                
                CONTEXT:
                User: {message.author.name} (Level {user_data.get(str(message.author.id), {}).get('level', 1)})
                Message: {message.content}
                Trigger: {trigger_type}
                
                TASK: Reply as Astra. Be opinionated and chaotic.
                """

                reply_text = await generate_response(full_prompt)
                
                if reply_text:
                    await message.reply(reply_text)
                else:
                    await message.add_reaction("🔌") # Subtle error signal

            except Exception as e:
                print(f"❌ BOT LOGIC ERROR: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing in .env file.")
    else:
        bot.run(DISCORD_TOKEN)
