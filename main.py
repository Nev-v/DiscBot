import discord # type: ignore
from discord.ext import commands # type: ignore
import sys
import os
import asyncio
import glob
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ghp import const # type: ignore

#GLOBAL VARIABLES
msg = {}
queue = []

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
        
        await play(ctx, filename, file_path, voice_client)
        

async def play(ctx, filename: str, file_path, voice_client):
    
    audio_source = discord.FFmpegPCMAudio(file_path)

    if not voice_client.is_playing():
        if ctx.guild_id in msg:
            try:
                playMsg = msg[ctx.guild_id]
                await playMsg.edit(content=f"Now playing: 🎵 {filename}")
            except discord.NotFound:
                pass
        else:
            await ctx.response.send_message(f'Now playing: 🎵 {filename}')
            playMsg = await ctx.original_response()
            msg[ctx.guild_id] = playMsg
        voice_client.play(audio_source, after=lambda e: after_played(voice_client, ctx, file_path))
    else:
            queue.append(filename)
            print(f'Added {filename} to queue: {queue}')

def after_played(voice_client, ctx):
    asyncio.run_coroutine_threadsafe(leave(voice_client, ctx), client.loop)

async def leave(voice_client, ctx):
    print(f"{queue}")
    if len(queue) == 0:
        await voice_client.disconnect()
        print("Queue is empty, leaving")
        playMsg = msg.get(ctx.guild_id)
        if playMsg:
            await playMsg.delete()
    else:
        next_filestr = queue.pop(0)
        search_pattern = os.path.join(const.audios, f"{next_filestr}.*")
        matches = glob.glob(search_pattern)
        file_path = matches[0]
        await play(ctx, next_filestr, file_path, voice_client)

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

@client.tree.command(name="leaderboard", description="Leaderboard of server", guild=GUILD_ID)
async def leaderboard(ctx, top_n: int = 10):
    data = load_data()

    sorted_users = sorted(data.items(), key=lambda x: x[1].get("Cash", 0), reverse=True)

    leaderboardStr = ""
    for i, (user_id, info) in enumerate(sorted_users[:top_n], start=1):
        money = info.get("Cash", 0)
        user = await client.fetch_user(user_id)
        leaderboardStr += f"**{i}.** {user.display_name} - {money} Cash\n"

    await ctx.response.send_message(f"**Leaderboard** \n\n{leaderboardStr}")

@client.tree.command(name="casino", description="Casino", guild=GUILD_ID)
async def casino(interaction: discord.Interaction):
    checkExist(interaction.user.id)


def checkExist(user_id: int):
    data = load_data()
    user_id_str = str(user_id)

    if user_id_str not in data:
        data[user_id_str] = {"Cash": 10, "Level":0}
        save_data(data)

def load_data():
    if not os.path.exists(const.data_file):
        return {}
    with open(const.data_file, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    print("Save")
    with open(const.data_file, "w") as f:
        json.dump(data, f, indent=4)

client.run(const.token)
