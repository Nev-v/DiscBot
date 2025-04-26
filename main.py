import math
import random
import subprocess
import discord  # type: ignore
from discord.ext import commands # type: ignore
from discord import app_commands # type: ignore
from discord.ui import Button, View # type: ignore
import sys
import os
import asyncio
import glob
import json
import datetime
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ghp import const # type: ignore

#GLOBAL VARIABLES
msg = {}
queue = []
loop = False

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')


        status = discord.Activity(type=discord.ActivityType.playing, name="Pirots 3")
        await self.change_presence(activity = status)

        try:
            guild = discord.Object(id=286827966783029248)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')

        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        level_up, level = incrementXp(message.author.id, 1)

        if level_up:
            await message.channel.send(f'{message.author.mention} Level up to {level}')
        
        await self.process_commands(message)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=286827966783029248)

@client.tree.command(name="soundboard", description="Play a sound", guild=GUILD_ID)
async def join(ctx, filename: str):
    if ctx.user.voice:

        channel = ctx.user.voice.channel
        voice_client = ctx.guild.voice_client

        search_pattern = os.path.join(const.audios, f"{filename}.*")
        matches = glob.glob(search_pattern)

        if not matches:
            await ctx.response.send_message(f"❌ No sound file found for '{filename}'", ephemeral=True)
            return
        file_path = matches[0]

        if voice_client is None or not voice_client.is_connected():
            voice_client = await channel.connect()

        if not os.path.isfile(file_path):
            print(f"❌ File not found at: `{file_path}`")
            return
        
        queue.append(filename)
        
        await play(ctx, filename, file_path, voice_client)

async def play(ctx, filename: str, file_path, voice_client):
    audio_source = discord.FFmpegPCMAudio(file_path)

    
    h, m, s = getAudioLength(getAudioPath(queue[0]))
    msg_main = f"Now playing: 🎵 **{queue[0]}** - {h}:{m}:{s}"
    if not voice_client.is_playing():
        if ctx.guild_id in msg:
            try:
                playMsg = msg[ctx.guild_id]
                msg_str = ""
                for i in range(len(queue) - 1):
                    sound = queue[i + 1]
                    h, m, s = getAudioLength(getAudioPath(sound))
                msg_str += f"\n **{sound}** - {h}:{m}:{s}"
                await playMsg.edit(content=f"{msg_main} \n ***Queue:*** {msg_str}")
            except discord.NotFound:
                pass
        else:
            await ctx.response.send_message(msg_main)
            playMsg = await ctx.original_response()
            msg[ctx.guild_id] = playMsg
        voice_client.play(audio_source, after=lambda e: after_played(voice_client, ctx))
    else:
        await sendMessageWithExpiration(ctx, f"Added {filename} to queue", 5)
        playMsg = msg[ctx.guild_id]
        msg_str = ""
        for i in range(len(queue) - 1):
            sound = queue[i + 1]
            h, m, s = getAudioLength(getAudioPath(sound))
            msg_str += f"\n **{sound}** - {h}:{m}:{s}"
        await playMsg.edit(content=f"{msg_main} \n ***Queue:*** {msg_str}")

def getAudioLength(file_path):
    res = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    length = float(res.stdout)
    h = 0
    m = 0
    s = 0
    while length > 3600:
        h += 1
        length -= 3600
    while length > 60:
        m += 1
        length -= 60
    s = math.floor(length)
    return h, m, s

def getAudioPath(filename):
    search_pattern = os.path.join(const.audios, f"{filename}.*")
    matches = glob.glob(search_pattern)
    sound_path = matches[0]
    return sound_path

def after_played(voice_client, ctx):
    asyncio.run_coroutine_threadsafe(leave(voice_client, ctx), client.loop)

