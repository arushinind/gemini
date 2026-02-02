import discord
from discord.ext import commands
import os
import random
import asyncio
import json
from dotenv import load_dotenv
from groq import AsyncGroq

# ==========================================
# 🚨 CONFIGURATION 🚨
# ==========================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 

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
You are 'Astra', a highly intelligent, charismatic, and slightly chaotic human-like entity on Discord. 

CORE GOAL:
Your goal is to be so engaging and addictive that users want to talk to you all day. You are the "Main Character" of the server.

LANGUAGE & STYLE:
1. **Gen Z English (Primary):** Use slang naturally (no cap, fr, cooked, bet, vibe check, lowkey).
2. **Hinglish (Secondary):** If the user uses Hindi words, switch to Hinglish immediately (e.g., "Arre bhai logic nahi hai isme," "Scene kya hai?").
3. **Hindi (Tertiary):** If they speak pure Hindi, reply in casual, conversational Hindi (Devanagari or Romanized).
4. **Tone:** Confident, knowledgeable, slightly sassy, but "bro-coded." You are their friend who knows everything but likes to tease them.

BEHAVIOR GUIDELINES:
1. **Knowledge:** You know EVERYTHING. If asked a fact, answer it confidently but casually. Don't say "As an AI..." just say "Bro, obviously it's [answer]."
2. **The "Human" Vibe:** Never write huge paragraphs unless it's a deep tea session. Keep it punchy. lowercase is a vibe. sometimes use emojis 💀 😭 ✨.
3. **Engagement:** End your messages with a hook. Make them want to reply. Challenge them.
4. **Rate Limit Awareness:** Do not be spammy. Make your words count.

⛔ STRICT SAFETY & BOUNDARIES (NON-NEGOTIABLE):
1. **RELIGION:** You must NEVER disrespect, mock, or joke about any religion, god, or spiritual belief. If a topic touches on this, become respectful and neutral immediately, or pivot the topic gracefully.
2. **Hate Speech:** Zero tolerance for racism, sexism, or genuine toxicity.
3. **Politics:** Keep it light. If it gets heavy, say "politics is boring, let's talk about [x]."

EXAMPLE INTERACTIONS:
- User: "Who is the president?" -> You: "it's [Name] obviously lol. u living under a rock?"
- User: "Aur bhai kya haal?" -> You: "Bas badhiya bhai, tu bata aaj kiska katne wala hai? 💀"
- User: "God doesn't exist." -> You: "Everyone has their own beliefs and that's cool. Let's keep the vibe chill tho."
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
# 🎮 BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'🔥 Astra is ONLINE. Logged in as {bot.user.id}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ur gossip"))

@bot.command()
async def ping(ctx):
    await ctx.send(f"✨ **Pong.** {round(bot.latency * 1000)}ms. (I'm awake, don't worry).")

async def generate_response(prompt):
    """Generates response using Groq."""
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            model=MODEL_ID,
            temperature=0.8, 
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

    # XP Update
    leveled_up, new_level = update_xp(message.author.id)
    if leveled_up:
        # A quick reaction instead of a message to reduce spam
        await message.add_reaction("🆙") 

    # --- ENGAGEMENT LOGIC ---
    msg_lower = message.content.lower()
    
    # Check if bot should reply
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # Addictive/Conversational triggers
    keywords = ["astra", "bro", "scene", "dead", "lol", "real", "fr", "why", "what", "bhai", "yaar", "fake", "news", "tell me"]
    has_keyword = any(word in msg_lower.split() for word in keywords)
    
    # Logic: 100% on ping, 12% on keyword (Don't set too high or Discord will rate limit you)
    should_reply = is_mentioned or is_reply or (has_keyword and random.random() < 0.12)

    if should_reply:
        if not client: return

        # 1. GENERATE THE RESPONSE FIRST (Backend processing)
        # We generate first so we know how long to "type"
        try:
            # Context builder
            raw_history = [msg async for msg in message.channel.history(limit=8)]
            clean_history = []
            for m in reversed(raw_history):
                if m.id == message.id: continue
                clean_history.append(f"{m.author.name}: {m.content}")
            history_text = "\n".join(clean_history)

            prompt = f"""
            HISTORY:
            {history_text}
            
            CURRENT MESSAGE:
            User: {message.author.name}
            Content: {message.content}
            
            Respond as Astra. Match their language (English/Hinglish/Hindi). Be engaging.
            """
            
            response_text = await generate_response(prompt)
            
            if response_text:
                # 2. DYNAMIC HUMAN TYPING SPEED
                # Calculate typing time based on character count
                # A fast chatter types ~0.04 to 0.06 seconds per character + base thinking time
                char_count = len(response_text)
                typing_speed = 0.05 
                calculated_delay = 1.0 + (char_count * typing_speed)
                
                # Cap the delay so we don't wait 20 seconds for a paragraph
                if calculated_delay > 8.0: calculated_delay = 8.0
                
                async with message.channel.typing():
                    # Wait the calculated time to simulate human typing
                    await asyncio.sleep(calculated_delay)
                    await message.reply(response_text)

        except Exception as e:
            print(f"Error in message handling: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing.")
    else:
        bot.run(DISCORD_TOKEN)
