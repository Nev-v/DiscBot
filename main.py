import discord # type: ignore
from discord.ext import commands # type: ignore
import sys
import os
import asyncio
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ghp import const # type: ignore

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

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
        print("Edit detected")
        if after.author.bot:
            return
        
        if after.content:
            await after.channel.send(f'Blod ändrade "{before.content}" till "{after.content}"')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=286827966783029248)

async def leave(voice_client, message):
    await message.delete()

    await voice_client.disconnect()

def after_played(voice_client, message):
    asyncio.run_coroutine_threadsafe(leave(voice_client, message), client.loop)

@client.tree.command(name="soundboard", description="Play a sound", guild=GUILD_ID)
async def join(ctx, filename: str):
    if ctx.user.voice:

        channel = ctx.user.voice.channel
        voice_client = ctx.guild.voice_client

        if voice_client is None or not voice_client.is_connected():
            voice_client = await channel.connect()

        search_pattern = os.path.join(const.audios, f"{filename}.*")
        matches = glob.glob(search_pattern)

        if not matches:
            await ctx.response.send_message(f"❌ No sound file found for '{filename}'")

        file_path = matches[0]
        if not os.path.isfile(file_path):
            print(f"❌ File not found at: `{file_path}`")
            return
        
        audio_source = discord.FFmpegPCMAudio(file_path)
        message = await ctx.response.send_message(f'Playing "{filename}"')

        voice_client.play(audio_source, after=lambda e: after_played(voice_client, message))

@client.tree.command(name="list", description="Display all playable sounds", guild=GUILD_ID)
async def list(ctx):
    files = os.listdir(const.audios)

    sound_files = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.ogg'))]

    sound_names = [os.path.splitext(f)[0] for f in sound_files]

    if not sound_names:
        await ctx.response.send_message("❌ No sounds")

    sound_list = ", ".join(sound_names)

    await ctx.response.send_message(f"**Available sounds:**  {sound_list}")


client.run(const.token)
