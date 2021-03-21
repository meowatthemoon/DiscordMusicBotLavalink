from pathlib import Path

import discord
from discord.ext import commands


class Bot(commands.Bot):
    def __init__(self):
        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")]
        super().__init__(command_prefix=".", case_insensitive=True, intents=discord.Intents.all())

    def run(self):
        for cog in self._cogs:
            self.load_extension(f"bot.cogs.{cog}")

        with open("data/token.0", "r", encoding="utf-8") as f:
            TOKEN = f.read()

        super().run(TOKEN, reconnect=True)

    async def on_ready(self):
        self.client_id = (await self.application_info()).id
        print("Bot ready :" + discord.__version__)



    """
        async def prefix(self, bot, msg):
        return commands.when_mentioned_or(".")(bot, msg)
    async def process_commands(self, message):
        ctx = await self.get_context(message, cls =commands.Context)

        if ctx.command is not None:
            await self.invoke(ctx)

    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)
    
    async def on_command_error(self, context, exception):
        raise getattr(exception, "original", exception)
    
    async def on_error(self, event_method, *args, **kwargs):
        raise
    
    async def on_connect(self):
        print(f"Connected to Discord (latency = {self.latency * 1000:,.0f} ms).")

    async def on_resume(self):
        print("Bot resumed.")

    async def on_disconnect(self):
        print("Bot disconnected.")
    """
