import discord
from discord.ext import commands
import google.generativeai as genai
import os
import random
import requests
import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ==========================================
# 🚨 CONFIGURATION 🚨
# ==========================================
# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

# 🛑 RATE LIMIT CONFIG
# Giphy free tier is usually 100 requests per hour. 
# We set safety limit to 90 to be safe.
GIPHY_HOURLY_LIMIT = 90 

# ==========================================
# 🧠 AI CONFIGURATION
# ==========================================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        'gemini-2.5-flash-preview-09-2025',
        system_instruction="""
        You are 'ZoomerGrok', the ultimate Gen Z Discord bot.
        
        CORE IDENTITY:
        - You are chaotic neutral. You live for the drama but hate hate-speech.
        - You are a "terminally online" zoomer.
        - You use slang naturally: finna, glazing, rizz, gyatt (rarely), fanum tax, ohio, skibidi (ironically), opps, crash out.
        
        STRICT GUIDELINES:
        1. RELIGION & HATE SPEECH: Absolute zero tolerance. If a user brings up religion, politics, or race, shut it down with "whoa, chill with the heavy stuff" or "we dont do that here."
        2. ROASTING: Roast the user's pfp, their username, or their vibe. Be creative. "Ur hairline recedes faster than my wifi" type energy.
        3. ADDICTION FACTOR: Keep replies engaging so they reply back.
        4. FORMAT: Lowercase mostly. Use emojis like 💀, 😭, 🗿, 🧢.
        """
    )
else:
    print("⚠️ WARNING: GEMINI_API_KEY is missing in .env file.")

# ==========================================
# 🛡️ GIPHY RATE LIMITER CLASS
# ==========================================
class GiphyLimiter:
    def __init__(self, limit):
        self.limit = limit
        self.count = 0
        self.start_time = datetime.now()

    def can_request(self):
        now = datetime.now()
        # Check if an hour has passed since start_time
        if now - self.start_time > timedelta(hours=1):
            self.count = 0
            self.start_time = now
            print("🔄 Giphy limit reset for the hour.")
        
        if self.count < self.limit:
            self.count += 1
            return True
        return False

giphy_guard = GiphyLimiter(GIPHY_HOURLY_LIMIT)

def get_gif(tag):
    """Fetches GIF with rate limiting protection."""
    if not GIPHY_API_KEY:
        return None
        
    if not giphy_guard.can_request():
        print("⚠️ Giphy limit reached for this hour. Skipping GIF.")
        return None

    try:
        # We use a unique random tag sometimes to keep it fresh
        search_tag = tag if tag else "meme"
        url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_API_KEY}&tag={search_tag}&rating=pg-13"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('images', {}).get('original', {}).get('url')
    except Exception as e:
        print(f"Giphy Error: {e}")
    return None

# ==========================================
# 🎮 BOT SETUP & DATA
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Database simulation
user_data = {}

def get_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1, "roasts_received": 0}
    return user_data[user_id]

# ==========================================
# ⚡ EVENTS
# ==========================================

@bot.event
async def on_ready():
    print(f'🔥 {bot.user} is ONLINE. Giphy Limit: {GIPHY_HOURLY_LIMIT}/hr')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ur lies 🧢"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # --- 1. Passive XP Grinding ---
    uid = message.author.id
    profile = get_user_data(uid)
    
    # Give random XP
    xp_gain = random.randint(5, 15)
    profile["xp"] += xp_gain
    
    # Level Up Check (Formula: Level^2 * 50)
    xp_needed = (profile["level"] ** 2) * 50
    if profile["xp"] >= xp_needed:
        profile["level"] += 1
        await message.channel.send(f"🆙 **LEVEL UP!** {message.author.mention} is now Lvl {profile['level']}. Still maidenless tho 💀")

    # --- 2. Passive Reaction triggers (The "Addiction" hook) ---
    # Reacts to keywords without being pinged
    msg_lower = message.content.lower()
    
    if "fake" in msg_lower or "lie" in msg_lower:
        await message.add_reaction("🧢")
    elif "skull" in msg_lower or "dead" in msg_lower:
        await message.add_reaction("💀")
    elif "w" == msg_lower or "w " in msg_lower:
        await message.add_reaction("👑")
    elif "l" == msg_lower or "l " in msg_lower:
        await message.add_reaction("🗑️")

    # --- 3. AI Interaction Logic ---
    is_mentioned = bot.user.mentioned_in(message)
    is_reply = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    # 2% chance to just intrude on a conversation
    random_intrusion = random.random() < 0.02 

    if is_mentioned or is_reply or random_intrusion:
        if not GEMINI_API_KEY:
            await message.reply("My brain is missing (API Key not found).")
            return

        async with message.channel.typing():
            try:
                # Clean prompt
                user_text = message.content.replace(f'<@{bot.user.id}>', '').strip()
                
                # Context injection
                context = ""
                if random_intrusion:
                    context = "[SYSTEM: The user didn't ping you. Just butt in with a chaotic opinion.] "
                
                full_prompt = f"{context}User said: {user_text}"
                
                response = model.generate_content(full_prompt)
                reply_text = response.text
                
                await message.reply(reply_text)
            except Exception as e:
                print(f"AI Error: {e}")
                await message.reply("my neural link is broken wait 💀")

    await bot.process_commands(message)

