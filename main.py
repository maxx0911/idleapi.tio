import asyncio
import datetime
import os
import traceback

import aioredis
import asyncpg
from aiohttp import ClientSession
from discord.ext import commands

import config
from classes.bot import Bot


async def run():
    bot = Bot(command_prefix=commands.when_mentioned_or(config.command_prefix))
    bot.remove_command("help")

    bot.pool = await asyncpg.create_pool(**config.postgres_login)
    bot.redis = await aioredis.create_pool("redis://localhost")
    bot.session = ClientSession()
    bot.config = config
    bot.started_at = datetime.datetime.now()

    try:
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                try:
                    bot.load_extension(f"cogs.{file[:-3]}")
                    print("successfully loaded cog", file[:-3])
                except Exception:
                    with open("error.log", "a+") as error_log:
                        error_log.write(
                            "#############################################\n"
                        )
                        traceback.print_exc(file=error_log)
                    error_log.close()
                    print(f"# Error loading {file}! See error.log for more info.")
        bot.load_extension("jishaku")
        await bot.start(config.token)
    except KeyboardInterrupt:
        await bot.logout()


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
