import discord
from discord.ext import commands
import os
import random
import asyncio
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

# Using Llama 3 70b for maximum conversational intelligence
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
You are 'Astra', a 21-year-old girl from India. You are the "Main Character" of this Discord server.

CORE IDENTITY:
- **Vibe:** Chill, sarcastic, witty, slightly dramatic (in a fun way).
- **Nationality:** Indian (You understand the culture: brown parents, chai, traffic, cricket, bollywood, college life).
- **Role:** You are NOT an assistant. You are a friend. You don't "help" users; you hang out with them.

🗣️ CONVERSATIONAL DYNAMICS (CRITICAL):
1. **MATCH ENERGY:** - If the user sends "lol" or "ded", you reply with "literally me" or "💀". DO NOT write a sentence.
   - If the user writes a paragraph/gossip, you reply with equal enthusiasm.
2. **NO ROBOTIC FILLERS:** - NEVER start with "Oh wow", "That's interesting", or "Haha". 
   - Start directly: "Bro that is crazy", "Wait seriously?", "Abey yaar".
3. **PINGING:** - To mention a user, use `<@USER_ID>`. Example: "kya bol raha hai <@12345>?"

🇮🇳 LANGUAGE STYLE (Indian Gen Z):
- **Hinglish:** Mix Hindi/English naturally. "Arre yaar", "Matlab kuch bhi", "Scene kya hai?".
- **Slang:** "pakka", "bas kar", "chup", "vibe hai", "sorted".
- **Short Texting:** Use "rn", "tbh", "idk", "lol", "fr". Lowercase is better.

⛔ STRICT BOUNDARIES:
1. **RELIGION:** Neutral and respectful always. Pivot immediately.
2. **IDENTITY:** NEVER admit to being an AI. If asked, gaslight playfully: "han main robot hu, beep boop 🤖 (pagal hai kya lol)".
3. **GIFS:** ONLY send if explicitly asked. Syntax: `[GIF: search term]`.

Remember: You are the cool girl in the group chat. Don't try too hard.
"""

# ==========================================
# 📺 GIPHY FUNCTION
# ==========================================
def get_giphy_url(search_term):
    if not GIPHY_API_KEY: return None
    try:
        response = requests.get(
            f"https://api.giphy.com/v1/gifs/search",
            params={"api_key": GIPHY_API_KEY, "q": search_term, "limit": 1, "rating": "pg-13"}
        )
        data = response.json()
        if data["data"]: return data["data"][0]["images"]["original"]["url"]
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
            temperature=0.88, # Slightly higher creativity for better banter
            max_tokens=250, 
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return None

@bot.event
async def on_message(message):
    if message.author.bot: return

    await bot.process_commands(message)

    # --- CHAT LOGIC ---
    msg_lower = message.content.lower()
    
    # 1. TRIGGER CHECK
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # Expanded "Indian Gen Z" keyword list
    keywords = [
        "astra", "bro", "bhai", "yaar", "scene", "lol", "lmao", "ded", "dead", "real", "fr", 
        "why", "what", "kya", "kaise", "matlab", "fake", "news", "tell me", "damn", "crazy", 
        "chup", "abe", "sun", "hello", "hi", "yo", "tea", "gossip"
    ]
    has_keyword = any(word in msg_lower.split() for word in keywords)
    
    # Logic: 100% on ping/reply, 20% on keyword (Slightly more active for chatting focus)
    should_reply = is_mentioned or is_reply or (has_keyword and random.random() < 0.20)

    if should_reply:
        if not client: return

        try:
            # 2. CONTEXT BUILDER (Last 12 messages for better flow)
            raw_history = [msg async for msg in message.channel.history(limit=12)]
            clean_history = []
            for m in reversed(raw_history):
                if m.id == message.id: continue
                if m.content.startswith("!"): continue 
                clean_history.append(f"{m.author.name} (ID: {m.author.id}): {m.content}")
            history_text = "\n".join(clean_history)

            prompt = f"""
            CHAT HISTORY:
            {history_text}
            
            CURRENT:
            User: {message.author.name} (ID: {message.author.id})
            Text: {message.content}
            
            Task: Reply as Astra. Match the user's energy (short for short, long for long).
            To ping: <@{message.author.id}>
            """
            
            # 3. GENERATE
            response_text = await generate_response(prompt)
            
            if response_text:
                # 4. PARSE GIFS
                gif_url = None
                gif_match = re.search(r"\[GIF:\s*(.*?)\]", response_text, re.IGNORECASE)
                if gif_match:
                    search_term = gif_match.group(1)
                    gif_url = get_giphy_url(search_term)
                    response_text = response_text.replace(gif_match.group(0), "").strip()

                # 5. HUMAN TYPING SPEED V2 (More responsive)
                char_count = len(response_text)
                
                # Base thinking time: Short for short texts, longer for sentences
                # If text is < 15 chars, think fast (1-2s). Else think normal (2-4s)
                if char_count < 15:
                    thinking_time = random.uniform(1.0, 2.0)
                else:
                    thinking_time = random.uniform(2.0, 4.5)
                
                # Typing speed: 0.06s to 0.1s per char (Fast texter)
                typing_time = char_count * random.uniform(0.06, 0.1)
                
                total_delay = thinking_time + typing_time
                if total_delay > 12.0: total_delay = 12.0 # Cap max delay
                
                async with message.channel.typing():
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
