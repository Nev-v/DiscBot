import discord
from discord.ext import commands
from discord import app_commands
import sys
import os

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
        if after.author == self.user:
            return
        
        await after.channel.send(f'Blod ändrade "{before.content}" till "{after.content}"')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = Client(command_prefix="!", intents=intents)
client.run(const.token)

GUILD_ID = discord.Object(id=286827966783029248)

@client.tree.command(name="soundboard", description="Play a sound", guild=GUILD_ID)
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()