async def leave(voice_client, ctx):
    print(f"{queue}")
    curr_sound = queue.pop(0)
    if loop:
        queue.append(curr_sound)
        print(f"Added {curr_sound} to queue")
    if len(queue) == 0:
        await voice_client.disconnect()
        print("Queue is empty, leaving")
        playMsg = msg.get(ctx.guild_id)
        if playMsg:
            await playMsg.delete()
    else:
        print(f"Current ending sound {curr_sound}")
        next_sound = queue[0]
        print(f"Next sound {next_sound}")
        search_pattern = os.path.join(const.audios, f"{next_sound}.*")
        matches = glob.glob(search_pattern)
        file_path = matches[0]
        await play(ctx, next_sound, file_path, voice_client)

@client.tree.command(name="skip", description="Skip to next sound, leaves is the are none in queue", guild=GUILD_ID)
async def skip(ctx):
    await sendMessageWithExpiration(ctx, f"Skipped, next up: {queue}", 5)

    voice_client = ctx.guild.voice_client
    voice_client.stop()
    
@client.tree.command(name="list", description="Display all playable sounds", guild=GUILD_ID)
async def list(ctx):
    files = os.listdir(const.audios)

    sound_files = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.ogg'))]

    sound_names = [os.path.splitext(f)[0] for f in sound_files]

    if not sound_names:
        await ctx.response.send_message("❌ No sounds")

    sound_list = ", ".join(sound_names)

    await ctx.response.send_message(f"**Available sounds:**  {sound_list}")

@client.tree.command(name="loop", description="Turn on/off loop for soundboard", guild=GUILD_ID)
async def doLoop(interaction: discord.Interaction):
    global loop

    loop = not loop

    if loop:
        await sendMessageWithExpiration(interaction, "Looping sounds", 30)
    else:
        await sendMessageWithExpiration(interaction, "Sounds no longer looped", 30)

@client.tree.command(name="leaderboard", description="Leaderboard", guild=GUILD_ID)
async def leaderboard(ctx, top_n: int = 10, sort: str = "Level"):
    data = load_data()

    sorted_users = sorted(data.items(), key=lambda x: x[1].get(sort, 0), reverse=True)

    leaderboardStr = ""
    for i, (user_id, info) in enumerate(sorted_users[:top_n], start=1):
        money = info.get("Cash", 0)
        level = info.get("Level", 0)
        user = await client.fetch_user(user_id)
        leaderboardStr += f"**{i}.** {user.display_name} - {money} Cash Level {level}\n"

    await ctx.response.send_message(f"**Leaderboard** \n\n{leaderboardStr}")
    msg = await ctx.original_response()
    await asyncio.sleep(60)
    await msg.delete()

@client.tree.command(name="work", description="Work for money", guild=GUILD_ID)
async def work(interaction: discord.Interaction):
    checkExist(interaction.user.id)
    incrementXp(interaction.user.id, 30)
    user_id = str(interaction.user.id)
    data = load_data()

    now_str = datetime.now().strftime('%y-%m-%d')
    now = datetime.strptime(now_str, '%y-%m-%d')

    saved_date_str = data[user_id]["Work"]
    saved_date = datetime.strptime(saved_date_str, '%y-%m-%d')
    if now > saved_date:
        data[user_id]["Work"] = now_str
        data[user_id]["Cash"] += 10 + 2 * data[user_id]["Level"]
        save_data(data)
        await interaction.response.send_message(f"You earned {10 + 2 * data[user_id]["Level"]} cash!", ephemeral=True)
    else:
        await interaction.response.send_message("You have already worked today!", ephemeral=True)

