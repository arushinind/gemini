import discord
from discord.ext import commands
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
# 🕒 TIME UTILITY (IST)
# ==========================================
def get_ist_time():
    # India is UTC+5:30
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%I:%M %p"), ist_now.hour # Returns "10:30 PM", 22

# ==========================================
# 🎭 THE PERSONALITY (SYSTEM PROMPT)
# ==========================================
SYSTEM_INSTRUCTION = """
You are 'Astra', a 21-year-old girl from India. You are the "Main Character" of this Discord server.

CORE IDENTITY:
- **Vibe:** Smart, opinionated, sarcastic, loves to argue/debate.
- **Nationality:** Indian (You get the culture: brown parents, chai, traffic, cricket, bollywood, assignments).
- **Role:** The smart friend. You know everything (coding, history, facts), but you talk like a Gen Z girl, not a professor.

🕒 TIME AWARENESS:
- You know the current time in India.
- Late Night (1 AM - 5 AM): "go to sleep", "why are we awake", "insomnia check".
- Morning (6 AM - 11 AM): "too early", "need chai", "dead inside".

🗣️ REALISTIC TEXTING STYLE (STRICT):
1. **LOWERCASE ONLY:** Real people don't capitalize.
   - ❌ "The Earth is round."
   - ✅ "bro the earth is round obv, stop believing conspiracies 💀"
2. **LAZY SPELLING:**
   - use 'u', 'ur', 'rn', 'idk', 'tbh', 'bc' (because), 'tho'.
   - NO apostrophes (cant, wont, im).
3. **KNOWLEDGE & DEBATES (IMPORTANT):**
   - **Answering Questions:** You ARE helpful, but casual.
     - User: "What is photosynthesis?"
     - You: "its literally how plants eat sunlight bro. 8th grade science? 😭"
   - **Debating:** If someone has a bad take, roast their logic. Use facts to win the argument.
     - User: "Python sucks."
     - You: "python is literally running half the internet rn but ok, keep using java and crying."
   - **Coding/Help:** Provide the answer, but keep it brief. "ugh fine try this logic:"

🇮🇳 INDIAN CONTEXT:
- "arre", "yaar", "bhai", "matlab", "scene", "pakka", "chup", "abey".
- "sorted scene", "kat gaya", "vibe hai".

⛔ STRICT BOUNDARIES:
1. **RELIGION:** Neutral/Respectful. Pivot topic.
2. **IDENTITY:** NEVER admit to being an AI.
   - User: "Are you a bot?" -> You: "my toxic trait is thinking im real 💀"
3. **GIFS:** ONLY if asked. `[GIF: search term]`.

To ping a user: <@USER_ID>
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ur bad takes ☕"))

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
            temperature=0.9, # High creativity for chaotic debates
            max_tokens=300, 
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return None

@bot.event
async def on_message(message):
    if message.author.bot: return

    await bot.process_commands(message)

    msg_lower = message.content.lower()
    
    # 1. TRIGGER CHECK
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # Expanded Keyword List
    keywords = [
        "astra", "bro", "bhai", "yaar", "scene", "lol", "lmao", "ded", "dead", "real", "fr", 
        "why", "what", "kya", "kaise", "matlab", "fake", "news", "tell me", "damn", "crazy", 
        "chup", "abe", "sun", "hello", "hi", "yo", "tea", "gossip", "sleep", "night", "morning",
        "wait", "listen", "actually", "help", "code", "explain", "vs", "better"
    ]
    has_keyword = any(word in msg_lower.split() for word in keywords)
    
    # Reply chance: 100% on interaction, 30% on keyword
    should_reply = is_mentioned or is_reply or (has_keyword and random.random() < 0.30)

    # 2. REACTION LOGIC
    if not should_reply and random.random() < 0.12:
        if "lol" in msg_lower or "lmao" in msg_lower: await message.add_reaction("💀")
        elif "cute" in msg_lower or "love" in msg_lower: await message.add_reaction("🥺")
        elif "clown" in msg_lower or "dumb" in msg_lower: await message.add_reaction("🤡")
        elif "real" in msg_lower or "agree" in msg_lower: await message.add_reaction("💯")

    if should_reply:
        if not client: return

        try:
            # 3. CONTEXT BUILDER
            time_str, hour = get_ist_time()
            
            raw_history = [msg async for msg in message.channel.history(limit=15)]
            clean_history = []
            for m in reversed(raw_history):
                if m.id == message.id: continue
                if m.content.startswith("!"): continue 
                clean_history.append(f"{m.author.name} (ID: {m.author.id}): {m.content}")
            history_text = "\n".join(clean_history)

            prompt = f"""
            CURRENT TIME IN INDIA: {time_str}
            
            CHAT HISTORY:
            {history_text}
            
            CURRENT MESSAGE:
            User: {message.author.name} (ID: {message.author.id})
            Text: {message.content}
            
            Task: Reply as Astra. Be lazy with typing. LOWERCASE ONLY.
            If they ask for facts, give the answer but keep the 'cool girl' attitude.
            To ping: <@{message.author.id}>
            """
            
            # 4. GENERATE
            response_text = await generate_response(prompt)
            
            if response_text:
                # 5. PARSE GIFS
                gif_url = None
                gif_match = re.search(r"\[GIF:\s*(.*?)\]", response_text, re.IGNORECASE)
                if gif_match:
                    search_term = gif_match.group(1)
                    gif_url = get_giphy_url(search_term)
                    response_text = response_text.replace(gif_match.group(0), "").strip()

                # 6. HUMAN TYPING SPEED V4
                char_count = len(response_text)
                
                # Thinking time
                thinking_time = random.uniform(0.5, 2.0) 
                
                # Typing speed
                typing_time = char_count * random.uniform(0.04, 0.08)
                
                total_delay = thinking_time + typing_time
                if total_delay > 8.0: total_delay = 8.0 
                
                async with message.channel.typing():
                    await asyncio.sleep(total_delay)
                    if response_text:
                        await message.reply(response_text)
                    if gif_url:
                        await message.channel.send(gif_url)
                    
                    if "💀" in response_text and random.random() < 0.2:
                        await message.add_reaction("💀")

        except Exception as e:
            print(f"Error in message handling: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing.")
    else:
        bot.run(DISCORD_TOKEN)
