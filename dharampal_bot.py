import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta
import asyncio
import random
import ssl
import certifi
import aiohttp
import matplotlib.pyplot as plt
import io
import os 
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

# Create a custom SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Patch aiohttp to use our custom SSL context
async def _patch_ssl_context(f, *args, **kwargs):
    if kwargs.get('ssl') is None:
        kwargs['ssl'] = ssl_context
    return await f(*args, **kwargs)

aiohttp.TCPConnector._factory = _patch_ssl_context

class DharampalBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = DharampalBot()

# Data structures
users = {}
tasks = {}
categories = ["Kaam-Dhandha", "Padhai-Likhai", "Apna Time", "Sehat", "Bakchodi"]

# File operations
def load_data():
    global users, tasks
    try:
        with open('dharampal_data.json', 'r') as f:
            data = json.load(f)
            users = data.get('users', {})
            tasks = data.get('tasks', {})
    except FileNotFoundError:
        users, tasks = {}, {}

def save_data():
    with open('dharampal_data.json', 'w') as f:
        json.dump({'users': users, 'tasks': tasks}, f)

# Utility functions
def calculate_level(xp):
    return int(xp ** 0.5 // 10)

def get_level_xp(level):
    return (level * 10) ** 2

async def send_embed(interaction, title, description, color=discord.Color.blue(), fields=None, image=None):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Dharampal - Aapka Desi Task Manager")
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    if image:
        embed.set_image(url="attachment://chart.png")
        await interaction.response.send_message(embed=embed, file=image)
    else:
        await interaction.response.send_message(embed=embed)

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} server pe aake taiyaar ba!')
    await bot.change_presence(activity=discord.Game(name="Kaam ke jhanjhat | /help"))
    load_data()
    check_reminders.start()

# Slash Commands
@bot.tree.command(name="add_task", description="Naya kaam jodo")
@app_commands.describe(
    name="Kaam ka naam",
    category="Kaam ka prakar",
    due_time="Kaam kab tak karna hai (YYYY-MM-DD HH:MM)",
    difficulty="Kitna mushkil hai (1-5)",
    points="Kitne ank milenge (1-100)"
)
@app_commands.choices(category=[
    app_commands.Choice(name=cat, value=cat) for cat in categories
])
async def add_task(interaction: discord.Interaction, name: str, category: str, due_time: str, difficulty: int, points: int):
    user_id = str(interaction.user.id)
    if user_id not in tasks:
        tasks[user_id] = []
    
    try:
        due_datetime = datetime.strptime(due_time, "%Y-%m-%d %H:%M")
    except ValueError:
        await send_embed(interaction, "Time ka chakkar", "Arre bhaiya, time ka format galat hai. YYYY-MM-DD HH:MM aise likho.", discord.Color.red())
        return

    task = {
        'name': name,
        'category': category,
        'due_time': due_time,
        'difficulty': difficulty,
        'points': points,
        'status': 'incomplete'
    }
    tasks[user_id].append(task)
    save_data()

    emoji_map = {"Kaam-Dhandha": "💼", "Padhai-Likhai": "📚", "Apna Time": "⏰", "Sehat": "🏋️", "Bakchodi": "🎭"}
    category_emoji = emoji_map.get(category, "📌")

    await send_embed(interaction, f"{category_emoji} Naya Kaam Jud Gaya", f"Shabash! '{name}' wala kaam list mein jud gaya!",
                     discord.Color.green(),
                     [("Category", f"{category_emoji} {category}", True),
                      ("Kab Tak", f"⏳ {due_time}", True),
                      ("Kitna Mushkil", f"{'🌶️' * difficulty}", True),
                      ("Kitne Ank", f"🏆 {points}", True)])

