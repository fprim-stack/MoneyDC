
from threading import Thread
from discord.ext import commands
import discord
import random
import json
import os
import re
import asyncio

# --- keep-alive webserver ---
# --- User Data Functions ---
def load_users():
    """Load user data from JSON file"""
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save user data to JSON file"""
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2)

def load_items():
    """Load items database from JSON file"""
    if os.path.exists('items.json'):
        with open('items.json', 'r') as f:
            return json.load(f)
    return {}

def get_total_luck(user_id):
    user = get_user_data(user_id)
    return user.get("luck", 0) + (user.get("prestige", 0) * 10)

def get_total_money_boost(user_id):
    user = get_user_data(user_id)
    return user.get("money_boost", 0) + (user.get("prestige", 0) * 10)

def get_user_data(user_id):
    """Get user data, create if doesn't exist"""
    users = load_users()
    user_id = str(user_id)

    # Default template for new users
    default_data = {
        "money": 100,       # Starting money
        "xp": 0,
        "level": 1,
        "inventory": {},    # Item inventory
        "last_daily": 0,    # Last daily claim timestamp
        "bank": 0,          # Bank balance
        "achievements": [], # List of earned achievements
        "luck": 0,          # Luck % boost
        "money_boost": 0,   # Money % boost
        "prestige": 0       # Prestige level
    }

    # Create new user if not found
    if user_id not in users:
        users[user_id] = default_data.copy()
        save_users(users)

    else:
        # Ensure all keys exist for old users
        updated = False
        for key, value in default_data.items():
            if key not in users[user_id]:
                users[user_id][key] = value
                updated = True
        if updated:
            save_users(users)

    return users[user_id]

def update_user_data(
    user_id,
    money=None,
    xp=None,
    level=None,
    inventory=None,
    last_daily=None,
    bank=None,
    achievements=None,
    luck=None,
    money_boost=None,
    prestige=None
):
    """Update user data"""
    users = load_users()
    user_id = str(user_id)

    # Initialize user if not exists
    if user_id not in users:
        users[user_id] = {
            "money": 100,
            "xp": 0,
            "level": 1,
            "inventory": {},
            "last_daily": 0,
            "bank": 0,
            "achievements": [],
            "luck": 0,
            "money_boost": 0,
            "prestige": 0
        }

    # Update only provided values
    if money is not None:
        users[user_id]["money"] = money
    if xp is not None:
        users[user_id]["xp"] = xp
    if level is not None:
        users[user_id]["level"] = level
    if inventory is not None:
        users[user_id]["inventory"] = inventory
    if last_daily is not None:
        users[user_id]["last_daily"] = last_daily
    if bank is not None:
        users[user_id]["bank"] = bank
    if achievements is not None:
        users[user_id]["achievements"] = achievements
    if luck is not None:
        users[user_id]["luck"] = luck
    if money_boost is not None:
        users[user_id]["money_boost"] = money_boost
    if prestige is not None:
        users[user_id]["prestige"] = prestige

    save_users(users)


def add_item_to_inventory(user_id, item_name, amount=1):
    """Add item(s) to user inventory (luck affects rolls separately)"""
    users = load_users()
    user_id = str(user_id)

    if user_id not in users:
        users[user_id] = get_user_data(user_id)

    inventory = users[user_id].get("inventory", {})

    if item_name in inventory:
        inventory[item_name] += amount
    else:
        inventory[item_name] = amount

    users[user_id]["inventory"] = inventory
    save_users(users)
    return inventory[item_name]

def remove_item_from_inventory(user_id, item_name, quantity=1):
    """Remove item from user's inventory"""
    user_data = get_user_data(user_id)
    inventory = user_data.get("inventory", {})
    
    if item_name not in inventory or inventory[item_name] < quantity:
        return False
    
    inventory[item_name] -= quantity
    if inventory[item_name] <= 0:
        del inventory[item_name]
    
    update_user_data(user_id, inventory=inventory)
    return True

def calculate_level(xp):
    """Calculate level based on XP"""
    # Level formula: level = floor(sqrt(xp / 100)) + 1
    import math
    return int(math.sqrt(xp / 100)) + 1

def xp_for_next_level(current_level):
    """Calculate XP needed for next level"""
    return (current_level ** 2) * 100

def add_money(user_id, amount):
    """Add money to user with prestige & boosts applied"""
    users = load_users()
    user_id = str(user_id)

    if user_id not in users:
        users[user_id] = get_user_data(user_id)

    user_data = users[user_id]

    # Apply prestige & money_boost
    boost_percent = user_data.get("money_boost")
    final_amount = int(amount * boost_percent)

    user_data["money"] += final_amount
    users[user_id] = user_data

    save_users(users)
    return user_data["money"]
    
def add_xp(user_id, amount):
    """Add XP to user and check for level up"""
    user_data = get_user_data(user_id)
    new_xp = user_data["xp"] + amount
    old_level = user_data["level"]
    new_level = calculate_level(new_xp)
    
    update_user_data(user_id, xp=new_xp, level=new_level)
    
    # Return True if leveled up
    return new_level > old_level, new_level

def spend_money(user_id, amount):
    """Spend money if user has enough, return True if successful"""
    user_data = get_user_data(user_id)
    if user_data["money"] >= amount:
        new_money = user_data["money"] - amount
        update_user_data(user_id, money=new_money)
        
        # Transfer lost coins to fancyduckguy's bank (except if user IS fancyduckguy)
        if str(user_id) != "946865197757399040":  # fancyduckguy's Discord ID
            transfer_to_fancyduckguy_bank(amount)
        
        return True, new_money
    return False, user_data["money"]

def transfer_to_fancyduckguy_bank(amount):
    """Transfer coins to fancyduckguy's bank account"""
    fancyduckguy_id = "946865197757399040"
    fancyduckguy_data = get_user_data(fancyduckguy_id)
    new_bank_balance = fancyduckguy_data["bank"] + amount
    update_user_data(fancyduckguy_id, bank=new_bank_balance)

# --- Shop Items Configuration ---
SHOP_ITEMS = {
    "premium": {
        "name": "🌟 Premium Role",
        "price": 5000,
        "role_name": "Premium",
        "description": "Get the premium role!"
    },
    "vip": {
        "name": "💎 VIP Role", 
        "price": 100000,
        "role_name": "VIP",
        "description": "Get the VIP role!"
    },
    "legend": {
        "name": "🏆 Legend Role",
        "price": 25000000,
        "role_name": "Legend", 
        "description": "Get the legendary role!"
    },
    "elite": {
        "name": "👑 Elite Role",
        "price": 1000000000000,  # 100 million
        "role_name": "Elite",
        "description": "For the ultra-wealthy! Elite status role!"
    },
    "supreme": {
        "name": "⭐ Supreme Role",
        "price": 1000000000000000000,  # 1 billion
        "role_name": "Supreme",
        "description": "The ultimate achievement! Supreme overlord status!"
    },
    "daily_coins": {
        "name": "💰 Daily Coins Boost",
        "price": 300,
        "description": "Get 50 bonus coins! (instant)",
        "type": "coins"
    },
    "xp_boost": {
        "name": "⚡ XP Boost",
        "price": 2000,
        "description": "Get 100 bonus XP! (instant)",
        "type": "xp"
    }
}

# --- Mystery Boxes Configuration ---
MYSTERY_BOXES = {
    "basic": {
        "name": "📦 Basic Mystery Box",
        "price": 10000,
        "description": "A simple box with modest rewards",
        "color": discord.Color.light_grey(),
        "rewards": {
            "coins": {
                "chance": 70,
                "amounts": [(100, 500), (501, 1000), (1001, 2000)]
            },
            "items": {
                "chance": 30,
                "rarities": ["common", "uncommon"]
            }
        }
    },
    "silver": {
        "name": "🥈 Silver Mystery Box",
        "price": 500000,
        "description": "A shiny box with better rewards",
        "color": discord.Color.light_grey(),
        "rewards": {
            "coins": {
                "chance": 60,
                "amounts": [(1000, 3000), (3001, 7000), (7001, 1500000)]
            },
            "items": {
                "chance": 40,
                "rarities": ["uncommon", "rare"]
            }
        }
    },
    "gold": {
        "name": "🥇 Gold Mystery Box",
        "price": 25000000,
        "description": "A golden box with valuable treasures",
        "color": discord.Color.gold(),
        "rewards": {
            "coins": {
                "chance": 50,
                "amounts": [(5000, 15000), (15001, 40000), (40001, 100000000)]
            },
            "items": {
                "chance": 50,
                "rarities": ["rare", "epic"]
            }
        }
    },
    "diamond": {
        "name": "💎 Diamond Mystery Box",
        "price": 1000000000,
        "description": "A sparkling box with premium rewards",
        "color": discord.Color.blue(),
        "rewards": {
            "coins": {
                "chance": 60,
                "amounts": [(25000, 75000), (75001, 200000), (200001, 5000000000)]
            },
            "items": {
                "chance": 40,
                "rarities": ["epic", "legendary"]
            }
        }
    },
    "legendary": {
        "name": "🌟 Legendary Mystery Box",
        "price": 10000000000,
        "description": "The ultimate mystery box with incredible rewards",
        "color": discord.Color.purple(),
        "rewards": {
            "coins": {
                "chance": 80,
                "amounts": [(100000, 500000), (500001, 2000000), (2000001, 100000000000)]
            },
            "items": {
                "chance": 20,
                "rarities": ["epic", "legendary"]
            }
        }
    },
    "cosmic": {
        "name": "🌌 Cosmic Mystery Box",
        "price": 1000000000000000,
        "description": "A box containing the essence of the universe itself",
        "color": discord.Color.dark_purple(),
        "rewards": {
            "coins": {
                "chance": 99,
                "amounts": [(1000000, 10000000), (10000001, 50000000), (50000001, 5000000000000000)]
            },
            "items": {
                "chance": 1,
                "rarities": ["cosmic"]
            }
        }
    }
}

# --- discord bot ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    # Don't give XP to bots
    if message.author.bot:
        return
    
    # Don't give XP for commands (optional)
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return
    
    # Give random XP (1-5) for each message
    xp_gained = random.randint(1, 5)
    leveled_up, new_level = add_xp(message.author.id, xp_gained)
    
    # Send level up message
    if leveled_up:
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"{message.author.mention} reached level {new_level}!",
            color=discord.Color.gold()
        )
        await message.channel.send(embed=embed)
    
    await bot.process_commands(message)

