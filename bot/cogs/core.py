import discord
from discord.ext import commands


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['prefix'])
    async def change_prefix(self, ctx, *, prefix: str = ""):
        if prefix == "":
            await ctx.send("Prefix can't be blank")
            return
        self.bot.command_prefix = prefix
        await ctx.send("Prefix updated to " + prefix)


def setup(bot):
    bot.add_cog(Core(bot))
