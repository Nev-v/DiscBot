import random
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

        level_up, level = incrementXp(message.author.id)

        if level_up:
            await message.channel.send(f'{message.author.mention} Level up to {level}')
        
        await self.process_commands(message)
        
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return
        
        if not after.embeds:
            await after.channel.send(f'Blod ändrade "{before.content}" till "{after.content}"')

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

    if not voice_client.is_playing():
        if ctx.guild_id in msg:
            try:
                playMsg = msg[ctx.guild_id]
                await playMsg.edit(content=f"Now playing: 🎵 {queue[0]}")
            except discord.NotFound:
                pass
        else:
            await ctx.response.send_message(f'Now playing: 🎵 {queue[0]}')
            playMsg = await ctx.original_response()
            msg[ctx.guild_id] = playMsg
        voice_client.play(audio_source, after=lambda e: after_played(voice_client, ctx))
    else:
            await sendMessageWithExpiration(ctx, f"Added {filename} to queue", 10)

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
    print(f'Skip, up next: {queue}')

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
    user_id = str(interaction.user.id)
    data = load_data()

    now_str = datetime.now().strftime('%y-%m-%d')
    now = datetime.strptime(now_str, '%y-%m-%d')

    saved_date_str = data[user_id]["Work"]
    saved_date = datetime.strptime(saved_date_str, '%y-%m-%d')
    if now > saved_date:
        data[user_id]["Work"] = now_str
        data[user_id]["Cash"] += 10
        save_data(data)
        await interaction.response.send_message("You earned 10 cash!", ephemeral=True)
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
        "🐙": "Legendary"
    }

    line = "🎣"
    water = "🟦"

    emoji = [] 
    hook_index = const.fish_minigame_width * const.line_length + const.line_x
    i = 0
    j = 0
    match bait.value:
        case "nb":
            fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg], weights=[8000, 1500, 490, 10], k=1)[0]
        case "bb":
            if checkReq(interaction.user.id, 1, "Bait", "Basic Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg], weights=[370, 500, 120, 10], k=1)[0]
            else:
                await sendMessageWithExpiration(interaction, "You have no bait", 10)
                return
        case "ab":
            if checkReq(interaction.user.id, 1, "Bait", "Advanced Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg], weights=[210, 420, 310, 30], k=1)[0]
            else:
                await sendMessageWithExpiration(interaction, "You have no bait", 10)
                return
        case "mab":
            if checkReq(interaction.user.id, 1, "Bait", "Master Bait"):
                fish = random.choices([const.fish_common, const.fish_uncommon, const.fish_rare, const.fish_leg], weights=[100, 400, 400, 100], k=1)[0]
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

            data[user_id_str]["Fish"][rarity] += 1

            save_data(data)
        else:
            self.result = "Missed!"
            await interaction.edit_original_response(content="💨 The fish got away!", view=None)

@client.tree.command(name="inventory", description="Display a players inventory", guild=GUILD_ID)
async def inventory(interaction: discord.Interaction, user: discord.User = None):
    data = load_data()
    user_id_str = ""
    user_name = ""
    if user:
        user_id_str = str(user.id)
        user_name = user.display_name
    else:
        user_id_str = str(interaction.user.id)
        user_name = interaction.user.display_name
    msg = f"**{user_name}'s Inventory** \n Cash {const.cash}: {data[user_id_str]["Cash"]} \n *Fish:* \n Common {const.fish_common}: {data[user_id_str]["Fish"]["Common"]} \n Uncommon {const.fish_uncommon}: {data[user_id_str]["Fish"]["Uncommon"]} \n Rare {const.fish_rare}: {data[user_id_str]["Fish"]["Rare"]} \n Legendary {const.fish_leg}: {data[user_id_str]["Fish"]["Legendary"]} \n *Bait* \n Basic {const.bait_basic}: {data[user_id_str]["Bait"]["Basic Bait"]} \n Advanced {const.bait_advanced}: {data[user_id_str]["Bait"]["Advanced Bait"]} \n Master {const.bait_master}: {data[user_id_str]["Bait"]["Master Bait"]}"
    await sendMessageWithExpiration(interaction, msg, 40)

async def sendMessageWithExpiration(interaction, msg_str, delay):
    await interaction.response.send_message(f"{msg_str}")
    msg = await interaction.original_response()
    await asyncio.sleep(delay)
    await msg.delete()

@client.tree.command(name="casino", description="Casino", guild=GUILD_ID)
@app_commands.describe(game="Casino game", bet_color="Pick color", amount="How much would you like to bet?")
@app_commands.choices(game=[app_commands.Choice(name="Roulette", value="roulette"), ], bet_color=[app_commands.Choice(name="Red 🔴", value="red"), app_commands.Choice(name="Black ⚫", value="black"), app_commands.Choice(name="Green 🟢", value="green"),])
async def casino(interaction: discord.Interaction, game: app_commands.Choice[str], bet_color: app_commands.Choice[str], amount: int):
    checkExist(interaction.user.id)

    if amount > 0:
        if checkReq(interaction.user.id, amount, "Cash"):
            match game.value:
                case "roulette":
                    n = random.randrange(0, 17)
                    if bet_color.value == "green" and n == 16:
                        win = amount * 16
                        updateMoney(interaction.user.id, win)
                        await sendMessageWithExpiration(interaction, f"You bet {amount} on {bet_color.value} won {win} cash :D", win**1.5 + 10)
                    elif bet_color.value == "red" and n <16 and n >= 9:
                        win = amount * 2
                        updateMoney(interaction.user.id, win)
                        await sendMessageWithExpiration(interaction, f"You bet {amount} on {bet_color.value} won {win} cash :D", win**1.5 + 10)
                    elif bet_color.value == "black" and n < 9:
                        win = amount * 2
                        updateMoney(interaction.user.id, win)
                        await sendMessageWithExpiration(interaction, f"You bet {amount} on {bet_color.value} won {win} cash :D", win**1.5 + 10)
                    else:
                        await sendMessageWithExpiration(interaction, f"You bet {amount} on {bet_color.value} lost :(", amount**1.5 + 10)
        else:
            await interaction.response.send_message(f'You are too broke, get a job', ephemeral = True)
    else:
        await interaction.response.send_message(f'You can not bet below 1', ephemeral=True)
   
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
            description = f"{'Cost' if action == "Buy" else 'Sell for'}: {price} cash"
            )
            for item_name, price in items.items()
        ]
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

        quantities = range(1, min(max_quantity, 25) + 1)

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


def checkExist(user_id: int):
    data = load_data()
    user_id_str = str(user_id)

    default_data = {"Cash": 10, "Level":0, "xp": 0, "Work": "00-01-01", "Fish": {"Common": 0, "Uncommon": 0, "Rare": 0, "Legendary": 0}, "Bait": {"Basic Bait": 0, "Advanced Bait": 0, "Master Bait": 0, "Mystery Bait": 0}}

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

def incrementXp(id):
    checkExist(id)
    data = load_data()
    user_id_str = str(id)

    data[user_id_str]["xp"] += 1

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
    reqXp = (data[user_id_str]["Level"] + 1) * 10
    level_up = False
    level = data[user_id_str]["Level"]
    if data[user_id_str]["xp"] >= reqXp:
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
