import datetime
import platform

import discord
import humanize
import psutil
from discord.ext import commands


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """View the current ping."""
        real_ping = int(
            (datetime.datetime.now() - ctx.message.created_at).microseconds / 1000
        )
        websocket = int(self.bot.latency * 1000)
        embed = (
            discord.Embed(title="Pong!", color=discord.Color.blurple())
            .add_field(name=":heartbeat: Websocket Latency", value=f"{websocket}ms")
            .add_field(name=":timer: Actual Latency", value=f"{real_ping}ms")
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """View how long the bot has been online for."""
        uptime_ = ".".join(
            str(datetime.datetime.now() - self.bot.started_at).split(".")[:-1]
        )
        return await ctx.send(f"I've been online for **{uptime_}**!")

    @commands.command(aliases=["statistics"])
    async def stats(self, ctx):
        """View some statisics about the bot."""
        meminfo = psutil.virtual_memory()
        embed = discord.Embed(title="Statistics", color=discord.Color.blurple())
        embed.add_field(name="CPU info", value=f"**{psutil.cpu_percent()}%** used")
        embed.add_field(
            name="RAM info",
            value=(
                f"**{meminfo.percent}%** of {humanize.naturalsize(meminfo.total)} used"
            ),
        )
        embed.add_field(
            name="Development",
            value=(
                f"Python Version: {platform.python_version()}\ndiscord.py Version:"
                f" {discord.__version__}"
            ),
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["src"])
    async def source(self, ctx):
        """Check out the inner workings of idleAPI.tio and host your own instance"""
        await ctx.send("Check out https://github.com/maxx0911/idleapi.tio")


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
