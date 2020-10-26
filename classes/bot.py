import datetime

from discord.ext import commands

from classes.context import Context
from utils.checks import ApiIsDead


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.launch_time = datetime.datetime.now()

    async def on_message(self, message):
        if (message.author.id in self.config.bans) or (message.author == self.user):
            return
        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await super().get_context(message, cls=Context)
        await super().invoke(ctx)

    async def check_for_error_500(self):
        ttl = await self.redis.execute("TTL", f"travapi:520")
        if ttl == -2:
            return True
        else:
            raise ApiIsDead(ttl)