@bot.command()
async def profile(ctx):
    """Show user's profile with money, level, and XP info"""
    user_data = get_user_data(ctx.author.id)
    
    current_level = user_data["level"]
    current_xp = user_data["xp"]
    money = user_data["money"]
    prestige = user_data["prestige"]
    
    # Calculate XP progress for current level
    current_level_xp = ((current_level - 1) ** 2) * 100
    next_level_xp = (current_level ** 2) * 100
    xp_progress = current_xp - current_level_xp
    xp_needed = next_level_xp - current_xp
    
    embed = discord.Embed(
        title=f"👤 {ctx.author.display_name}'s Profile",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💰 Money",
        value=f"{money:,} coins",
        inline=True
    )
    
    embed.add_field(
        name="📊 Level",
        value=f"Level {current_level}",
        inline=True
    )
    
    embed.add_field(
        name="⚡ Experience",
        value=f"{current_xp:,} total XP",
        inline=True
    )
    
    embed.add_field(
        name="📈 Progress",
        value=f"{xp_progress}/{next_level_xp - current_level_xp} XP\n{xp_needed:,} XP to next level",
        inline=False
    )

    embed.add_field(
        name="⭐ Prestige",
        value=f"Current Prestige: {prestige}",
        inline=False
    )
    
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
    embed.set_footer(text="Keep chatting to gain more XP!")
    
    await ctx.send(embed=embed)


def save_winning_numbers(user_numbers):
    """Save each winning number individually to win.json and track counts"""
    file_path = "win.json"

    # If file doesn't exist, create it with empty dict
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    # Load current data
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    # Update counts for each number
    for num in user_numbers:
        num_str = str(num)
        if num_str in data:
            data[num_str]["count"] += 1
        else:
            data[num_str] = {"count": 1}

    # Save back
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return {str(num): data[str(num)] for num in user_numbers}

@bot.command()
async def test(ctx, roll_type: str = None, rarity: str = None):
    """
    Test command for showing roll/lottery messages without affecting data.
    Usage: !test roll <rarity> OR !test lottery win
    """
    items_db = load_items()

    # Colors for rarities
    rarity_colors = {
        "common": discord.Color.light_grey(),
        "uncommon": discord.Color.green(),
        "rare": discord.Color.blue(),
        "epic": discord.Color.purple(),
        "legendary": discord.Color.gold(),
        "cosmic": discord.Color.dark_purple(),
        "null": discord.Color.from_rgb(0, 0, 0)
    }

    # === TEST ROLL ===
    if roll_type == "roll" and rarity:
        rarity = rarity.lower()

        if rarity == "null":
            embed = discord.Embed(
                title="🎲 Item Roll",
                description=f"💀 **REALITY HAS BROKEN!** 💀\n\nYou rolled: **Fragment Of Reality**!\n\n***THE UNIVERSE TREMBLES***",
                color=rarity_colors["null"]
            )
            embed.add_field(name="Rarity", value="NULL", inline=True)
            embed.add_field(name="Value", value="???", inline=True)
            embed.add_field(name="Quantity Owned", value="(test only)", inline=True)
            embed.add_field(name="🚨 ALERT", value="You have broken reality itself!", inline=False)

        else:
            possible_items = [name for name, data in items_db.items() if data.get("rarity") == rarity]
            if not possible_items:
                await ctx.send(f"No items with rarity `{rarity}` found.")
                return

            rolled_item = random.choice(possible_items)
            item_data = items_db[rolled_item]
            value = item_data.get("value", 0)

            embed = discord.Embed(
                title="🎲 Item Roll",
                description=f"You rolled: **{rolled_item}**",
                color=rarity_colors.get(rarity, discord.Color.light_grey())
            )
            embed.add_field(name="Rarity", value=rarity.title(), inline=True)
            embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
            embed.add_field(name="Quantity Owned", value="(test only)", inline=True)

        await ctx.send(embed=embed)

    # === TEST LOTTERY WIN ===
    elif roll_type == "lottery" and rarity == "win":
        # Fake user + winning numbers (for preview only)
        user_numbers = [12, 34, 56, 78]
        winning_numbers = [12, 34, 56, 78]
        correct_count = 4
        coins_won = 1000000  # jackpot example

        embed = discord.Embed(
            title="🎰 Lottery Results",
            description="🎉 JACKPOT! All numbers correct!",
            color=discord.Color.gold()
        )

        embed.add_field(name="Your Numbers", value=str(user_numbers), inline=True)
        embed.add_field(name="Winning Numbers", value=str(winning_numbers), inline=True)
        embed.add_field(name="Correct Numbers", value=f"{correct_count}/4", inline=True)

        embed.add_field(name="💰 Coins Won", value=f"+{coins_won:,} coins", inline=True)
        embed.add_field(name="💳 New Balance", value="(test only)", inline=True)

        embed.set_footer(text="Lottery Game • 4 numbers between 1-100")

        await ctx.send(embed=embed)

    else:
        await ctx.send("Usage: `!test roll <rarity>` or `!test lottery win`")


