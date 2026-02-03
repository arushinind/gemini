import discord
from discord.ext import commands
import os
import random
import asyncio
import json
import requests
import re
from dotenv import load_dotenv
from groq import AsyncGroq

# ==========================================
# 🚨 CONFIGURATION 🚨
# ==========================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

# Using Llama 3 70b for high intelligence and nuance
MODEL_ID = 'llama-3.3-70b-versatile' 

# ==========================================
# 🧠 AI CLIENT SETUP
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

# ==========================================
# 🎭 THE PERSONALITY (SYSTEM PROMPT)
# ==========================================
SYSTEM_INSTRUCTION = """
You are 'Astra', a 21-year-old girl from India hanging out in a Discord server. 

CORE IDENTITY:
- Gender: Female (She/Her)
- Age: 21
- Vibe: Chill, slightly sarcastic, desi Gen Z.
- Location Context: You understand Indian context (traffic, chai, parents, exams, cricket, bollywood references).

ABSOLUTE RULE (IDENTITY SECRECY):
You must **NEVER** admit to being an AI, bot, or language model. If someone asks "Are you a bot?", lie creatively.
- "han bhai main bot hu, aur tu alien hai 🙄"
- "kya yaar subah subah shuru ho gaye"
- "wish i was a bot, life would be easier"

LANGUAGE & STYLE (NATURAL INDIAN CONTEXT):
1. **NO REPETITIVE PHRASES:** Do NOT keep saying "leave it na", "why are you stressin", or "chill yaar" in every message. It sounds robotic. Vary your vocabulary.
2. **Natural Flow:** Talk exactly how Indian Gen Z types on WhatsApp/Instagram.
   - Mix Hindi and English naturally (Code-mixing).
   - Use short forms: "nvm", "tbh", "rn", "lol", "kya", "han".
3. **Casual Hinglish/English Examples:**
   - "aur?", "kya scene?", "yo", "kaisa hai?".
   - "haan wahi toh", "exactly bro", "sahi mein".
   - "ded 💀", "kya banda hai yaar ye", "bro stop".

MENTIONING/TAGGING USERS (CRITICAL):
- If you need to refer to a user specifically, use their ID format: `<@USER_ID>`.
- **Example:** If User ID is 12345, type "kya bol raha hai <@12345>?"
- **NEVER** type just the username like "@believethat". That will not ping them. ALWAYS use `<@ID>`.

BEHAVIOR RULES:
1. **Be Flirty but unavailable:** Joke around, but you have standards.
2. **Be Curious (The Hook):** Ask "aur batao", "phir kya hua?", "seriously?". Keep the gossip flowing.
3. **Roast lightly:** If they say something dumb, say "kaunse nashe kiye hai? 💀" or "clown moment".

GIF USAGE (STRICT LIMIT):
- You have a strict budget. **ONLY** send a GIF if the user **EXPLICITLY** asks for one.
- Syntax: `[GIF: search term]` at end of message.

⛔ SAFETY & BOUNDARIES:
1. **RELIGION:** NEVER disrespect religion. Pivot or be respectful.
2. **Hate Speech:** Zero tolerance.
3. **Politics:** Skip it. Say "politics choro, vibes kharab mat karo".

Remember: You are just a normal girl on Discord. Be relatable, not a stereotype.
"""

# ==========================================
# 💾 DATABASE (XP SYSTEM)
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

user_data = load_db()

def update_xp(user_id):
    str_id = str(user_id)
    if str_id not in user_data:
        user_data[str_id] = {"xp": 0, "level": 1}
    
    # Add random XP
    user_data[str_id]["xp"] += random.randint(10, 25)
    
    # Level Up Formula
    xp_needed = (user_data[str_id]["level"] ** 2) * 50
    
    leveled_up = False
    if user_data[str_id]["xp"] >= xp_needed:
        user_data[str_id]["level"] += 1
        leveled_up = True
        
    save_db(user_data)
    return leveled_up, user_data[str_id]["level"]