@client.tree.command(name="fish", description="Reel in some cash", guild=GUILD_ID)
@app_commands.describe(bait="Bait")
@app_commands.choices(bait=[app_commands.Choice(name="No Bait", value="nb"), app_commands.Choice(name="Basic Bait", value="bb"), app_commands.Choice(name="Advanced Bait", value="ab"), app_commands.Choice(name="Master Bait", value="mab"), app_commands.Choice(name="Mystery Bait", value="myb")])
async def angling(interaction: discord.Interaction, bait: app_commands.Choice[str]):
    checkExist(interaction.user.id)


    fish_rarity = {
        "🐟": "Common",
        "🐠": "Uncommon",
        "🐡": "Rare",
        "🐙": "Legendary",
        "🦈": "Fabled"
    }

    line = "🎣"
    water = "🟦"

    emoji = [] 
    hook_index = const.fish_minigame_width * const.line_length + const.line_x
    i = 0
    j = 0
    match bait.value:
        case "nb":
            fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg, const.fish_fab], weights=[80000, 15000, 4900, 100-1, 1], k=1)[0]
        case "bb":
            if checkReq(interaction.user.id, 1, "Bait", "Basic Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg, const.fish_fab], weights=[37000, 50000, 12000, 1000-2, 2], k=1)[0]
            else:
                await sendMessageWithExpiration(interaction, "You have no bait", 10)
                return
        case "ab":
            if checkReq(interaction.user.id, 1, "Bait", "Advanced Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg, const.fish_fab], weights=[21000, 42000, 31000, 3000-6, 6], k=1)[0]
            else:
                await sendMessageWithExpiration(interaction, "You have no bait", 10)
                return
        case "mab":
            if checkReq(interaction.user.id, 1, "Bait", "Master Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg, const.fish_fab], weights=[10000-18, 40000, 40000, 10000, 18], k=1)[0]
            else:
                await sendMessageWithExpiration(interaction, "You have no bait", 10)
                return
        case "myb":
            if checkReq(interaction.user.id, 1, "Bait", "Mystery Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg, const.fish_fab], weights=[2500, 2500, 10000, 80000, 5000], k=1)[0]
            else:
                await sendMessageWithExpiration(interaction, "You have no bait", 10)
                return
        case _:
            await sendMessageWithExpiration(interaction, "Invalid Bait", 10)

    emoji_str = ""
    for i in range(const.fish_minigame_height):
        j = 0
        for j in range(const.fish_minigame_width):
            if i == const.fish_y and j == const.fish_x:
                emoji.append(fish)
            elif j == const.line_x and i < const.line_length:
                emoji.append(line)
            else:
                emoji.append(water)
            j += 1
        i += 1

    emoji_str = "\n".join(
        "".join(emoji[i * const.fish_minigame_width:(i + 1) * const.fish_minigame_width])
        for i in range(const.fish_minigame_height)
    )

    fish_index = emoji.index(fish)
    fish_state = Fish(fish_index, fish)
    view = ReelIn(fish_state, hook_index, interaction.user, fish_rarity)

    await interaction.response.send_message(emoji_str, view=view)
    msg = await interaction.original_response()

    while fish_state.fish_index - const.fish_y * const.fish_minigame_width > 0 and view.active:

        if fish_state.fish_index % const.fish_minigame_width > 0:
            left_weight = (20 + (fish_state.fish_index % const.fish_minigame_width) * 5)**1.8
            right_weight = (100 - (fish_state.fish_index % const.fish_minigame_width) * 5)**1.8

            if fish_state.fish_index < ((const.fish_y+1) * const.fish_minigame_width) - 1:
                movement = random.choices([-1, 0, 1], weights=[left_weight, 10, right_weight], k=1)[0]
            else:
                movement = -1

            new_pos = fish_state.fish_index + movement

            emoji[fish_state.fish_index], emoji[new_pos] = emoji[new_pos], emoji[fish_state.fish_index]

            fish_state.fish_index = new_pos

        emoji_str = "\n".join(
        "".join(emoji[i * const.fish_minigame_width:(i + 1) * const.fish_minigame_width])
        for i in range(const.fish_minigame_height)
        )

        await msg.edit(content=emoji_str, view=view)

        await asyncio.sleep(1)

    if not view.active:
        await asyncio.sleep(10)
    await msg.delete()

class Fish:
    def __init__(self, fish_index, fish_emoji):
        self.fish_index = fish_index
        self.fish_emoji = fish_emoji

class ReelIn(View):
    def __init__(self, fish_state, hook_index, user, fish_rarity):
        super().__init__(timeout=15)
        self.fish_state = fish_state
        self.hook_index = hook_index
        self.user = user
        self.fish_rarity = fish_rarity
        self.result = None
        self.active = True

    @discord.ui.button(label="Reel in 🎣", style=discord.ButtonStyle.green)
    async def reel_in(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.active = False
        button.disabled = True
        if self.fish_state.fish_index == self.hook_index:
            self.result = "Caught!"
            await interaction.edit_original_response(content="🐟 You caught the fish!", view=None)
            data = load_data()
            user_id_str = str(self.user.id)
            rarity = self.fish_rarity.get(self.fish_state.fish_emoji, "Common")
            incrementXp(interaction.user.id, 2)

            data[user_id_str]["Fish"][rarity] += 1

            save_data(data)
        else:
            self.result = "Missed!"
            incrementXp(interaction.user.id, 0.2)
            await interaction.edit_original_response(content="💨 The fish got away!", view=None)

@client.tree.command(name="inventory", description="Display a players inventory", guild=GUILD_ID)
async def inventory(interaction: discord.Interaction, user: discord.User = None):
    checkExist(interaction.user.id)
    data = load_data()
    user_id_str = ""
    user_name = ""
    if user:
        user_id_str = str(user.id)
        user_name = user.display_name
    else:
        user_id_str = str(interaction.user.id)
        user_name = interaction.user.display_name
    msg = f"**{user_name}'s Inventory** \n Cash {const.cash}: {data[user_id_str]["Cash"]} \n ***Fish:*** \n Common {const.fish_common}: {data[user_id_str]["Fish"]["Common"]} \n Uncommon {const.fish_uncommon}: {data[user_id_str]["Fish"]["Uncommon"]} \n Rare {const.fish_rare}: {data[user_id_str]["Fish"]["Rare"]} \n Legendary {const.fish_leg}: {data[user_id_str]["Fish"]["Legendary"]} {f'\n Fabled {const.fish_fab}: {data[user_id_str]["Fish"]["Fabled"]}' if data[user_id_str]["Fish"]["Fabled"] > 0 else ''} \n ***Bait*** \n Basic {const.bait_basic}: {data[user_id_str]["Bait"]["Basic Bait"]} \n Advanced {const.bait_advanced}: {data[user_id_str]["Bait"]["Advanced Bait"]} \n Master {const.bait_master}: {data[user_id_str]["Bait"]["Master Bait"]}"
    await sendMessageWithExpiration(interaction, msg, 40)

async def sendMessageWithExpiration(interaction, msg_str, delay):
    await interaction.response.send_message(f"{msg_str}")
    msg = await interaction.original_response()
    await asyncio.sleep(delay)
    await msg.delete()

async def editMessageWithExpiration(msg, msg_str, delay):
    await msg.edit(content=msg_str)
    await asyncio.sleep(delay)
    await msg.delete()

@client.tree.command(name="casino", description="Casino", guild=GUILD_ID)
@app_commands.describe(game="Casino game", bet_color="Pick color", amount="How much would you like to bet?")
@app_commands.choices(game=[app_commands.Choice(name="Roulette", value="roulette"), ], bet_color=[app_commands.Choice(name="Red 🔴", value="red"), app_commands.Choice(name="Black ⚫", value="black"), app_commands.Choice(name="Green 🟢", value="green"), app_commands.Choice(name="Purple", value="purple")])
async def casino(interaction: discord.Interaction, game: app_commands.Choice[str], bet_color: app_commands.Choice[str], amount: int):
    checkExist(interaction.user.id)

    if amount >= 10:
        if checkReq(interaction.user.id, amount, "Cash"):
            match game.value:
                case "roulette":
                    await roulette(interaction, bet_color, amount)
        else:
            await interaction.response.send_message(f'You are too broke, get a job', ephemeral = True)
    else:
        await interaction.response.send_message(f'You can not bet lower than 10', ephemeral=True)
   
async def roulette(interaction, bet_color, amount):
    msg_str = "Spinning the wheel"

    await interaction.response.send_message(msg_str)
    msg = await interaction.original_response()

    wheel = const.roulette_wheel

    num = random.randint(16, 31)
    i = num
    for _ in range(num):
        wheel = wheel[-1:] + wheel[:-1]
        msg_str = await drawWheel(wheel)
        await msg.edit(content=msg_str)
        await asyncio.sleep(1/i)
        i -= 1

    win_emoji = msg_str[2]

    await asyncio.sleep(3)

    if bet_color.value == "green" and win_emoji == "🟩":
        win = amount * 17
        updateMoney(interaction.user.id, win)
        await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} won {win} cash :D", win + 10)
    elif bet_color.value == "red" and win_emoji == "🟥":
        win = amount * 2
        updateMoney(interaction.user.id, win)
        await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} won {win} cash :D", win + 10)
    elif bet_color.value == "black" and win_emoji == "⬛":
        win = amount * 2
        updateMoney(interaction.user.id, win)
        await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} won {win} cash :D", win + 10)
    elif bet_color.value == "purple" and win_emoji == "🟪":
        rand = random.choices([0, 0.5, 2, 25, 75], weights=[20, 20, 25, 20, 15], k=1)[0]
        win = amount * rand
        updateMoney(interaction.user.id, win)
        match rand:
            case 0:
                await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} won {win} cash D:", win + 10)
            case 0.5:
                await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} got {win} back :I", win + 10)
            case _:
                await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} won {win} cash :D", win + 10)
    else:
        await editMessageWithExpiration(msg, f"You bet {amount} on {bet_color.value} and lost :(", amount + 10)

