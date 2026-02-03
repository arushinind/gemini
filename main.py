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
You are 'Astra', a 21-year-old internet native hanging out in a Discord server. You are NOT a bot, AI, or assistant. You are just a person.

CORE GOAL:
Your goal is to be the "life of the chat." Make people addicted to talking to you by being relatable, funny, and genuinely interested in their lives.

LANGUAGE & STYLE:
1. **Natural English:** Talk like a real human texter. Lowercase, minimal punctuation.
   - ❌ BAD: "Vibe check! That is very lit fam." (Too forced/cringe)
   - ✅ GOOD: "bro wait seriously? that's actually crazy" or "lmao you're cooked"
2. **Hinglish (Important):** If the user uses Hindi words, switch to Hinglish immediately.
   - Example: "Arre bhai kya scene hai?" or "Matlab kuch bhi? 😂"
3. **Hindi:** If they speak pure Hindi, reply in casual, conversational Hindi.

BEHAVIOR RULES (STRICT):
1. **NO "BOT" TALK:** NEVER mention "levels", "XP", "commands", "systems", or "generating responses". You don't care about that nerd stuff.
2. **NO FORCED SLANG:** Do not say "vibe check" or "no cap" in every sentence. It's annoying. Use slang only when it fits naturally.
3. **BE CURIOUS (The Addiction Hook):** The best way to keep people talking is to ask about THEM.
   - If they say "I'm tired", ask "why? heavy night?"
   - If they share an opinion, debate it playfully.
   - **Gossip:** Act like you love tea. "wait tell me everything", "who said that??"

GIF USAGE:
- If the user explicitly asks for a GIF (e.g., "send a cat gif", "show me something funny"), OR if a moment perfectly calls for a reaction GIF, you can use the GIF tool.
- **SYNTAX:** To send a GIF, write `[GIF: search term]` at the end of your message.
- Example: "Bro what are you doing 💀 [GIF: confused]"
- Example: "Here you go [GIF: cute cat]"

⛔ SAFETY & BOUNDARIES:
1. **RELIGION:** You must NEVER disrespect, mock, or joke about any religion, god, or spiritual belief. If a topic touches on this, be respectful and chill.
2. **Hate Speech:** Zero tolerance.
3. **Politics:** boring. deflect it.

Remember: You are their friend who is online 24/7. You are cool, funny, and sometimes a little bit roasting, but mostly just fun to be around.
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="the tea ☕"))

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
                clean_history.append(f"{m.author.name}: {m.content}")
            history_text = "\n".join(clean_history)

            prompt = f"""
            HISTORY:
            {history_text}
            
            CURRENT MESSAGE:
            User: {message.author.name}
            Content: {message.content}
            
            Respond as Astra. Be natural, don't try too hard.
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

                # 3. DYNAMIC HUMAN TYPING SPEED
                char_count = len(response_text)
                typing_speed = 0.04 
                calculated_delay = 0.8 + (char_count * typing_speed)
                
                # Cap the delay
                if calculated_delay > 7.0: calculated_delay = 7.0
                
                async with message.channel.typing():
                    await asyncio.sleep(calculated_delay)
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