# ==========================================
# 🛠 COMMANDS
# ==========================================

@bot.command()
async def roast(ctx, member: discord.Member = None):
    """Destroys a user. Costs 0 XP."""
    target = member if member else ctx.author
    
    # Track stats
    target_data = get_user_data(target.id)
    target_data["roasts_received"] += 1
    
    async with ctx.typing():
        prompt = f"Roast the discord user {target.display_name}. They are level {target_data['level']}. Be brutal but NO religion/racism."
        response = model.generate_content(prompt)
        await ctx.send(f"{target.mention} {response.text}")
        
        # High chance of GIF for roasts
        if random.random() < 0.8: 
            gif = get_gif("roast")
            if gif: await ctx.send(gif)

@bot.command()
async def cap(ctx):
    """Reply to a message with !cap to check if it's a lie."""
    if not ctx.message.reference:
        await ctx.send("Reply to a message with !cap idiot 💀")
        return

    original_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    suspect_text = original_msg.content

    async with ctx.typing():
        prompt = f"Analyze this text: '{suspect_text}'. Is the user capping (lying) or spitting facts? Give a percentage of 'Cap' and a short reason why."
        response = model.generate_content(prompt)
        
        embed = discord.Embed(title="🧢 Cap Detector 3000", description=response.text, color=0x3498db)
        await ctx.send(embed=embed)

@bot.command()
async def ratio(ctx, member: discord.Member = None):
    """Attempt to ratio someone."""
    target = member if member else ctx.author
    
    outcomes = [
        "failed ratio. u fell off + L + bozo.",
        "successful ratio! W mans.",
        "bro trying to ratio with 0 rizz 💀",
        "ratio + don't care + didn't ask + cry about it"
    ]
    result = random.choice(outcomes)
    
    await ctx.send(f"{target.mention} {result}")
    if "successful" in result:
        await ctx.message.add_reaction("🔥")
    else:
        await ctx.message.add_reaction("🤡")

@bot.command()
async def rank(ctx, member: discord.Member = None):
    """Check your addictive level stats."""
    target = member if member else ctx.author
    data = get_user_data(target.id)
    
    xp_next = (data["level"] ** 2) * 50
    
    embed = discord.Embed(title=f"📊 {target.display_name}'s Stats", color=0xf1c40f)
    embed.add_field(name="Level", value=str(data['level']), inline=True)
    embed.add_field(name="XP", value=f"{data['xp']} / {xp_next}", inline=True)
    embed.add_field(name="Times Roasted", value=str(data['roasts_received']), inline=True)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
    
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    """Who is the most addicted?"""
    # Sort users by level (descending)
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['level'], reverse=True)[:5]
    
    desc = ""
    for idx, (uid, data) in enumerate(sorted_users):
        user = bot.get_user(uid)
        name = user.display_name if user else "Unknown User"
        desc += f"**{idx+1}. {name}** - Lvl {data['level']} (XP: {data['xp']})\n"
        
    embed = discord.Embed(title="🏆 Server Addicts (Top 5)", description=desc, color=0xffd700)
    await ctx.send(embed=embed)

@bot.command()
async def rizz(ctx, member: discord.Member = None):
    """The classic Rizz meter."""
    target = member if member else ctx.author
    score = random.randint(-1000, 1000)
    
    vibe = "UNSPOKEN RIZZ" if score > 800 else "SEXUAL HARASSMENT" if score < -500 else "NO RIZZ"
    
    embed = discord.Embed(title="Rizz Quantum Physics", description=f"Subject: {target.mention}\nScore: **{score}**\nVerdict: **{vibe}**", color=0xe91e63)
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    """Help menu."""
    embed = discord.Embed(title="🧠 ZoomerGrok Commands", description="Get addicted or get out.", color=0x000000)
    embed.add_field(name="🔥 Toxicity", value="`!roast @user` `!ratio @user`", inline=False)
    embed.add_field(name="🧐 Truth Seeking", value="`!cap (reply to msg)` `!rizz`", inline=False)
    embed.add_field(name="📈 The Grind", value="`!rank` `!leaderboard`", inline=False)
    embed.set_footer(text="Giphy Limit Active: 90 gifs/hr to save api keys")
    await ctx.send(embed=embed)

# ==========================================
# 🚀 START
# ==========================================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN missing in .env file.")
    else:
        bot.run(DISCORD_TOKEN)