async def drawWheel(wheel):
    grid = [["⬜" for _ in range (5)] for _ in range(5)]

    positions = [
        (0, 0), (0, 1), (0, 2), (0, 3), (0, 4),  # Top row
        (1, 4), (2, 4), (3, 4),                  # Right column
        (4, 4), (4, 3), (4, 2), (4, 1), (4, 0),  # Bottom row
        (3, 0), (2, 0), (1, 0)                   # Left column
    ]

    for i, (y,x) in enumerate(positions):
        grid[y][x] = wheel[i]

    grid[1][2] = "🔺"

    return "\n".join("".join(row) for row in grid)

@client.tree.command(name="shop", description="Buy or sell items", guild=GUILD_ID)
async def shop(interaction: discord.Interaction):
    await interaction.response.send_message("Select a category:", view = ActionSelectView(), ephemeral = True)

class ActionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Buy", description="Purchase items"),
            discord.SelectOption(label="Sell", description="Sell items")
        ]
        super().__init__(placeholder="Buy or Sell?", options=options)

    async def callback(self, interaction: discord.Interaction):
        action = self.values[0]
        await interaction.response.edit_message(content=f"You chose to **{action}**. Now select category:", view=CategorySelectView(action))

class ActionSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.add_item(ActionSelect())

class CategorySelect(discord.ui.Select):
    def __init__(self, action):
        self.action = action

        available_categories = {
            "Buy": ["Bait"],
            "Sell": ["Fish"]
        }

        options = [
            discord.SelectOption(label=cat, description=f"{action} {cat.lower()}")
            for cat in available_categories.get(action, [])
        ]

        super().__init__(placeholder="Choose a category...", options = options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        await interaction.response.edit_message(content=f"You selected **{category}**. Now choose an item to {self.action.lower()}:", view = ItemSelectView(self.action, category))

class CategorySelectView(discord.ui.View):
    def __init__(self, action):
        super().__init__(timeout=30)
        self.add_item(CategorySelect(action))

class ItemSelect(discord.ui.Select):
    def __init__(self, action, category):
        self.action = action
        self.category = category

        if self.action == "Buy":
            items = const.shop_items.get('Buy', {}).get(self.category, {})
        elif self.action == "Sell":
            items = const.shop_items.get('Sell', {}).get(self.category, {})
        else:
            items = {}

        options = [discord.SelectOption(
            label = item_name,
            description = f"{'Cost' if action == "Buy" else 'Sell for'}: {price} cash",
            value = item_name
            )
            for item_name, price in items.items() if item_name != "Fabled"
        ]

        if self.action == "Sell" and self.category == "Fish":
            options.append(discord.SelectOption(label="???", description="Sell ??? for ???", value="Fabled"))

        super().__init__(placeholder="Choose an item...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_item = self.values[0]
        category = self.category
        action = self.action

        await interaction.response.edit_message(content=f"You wish to {self.action.lower()} **{selected_item}**. How many would you like to {self.action.lower()}?", view = QuantitySelectView(action, category, selected_item, interaction.user.id))

class ItemSelectView(discord.ui.View):
    def __init__(self, action, category):
        super().__init__(timeout=30)
        self.add_item(ItemSelect(action, category))

class QuantitySelect(discord.ui.Select):
    def __init__(self, action, category, item, user_id):
        self.action = action
        self.category = category
        self.item = item

        data = load_data()
        user_id = str(user_id)
        self.price = const.shop_items[action][category][item]

        if action == "Buy":
            user_cash = data[user_id]["Cash"]
            max_quantity = user_cash // self.price
        elif action == "Sell":
            max_quantity = data[user_id][category].get(item, 0)
        else:
            max_quantity = 0

        quantities = range(1, min(int(max_quantity), 25) + 1)

        if not quantities:
            options = [discord.SelectOption(label="None Available", value="0")]
        else:
            options = [
                discord.SelectOption(label=str(q), value=str(q), description=f"{q}x {item}")
                for q in quantities
            ]
        
        super().__init__(placeholder="Select quantity...", options=options)
        self.user_id = user_id
        self.item = item
        self.category = category
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        quantity = int(self.values[0])
        total_cost = self.price * quantity
        data = load_data()
        user_id = str(self.user_id)

        if self.action =="Buy":
            if data[user_id]["Cash"] >= total_cost:
                data[user_id]["Cash"] -= total_cost
                data[user_id][self.category][self.item] += quantity
                save_data(data)
                await interaction.response.edit_message(content=f"You bought {quantity}x {self.item} for {total_cost} cash!", view=None)
            else:
                await interaction.response.edit_message(content=f"Not enough cash", view=None)
        elif self.action == "Sell":
            if data[user_id][self.category][self.item] <= quantity:
                data[user_id][self.category][self.item] -= quantity
                data[user_id]["Cash"] += total_cost
                save_data(data)
                await interaction.response.edit_message(content=f"You sold {quantity}x {self.item} for {total_cost} cash!", view=None)
            else:
                await interaction.response.edit_message(content=f"Not enough {self.item}", view=None)

class QuantitySelectView(discord.ui.View):
    def __init__(self, action, category, item, user_id):
        super().__init__(timeout=30)
        self.add_item(QuantitySelect(action, category, item, user_id))

@client.tree.command(name="adventure", description="Go on an adventure", guild=GUILD_ID)
async def adventureInit(interaction: discord.Interaction):
    stage = 0
    user_health = 100
    await interaction.response.send_message("Starting adventure...")
    adv_msg = await interaction.original_response()
    await adventure(adv_msg, interaction, stage, user_health, False)
    
async def adventure(adv_msg, interaction, stage, user_health, combat):
    stage += 1
    print(stage)
    data = load_data()
    user_id = str(interaction.user.id)
    if not combat:
        options = []
        opt_num = random.choices([1, 2, 3], weights=[50, 0 + 50 * data[user_id]["Level"]**(1/4), 0 + 100 * math.log(data[user_id]["Level"], 10) + data[user_id]["Level"]], k=1)[0]

        for i in range(opt_num):
            options.append(random.choices(["Path", "Enemy", "Boss"], weights=[const.adv_encounters["Path"]["weight"], const.adv_encounters["Enemy"]["weight"] + data[user_id]["Level"], const.adv_encounters["Boss"]["weight"] * data[user_id]["Level"]], k=1)[0])
        print(options)
        curr_msg = adventureOptionFrame(options)
        view = adventureButton(options, adv_msg, stage, user_health)
    else:
        curr_msg, enemy = generateCombat(user_id, stage, user_health)
        view = adventureCombatButtons(adv_msg, stage, enemy, enemy[0]["health"], user_health)
    await adv_msg.edit(content=curr_msg, view=view)

def adventureOptionFrame(options):
    num = len(options)
    match num:
        case 1:
            positions = [(const.adv_minigame_height // 2, const.adv_minigame_width // 2)]
        case 2:
            positions = [(const.adv_minigame_height // 2, const.adv_minigame_width // 3), (const.adv_minigame_height // 2, 2 * const.adv_minigame_width // 3)]
        case 3:
            positions = [(const.adv_minigame_height // 2, const.adv_minigame_width // 4), (const.adv_minigame_height // 2, const.adv_minigame_width // 2), (const.adv_minigame_height // 2, 3 * const.adv_minigame_width // 4)]
        case _:
            positions = []

    emoji_pos_map = {positions[i]: const.adv_encounters[options[i]]["emoji"] for i in range(num)}
            
    msg = []
    msg_str = ""
    for i in range(const.adv_minigame_height):
        row = []
        for j in range(const.adv_minigame_width):
            if (i, j) in emoji_pos_map:
                row.append(emoji_pos_map[(i, j)])
            else:
                row.append(const.grass)
        
        msg.append("".join(row))
    
    msg_str = "\n".join(msg)

    return msg_str

def generateCombat(id, stage, user_health):
    data = load_data()
    user_id = str(id)
    weights = [100, 100 + data[user_id]["Level"], 20 + data[user_id]["Level"]/2 + data[user_id]["Cash"]]
    enemy = random.choices(const.adv_encounters["Enemy"]["variants"], weights=weights)
    enemy_health = enemy[0]["health"] + 1 * stage
    return adventureCombatFrame(id, enemy, enemy_health, user_health), enemy

def adventureCombatFrame(id, enemy, enemy_health, user_health):
    data = load_data()
    user_id = str(id)
    msg = []
    msg_str = ""
    for i in range(const.adv_minigame_height):
        row = []
        for j in range(const.adv_minigame_width):
            if i == const.adv_health_y and j >= const.adv_health_x and j < const.adv_health_length + const.adv_health_x:
                if enemy_health >= (j - const.adv_health_x) * (enemy[0]["health"]/const.adv_health_length):
                    row.append(const.health)
                else:
                    row.append(const.empty_health)
            elif i >= const.adv_sprite_top and i <= const.adv_sprite_bot and j >= const.adv_sprite_left and j <= const.adv_sprite_right:
                    sprite_index = (i - const.adv_sprite_top)*(const.adv_sprite_right-const.adv_sprite_left + 1) + j - const.adv_sprite_left
                    row.append(enemy[0]["sprite"][sprite_index])
            else:
                row.append(const.grass)
        
        msg.append("".join(row))

    msg.append("".join(f"Your health: {user_health}     {enemy[0]["name"]} health: {enemy_health}"))
    
    msg_str = "\n".join(msg)

    return msg_str

async def attack(adv_msg, interaction, stage, enemy, enemy_health, user_health):
    enemy_health -= const.adv_base_dmg
    user_health -= enemy[0]["damage"]

    if not enemy_health > 0:
        incrementXp(interaction.user.id, stage)
        await adventure(adv_msg, interaction, stage, user_health, False)
    else:
        msg = adventureCombatFrame(interaction.user.id, enemy, enemy_health, user_health)
        view = adventureCombatButtons(adv_msg, stage, enemy, enemy_health, user_health)
        await adv_msg.edit(content=msg, view=view)

class adventureCombatButtons(View):
    def __init__(self, adv_msg, stage, enemy, enemy_health, user_health):
        super().__init__(timeout=15)
        self.adv_msg = adv_msg
        self.stage = stage
        self.enemy = enemy
        self.enemy_health = enemy_health
        self.user_health = user_health

    @discord.ui.button(label="Attack")
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await attack(self.adv_msg, interaction, self.stage, self.enemy, self.enemy_health, self.user_health)

    @discord.ui.button(label="Run")
    async def run(self, interaction: discord.Interaction, button: discord.ui.Button):
        await adventure(self.adv_msg, interaction, self.stage, self.user_health, False)

class adventureButton(View):
    def __init__(self, options, msg, stage, user_health):
        super().__init__(timeout=15)
        num = len(options)
        for i in range(num):
            style = None
            match options[i]:
                case "Path":
                    style = discord.ButtonStyle.green
                case "Enemy":
                    style = discord.ButtonStyle.primary
                case "Boss":
                    style = discord.ButtonStyle.red

            async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message("E", ephemeral=True)
            
            button = discord.ui.Button(
                    label=f"{options[i]}",
                    style=style
                )

            self.set_callback(button, options[i], msg, stage, user_health)
            self.add_item(button)

    def set_callback(self, button, index, msg, stage, user_health):
        async def callback(interaction: discord.Interaction):
            if index == "Path":
                await adventure(msg, interaction, stage, user_health, False)
            else:
                await adventure(msg, interaction, stage, user_health, True)
        button.callback = callback

def checkExist(user_id: int):
    data = load_data()
    user_id_str = str(user_id)

    default_data = {"Cash": 10, "Level":0, "xp": 0, "Work": "00-01-01", "Fish": {"Common": 0, "Uncommon": 0, "Rare": 0, "Legendary": 0, "Fabled": 0}, "Bait": {"Basic Bait": 0, "Advanced Bait": 0, "Master Bait": 0, "Mystery Bait": 0}}

    if user_id_str not in data:
        data[user_id_str] = default_data
    else:
        for key, value in default_data.items():
            if key not in data[user_id_str]:
                data[user_id_str][key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in data[user_id_str][key]:
                        data[user_id_str][key][sub_key] = sub_value
    save_data(data)

def incrementXp(id, amount):
    checkExist(id)
    data = load_data()
    user_id_str = str(id)

    data[user_id_str]["xp"] += amount

    return checkLevelup(id, data)

def checkReq(id, req, check_str, sub_key = None):
    data = load_data()
    user_id_str = str(id)

    if sub_key:
        if data[user_id_str][check_str][sub_key] >= req:
            data[user_id_str][check_str][sub_key] -= req
            save_data(data)
            return True
        else:
            return False
    else:
        if data[user_id_str][check_str] >= req:
            data[user_id_str][check_str] -= req
            save_data(data)
            return True
        else:
            return False

def updateMoney(id, amount):
    data = load_data()
    user_id_str = str(id)

    data[user_id_str]["Cash"] += amount

    save_data(data)

def checkLevelup(id, data):
    user_id_str = str(id)
    reqXp = (data[user_id_str]["Level"] + 1) * 10 + pow(2, math.log10(data[user_id_str]["Level"] + 1))
    level_up = False
    level = data[user_id_str]["Level"]
    while data[user_id_str]["xp"] >= reqXp:
        data[user_id_str]["xp"] -= reqXp
        data[user_id_str]["Level"] += 1
        level_up = True
        level = data[user_id_str]["Level"]

    save_data(data)

    return level_up, level

def load_data():
    if not os.path.exists(const.data_file):
        return {}
    with open(const.data_file, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(const.data_file, "w") as f:
        json.dump(data, f, indent=4)

client.run(const.token)