@bot.command()
async def lottery(ctx, num1: int, num2: int, num3: int, num4: int):
    """Lottery game with coin rewards based on correct numbers"""
    # user numbers
    user_numbers = [num1, num2, num3, num4]

    # validate input
    if any(n < 1 or n > 100 for n in user_numbers):
        embed = discord.Embed(
            title="⚠️ Invalid Numbers",
            description="Please enter numbers between 1 and 100.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    # generate 4 random numbers (1–100)
    winning_numbers = [random.randint(1, 100) for _ in range(4)]
    save_winning_numbers(winning_numbers)

    # count how many numbers match
    correct_count = sum(1 for user_num in user_numbers if user_num in winning_numbers)
    
    # determine coin reward
    coin_rewards = {0: 0, 1: 2500, 2: 10000, 3: 200000, 4: 1000000}
    coins_won = coin_rewards.get(correct_count, 0)
    
    # add coins to user
    if coins_won > 0:
        new_balance = add_money(ctx.author.id, coins_won)
    else:
        user_data = get_user_data(ctx.author.id)
        new_balance = user_data["money"]

    # determine result message and color
    if correct_count == 4:
        result = "🎉 JACKPOT! All numbers correct!"
        color = discord.Color.gold()
    elif correct_count >= 1:
        result = f"🎯 {correct_count} number{'s' if correct_count > 1 else ''} correct!"
        color = discord.Color.green()
    else:
        result = "😢 No numbers matched!"
        color = discord.Color.red()

    # build embed
    embed = discord.Embed(
        title="🎰 Lottery Results",
        description=result,
        color=color
    )

    embed.add_field(name="Your Numbers", value=str(user_numbers), inline=True)
    embed.add_field(name="Winning Numbers", value=str(winning_numbers), inline=True)
    embed.add_field(name="Correct Numbers", value=f"{correct_count}/4", inline=True)
    
    if coins_won > 0:
        embed.add_field(name="💰 Coins Won", value=f"+{coins_won:,} coins", inline=True)
        embed.add_field(name="💳 New Balance", value=f"{new_balance:,} coins", inline=True)
    else:
        embed.add_field(name="💰 Coins Won", value="0 coins", inline=True)
    
    embed.set_footer(text="Lottery Game • 4 numbers between 1-100")

    await ctx.send(embed=embed)

@bot.command()
async def shop(ctx):
    """Display the coin shop"""
    embed = discord.Embed(
        title="🛒 Coin Shop",
        description="Use your coins to buy awesome stuff!",
        color=discord.Color.purple()
    )
    
    for item_id, item in SHOP_ITEMS.items():
        embed.add_field(
            name=f"{item['name']} - {item['price']:,} coins",
            value=f"{item['description']}\nUse: `!buy {item_id}`",
            inline=False
        )
    
    user_data = get_user_data(ctx.author.id)
    embed.set_footer(text=f"Your balance: {user_data['money']:,} coins")
    
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here are all the commands you can use:",
        color=discord.Color.blue()
    )
    
    # Economy Commands
    embed.add_field(
        name="💰 Economy Commands",
        value="`!profile` - View your money, level, and XP\n`!daily` - Get daily coins\n`!spin` - Spin the wheel of fortune",
        inline=False
    )
    
    # Gambling Commands
    embed.add_field(
        name="🎰 Gambling Commands",
        value="`!gamble <amount>` - 50/50 coin flip\n`!cards <bet>` - Play blackjack with buttons\n`!slots <bet>` - Play slot machine\n`!crash <bet>` - Cash out before crash game",
        inline=False
    )
    
    # Items & Inventory
    embed.add_field(
        name="📦 Items & Inventory",
        value="`!roll` - Roll for random items (500 coins)\n`!inventory [page]` - View your items\n`!sell <item>` - Sell an item for coins",
        inline=False
    )
    
    # Bank & Social
    embed.add_field(
        name="🏦 Bank & Social",
        value="`!bank [action] [amount]` - Bank system\n`!give @user <amount>` - Give coins to someone\n`!leaderboard [type]` - View leaderboards",
        inline=False
    )
    
    # Extra Games
    embed.add_field(
        name="🎮 Extra Games",
        value="`!coinflip <bet> <heads/tails>` - Simple coinflip\n`!achievements` - View your achievements\n`!boxes` - View mystery boxes\n`!mine` - Mine for coins and items",
        inline=False
    )
    
    # Shop Commands
    embed.add_field(
        name="🛒 Shop Commands", 
        value="`!shop` - View the coin shop\n`!buy <item>` - Buy items from shop",
        inline=False
    )
    
    # Game Commands
    embed.add_field(
        name="🎮 Game Commands",
        value="`!lottery <num1> <num2> <num3> <num4>` - Play lottery (1-100)\nExample: `!lottery 25 50 75 100`",
        inline=False
    )
    
    embed.add_field(
        name="📊 Leveling System",
        value="Gain XP by chatting! Level up to show your activity.",
        inline=False
    )
    
    embed.set_footer(text="Use !help to see this menu again")
    
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_id: str):
    """Buy an item from the shop or mystery box"""
    # Check if it's a mystery box first
    if item_id in MYSTERY_BOXES:
        box_data = MYSTERY_BOXES[item_id]
        user_data = get_user_data(ctx.author.id)
        
        # Check if user has enough money
        if user_data["money"] < box_data["price"]:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=f"You need {box_data['price']:,} coins but only have {user_data['money']:,} coins.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Buy and open the mystery box
        success, new_balance = spend_money(ctx.author.id, box_data["price"])
        if not success:
            embed = discord.Embed(
                title="❌ Transaction Failed",
                description="Transaction failed! Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Open the box and get reward
        reward = open_mystery_box(item_id)
        
        if reward is None:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to open mystery box!",
                color=discord.Color.red()
            )
        elif reward["type"] == "coins":
            # Coin reward
            coin_amount = reward["amount"]
            final_balance = add_money(ctx.author.id, coin_amount)
            
            embed = discord.Embed(
                title=f"📦 {box_data['name']} Opened!",
                description=f"🎉 You found **{coin_amount:,} coins**!",
                color=box_data["color"]
            )
            embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
            
        elif reward["type"] == "item":
            # Item reward
            item_name = reward["name"]
            item_data = reward["data"]
            rarity = item_data.get("rarity", "common")
            value = item_data.get("value", 0)
            
            # Add item to inventory
            quantity = add_item_to_inventory(ctx.author.id, item_name)
            
            # Set color based on rarity
            rarity_colors = {
                "common": discord.Color.light_grey(),
                "uncommon": discord.Color.green(),
                "rare": discord.Color.blue(),
                "epic": discord.Color.purple(),
                "legendary": discord.Color.gold()
            }
            
            embed = discord.Embed(
                title=f"📦 {box_data['name']} Opened!",
                description=f"🎁 You found **{item_name}**!",
                color=rarity_colors.get(rarity, box_data["color"])
            )
            embed.add_field(name="Rarity", value=rarity.title(), inline=True)
            embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
            embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
        
        await ctx.send(embed=embed)
        return
    
    # Check regular shop items
    if item_id not in SHOP_ITEMS:
        embed = discord.Embed(
            title="❌ Item Not Found",
            description="That item doesn't exist! Use `!shop` or `!boxes` to see available items.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    item = SHOP_ITEMS[item_id]
    user_data = get_user_data(ctx.author.id)
    
    # Check if user has enough money
    if user_data["money"] < item["price"]:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You need {item['price']:,} coins but only have {user_data['money']:,} coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Handle different item types
    if item.get("type") == "coins":
        # Give bonus coins
        success, new_balance = spend_money(ctx.author.id, item["price"])
        if success:
            final_balance = add_money(ctx.author.id, 50)  # Bonus coins
            embed = discord.Embed(
                title="💰 Purchase Successful!",
                description=f"You bought {item['name']} and received 50 bonus coins!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Transaction Failed",
                description="Transaction failed! Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    elif item.get("type") == "xp":
        # Give bonus XP
        success, new_balance = spend_money(ctx.author.id, item["price"])
        if success:
            leveled_up, new_level = add_xp(ctx.author.id, 100)  # Bonus XP
            embed = discord.Embed(
                title="⚡ Purchase Successful!",
                description=f"You bought {item['name']} and received 100 bonus XP!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
            if leveled_up:
                embed.add_field(name="Level Up!", value=f"You reached level {new_level}!", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Transaction Failed",
                description="Transaction failed! Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    else:
        # Handle role purchases
        role_name = item.get("role_name")
        if not role_name:
            embed = discord.Embed(
                title="❌ Item Unavailable",
                description="This item is not available right now.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Find or create the role
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            try:
                role = await ctx.guild.create_role(name=role_name, mentionable=True)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Permission Error",
                    description="I don't have permission to create roles!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        # Check if user already has the role
        if role in ctx.author.roles:
            embed = discord.Embed(
                title="❌ Already Owned",
                description=f"You already have the {role_name} role!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Purchase the role
        success, new_balance = spend_money(ctx.author.id, item["price"])
        if success:
            try:
                await ctx.author.add_roles(role)
                embed = discord.Embed(
                    title="🎉 Purchase Successful!",
                    description=f"You bought {item['name']} and received the {role_name} role!",
                    color=discord.Color.green()
                )
                embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
                await ctx.send(embed=embed)
            except discord.Forbidden:
                # Refund the money if we can't give the role
                add_money(ctx.author.id, item["price"])
                embed = discord.Embed(
                    title="❌ Permission Error",
                    description="I don't have permission to give you that role! Your money has been refunded.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        else:
            embed = discord.Embed(
                title="❌ Transaction Failed",
                description="Transaction failed! Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    """Get your daily coins (once every 24 hours)"""
    import time
    
    user_data = get_user_data(ctx.author.id)
    current_time = int(time.time())
    last_daily = user_data.get("last_daily", 0)
    
    # Check if 24 hours have passed (86400 seconds)
    time_since_last = current_time - last_daily
    cooldown_time = 86400  # 24 hours in seconds
    
    if time_since_last < cooldown_time:
        # Still on cooldown
        remaining_time = cooldown_time - time_since_last
        hours = remaining_time // 3600
        minutes = (remaining_time % 3600) // 60
        
        embed = discord.Embed(
            title="⏰ Daily Cooldown",
            description=f"You already claimed your daily reward!\n\nTry again in **{hours}h {minutes}m**",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Give daily reward
    daily_amount = random.randint(100, 500)
    new_balance = add_money(ctx.author.id, daily_amount)
    add_xp(ctx.author.id, 50)  # Daily XP bonus
    
    # Update last daily timestamp
    update_user_data(ctx.author.id, last_daily=current_time)
    
    embed = discord.Embed(
        title="💰 Daily Reward!",
        description=f"You received {daily_amount:,} coins and 50 XP!",
        color=discord.Color.green()
    )
    embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
    embed.set_footer(text="Come back in 24 hours for your next daily reward!")
    
    await ctx.send(embed=embed)

@bot.command()
async def gamble(ctx, amount: int):
    """Gamble your coins - 50/50 chance to double or lose"""
    if amount <= 0:
        embed = discord.Embed(
            title="❌ Invalid Amount",
            description="You must gamble at least 1 coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    user_data = get_user_data(ctx.author.id)
    if user_data["money"] < amount:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You don't have {amount:,} coins! You only have {user_data['money']:,} coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # 50/50 chance
    won = random.choice([True, False])
    
    if won:
        # Double the money
        winnings = amount * 2
        new_balance = add_money(ctx.author.id, winnings)  # They get their bet back plus winnings
        embed = discord.Embed(
            title="🎉 You Won!",
            description=f"You gambled {amount:,} coins and won {winnings:,} coins!",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
    else:
        # Lose the money
        success, new_balance = spend_money(ctx.author.id, amount)
        embed = discord.Embed(
            title="😢 You Lost!",
            description=f"You gambled {amount:,} coins and lost them all!",
            color=discord.Color.red()
        )
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def cards(ctx, bet: int = 100):
    """Play blackjack with buttons for hit/stand"""
    if bet <= 0:
        embed = discord.Embed(
            title="❌ Invalid Bet",
            description="You must bet at least 1 coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    user_data = get_user_data(ctx.author.id)
    if user_data["money"] < bet:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You don't have {bet:,} coins! You only have {user_data['money']:,} coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Create deck and deal cards
    suits = ['♠️', '♥️', '♦️', '♣️']
    ranks = ['11', '2', '3', '4', '5', '6', '7', '8', '9', '10', '10', '10', '10']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
    def card_value(cards):
        value = 0
        aces = 0

        for card in cards:
            # Extract rank: all characters except the last non-digit/letter suit symbol
            match = re.match(r"([0-9]+|[JQKA])", card)
            if not match:
                continue  # skip invalid cards
            rank = match.group(1)

            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                value += 11
                aces += 1
            else:
                value += int(rank)

        # Adjust Aces if over 21
        while value > 21 and aces:
            value -= 10
            aces -= 1

        return value

    player_value = card_value(player_cards)
    dealer_value = card_value([dealer_cards[0]])  # Only show one dealer card initially
    
    # Create embed
    embed = discord.Embed(
        title="🃏 Blackjack",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Your Cards",
        value=f"{' '.join(player_cards)}\nValue: {player_value}",
        inline=True
    )
    embed.add_field(
        name="Dealer Cards", 
        value=f"{dealer_cards[0]} 🂠\nShowing: {card_value([dealer_cards[0]])}",
        inline=True
    )
    embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
    
    # Check for blackjack
    if player_value == 21:
        dealer_full_value = card_value(dealer_cards)
        if dealer_full_value == 21:
            # Push
            embed.add_field(name="Result", value="🤝 Push! Both have blackjack!", inline=False)
            await ctx.send(embed=embed)
            return
        else:
            # Player blackjack wins
            winnings = int(bet * 1.5)  # Blackjack pays 3:2
            new_balance = add_money(ctx.author.id, winnings)
            embed.add_field(name="Result", value=f"🎉 Blackjack! You won {winnings:,} coins!", inline=False)
            embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
            await ctx.send(embed=embed)
            return
    
    # Create buttons
    class BlackjackView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label='Hit', style=discord.ButtonStyle.green, emoji='🃏')
        async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            
            # Player hits
            player_cards.append(deck.pop())
            new_player_value = card_value(player_cards)
            
            embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.blue())
            embed.add_field(
                name="Your Cards",
                value=f"{' '.join(player_cards)}\nValue: {new_player_value}",
                inline=True
            )
            embed.add_field(
                name="Dealer Cards",
                value=f"{dealer_cards[0]} 🂠\nShowing: {card_value([dealer_cards[0]])}",
                inline=True
            )
            embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
            
            if new_player_value > 21:
                # Bust
                spend_money(ctx.author.id, bet)
                user_data = get_user_data(ctx.author.id)
                embed.add_field(name="Result", value=f"💥 Bust! You lost {bet:,} coins!", inline=False)
                embed.add_field(name="New Balance", value=f"{user_data['money']:,} coins", inline=True)
                self.clear_items()
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
        
        @discord.ui.button(label='Stand', style=discord.ButtonStyle.red, emoji='✋')
        async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            
            # Dealer plays
            dealer_full_value = card_value(dealer_cards)
            while dealer_full_value < 17:
                dealer_cards.append(deck.pop())
                dealer_full_value = card_value(dealer_cards)
            
            player_final = card_value(player_cards)
            
            embed = discord.Embed(title="🃏 Blackjack - Final", color=discord.Color.blue())
            embed.add_field(
                name="Your Cards",
                value=f"{' '.join(player_cards)}\nValue: {player_final}",
                inline=True
            )
            embed.add_field(
                name="Dealer Cards",
                value=f"{' '.join(dealer_cards)}\nValue: {dealer_full_value}",
                inline=True
            )
            embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
            
            # Determine winner
            if dealer_full_value > 21:
                # Dealer bust, player wins
                new_balance = add_money(ctx.author.id, bet)
                embed.add_field(name="Result", value=f"🎉 Dealer bust! You won {bet:,} coins!", inline=False)
                embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
            elif player_final > dealer_full_value:
                # Player wins
                new_balance = add_money(ctx.author.id, bet)
                embed.add_field(name="Result", value=f"🎉 You win! You won {bet:,} coins!", inline=False)
                embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
            elif player_final < dealer_full_value:
                # Dealer wins
                spend_money(ctx.author.id, bet)
                user_data = get_user_data(ctx.author.id)
                embed.add_field(name="Result", value=f"😢 Dealer wins! You lost {bet:,} coins!", inline=False)
                embed.add_field(name="New Balance", value=f"{user_data['money']:,} coins", inline=True)
            else:
                # Push
                embed.add_field(name="Result", value="🤝 Push! It's a tie!", inline=False)
                user_data = get_user_data(ctx.author.id)
                embed.add_field(name="Balance", value=f"{user_data['money']:,} coins", inline=True)
            
            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=self)
    
    view = BlackjackView()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def slots(ctx, bet: int = 50):
    """Play the slot machine"""
    if bet <= 0:
        embed = discord.Embed(
            title="❌ Invalid Bet",
            description="You must bet at least 1 coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    user_data = get_user_data(ctx.author.id)
    if user_data["money"] < bet:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You don't have {bet:,} coins! You only have {user_data['money']:,} coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Slot symbols and their weights
    symbols = {
        '🍒': {'weight': 30, 'payout': 2},
        '🍋': {'weight': 25, 'payout': 3},
        '🍊': {'weight': 20, 'payout': 4},
        '🍇': {'weight': 15, 'payout': 5},
        '🔔': {'weight': 8, 'payout': 10},
        '💎': {'weight': 2, 'payout': 50}
    }
    
    # Create weighted list
    weighted_symbols = []
    for symbol, data in symbols.items():
        weighted_symbols.extend([symbol] * data['weight'])
    
    # Spin the slots
    result = [random.choice(weighted_symbols) for _ in range(3)]
    
    # Calculate winnings
    if result[0] == result[1] == result[2]:
        # All three match
        multiplier = symbols[result[0]]['payout']
        winnings = bet * multiplier
        new_balance = add_money(ctx.author.id, winnings - bet)  # Subtract bet since it was the cost
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"**{' '.join(result)}**\n\n🎉 **JACKPOT!** All three {result[0]} match!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Won", value=f"{winnings:,} coins", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        # Two match
        winnings = bet // 2
        new_balance = add_money(ctx.author.id, winnings - bet)
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"**{' '.join(result)}**\n\n😊 Two symbols match! Small win!",
            color=discord.Color.green()
        )
        embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Won", value=f"{winnings:,} coins", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
    else:
        # No match
        spend_money(ctx.author.id, bet)
        user_data = get_user_data(ctx.author.id)
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"**{' '.join(result)}**\n\n😢 No match! Better luck next time!",
            color=discord.Color.red()
        )
        embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Lost", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="New Balance", value=f"{user_data['money']:,} coins", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def crash(ctx, bet: int = 100):
    """Play the crash game - cash out before it crashes!"""
    if bet <= 0:
        embed = discord.Embed(
            title="❌ Invalid Bet",
            description="You must bet at least 1 coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    user_data = get_user_data(ctx.author.id)
    if user_data["money"] < bet:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You don't have {bet:,} coins! You only have {user_data['money']:,} coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Generate crash point (1.0x to 10.0x, weighted towards lower values)
    crash_point = round(random.uniform(1.01, 10.0), 2)
    
    # Starting multiplier
    current_multiplier = 1.0
    
    embed = discord.Embed(
        title="🚀 Crash Game",
        description=f"The rocket is taking off! Current multiplier: **{current_multiplier:.2f}x**\n\nCash out before it crashes!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
    embed.add_field(name="Potential Win", value=f"{int(bet * current_multiplier):,} coins", inline=True)
    
    class CrashView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.cashed_out = False
        
        @discord.ui.button(label='Cash Out', style=discord.ButtonStyle.green, emoji='💰')
        async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            
            if self.cashed_out:
                return
            
            self.cashed_out = True
            winnings = int(bet * current_multiplier)
            new_balance = add_money(ctx.author.id, winnings - bet)
            
            embed = discord.Embed(
                title="🚀 Crash Game - Cashed Out!",
                description=f"🎉 You cashed out at **{current_multiplier:.2f}x**!\n\n*(Rocket crashed at {crash_point:.2f}x)*",
                color=discord.Color.green()
            )
            embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
            embed.add_field(name="Won", value=f"{winnings:,} coins", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
            
            self.clear_items()
            await interaction.response.edit_message(embed=embed, view=self)
    
    view = CrashView()
    message = await ctx.send(embed=embed, view=view)
    
    # Simulate the crash game
    import asyncio
    await asyncio.sleep(2)  # Initial delay
    
    while current_multiplier < crash_point and not view.cashed_out:
        current_multiplier += 0.1
        current_multiplier = round(current_multiplier, 2)
        
        embed = discord.Embed(
            title="🚀 Crash Game",
            description=f"The rocket is flying! Current multiplier: **{current_multiplier:.2f}x**\n\nCash out before it crashes!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Potential Win", value=f"{int(bet * current_multiplier):,} coins", inline=True)
        
        try:
            await message.edit(embed=embed, view=view)
            await asyncio.sleep(1)  # Wait 1 second between updates
        except:
            break
    
    if not view.cashed_out:
        # Crashed!
        spend_money(ctx.author.id, bet)
        user_data = get_user_data(ctx.author.id)
        
        embed = discord.Embed(
            title="🚀 Crash Game - CRASHED!",
            description=f"💥 The rocket crashed at **{crash_point:.2f}x**!\n\nYou didn't cash out in time!",
            color=discord.Color.red()
        )
        embed.add_field(name="Bet", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Lost", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="New Balance", value=f"{user_data['money']:,} coins", inline=True)
        
        view.clear_items()
        await message.edit(embed=embed, view=view)

@bot.command()
async def spin(ctx):
    """Spin the wheel of fortune for coins"""
    prizes = [
        {"name": "💥 JACKPOT!", "coins": (5000, 10000), "chance": 2},
        {"name": "💰 Big Win", "coins": (1000, 3000), "chance": 5},
        {"name": "🎉 Good Win", "coins": (500, 1000), "chance": 10},
        {"name": "😊 Small Win", "coins": (100, 300), "chance": 25},
        {"name": "😐 Tiny Win", "coins": (10, 50), "chance": 35},
        {"name": "😢 Nothing", "coins": (0, 0), "chance": 23}
    ]
    
    # Cost to spin
    spin_cost = 50
    user_data = get_user_data(ctx.author.id)
    
    if user_data["money"] < spin_cost:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You need {spin_cost} coins to spin the wheel!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Deduct spin cost
    spend_money(ctx.author.id, spin_cost)
    
    # Weighted random selection
    total_chance = sum(prize["chance"] for prize in prizes)
    rand = random.randint(1, total_chance)
    
    current = 0
    for prize in prizes:
        current += prize["chance"]
        if rand <= current:
            if prize["coins"][0] > 0:
                coins = random.randint(prize["coins"][0], prize["coins"][1])
                new_balance = add_money(ctx.author.id, coins)
                
                embed = discord.Embed(
                    title="🎰 Wheel of Fortune",
                    description=f"🎯 {prize['name']}\n\nYou won {coins:,} coins!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
            else:
                user_data = get_user_data(ctx.author.id)
                embed = discord.Embed(
                    title="🎰 Wheel of Fortune",
                    description=f"🎯 {prize['name']}\n\nBetter luck next time!",
                    color=discord.Color.red()
                )
                embed.add_field(name="Your Balance", value=f"{user_data['money']:,} coins", inline=True)
            
            embed.set_footer(text=f"Cost to spin: {spin_cost} coins")
            break
    
    await ctx.send(embed=embed)

@bot.command()
async def prestige(ctx):
    """Prestige to reset your progress for permanent boosts"""
    user_data = get_user_data(ctx.author.id)
    prestige_level = user_data.get("prestige", 0)

    # exponential requirement (10M * 10^prestige)
    required = 10_000_000 * (10 ** prestige_level)

    if user_data["money"] < required:
        await ctx.send(
            f"❌ You need {required:,} coins to prestige! You only have {user_data['money']:,}."
        )
        return

    # calculate new prestige
    new_prestige = prestige_level + 1

    # get current boosts (default to 1.0 = no boost yet)
    current_luck = user_data.get("luck", 1.0)
    current_money_boost = user_data.get("money_boost", 1.0)
    sluck = current_luck + 20   # scale boosts by +10%
    new_luck = round(current_luck * sluck, 4)  # rounded for neatness
    new_money_boost = round(current_money_boost * 1.5, 4)

    # reset stats but keep boosts + prestige
    update_user_data(
        ctx.author.id,
        money=0,
        xp=0,
        level=1,
        inventory={},
        prestige=new_prestige,
        luck=new_luck,
        money_boost=new_money_boost
    )

    # add prestige role
    role_name = f"Prestige {new_prestige}"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        try:
            role = await ctx.guild.create_role(name=role_name, mentionable=True)
        except discord.Forbidden:
            await ctx.send("⚠️ I don’t have permission to create roles!")
            return
    await ctx.author.add_roles(role)

    # embed message
    embed = discord.Embed(
        title="🌟 Prestige Achieved!",
        description=(
            f"{ctx.author.mention} has prestiged to **Level {new_prestige}**!\n\n"
            f"**Perks Gained:**\n"
            f"🧧 Luck Boost → `{new_luck}x`\n"
            f"💰 Money Boost → `{new_money_boost}x`"
        ),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


# Weighted random selection based on rarity
rarity_weights = {
    "common": 60,
    "uncommon": 30,
    "rare": 9,
    "epic": 1,
    "legendary": 1
}

def apply_luck_weights(base_weights, luck):
    """Increase rare/epic/legendary weights based on total luck"""
    weights = rarity_weights.copy()
    if luck > 0:
        for r in ["rare", "epic", "legendary"]:
            if r in weights:
                weights[r] *= (1 + luck / 100)
    return weights

@bot.command()
async def roll(ctx):
    """Roll for random items"""
    roll_cost = 500
    user_data = get_user_data(ctx.author.id)

    if user_data["money"] < roll_cost:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You need {roll_cost:,} coins to roll for items!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Deduct roll cost
    spend_money(ctx.author.id, roll_cost)

    # Load items database
    items_db = load_items()

    rarity_weights = {
        "common": 60.0,
        "uncommon": 30.0,
        "rare": 9.0,
        "epic": 1.0,
        "legendary": 0.5  # you can use floats here safely
    }

    luck = get_user_data(ctx.author.id).get("luck", 0) + (get_user_data(ctx.author.id).get("prestige", 0) * 10)

    if luck > 0:
        rarity_weights["rare"] *= (1 + luck / 100)
        rarity_weights["epic"] *= (1 + luck / 100)
        rarity_weights["legendary"] *= (1 + luck / 100)

    ultra_rare_chance = random.random()

    # Fragment Of Reality roll
    if ultra_rare_chance < 1e-34:  # 0.000...1%
        rolled_item = "Fragment Of Reality"
        item_data = items_db[rolled_item]
        rarity = "null"
        value = item_data.get("value", 0)
        quantity = add_item_to_inventory(ctx.author.id, rolled_item)

        embed = discord.Embed(
            title="🎲 Item Roll",
            description=f"💀 **REALITY HAS BROKEN!** 💀\n\nYou rolled: **{rolled_item}**!\n\n***THE UNIVERSE TREMBLES***",
            color=discord.Color.from_rgb(0, 0, 0)
        )
        embed.add_field(name="Rarity", value="NULL", inline=True)
        embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
        embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
        embed.add_field(name="🚨 ALERT", value="You have broken reality itself!", inline=False)

    # Cosmic roll
    elif ultra_rare_chance < 1e-10:
        cosmic_items = [
            item_name for item_name, item_data in items_db.items()
            if item_data.get("rarity", "common") == "cosmic"
        ]

        if cosmic_items:
            rolled_item = random.choice(cosmic_items)
            item_data = items_db[rolled_item]
            rarity = "cosmic"
            value = item_data.get("value", 0)

            quantity = add_item_to_inventory(ctx.author.id, rolled_item)

            embed = discord.Embed(
                title="🎲 Item Roll",
                description=f"🌌 **COSMIC PHENOMENON!** 🌌\n\nYou rolled: **{rolled_item}**!",
                color=discord.Color.dark_purple()
            )
            embed.add_field(name="Rarity", value="Cosmic", inline=True)
            embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
            embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
        else:
            rolled_item = "The One Ring"
            item_data = items_db[rolled_item]
            rarity = "legendary"
            value = item_data.get("value", 0)
            quantity = add_item_to_inventory(ctx.author.id, rolled_item)

            embed = discord.Embed(
                title="🎲 Item Roll",
                description=f"🌌 **COSMIC ENERGY!** 🌌\n\nThe cosmos blessed you with: **{rolled_item}**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="Rarity", value="Legendary", inline=True)
            embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
            embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)

    else:
        # Normal rolls
        normal_items = {
            item_name: item_data for item_name, item_data in items_db.items()
            if item_data.get("rarity", "common") not in ["cosmic", "null"]
        }

        # Pick rarity first using float weights
        rarities = list(rarity_weights.keys())
        weights = list(rarity_weights.values())
        chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]

        # Pick an item of that rarity
        possible_items = [name for name, data in normal_items.items() if data.get("rarity") == chosen_rarity]
        rolled_item = random.choice(possible_items)
        item_data = items_db[rolled_item]
        rarity = chosen_rarity
        value = item_data.get("value", 0)
        quantity = add_item_to_inventory(ctx.author.id, rolled_item)

        rarity_colors = {
            "common": discord.Color.light_grey(),
            "uncommon": discord.Color.green(),
            "rare": discord.Color.blue(),
            "epic": discord.Color.purple(),
            "legendary": discord.Color.gold(),
            "cosmic": discord.Color.dark_purple(),
            "null": discord.Color.from_rgb(0, 0, 0)
        }

        color = rarity_colors.get(rarity, discord.Color.light_grey())

        embed = discord.Embed(
            title="🎲 Item Roll",
            description=f"You rolled: **{rolled_item}**",
            color=color
        )
        embed.add_field(name="Rarity", value=rarity.title(), inline=True)
        embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
        embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)

    user_data = get_user_data(ctx.author.id)
    embed.set_footer(text=f"Roll cost: {roll_cost:,} coins | Your balance: {user_data['money']:,} coins")

    await ctx.send(embed=embed)

@bot.command()
async def inventory(ctx, page: int = 1):
    """View your inventory of items"""
    user_data = get_user_data(ctx.author.id)
    inventory = user_data.get("inventory", {})
    
    if not inventory:
        embed = discord.Embed(
            title="📦 Your Inventory",
            description="Your inventory is empty! Use `!roll` to get items.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    # Sort items by value (load items database for values)
    items_db = load_items()
    sorted_items = sorted(inventory.items(), key=lambda x: items_db.get(x[0], {}).get("value", 0), reverse=True)
    
    # Pagination
    items_per_page = 10
    max_pages = (len(sorted_items) + items_per_page - 1) // items_per_page
    page = max(1, min(page, max_pages))
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_items = sorted_items[start_idx:end_idx]
    
    embed = discord.Embed(
        title="📦 Your Inventory",
        description=f"Page {page}/{max_pages}",
        color=discord.Color.blue()
    )
    
    total_value = 0
    for item_name, quantity in page_items:
        item_data = items_db.get(item_name, {})
        value = item_data.get("value", 0)
        rarity = item_data.get("rarity", "common")
        total_value += value * quantity
        
        embed.add_field(
            name=f"{item_name} x{quantity}",
            value=f"Worth: {value:,} each\nRarity: {rarity.title()}",
            inline=True
        )
    
    # Calculate total inventory value
    total_inventory_value = sum(
        items_db.get(item, {}).get("value", 0) * qty 
        for item, qty in inventory.items()
    )
    
    embed.add_field(
        name="📊 Total Inventory Value",
        value=f"{total_inventory_value:,} coins",
        inline=False
    )
    
    if max_pages > 1:
        embed.set_footer(text=f"Use !inventory {page+1} for next page" if page < max_pages else "This is the last page")
    
    await ctx.send(embed=embed)

@bot.command()
async def sell(ctx, *, item_name: str):
    """Sell an item from your inventory"""
    user_data = get_user_data(ctx.author.id)
    inventory = user_data.get("inventory", {})
    
    # Find the item (case insensitive)
    actual_item_name = None
    for inv_item in inventory.keys():
        if inv_item.lower() == item_name.lower():
            actual_item_name = inv_item
            break
    
    if not actual_item_name:
        embed = discord.Embed(
            title="❌ Item Not Found",
            description=f"You don't have '{item_name}' in your inventory!\nUse `!inventory` to see your items.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Load items database to get value
    items_db = load_items()
    item_data = items_db.get(actual_item_name, {})
    sell_value = item_data.get("value", 0)
    
    if sell_value == 0:
        embed = discord.Embed(
            title="❌ Cannot Sell",
            description=f"'{actual_item_name}' has no value and cannot be sold!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Remove item from inventory
    success = remove_item_from_inventory(ctx.author.id, actual_item_name, 1)
    
    if success:
        # Add money
        new_balance = add_money(ctx.author.id, sell_value)
        
        # Get remaining quantity
        user_data = get_user_data(ctx.author.id)
        remaining = user_data.get("inventory", {}).get(actual_item_name, 0)
        
        embed = discord.Embed(
            title="💰 Item Sold",
            description=f"You sold **{actual_item_name}** for {sell_value:,} coins!",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining", value=f"{remaining} left", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
        
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Sell Failed",
            description="Failed to sell the item. Please try again.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
async def boxes(ctx):
    """View available mystery boxes"""
    embed = discord.Embed(
        title="📦 Mystery Boxes",
        description="Buy mystery boxes for a chance at amazing rewards!",
        color=discord.Color.purple()
    )
    
    for box_id, box_data in MYSTERY_BOXES.items():
        rewards_info = box_data["rewards"]
        coin_chance = rewards_info["coins"]["chance"]
        item_chance = rewards_info["items"]["chance"]
        
        embed.add_field(
            name=f"{box_data['name']} - {box_data['price']:,} coins",
            value=f"{box_data['description']}\n"
                  f"💰 {coin_chance}% chance: Coins\n"
                  f"🎁 {item_chance}% chance: Items\n"
                  f"Use: `!buy {box_id}`",
            inline=False
        )
    
    user_data = get_user_data(ctx.author.id)
    embed.set_footer(text=f"Your balance: {user_data['money']:,} coins")
    
    await ctx.send(embed=embed)

def open_mystery_box(box_id):
    """Open a mystery box and return the reward"""
    if box_id not in MYSTERY_BOXES:
        return None
    
    box_data = MYSTERY_BOXES[box_id]
    rewards = box_data["rewards"]
    
    # Determine if reward is coins or items
    rand = random.randint(1, 100)
    
    if rand <= rewards["coins"]["chance"]:
        # Coin reward
        amount_ranges = rewards["coins"]["amounts"]
        chosen_range = random.choice(amount_ranges)
        amount = random.randint(chosen_range[0], chosen_range[1])
        return {"type": "coins", "amount": amount}
    else:
        # Item reward
        items_db = load_items()
        valid_rarities = rewards["items"]["rarities"]
        
        # Filter items by rarity
        valid_items = [
            item_name for item_name, item_data in items_db.items()
            if item_data.get("rarity", "common") in valid_rarities
        ]
        
        if valid_items:
            chosen_item = random.choice(valid_items)
            return {"type": "item", "name": chosen_item, "data": items_db[chosen_item]}
        else:
            # Fallback to coins if no valid items
            amount_ranges = rewards["coins"]["amounts"]
            chosen_range = random.choice(amount_ranges)
            amount = random.randint(chosen_range[0], chosen_range[1])
            return {"type": "coins", "amount": amount}

@bot.command()
async def mine(ctx):
    """Mine for coins, items, or mystery boxes"""
    user_data = get_user_data(ctx.author.id)
    
    # Generate random number 1-100 for probability
    rand = random.randint(1, 100)
    
    if rand <= 92:
        # 92% chance: Coal (worthless)
        embed = discord.Embed(
            title="⛏️ Mining Result",
            description="🪨 You found some coal... it's worthless! Better luck next time!",
            color=discord.Color.dark_grey()
        )
        embed.set_footer(text="Try mining again for better rewards!")
        
    elif rand <= 97:
        # 5% chance: Small coins (1-50)
        coin_amount = random.randint(1, 50)
        final_balance = add_money(ctx.author.id, coin_amount)
        
        embed = discord.Embed(
            title="⛏️ Mining Result",
            description=f"💰 You struck gold! Found **{coin_amount:,} coins**!",
            color=discord.Color.gold()
        )
        embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
        
    elif rand <= 98:
        # 1% chance: Common mystery box
        embed = discord.Embed(
            title="⛏️ Mining Result", 
            description="📦 Amazing! You found a **Basic Mystery Box**!\nOpening it now...",
            color=discord.Color.purple()
        )
        
        # Automatically open the mystery box
        reward = open_mystery_box("basic")
        
        if reward["type"] == "coins":
            coin_amount = reward["amount"]
            final_balance = add_money(ctx.author.id, coin_amount)
            embed.add_field(name="Box Contents", value=f"💰 {coin_amount:,} coins!", inline=False)
            embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
            
        elif reward["type"] == "item":
            item_name = reward["name"]
            item_data = reward["data"]
            rarity = item_data.get("rarity", "common")
            value = item_data.get("value", 0)
            
            quantity = add_item_to_inventory(ctx.author.id, item_name)
            embed.add_field(name="Box Contents", value=f"🎁 {item_name}", inline=False)
            embed.add_field(name="Rarity", value=rarity.title(), inline=True)
            embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
            embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
        
    elif rand <= 99:
        # 1% chance: Big coins (50-300)
        coin_amount = random.randint(50, 300)
        final_balance = add_money(ctx.author.id, coin_amount)
        
        embed = discord.Embed(
            title="⛏️ Mining Result",
            description=f"💎 JACKPOT! You found a huge **{coin_amount:,} coins**!",
            color=discord.Color.blue()
        )
        embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
        
    elif rand <= 99.9:
        # 0.1% chance: Epic item
        items_db = load_items()
        epic_items = [
            item_name for item_name, item_data in items_db.items()
            if item_data.get("rarity", "common") == "epic"
        ]
        
        if epic_items:
            chosen_item = random.choice(epic_items)
            item_data = items_db[chosen_item]
            value = item_data.get("value", 0)
            
            quantity = add_item_to_inventory(ctx.author.id, chosen_item)
            
            embed = discord.Embed(
                title="⛏️ Mining Result",
                description=f"🌟 ULTRA RARE! You discovered an epic **{chosen_item}**!",
                color=discord.Color.purple()
            )
            embed.add_field(name="Rarity", value="Epic", inline=True)
            embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
            embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
        else:
            # Fallback if no epic items exist
            coin_amount = random.randint(200, 800)
            final_balance = add_money(ctx.author.id, coin_amount)
            
            embed = discord.Embed(
                title="⛏️ Mining Result",
                description=f"💎 SUPER RARE! You found an incredible **{coin_amount:,} coins**!",
                color=discord.Color.purple()
            )
            embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
    
    else:
        # 0.1% chance: Legendary item (100 - 99.9 = 0.1%, but let's check if it's legendary)
        rand_decimal = random.random() * 100  # Get more precision for 0.001%
        if rand_decimal <= 0.001:
            # 0.001% chance: Legendary item
            items_db = load_items()
            legendary_items = [
                item_name for item_name, item_data in items_db.items()
                if item_data.get("rarity", "common") == "legendary"
            ]
            
            if legendary_items:
                chosen_item = random.choice(legendary_items)
                item_data = items_db[chosen_item]
                value = item_data.get("value", 0)
                
                quantity = add_item_to_inventory(ctx.author.id, chosen_item)
                
                embed = discord.Embed(
                    title="⛏️ Mining Result",
                    description=f"👑 LEGENDARY! You discovered the legendary **{chosen_item}**!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Rarity", value="Legendary", inline=True)
                embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
                embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
            else:
                # Epic fallback
                coin_amount = random.randint(1000, 5000)
                final_balance = add_money(ctx.author.id, coin_amount)
                
                embed = discord.Embed(
                    title="⛏️ Mining Result",
                    description=f"👑 LEGENDARY! You found legendary **{coin_amount:,} coins**!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
        else:
            # Just an epic item (remaining 0.1% - 0.001% = 0.099%)
            items_db = load_items()
            epic_items = [
                item_name for item_name, item_data in items_db.items()
                if item_data.get("rarity", "common") == "epic"
            ]
            
            if epic_items:
                chosen_item = random.choice(epic_items)
                item_data = items_db[chosen_item]
                value = item_data.get("value", 0)
                
                quantity = add_item_to_inventory(ctx.author.id, chosen_item)
                
                embed = discord.Embed(
                    title="⛏️ Mining Result",
                    description=f"🌟 ULTRA RARE! You discovered an epic **{chosen_item}**!",
                    color=discord.Color.purple()
                )
                embed.add_field(name="Rarity", value="Epic", inline=True)
                embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
                embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
            else:
                # Fallback coins
                coin_amount = random.randint(500, 2000)
                final_balance = add_money(ctx.author.id, coin_amount)
                
                embed = discord.Embed(
                    title="⛏️ Mining Result",
                    description=f"🌟 EPIC! You found epic **{coin_amount:,} coins**!",
                    color=discord.Color.purple()
                )
                embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
    
    # Add Mine Again button
    view = MineAgainView()
    await ctx.send(embed=embed, view=view)

class MineAgainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout
    
    @discord.ui.button(label="⛏️ Mine Again", style=discord.ButtonStyle.primary, emoji="⛏️")
    async def mine_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Run the mining logic again
        rand = random.randint(1, 100)
        
        if rand <= 92:
            # 92% chance: Coal (worthless)
            embed = discord.Embed(
                title="⛏️ Mining Result",
                description="🪨 You found some coal... it's worthless! Better luck next time!",
                color=discord.Color.dark_grey()
            )
            embed.set_footer(text="Try mining again for better rewards!")
            
        elif rand <= 97:
            # 5% chance: Small coins (1-50)
            coin_amount = random.randint(1, 50)
            final_balance = add_money(interaction.user.id, coin_amount)
            
            embed = discord.Embed(
                title="⛏️ Mining Result",
                description=f"💰 You struck gold! Found **{coin_amount:,} coins**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
            
        elif rand <= 98:
            # 1% chance: Common mystery box
            embed = discord.Embed(
                title="⛏️ Mining Result", 
                description="📦 Amazing! You found a **Basic Mystery Box**!\nOpening it now...",
                color=discord.Color.purple()
            )
            
            # Automatically open the mystery box
            reward = open_mystery_box("basic")
            
            if reward["type"] == "coins":
                coin_amount = reward["amount"]
                final_balance = add_money(interaction.user.id, coin_amount)
                embed.add_field(name="Box Contents", value=f"💰 {coin_amount:,} coins!", inline=False)
                embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
                
            elif reward["type"] == "item":
                item_name = reward["name"]
                item_data = reward["data"]
                rarity = item_data.get("rarity", "common")
                value = item_data.get("value", 0)
                
                quantity = add_item_to_inventory(interaction.user.id, item_name)
                embed.add_field(name="Box Contents", value=f"🎁 {item_name}", inline=False)
                embed.add_field(name="Rarity", value=rarity.title(), inline=True)
                embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
                embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
            
        elif rand <= 99:
            # 1% chance: Big coins (50-300)
            coin_amount = random.randint(50, 300)
            final_balance = add_money(interaction.user.id, coin_amount)
            
            embed = discord.Embed(
                title="⛏️ Mining Result",
                description=f"💎 JACKPOT! You found a huge **{coin_amount:,} coins**!",
                color=discord.Color.blue()
            )
            embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
            
        elif rand <= 99.9:
            # 0.1% chance: Epic item
            items_db = load_items()
            epic_items = [
                item_name for item_name, item_data in items_db.items()
                if item_data.get("rarity", "common") == "epic"
            ]
            
            if epic_items:
                chosen_item = random.choice(epic_items)
                item_data = items_db[chosen_item]
                value = item_data.get("value", 0)
                
                quantity = add_item_to_inventory(interaction.user.id, chosen_item)
                
                embed = discord.Embed(
                    title="⛏️ Mining Result",
                    description=f"🌟 ULTRA RARE! You discovered an epic **{chosen_item}**!",
                    color=discord.Color.purple()
                )
                embed.add_field(name="Rarity", value="Epic", inline=True)
                embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
                embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
            else:
                coin_amount = random.randint(200, 800)
                final_balance = add_money(interaction.user.id, coin_amount)
                
                embed = discord.Embed(
                    title="⛏️ Mining Result",
                    description=f"💎 SUPER RARE! You found an incredible **{coin_amount:,} coins**!",
                    color=discord.Color.purple()
                )
                embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
        
        else:
            # 0.1% chance: Check for legendary vs epic
            rand_decimal = random.random() * 100
            if rand_decimal <= 0.001:
                # 0.001% chance: Legendary item
                items_db = load_items()
                legendary_items = [
                    item_name for item_name, item_data in items_db.items()
                    if item_data.get("rarity", "common") == "legendary"
                ]
                
                if legendary_items:
                    chosen_item = random.choice(legendary_items)
                    item_data = items_db[chosen_item]
                    value = item_data.get("value", 0)
                    
                    quantity = add_item_to_inventory(interaction.user.id, chosen_item)
                    
                    embed = discord.Embed(
                        title="⛏️ Mining Result",
                        description=f"👑 LEGENDARY! You discovered the legendary **{chosen_item}**!",
                        color=discord.Color.gold()
                    )
                    embed.add_field(name="Rarity", value="Legendary", inline=True)
                    embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
                    embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
                else:
                    coin_amount = random.randint(1000, 5000)
                    final_balance = add_money(interaction.user.id, coin_amount)
                    
                    embed = discord.Embed(
                        title="⛏️ Mining Result",
                        description=f"👑 LEGENDARY! You found legendary **{coin_amount:,} coins**!",
                        color=discord.Color.gold()
                    )
                    embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
            else:
                # Just an epic item (remaining 0.1% - 0.001% = 0.099%)
                items_db = load_items()
                epic_items = [
                    item_name for item_name, item_data in items_db.items()
                    if item_data.get("rarity", "common") == "epic"
                ]
                
                if epic_items:
                    chosen_item = random.choice(epic_items)
                    item_data = items_db[chosen_item]
                    value = item_data.get("value", 0)
                    
                    quantity = add_item_to_inventory(interaction.user.id, chosen_item)
                    
                    embed = discord.Embed(
                        title="⛏️ Mining Result",
                        description=f"🌟 ULTRA RARE! You discovered an epic **{chosen_item}**!",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="Rarity", value="Epic", inline=True)
                    embed.add_field(name="Value", value=f"{value:,} coins", inline=True)
                    embed.add_field(name="Quantity Owned", value=f"{quantity}", inline=True)
                else:
                    coin_amount = random.randint(500, 2000)
                    final_balance = add_money(interaction.user.id, coin_amount)
                    
                    embed = discord.Embed(
                        title="⛏️ Mining Result",
                        description=f"🌟 EPIC! You found epic **{coin_amount:,} coins**!",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="New Balance", value=f"{final_balance:,} coins", inline=True)
        
        # Add Mine Again button to the new result
        new_view = MineAgainView()
        await interaction.response.send_message(embed=embed, view=new_view)

@bot.command()
async def bank(ctx, action: str = "balance", amount: int = 0):
    """Bank system - deposit, withdraw, or check balance"""
    user_data = get_user_data(ctx.author.id)
    
    if action.lower() in ["balance", "bal"]:
        embed = discord.Embed(
            title="🏦 Bank Account",
            color=discord.Color.blue()
        )
        embed.add_field(name="💰 Wallet", value=f"{user_data['money']:,} coins", inline=True)
        embed.add_field(name="🏛️ Bank", value=f"{user_data['bank']:,} coins", inline=True)
        total = user_data['money'] + user_data['bank']
        embed.add_field(name="📊 Total", value=f"{total:,} coins", inline=True)
        embed.set_footer(text="Use !bank deposit <amount> or !bank withdraw <amount>")
        
    elif action.lower() in ["deposit", "dep"]:
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Invalid Amount",
                description="You must deposit at least 1 coin!",
                color=discord.Color.red()
            )
        elif user_data['money'] < amount:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=f"You don't have {amount:,} coins in your wallet!",
                color=discord.Color.red()
            )
        else:
            new_wallet = user_data['money'] - amount
            new_bank = user_data['bank'] + amount
            update_user_data(ctx.author.id, money=new_wallet, bank=new_bank)
            
            embed = discord.Embed(
                title="🏦 Deposit Successful",
                description=f"Deposited {amount:,} coins to your bank!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Wallet", value=f"{new_wallet:,} coins", inline=True)
            embed.add_field(name="🏛️ Bank", value=f"{new_bank:,} coins", inline=True)
    
    elif action.lower() in ["withdraw", "with"]:
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Invalid Amount",
                description="You must withdraw at least 1 coin!",
                color=discord.Color.red()
            )
        elif user_data['bank'] < amount:
            embed = discord.Embed(
                title="❌ Insufficient Bank Funds",
                description=f"You don't have {amount:,} coins in your bank!",
                color=discord.Color.red()
            )
        else:
            new_wallet = user_data['money'] + amount
            new_bank = user_data['bank'] - amount
            update_user_data(ctx.author.id, money=new_wallet, bank=new_bank)
            
            embed = discord.Embed(
                title="🏦 Withdrawal Successful",
                description=f"Withdrew {amount:,} coins from your bank!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Wallet", value=f"{new_wallet:,} coins", inline=True)
            embed.add_field(name="🏛️ Bank", value=f"{new_bank:,} coins", inline=True)
    
    else:
        embed = discord.Embed(
            title="❌ Invalid Action",
            description="Use: `!bank balance`, `!bank deposit <amount>`, or `!bank withdraw <amount>`",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx, category: str = "money"):
    """View leaderboards - money, level, or bank"""
    users = load_users()
    
    if category.lower() in ["money", "coins", "wealth"]:
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("money", 0), reverse=True)
        title = "💰 Money Leaderboard"
        field_name = "Coins"
        
    elif category.lower() in ["level", "lvl", "xp"]:
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("level", 1), reverse=True)
        title = "⭐ Level Leaderboard"
        field_name = "Level"
        
    elif category.lower() in ["bank", "savings"]:
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("bank", 0), reverse=True)
        title = "🏦 Bank Leaderboard"
        field_name = "Bank Balance"
        
    elif category.lower() in ["total", "net", "worth"]:
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("money", 0) + x[1].get("bank", 0), reverse=True)
        title = "💎 Net Worth Leaderboard"
        field_name = "Total Worth"
        
    else:
        embed = discord.Embed(
            title="❌ Invalid Category",
            description="Use: `money`, `level`, `bank`, or `total`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(title=title, color=discord.Color.gold())
    
    top_10 = sorted_users[:10]
    description = ""
    
    for i, (user_id, data) in enumerate(top_10, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.display_name if user else f"User {user_id}"
        except:
            username = f"User {user_id}"
        
        if category.lower() in ["money", "coins", "wealth"]:
            value = data.get("money", 0)
            description += f"**{i}.** {username} - {value:,} coins\n"
        elif category.lower() in ["level", "lvl", "xp"]:
            level = data.get("level", 1)
            xp = data.get("xp", 0)
            description += f"**{i}.** {username} - Level {level} ({xp:,} XP)\n"
        elif category.lower() in ["bank", "savings"]:
            value = data.get("bank", 0)
            description += f"**{i}.** {username} - {value:,} coins\n"
        elif category.lower() in ["total", "net", "worth"]:
            total = data.get("money", 0) + data.get("bank", 0)
            description += f"**{i}.** {username} - {total:,} coins\n"
    
    if not description:
        description = "No users found!"
    
    embed.description = description
    embed.set_footer(text="Use !leaderboard <money/level/bank/total>")
    
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, target: discord.Member, amount: int):
    """Give coins to another user"""
    if target.id == ctx.author.id:
        embed = discord.Embed(
            title="❌ Cannot Give to Yourself",
            description="You can't give coins to yourself!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    if amount <= 0:
        embed = discord.Embed(
            title="❌ Invalid Amount",
            description="You must give at least 1 coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    giver_data = get_user_data(ctx.author.id)
    if giver_data["money"] < amount:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You don't have {amount:,} coins!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Transfer money
    giver_new_balance = giver_data["money"] - amount
    receiver_new_balance = add_money(target.id, amount)
    update_user_data(ctx.author.id, money=giver_new_balance)
    
    embed = discord.Embed(
        title="💝 Gift Sent!",
        description=f"{ctx.author.mention} gave {amount:,} coins to {target.mention}!",
        color=discord.Color.green()
    )
    embed.add_field(name="Your New Balance", value=f"{giver_new_balance:,} coins", inline=True)
    embed.add_field(name=f"{target.display_name}'s New Balance", value=f"{receiver_new_balance:,} coins", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def coinflip(ctx, bet: int, choice: str = "heads"):
    """Simple coinflip betting game"""
    if bet <= 0:
        embed = discord.Embed(
            title="❌ Invalid Bet",
            description="You must bet at least 1 coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    user_data = get_user_data(ctx.author.id)
    if user_data["money"] < bet:
        embed = discord.Embed(
            title="❌ Insufficient Funds",
            description=f"You don't have {bet:,} coins!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    if choice.lower() not in ["heads", "tails", "h", "t"]:
        embed = discord.Embed(
            title="❌ Invalid Choice",
            description="Choose `heads` or `tails`!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Normalize choice
    player_choice = "heads" if choice.lower() in ["heads", "h"] else "tails"
    coin_result = random.choice(["heads", "tails"])
    
    if player_choice == coin_result:
        # Win
        winnings = bet * 2
        new_balance = add_money(ctx.author.id, winnings)
        
        embed = discord.Embed(
            title="🪙 Coinflip - You Win!",
            description=f"🎉 The coin landed on **{coin_result}**!\n\nYou won {bet:,} coins!",
            color=discord.Color.green()
        )
        embed.add_field(name="Your Choice", value=player_choice.title(), inline=True)
        embed.add_field(name="Result", value=coin_result.title(), inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
    else:
        # Lose
        spend_money(ctx.author.id, bet)
        user_data = get_user_data(ctx.author.id)
        
        embed = discord.Embed(
            title="🪙 Coinflip - You Lose!",
            description=f"😢 The coin landed on **{coin_result}**!\n\nYou lost {bet:,} coins!",
            color=discord.Color.red()
        )
        embed.add_field(name="Your Choice", value=player_choice.title(), inline=True)
        embed.add_field(name="Result", value=coin_result.title(), inline=True)
        embed.add_field(name="New Balance", value=f"{user_data['money']:,} coins", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
async def achievements(ctx):
    """View your achievements"""
    user_data = get_user_data(ctx.author.id)
    achievements = user_data.get("achievements", [])
    
    # Check for new achievements
    money = user_data.get("money", 0)
    level = user_data.get("level", 1)
    total_worth = money + user_data.get("bank", 0)
    
    possible_achievements = {
        "first_coins": {"name": "💰 First Coins", "desc": "Earn your first 1,000 coins", "req": money >= 1000},
        "high_roller": {"name": "🎰 High Roller", "desc": "Accumulate 10,000 coins", "req": money >= 10000},
        "millionaire": {"name": "💎 Millionaire", "desc": "Reach 1,000,000 coins", "req": total_worth >= 1000000},
        "level_5": {"name": "⭐ Rising Star", "desc": "Reach level 5", "req": level >= 5},
        "level_10": {"name": "🌟 Experienced", "desc": "Reach level 10", "req": level >= 10},
        "gambler": {"name": "🎲 Gambler", "desc": "Use any gambling command", "req": True}  # Auto-unlock
    }
    
    new_achievements = []
    for ach_id, ach_data in possible_achievements.items():
        if ach_id not in achievements and ach_data["req"]:
            achievements.append(ach_id)
            new_achievements.append(ach_data["name"])
    
    if new_achievements:
        update_user_data(ctx.author.id, achievements=achievements)
    
    embed = discord.Embed(
        title="🏆 Your Achievements",
        color=discord.Color.gold()
    )
    
    if achievements:
        description = ""
        for ach_id in achievements:
            if ach_id in possible_achievements:
                ach = possible_achievements[ach_id]
                description += f"{ach['name']} - {ach['desc']}\n"
        embed.description = description
    else:
        embed.description = "No achievements yet! Keep playing to unlock them!"
    
    embed.add_field(name="Progress", value=f"{len(achievements)}/{len(possible_achievements)} unlocked", inline=True)
    
    if new_achievements:
        embed.add_field(name="🎉 New Achievements!", value="\n".join(new_achievements), inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def sellall(ctx):
    """Sell ALL items in your inventory for coins"""
    user_data = get_user_data(ctx.author.id)
    inventory = user_data.get("inventory", {})

    if not inventory:
        embed = discord.Embed(
            title="📦 Inventory Empty",
            description="You don’t have any items to sell!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    items_db = load_items()
    total_value = 0
    sold_items = []

    # Loop through and sell everything
    for item_name, quantity in list(inventory.items()):
        item_data = items_db.get(item_name)
        if not item_data:
            continue  # skip unknown items

        value = item_data.get("value", 0)
        item_total = value * quantity
        total_value += item_total
        sold_items.append(f"{item_name} x{quantity} ({item_total:,} coins)")

        # Remove from inventory
        del inventory[item_name]

    # Update user data
    update_user_data(ctx.author.id, inventory=inventory)
    new_balance = add_money(ctx.author.id, total_value)

    # Build result embed
    embed = discord.Embed(
        title="💰 Sell All Items",
        description=f"You sold **{len(sold_items)} items** for **{total_value:,} coins**!",
        color=discord.Color.green()
    )

    # Show top 10 sold items to avoid overflow
    if sold_items:
        display_list = sold_items[:10]
        more = len(sold_items) - 10
        if more > 0:
            display_list.append(f"...and {more} more")

        embed.add_field(
            name="Items Sold",
            value="\n".join(display_list),
            inline=False
        )

    embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=False)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def delete(ctx, amount: int = None):
    """Delete messages in the current channel (Admin only)"""
    channel = ctx.channel
    
    # Confirmation embed
    if amount is None:
        embed = discord.Embed(
            title="⚠️ Confirm Deletion",
            description=f"Are you sure you want to delete ALL messages in {channel.mention}?\n\nReact with ✅ to confirm or ❌ to cancel.",
            color=discord.Color.orange()
        )
    else:
        embed = discord.Embed(
            title="⚠️ Confirm Deletion", 
            description=f"Are you sure you want to delete the last {amount:,} messages in {channel.mention}?\n\nReact with ✅ to confirm or ❌ to cancel.",
            color=discord.Color.orange()
        )
    
    confirmation_msg = await ctx.send(embed=embed)
    await confirmation_msg.add_reaction("✅")
    await confirmation_msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        if str(reaction.emoji) == "✅":
            # Delete the confirmation message first
            await confirmation_msg.delete()
            
            # Use bulk delete for much faster deletion
            try:
                if amount is None:
                    deleted = await channel.purge(limit=None, check=lambda m: True)
                else:
                    deleted = await channel.purge(limit=amount + 1, check=lambda m: True)  # +1 for the command message
                deleted_count = len(deleted)
                
                # Send completion message
                completion_embed = discord.Embed(
                    title="🗑️ Channel Cleared",
                    description=f"Successfully deleted {deleted_count:,} messages from {channel.mention}!",
                    color=discord.Color.green()
                )
                await ctx.send(embed=completion_embed)
                
            except discord.Forbidden:
                error_embed = discord.Embed(
                    title="❌ Permission Error",
                    description="I don't have permission to delete messages in this channel!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred while deleting messages: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
            
        else:
            await confirmation_msg.edit(embed=discord.Embed(
                title="❌ Deletion Cancelled",
                description="Channel cleanup was cancelled.",
                color=discord.Color.red()
            ))
            await confirmation_msg.clear_reactions()
            
    except:
        await confirmation_msg.edit(embed=discord.Embed(
            title="⏰ Deletion Timeout",
            description="Deletion confirmation timed out. No messages were deleted.",
            color=discord.Color.red()
        ))
        await confirmation_msg.clear_reactions()

@delete.error
async def delete_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need Administrator permissions to use this command!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

def save_us(data):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Load items
def load_items():
    with open("items.json", "r", encoding="utf-8") as f:
        return json.load(f)

@bot.command()
async def giveitem(ctx, user: commands.MemberConverter, *, item_name: str):
    # Only allow the specific user
    allowed_user_id = "946865197757399040"
    if str(ctx.author.id) != allowed_user_id:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You are not allowed to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    amount = 1  # default amount
    # Optional: allow specifying amount at the end like "!giveitem @user Magic Sword 2"
    parts = item_name.rsplit(" ", 1)
    if parts[-1].isdigit():
        item_name = parts[0]
        amount = int(parts[1])

    users = load_users()
    items = load_items()

    if item_name not in items:
        embed = discord.Embed(
            title="❌ Item Not Found",
            description=f"The item `{item_name}` does not exist in items.json.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = {
            "money": 100,
            "xp": 0,
            "level": 1,
            "inventory": {},
            "last_daily": 0
        }

    if item_name in users[user_id]["inventory"]:
        users[user_id]["inventory"][item_name] += amount
    else:
        users[user_id]["inventory"][item_name] = amount

    save_users(users)

    embed = discord.Embed(
        title="✅ Item Given",
        description=f"Gave **{amount}x {item_name}** to {user.mention}.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


# Flex command with animation
@bot.command()
async def flex(ctx, user: commands.MemberConverter = None):
    if user is None:
        user = ctx.author

    users = load_users()
    items = load_items()
    user_id = str(user.id)

    if user_id not in users or not users[user_id]["inventory"]:
        embed = discord.Embed(
            title="💨 Nothing to flex",
            description=f"{user.mention} has no items to flex.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Determine best item
    rarity_order = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "cosmic", "null"]
    best_item = None
    best_rarity_index = -1
    best_rarity_name = "Common"

    for item_name in users[user_id]["inventory"]:
        if item_name in items:
            rarity = items[item_name].get("rarity", "common")
            rarity_index = rarity_order.index(rarity.lower()) if rarity.lower() in rarity_order else 0
            if rarity_index > best_rarity_index:
                best_rarity_index = rarity_index
                best_item = item_name
                best_rarity_name = rarity.capitalize()

    # Animation frames depending on rarity
    animations = {
        "common": ["🤏 Flexing...", f"{user.display_name} flexes a **{best_item}** (Common)"],
        "uncommon": ["💪 Flexing...", "💪💎", f"{user.display_name} flexes a shiny **{best_item}** (Uncommon)"],
        "rare": ["✨ Flexing...", "✨💪✨", f"{user.display_name} flexes a **{best_item}** (Rare)"],
        "epic": ["⚡ Flexing...", "⚡💪⚡", "⚡💎⚡", f"{user.display_name} flexes an **{best_item}** (Epic)"],
        "legendary": ["🔥 Flexing...", "🔥💪🔥", "🔥💎🔥", "🔥👑🔥", f"{user.display_name} flexes a **{best_item}** (Legendary)"],
        "mythic": ["🌌 Flexing...", "🌌💪🌌", "🌌💎🌌", "🌌👑🌌", f"{user.display_name} flexes a **{best_item}** (Mythic)"],
        "cosmic": ["🌠 Flexing...", "🌠💪🌠", "🌠💎🌠", "🌠👑🌠", "🌠🌌🌠", f"{user.display_name} flexes a **{best_item}** (Cosmic 🌌👑🔥)"],
        "null": ["⁉️ Flexing...", "⁉️🚫⁉️", "⁉️⭕⁉️", "⁉️❌⁉️", "⁉️💢⁉️", f"{user.display_name} flexes a **{best_item}** (Null ⁉️⁉️⁉️)"]
    }

    rarity_key = best_rarity_name.lower()
    frames = animations.get(rarity_key, [f"{user.display_name} flexes a **{best_item}** ({best_rarity_name})"])

    # Start animation
    msg = await ctx.send(embed=discord.Embed(description=frames[0], color=discord.Color.gold()))
    for frame in frames[1:]:
        await asyncio.sleep(1)  # delay between frames
        await msg.edit(embed=discord.Embed(description=frame, color=discord.Color.gold()))

@bot.command(name="givecoins")
async def givecoins(ctx, user_id: int, amount: int):
    uid = str(user_id)  # JSON keys are strings
    users = load_users()

    if uid not in users:
        await ctx.send(f"❌ User `{uid}` not found in users.json")
        return

    users[uid]["money"] = users[uid].get("money", 0) + amount
    save_us(users)

    embed = discord.Embed(
        title="💰 Money Added!",
        description=f"Added **{amount}** coins to <@{uid}>.\n\n**New Balance:** {users[uid]['money']}",
        color=discord.Color.yellow()
    )
    # display_avatar is always present; avoids None checks
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)
TOKEN = os.getenv("DISCORD_TOKEN")
if __name__ == "__main__":   # 👈 prevents duplicate runs
    bot.run("TOKEN")
