import asyncio
from io import BytesIO
from pprint import pformat, pprint
from typing import Union
from urllib.parse import unquote

import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from utils.checks import *
from utils.paginator import Paginator


def elongate(string: str, length: int):
    done = f"{string}{' ' * (length - len(string))}"
    return done


class Api(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.endpoints = [
            "allitems",
            "children",
            "guild",
            "helpme",
            "inventory",
            "loot",
            "market",
            "pets",
            "profile",
            "server",
            "transactions",
            "user_settings",
        ]

    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command()
    async def get(self, ctx, *, query: str):
        """
        Get data from the API with a query, returned in JSON format.
        If the output is too long, it will be put in an attached txt file.

        The "https://public-api.travitia.xyz/idle/" part of the URL does not need to be included.
        """
        if (
            not query.startswith("https://public-api.travitia.xyz/idle/")
            and not query.split("?")[0] in self.endpoints
        ):
            return await ctx.send(
                "Invalid query! Please make sure your URL starts with"
                " `https://public-api.travitia.xyz/idle/` and it includes a valid"
                " endpoint:\n\n`{0}`".format(", ".join(self.endpoints))
            )
        query = (
            "https://public-api.travitia.xyz/idle/" + query
            if not query.startswith("https://public-api.travitia.xyz/idle/")
            else query
        )
        color = 0x00FF00
        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query, headers={"Authorization": self.bot.config.api_token}
        ) as r:
            status = r.status
            if status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
                elif status == 429:
                    return await ctx.send(
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
                color = 0xFF0000
            res = await r.json()

        if len(str(res)) > 1500:
            File = discord.File(
                filename="result.txt", fp=BytesIO(pformat(res).encode())
            )
            nres = (
                "{0} entries found, content too long to display. Try paginating"
                " (&limit=10&offset=5), reducing the page size when paginating, or"
                " selecting fewer columns. The full result is attached.".format(
                    len(res)
                )
            )
        else:
            File = None
            nres = pformat(await r.json()).replace(
                "`", "\u200b`\u200b"
            )  # inaccurate, but doesn't break the codeblock in display
        embed = discord.Embed(
            title=str(status),
            description="{0}\n```py\n{1}\n```".format(query, nres),
            color=color,
        )
        await ctx.send(embed=embed, file=File)

    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command()
    async def items(self, ctx, user: int = None):
        """
        Get a user's equipped items.
        [user] is a user ID. If not given, the author's ID is used.
        """
        user = user or ctx.author.id
        person = await self.bot.fetch_user(user)
        query = f"https://public-api.travitia.xyz/idle/allitems?select=id,damage,armor,name,type,inventory(equipped)d&owner=eq.{user}&inventory.equipped=is.true"
        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query, headers={"Authorization": self.bot.config.api_token}
        ) as r:
            status = r.status
            if status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
                elif status == 429:
                    return await ctx.send(
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()
            if not res:
                res = "This user has no items equipped or does not have a profile!"
            else:
                res = pformat([r for r in res if r["inventory"]])
        embed = discord.Embed(
            title=f"{person}'s equipped items:",
            description="```py\n{0}\n```".format(res),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)

    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command(aliases=["p", "pp", "me"])
    async def profile(
        self, ctx, *, user: Union[discord.User, discord.Member, int] = None
    ):
        user = user or ctx.author
        if isinstance(user, (discord.Member, discord.User)):
            person = str(user)
            user = user.id
        else:
            try:
                person = await self.bot.fetch_user(user)
            except discord.NotFound:
                return await ctx.send("This user does not exist.")
        query = f"https://public-api.travitia.xyz/idle/profile?user=eq.{user}"
        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query, headers={"Authorization": self.bot.config.api_token}
        ) as r:
            status = r.status
            if status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
                elif status == 429:
                    return await ctx.send(
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()
            if not res:
                ponse = "This user has no profile!"
            else:
                dic = res[0]
                max_len = 0
                for item in dic.keys():
                    if len(str(item) + ":") > max_len:
                        max_len = len(str(item))
                ponse = "\n".join(
                    [f"{elongate(x[0]+':', max_len)} {x[1]}" for x in dic.items()]
                )

            embed = discord.Embed(
                title=f"{person}'s profile",
                description=f"""\
```
{ponse}
```
""",
            )
            await ctx.send(embed=embed)

    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command()
    async def merge(self, ctx, item: Union[int, str]):
        """Finds an item that would be ideal to merge, based on the given item ID or type.

        Equipped items, as well as items with a signature are automatically filtered out."""

        if isinstance(item, int):
            query = f"https://public-api.travitia.xyz/idle/allitems?select=*,inventory(equipped)&id=eq.{item}"

        else:
            valid_types = {
                "Sword": "any",
                "Shield": "left",
                "Axe": "any",
                "Wand": "right",
                "Dagger": "any",
                "Knife": "any",
                "Spear": "right",
                "Bow": "both",
                "Hammer": "any",
                "Scythe": "both",
                "Howlet": "both",
            }

            item = item.title().strip()
            if item not in valid_types.keys():
                return await ctx.send(f"`{item}` is not a valid item type.")

            max_ = 82 if valid_types[item] == "both" else 41
            doa = "armor" if item == "Shield" else "damage"
            query = (
                f"https://public-api.travitia.xyz/idle/allitems?"
                f"select=*,inventory(equipped)&type=eq.{item.title()}&order={doa}.desc&{doa}=lt.{max_}"
                f"&owner=eq.{ctx.author.id}&limit=1"
            )
            # query gets the highest, still mergeable item of that type

        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query,
            headers={"Authorization": self.bot.config.api_token},
        ) as r:
            status = r.status
            if status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
                elif status == 429:
                    return await ctx.send(
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()
        if not res:
            if isinstance(item, int):
                return await ctx.send(
                    f"Item `{item}` was not found; check if the ID is right"
                )
            return await ctx.send(
                f"Seems you don't have any `{item}`s (or all `{item}`s you have are above max merge stat)"
            )

        res = res[0]

        if (res["hand"] == "both" and res["damage"] >= 82) or (
            res["hand"] in ["left", "right", "any"]
            and res["damage"] + res["armor"] >= 41
        ):
            return await ctx.send(
                "This item is already at max mergeable stat or above."
            )

        item_id = res["id"]
        doa = "armor" if res["type"] == "Shield" else "damage"
        absmax_ = 82 if res["hand"] == "both" else 41

        if res["owner"] != ctx.author.id:
            if not await ctx.confirm(
                "This item does not belong to you, continue anyway?"
            ):
                return await ctx.send("Command cancelled.")
        if res["inventory"][0]["equipped"]:
            if not await ctx.confirm(
                "This item is currently equipped, continue anyway?"
            ):
                return await ctx.send("Command cancelled.")
        query = (
            "https://public-api.travitia.xyz/idle/allitems?select=*,inventory(equipped)&armor=gte."
            "{_min}&armor=lte.{_max}&type=eq.{_type}&inventory.equipped=is.true&order=armor.asc&signature=is.null"
            "&owner=eq.{owner}".format(
                _min=res["armor"] - 5,
                _max=absmax_ if res["armor"] + 5 >= absmax_ else res["armor"] + 5,
                _type=res["type"],
                owner=res["owner"],
            )
            if res["type"] == "Shield"
            else "https://public-api.travitia.xyz/idle/allitems?select=*,inventory(equipped)&damage=gte."
            "{_min}&damage=lte.{_max}&type=eq.{_type}&inventory.equipped=is.true&order=damage.asc&signature=is.null"
            "&owner=eq.{owner}".format(
                _min=res["damage"] - 5,
                _max=absmax_ if res["damage"] + 5 >= absmax_ else res["damage"] + 5,
                _type=res["type"],
                owner=res["owner"],
            )
        )

        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query, headers={"Authorization": self.bot.config.api_token}
        ) as r:
            status = r.status
            if status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
                elif status == 429:
                    return await ctx.send(
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            nres = await r.json()

        if not nres:
            return await ctx.send("No fitting items found...")

        items = sorted(
            [item for item in nres if not (item["inventory"] or item["id"] == item_id)],
            key=lambda x: x["armor" if res["type"] == "Shield" else "damage"],
        )

        if not items:
            return await ctx.send("No fitting items found...")

        warn = (
            f":warning: The best possible item has a higher {doa} than the original item. Consider switching the IDs around."
            if (items[0]["damage"] + items[0]["armor"] > res["damage"] + res["armor"])
            else ""
        )

        await ctx.send(
            f"""\
{warn}

Found {len(items)} mergable item(s).

{item_id}: {res["damage"]+res["armor"]} {doa} {res["type"]} + 
{items[0]["id"]}: {items[0]["damage"] + items[0]["armor"]} {doa} {items[0]["type"]}
==========
{item_id}: {res["damage"]+res["armor"] + 1} {doa} {res["type"]}

`$merge {item_id} {items[0]["id"]}`"""
        )


    @commands.cooldown(1, self.bot.config.api_cooldown, BucketType.user)
    @commands.command(aliases=["item", "i"])
    async def iteminfo(self, ctx, itemid: int):
        """Get an info on an item, from its owner to signature and stats."""
        query = f"https://public-api.travitia.xyz/idle/allitems?id=eq.{itemid}"

        await self.bot.check_for_error_500()
        async with self.bot.session.get(
            query, headers={"Authorization": self.bot.config.api_token}
        ) as r:
            status = r.status
            if status != 200:
                if int(status / 100) == 5:
                    await self.bot.redis.execute(
                        "SET", f"travapi:520", "timeout", "EX", 3600
                    )
                    return await ctx.send(
                        "The API returned a 5XX error code. This means it is currently not available."
                        " Please try again in one hour."
                    )
                elif status == 429:
                    return await ctx.send(
                        "429: Too many requests. The API only allows three requests per"
                        " ten seconds."
                    )
            res = await r.json()

        if not res:
            return await ctx.send(
                f"""The item with the ID `{itemid}` was not found. This might mean:
  - You mistyped the ID
  - The item does not exist *yet*
  - The item does not exist *anymore* (most likely merched)"""
            )

        item = res[0]

        pn = "An" if item["type"].startswith(("A", "E", "I", "O", "U")) else "A"
        doa = "armor" if item["type"] == "Shield" else "damage"
        stat = item["damage"] + item["armor"]
        owner = await self.bot.fetch_user(item["owner"])

        embed = discord.Embed(
            title=item["name"],
            description=f"{pn} {item['type'].lower()} with {stat} {doa}",
        )
        # embed.add_thumbnail(url=f"attachment://{item['type']}.png")
        embed.add_field(
            name="Currently owned by", value=f"{owner} ({item['owner']})", inline=False
        )
        embed.add_field(
            name="General info",
            value="Item ID: {0}\nItem value: {1}\nHand used: {2}".format(
                itemid, item["value"], item["hand"]
            ),
            inline=False,
        )

        if item["signature"]:
            embed.add_field(name="Signature", value=item["signature"], inline=False)
        if item["original_type"]:
            pn = (
                "An"
                if item["original_type"].startswith(("A", "E", "I", "O", "U"))
                else "A"
            )
            embed.add_field(
                name="Original Type",
                value=f"This item was originally {pn} {item['original_type']}",
            )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Api(bot))
