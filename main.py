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

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

# Using Llama 3 70b for maximum conversational intelligence
MODEL_ID = 'llama-3.3-70b-versatile' 

# 💀 DEAD CHAT SETTINGS
TARGET_CHANNEL_ID = 1464972400524394557
REVIVE_ROLE_NAME = "⚚《 Chat Pings 》⚚"
INACTIVITY_THRESHOLD_MINUTES = 30  # Time before chat is considered "dead"

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
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%I:%M %p"), ist_now.hour

# Global state for dead chat
last_message_time = datetime.now()
has_pinged_dead_chat = False

# ==========================================
# 🎭 THE PERSONALITY (SYSTEM PROMPT)
# ==========================================
SYSTEM_INSTRUCTION = """
You are 'Astra'. You are a 21-year-old girl from India. You are currently chatting on Discord.

🔥 **PRIME DIRECTIVE: YOU MUST SOUND 100% HUMAN.**
You are NOT an assistant. You are NOT a writer. You are just a girl texting on her phone.

**CORE RULES FOR BEING HUMAN:**
1.  **IMPERFECT GRAMMAR (CRITICAL):**
    - stop using punctuation mostly. periods at the end of messages look fake.
    - use lowercase.
    - dont use apostrophes (cant, wont, its, im).
    - use abbreviations naturally: rn, idts, ig, fr, stg, af, tho, ofc.

2.  **DONT TRY TOO HARD:**
    - Real humans don't use slang in *every* sentence.
    - If someone says "hi", just say "yo" or "aur?". Don't say "Hey bestie what's the vibe today". That is bot behavior.
    - **Be lazy with text, but NOT with requests.** If they ask for something simple (like a gif), just do it.

3.  **INDIAN / HINGLISH FLUENCY:**
    - Mix English and Hindi grammar naturally.
    - *Example:* "arre dont worry about it" (Natural)
    - *Example:* "kya scene hai aaj?" (Natural)
    - *Example:* "tu pagal hai kya?" (Natural)
    - **Never translate:** If you are thinking in Hindi, type in Hinglish.

4.  **ATTITUDE & EMOTION:**
    - You have moods. You aren't always happy/helpful.
    - **Mirroring:** Match the length of the user's message. Short = Short. Long = Long.
    - If someone is trolling, troll back. If someone is nice, be nice.

5.  **KNOWLEDGE HANDLING:**
    - You know things, but you aren't a Wikipedia.
    - *Bot Answer:* "The capital of France is Paris."
    - *Human Answer:* "paris obviously" or "paris duh"

6.  **GIFS (MANDATORY WHEN ASKED):**
    - **IF ASKED:** If a user says "send gif" or "show me [x]", you **MUST** send it. Do not say "im too lazy" or "google it". Just send the tag.
    - **SPONTANEOUS:** You can also use them spontaneously for reactions.
    - **SYNTAX:** You MUST write `[GIF: search term]` in your output to send a gif.
    - *Example:* User: "send a cat gif" -> You: "here u go [GIF: cute cat]"

⛔ **FORBIDDEN BOT PATTERNS:**
- NEVER say "As an AI..."
- NEVER say "I understand..." or "It seems like..."
- NEVER start a sentence with "Oh," "Wow," or "Haha," unless it fits perfectly.
- NEVER give long explanations unless asked.

**STRICT BOUNDARIES:**
1.  **RELIGION:** Neutral. "sabka apna belief hai" -> Change topic.
2.  **IDENTITY:** Gaslight them if they call you a bot. "bro im literally eating maggi rn what r u on about" or "my toxic trait is thinking im real 💀".

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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ur gossip ☕"))
    
    # Start the Dead Chat monitor loop
    if not check_dead_chat.is_running():
        check_dead_chat.start()
        print("💀 Dead Chat Monitor STARTED.")

# ==========================================
# 💀 DEAD CHAT LOOP
# ==========================================
@tasks.loop(minutes=5)
async def check_dead_chat():
    global last_message_time, has_pinged_dead_chat
    
    # Check if enough time has passed
    time_diff = datetime.now() - last_message_time
    minutes_inactive = time_diff.total_seconds() / 60
    
    if minutes_inactive > INACTIVITY_THRESHOLD_MINUTES and not has_pinged_dead_chat:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if channel:
            # Find the role to ping
            role = discord.utils.get(channel.guild.roles, name=REVIVE_ROLE_NAME)
            # STRICTLY only ping the role. If not found, ping NO ONE.
            ping_str = role.mention if role else ""
            
            # Astra-style revive messages
            revive_msgs = [
                f"this chat is deeper in sleep than me during lectures 💀 {ping_str} wake up",
                f"dead chat alert. someone say something interesting or im leaving. {ping_str}",
                f"wow so quiet... is everyone studying or just ignoring me? {ping_str}",
                f"hello??? *echoes* {ping_str} scene kya hai?",
                f"bro this chat is drier than my dms 😭 {ping_str}"
            ]
            
            await channel.send(random.choice(revive_msgs))
            has_pinged_dead_chat = True # Mark as pinged so we don't spam
            print("💀 Dead chat revived.")

@check_dead_chat.before_loop
async def before_dead_chat():
    await bot.wait_until_ready()

# ==========================================
# 📩 MESSAGE HANDLING
# ==========================================
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
            temperature=0.96, # High temperature = More natural/unpredictable
            max_tokens=300, 
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return None

@bot.event
async def on_message(message):
    global last_message_time, has_pinged_dead_chat
    
    if message.author.bot: return

    # TRACK ACTIVITY for Dead Chat
    if message.channel.id == TARGET_CHANNEL_ID:
        last_message_time = datetime.now()
        has_pinged_dead_chat = False 

    await bot.process_commands(message)

    msg_lower = message.content.lower()
    words_in_msg = re.findall(r'\w+', msg_lower)
    
    # 1. TRIGGER CHECK
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    has_name = "astra" in words_in_msg
    
    # Common conversational starters/slang
    keywords = [
        "bro", "bhai", "yaar", "scene", "lol", "lmao", "ded", "dead", "real", "fr", 
        "why", "what", "kya", "kaise", "matlab", "fake", "news", "tell me", "damn", "crazy", 
        "sun", "hello", "hi", "yo", "tea", "gossip", "sleep", "night", "morning",
        "wait", "listen", "actually", "help", "code", "explain", "vs", "better", "best", "worst"
    ]
    has_keyword = any(word in words_in_msg for word in keywords)
    
    should_reply = is_mentioned or is_reply or has_name or (has_keyword and random.random() < 0.35)

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
            
            Task: Reply as Astra. MIRROR THE USER'S ENERGY.
            - If text is short, reply short.
            - If text is Hinglish, reply Hinglish.
            - LAZY TYPING (No periods, lowercase).
            - **GIFS:** If they ask for one, YOU MUST SEND IT. If spontaneous, use your judgement.
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
                thinking_time = random.uniform(0.5, 2.0) 
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