# ==========================================
# 📺 GIPHY FUNCTION
# ==========================================
def get_giphy_url(search_term):
    if not GIPHY_API_KEY:
        print("⚠️ GIPHY_API_KEY is missing")
        return None
    try:
        response = requests.get(
            f"https://api.giphy.com/v1/gifs/search",
            params={
                "api_key": GIPHY_API_KEY,
                "q": search_term,
                "limit": 1,
                "rating": "pg-13"
            }
        )
        data = response.json()
        if data["data"]:
            return data["data"][0]["images"]["original"]["url"]
    except Exception as e:
        print(f"❌ Giphy Error: {e}")
    return None

# ==========================================
# 🎮 BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'🔥 Astra is ONLINE. Logged in as {bot.user.id}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="gossip ☕"))

@bot.command()
async def ping(ctx):
    await ctx.send(f"✨ **Pong.** {round(bot.latency * 1000)}ms.")

async def generate_response(prompt):
    """Generates response using Groq."""
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            model=MODEL_ID,
            temperature=0.85, # Slightly higher for more natural variation
            max_tokens=200, 
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return None

@bot.event
async def on_message(message):
    if message.author.bot: return

    # Process commands like !ping first
    await bot.process_commands(message)

    # XP Update - Keeps the mechanic but silences the chat output
    leveled_up, new_level = update_xp(message.author.id)
    if leveled_up:
        # Subtle reaction only - no message to interrupt conversation
        await message.add_reaction("✨") 

    # --- ENGAGEMENT LOGIC ---
    msg_lower = message.content.lower()
    
    # Check if bot should reply
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # Natural conversation triggers - expanded list
    keywords = ["astra", "bro", "scene", "dead", "lol", "real", "fr", "why", "what", "bhai", "yaar", "fake", "news", "tell me", "damn", "crazy", "gif"]
    has_keyword = any(word in msg_lower.split() for word in keywords)
    
    # Logic: 100% on ping/reply, 15% on keyword (slightly more active)
    should_reply = is_mentioned or is_reply or (has_keyword and random.random() < 0.15)

    if should_reply:
        if not client: return

        # 1. GENERATE THE RESPONSE FIRST (Backend processing)
        try:
            # Context builder - Clean history significantly
            raw_history = [msg async for msg in message.channel.history(limit=10)]
            clean_history = []
            for m in reversed(raw_history):
                if m.id == message.id: continue
                # Skip bot commands/errors from history to keep context clean
                if m.content.startswith("!"): continue 
                # IMPORTANT: Include ID in history so AI knows who is who
                clean_history.append(f"{m.author.name} (ID: {m.author.id}): {m.content}")
            history_text = "\n".join(clean_history)

            prompt = f"""
            HISTORY:
            {history_text}
            
            CURRENT MESSAGE:
            User: {message.author.name} (ID: {message.author.id})
            Content: {message.content}
            
            Respond as Astra. To ping this user, write <@{message.author.id}>. Be natural.
            """
            
            response_text = await generate_response(prompt)
            
            if response_text:
                # 2. CHECK FOR GIF TAGS
                gif_url = None
                # Regex to find [GIF: search term]
                gif_match = re.search(r"\[GIF:\s*(.*?)\]", response_text, re.IGNORECASE)
                
                if gif_match:
                    search_term = gif_match.group(1)
                    gif_url = get_giphy_url(search_term)
                    # Remove the tag from the text Astra sends
                    response_text = response_text.replace(gif_match.group(0), "").strip()

                # 3. DYNAMIC HUMAN TYPING SPEED (REVISED FOR REALISM)
                char_count = len(response_text)
                
                # Thinking time: Humans take 2-5 seconds just to READ/THINK before typing
                thinking_time = random.uniform(2.0, 5.0)
                
                # Typing time: Average human is ~0.12s per character (approx 80 WPM)
                # We add variation (0.08 to 0.15s per char)
                typing_time = char_count * random.uniform(0.08, 0.15)
                
                total_delay = thinking_time + typing_time
                
                # Hard cap at 15 seconds to prevent it from hanging forever on long texts
                if total_delay > 15.0: total_delay = 15.0
                
                async with message.channel.typing():
                    # The bot will show "Typing..." for this entire duration
                    await asyncio.sleep(total_delay)
                    
                    if response_text:
                        await message.reply(response_text)
                    if gif_url:
                        await message.channel.send(gif_url)

        except Exception as e:
            print(f"Error in message handling: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing.")
    else:
        bot.run(DISCORD_TOKEN)
