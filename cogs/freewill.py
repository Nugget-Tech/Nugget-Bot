import json
import random
import asyncio

from discord import Message, AllowedMentions
from discord.ext import commands
from modules.DiscordBot import Gemini
from modules.ManagedMessages import ManagedMessages
from modules.CommonCalls import CommonCalls
from typing import List, Any

allowed_mentions = AllowedMentions(everyone=False, users=False, roles=False)
activation_path = f"data/{CommonCalls.config().get('alias')}-activation.json"


class Freewill(commands.Cog):

    def __init__(self, bot) -> None:
        self.bot: commands.Bot = bot

    def is_activated(self, channel_id) -> bool:
        with open(activation_path, "r") as ul_activation:
            activated: dict = json.load(ul_activation)
            print(
                "[BOT][INFO] | Activated channels function call `is_activated` (Message from line 23 @ cogs/new_freewill.py)"
            )
            return bool(activated.get(str(channel_id), False))

    @commands.Cog.listener("on_message")
    async def freewill(self, message: Message) -> None:
        if CommonCalls.config().get("freewill") == "on":  # TODO implement

            ctx = await self.bot.get_context(message)

            if ctx.valid:
                return

            if ctx.message.author.id == self.bot.user.id:
                return

            if self.bot.user.mentioned_in(message) or self.is_activated(ctx.channel.id):
                return

            text_frequency = float(CommonCalls.config().get("textFrequency", 0)) * 0.01
            reaction_frequency = (
                float(CommonCalls.config().get("reactionFrequency", 0)) * 0.01
            )
            keywords = CommonCalls.config().get("keywords", [])
            keyword_added_chance = 0

            for i in keywords:
                if i.lower() in message.content.lower():
                    keyword_added_chance = (
                        float(CommonCalls.config().get("keywordChance")) * 0.01
                    )

            if random.random() < min(text_frequency + keyword_added_chance, 1.0):
                try:
                    response = await Gemini.generate_response(
                        message, await self.bot.get_context(message)
                    )

                except Exception as E:
                    debug_mode = CommonCalls.config().get("debugMode")
                    if debug_mode == "on":
                        return await message.reply(
                            f"""{CommonCalls.config().get("error_message")}\nFault located @ freewill, error message @ L65.\nException:\n{E}\n
                            -# Why did *I* get this? Learn more at <insert docs link>#debugMode
                            """,
                            mention_author=False,
                        )
                    else:
                        return await message.reply(
                            CommonCalls.config().get(
                                ["error_message"],
                            ),
                            mention_author=False,
                        )

                if type(response) == tuple:
                    print("Voice mode on!")
                    text = await message.reply(file=response[1], mention_author=False)
                    await ManagedMessages.add_to_message_list(
                        channel_id=ctx.channel.id,
                        message_id=text.id,
                        message=f"{CommonCalls.load_character_details()['name']}: {response[0]}",
                    )
                    return

                async with message.channel.typing():
                    await asyncio.sleep(2)  # artificial delay lol

                chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]

                for chunk in chunks:
                    try:
                        text = await message.reply(
                            chunk,
                            mention_author=False,
                            allowed_mentions=allowed_mentions,
                            mention_author=False,
                        )
                        await ManagedMessages.add_to_message_list(
                            channel_id=ctx.channel.id,
                            message_id=text.id,
                            message=f"{CommonCalls.load_character_details()['name']}: {text.content}",
                        )
                    except Exception as E:
                        print(f"Error replying response: {E}")

            if random.random() < min(reaction_frequency + keyword_added_chance, 1.0):
                try:
                    response = await Gemini.generate_response(
                        message, await self.bot.get_context(message)
                    )

                except Exception as E:
                    debug_mode = CommonCalls.config().get("debugMode")
                    if debug_mode == "on":
                        return await message.reply(
                            f"""{CommonCalls.config().get("error_message")}\nFault located @ freewill, error message @ L112.\nException:\n{E}\n
                            -# Why did *I* get this? Learn more at <insert docs link>#debugMode
                            """,
                            mention_author=False,
                        )
                    else:
                        return await message.reply(
                            CommonCalls.config().get("error_message"),
                            mention_author=False,
                        )

                async with message.channel.typing():
                    await asyncio.sleep(2)  # artificial delay lol

                chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]

                for chunk in chunks:
                    try:
                        text = await message.reply(
                            chunk,
                            mention_author=False,
                            allowed_mentions=allowed_mentions,
                            mention_author=False,
                        )
                        await ManagedMessages.add_to_message_list(
                            channel_id=ctx.channel.id,
                            message_id=text.id,
                            message=f"{CommonCalls.load_character_details()['name']}: {text.content}",
                        )
                    except Exception as E:
                        print(f"Error replying response: {E}")


def setup(bot: commands.Bot):
    bot.add_cog(Freewill(bot))