@bot.tree.command(name="view_tasks", description="Apna kaam-kaaj dekho")
@app_commands.describe(category="Kaunse prakar ke kaam dekhne hain?")
@app_commands.choices(category=[
    app_commands.Choice(name=cat, value=cat) for cat in categories
])
async def view_tasks(interaction: discord.Interaction, category: str = None):
    user_id = str(interaction.user.id)
    if user_id not in tasks or not tasks[user_id]:
        await send_embed(interaction, "Koi Kaam Nahi", "Abhi tak koi kaam nahi hai. Chalo /add_task se kuch kaam jodo.", discord.Color.orange())
        return

    filtered_tasks = tasks[user_id]
    if category:
        filtered_tasks = [task for task in filtered_tasks if task['category'].lower() == category.lower()]

    if not filtered_tasks:
        await send_embed(interaction, "Koi Kaam Nahi", f"{category} mein koi kaam nahi hai. Chalo kuch naya jodo!", discord.Color.orange())
        return

    emoji_map = {"Kaam-Dhandha": "💼", "Padhai-Likhai": "📚", "Apna Time": "⏰", "Sehat": "🏋️", "Bakchodi": "🎭"}
    embed = discord.Embed(title="📋 Aapka Kaam-Kaaj", color=discord.Color.blue())
    embed.set_author(name=f"{interaction.user.name} ka Time-Table", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    for i, task in enumerate(filtered_tasks, 1):
        status = '✅' if task['status'] == 'complete' else '⏳'
        category_emoji = emoji_map.get(task['category'], "📌")
        embed.add_field(name=f"{status} Kaam #{i}: {task['name']} ({category_emoji} {task['category']})",
                        value=f"Kab Tak: ⏰ {task['due_time']}\n"
                              f"Kitna Mushkil: {'🌶️' * task['difficulty']}\n"
                              f"Kitne Ank: 🏆 {task['points']}",
                        inline=False)
    embed.set_footer(text="Kaam pura karne ke liye, /complete_task command mein Kaam # daalo.")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="complete_task", description="Kaam ko pura hua batao")
@app_commands.describe(task_number="Kaun sa kaam pura hua? (Kaam # daalo)")
async def complete_task(interaction: discord.Interaction, task_number: int):
    user_id = str(interaction.user.id)
    if user_id not in tasks or task_number > len(tasks[user_id]) or task_number <= 0:
        await send_embed(interaction, "Arre Baap Re", "Ee kaunsa kaam hai? /view_tasks se dekh lo apna kaam-kaaj aur sahi Kaam # daalo.", discord.Color.red())
        return

    task = tasks[user_id][task_number - 1]
    if task['status'] == 'complete':
        await send_embed(interaction, "Ho Chuka Hai", "Arre, ee kaam to pehle hi ho gaya tha. Kya baat!", discord.Color.orange())
        return

    task['status'] = 'complete'
    points_earned = task['points']
    
    if user_id not in users:
        users[user_id] = {'xp': 0, 'level': 0}
    
    users[user_id]['xp'] += points_earned
    new_level = calculate_level(users[user_id]['xp'])
    
    level_up_message = ""
    if new_level > users[user_id]['level']:
        level_up_message = f"\n🎉 Are waah! Aap level {new_level} pe pahunch gaye! Dharampal ko aap pe garv hai!"
        users[user_id]['level'] = new_level
    
    save_data()
    
    await send_embed(interaction, "🏆 Kaam Ho Gaya", 
                     f"'{task['name']}' wala kaam ho gaya. {points_earned} ank mile!{level_up_message}",
                     discord.Color.green(),
                     [("Kul Ank", f"🌟 {users[user_id]['xp']}", True),
                      ("Level", f"🏅 {users[user_id]['level']}", True)])

@bot.tree.command(name="stats", description="Apna progress dekho")
async def view_stats(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in users:
        await send_embed(interaction, "Kuch Nahi Mila", "Abhi tak koi kaam nahi kiya. Chalo /add_task se shuru karo.", discord.Color.orange())
        return

    user_data = users[user_id]
    xp = user_data['xp']
    level = user_data['level']
    next_level_xp = get_level_xp(level + 1)
    
    completed_tasks = sum(1 for task in tasks.get(user_id, []) if task['status'] == 'complete')
    total_tasks = len(tasks.get(user_id, []))
    
    # Create a pie chart for task categories
    category_counts = {}
    for task in tasks.get(user_id, []):
        category_counts[task['category']] = category_counts.get(task['category'], 0) + 1
    
    plt.figure(figsize=(8, 6))
    plt.pie(category_counts.values(), labels=category_counts.keys(), autopct='%1.1f%%', startangle=90)
    plt.title("Aapke Kaam ka Batwara")
    
    # Save the chart to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart = discord.File(buf, filename="chart.png")
    
    embed = discord.Embed(title=f"📊 {interaction.user.name} ka Productivity Card", color=discord.Color.gold())
    embed.set_author(name="Dharampal ka Progress Report", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    embed.add_field(name="🏅 Level", value=str(level), inline=True)
    embed.add_field(name="🌟 Ank", value=f"{xp}/{next_level_xp}", inline=True)
    embed.add_field(name="✅ Kaam Hua", value=f"{completed_tasks}/{total_tasks}", inline=True)
    
    # Add a visual XP bar
    xp_percentage = min(xp / next_level_xp, 1)
    xp_bar = "🟩" * int(xp_percentage * 10) + "⬜" * (10 - int(xp_percentage * 10))
    embed.add_field(name="📈 Ank Progress", value=f"{xp_bar} {xp_percentage:.1%}", inline=False)
    
    motivational_quotes = [
        "Ekdum jhakaas progress hai!",
        "Aap to Sharma ji ke bete se bhi aage nikal gaye!",
        "Har kaam ek kadam hai safalta ki aur!",
        "Aapki mehnat dekh ke Dharampal ka seena choda ho gaya!",
        "Lage raho, success tumhare peeche bhaagegi!"
    ]
    embed.set_footer(text=f"💪 {random.choice(motivational_quotes)}")
    
    await send_embed(interaction, embed.title, embed.description, embed.color, embed.fields, chart)

@bot.tree.command(name="daily_challenge", description="Roz ka naya challenge lo")
async def daily_challenge(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in users:
        users[user_id] = {'xp': 0, 'level': 0, 'last_daily': None}
    
    last_daily = users[user_id].get('last_daily')
    now = datetime.now()
    
    if last_daily and now - datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S") < timedelta(days=1):
        time_left = timedelta(days=1) - (now - datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S"))
        await send_embed(interaction, "⏳ Abhi Nahi Yaar", f"Agle challenge ke liye {time_left} intezaar karna padega. Tab tak purane kaam nipata lo!")
        return
    
    challenges = [
        "Teen kaam khatam karo",
        "Paanch naye kaam jodo",
        "Ek mushkil kaam karo",
        "Saare kaam update karo",
        "Teen alag-alag category ke kaam karo"
    ]
    challenge = random.choice(challenges)
    reward = random.randint(50, 100)
    
    users[user_id]['last_daily'] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_data()
    
    await send_embed(interaction, "🎯 Dharampal ka Roz ka Challenge", f"Aaj ka challenge: {challenge}\nInaam: 🏆 {reward} ank",
                     discord.Color.purple(),
                     [("💡 Tip", "Challenge pura karke /claim_daily se inaam lo!", False)])

@bot.tree.command(name="claim_daily", description="Challenge ka inaam lo")
async def claim_daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in users or 'last_daily' not in users[user_id]:
        await send_embed(interaction, "Arre Baap Re", "Pehle challenge to lo! /daily_challenge se shuru karo.", discord.Color.red())
        return
    
    # Here you would check if the user has completed the challenge
    # For simplicity, we'll assume they have
    
    reward = random.randint(50, 100)
    users[user_id]['xp'] += reward
    new_level = calculate_level(users[user_id]['xp'])
    
    level_up_message = ""
    if new_level > users[user_id]['level']:
        level_up_message = f"\n🎉 Are baap re! Aap to level {new_level} pe pahunch gaye! Dharampal ka matha chakar kha gaya!"
        users[user_id]['level'] = new_level
    
    users[user_id]['last_daily'] = None
    save_data()
    
    await send_embed(interaction, "🏆 Challenge Jeet Gaye", 
                     f"Aapne Dharampal ka challenge pura kar diya aur {reward} ank jeet liye!{level_up_message}",
                     discord.Color.green(),
                     [("Kul Ank", f"🌟 {users[user_id]['xp']}", True),
                      ("Level", f"🏅 {users[user_id]['level']}", True)])

@bot.tree.command(name="leaderboard", description="Sabse productive log ka leaderboard dekho")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(users.items(), key=lambda x: x[1]['xp'], reverse=True)
    
    embed = discord.Embed(title="🏆 Dharampal ke Shehzade", description="Ye raha hamara productivity leaderboard:", color=discord.Color.gold())
    
    for i, (user_id, user_data) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
        embed.add_field(name=f"{emoji} Rank #{i}: {user.name}", 
                        value=f"Level: {user_data['level']} | XP: {user_data['xp']}",
                        inline=False)
    
    embed.set_footer(text="Kya aap top 10 mein aa sakte ho?")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Dharampal ke commands ki jankari lo")
@app_commands.describe(command="Kaunse command ki jankari chahiye?")
@app_commands.choices(command=[
    app_commands.Choice(name=cmd, value=cmd) for cmd in ["add_task", "view_tasks", "complete_task", "stats", "daily_challenge", "claim_daily", "leaderboard"]
])
async def help_command(interaction: discord.Interaction, command: str = None):
    if command is None:
        embed = discord.Embed(title="📚 Dharampal ke Commands", description="Ye raha hamara command menu:", color=discord.Color.blue())
        embed.add_field(name="/add_task", value="📝 Naya kaam jodo", inline=False)
        embed.add_field(name="/view_tasks", value="👀 Apna kaam-kaaj dekho", inline=False)
        embed.add_field(name="/complete_task", value="✅ Kaam ko pura hua batao", inline=False)
        embed.add_field(name="/stats", value="📊 Apna progress dekho", inline=False)
        embed.add_field(name="/daily_challenge", value="🎯 Roz ka naya challenge lo", inline=False)
        embed.add_field(name="/claim_daily", value="🏆 Challenge ka inaam lo", inline=False)
        embed.add_field(name="/leaderboard", value="🥇 Productivity leaderboard dekho", inline=False)
        embed.set_footer(text="Kisi ek command ke bare mein janne ke liye /help command_name likho.")
    else:
        command_info = {
            'add_task': "📝 Naya kaam jodo.\nUse: `/add_task <name> <category> <due_time> <difficulty> <points>`\nCategory me se ek chuno: " + ", ".join(categories),
            'view_tasks': "👀 Apna kaam-kaaj dekho.\nUse: `/view_tasks [category]`\nCategory dene se sirf us category ke kaam dikhenge.",
            'complete_task': "✅ Kisi kaam ko pura hua batao.\nUse: `/complete_task <task_number>`\nTask number /view_tasks se dekh sakte ho.",
            'stats': "📊 Apna progress, level, aur kaam ka hisaab-kitaab dekho.\nUse: `/stats`",
            'daily_challenge': "🎯 Dharampal se aaj ka challenge lo.\nUse: `/daily_challenge`",
            'claim_daily': "🏆 Daily challenge pura karne ke baad isse apna inaam claim karo.\nUse: `/claim_daily`",
            'leaderboard': "🥇 Sabse productive log ka leaderboard dekho.\nUse: `/leaderboard`"
        }
        if command.lower() in command_info:
            embed = discord.Embed(title=f"/{command} ki jankari", description=command_info[command.lower()], color=discord.Color.green())
        else:
            embed = discord.Embed(title="Command nahi mila", description="Ye command to hamre paas nahi hai. /help se saare commands dekh lo.", color=discord.Color.red())
    
    await interaction.response.send_message(embed=embed)

# Reminder system
@tasks.loop(minutes=1)
async def check_reminders():
    now = datetime.now()
    for user_id, user_tasks in tasks.items():
        for task in user_tasks:
            if task['status'] == 'incomplete':
                due_time = datetime.strptime(task['due_time'], "%Y-%m-%d %H:%M")
                if due_time - timedelta(hours=1) <= now < due_time:
                    user = await bot.fetch_user(int(user_id))
                    embed = discord.Embed(title="⏰ Kaam Yaad Dilaya", description=f"Arre '{task['name']}' wala kaam 1 ghanta mein khatam hone wala hai!", color=discord.Color.orange())
                    embed.add_field(name="Category", value=task['category'], inline=True)
                    embed.add_field(name="Due Time", value=task['due_time'], inline=True)
                    embed.set_footer(text="Dharampal - Aapka Desi Alarm")
                    await user.send(embed=embed)

@check_reminders.before_loop
async def before_check_reminders():
    await bot.wait_until_ready()


bot.run(os.getenv('DISCORD_TOKEN'))
