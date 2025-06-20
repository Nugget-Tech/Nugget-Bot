import json
import asyncio

from discord.ext import commands
from modules.DiscordBot import Gemini
from modules.CommonCalls import CommonCalls
from modules.ManagedMessages import ManagedMessages
from discord import Message, AllowedMentions, Reaction, Member

allowed_mentions = AllowedMentions(everyone=False, users=False, roles=False)
activation_path = f"data/{CommonCalls.config()['alias']}-activation.json"


class GeminiCog(commands.Cog):

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    def is_activated(self, channel_id) -> bool:
        try:
            with open(activation_path, "r") as ul_activation:
                activated: dict = json.load(ul_activation)
                debug_mode = CommonCalls.config().get("debugMode")
                if debug_mode == "on":
                    print(
                        "[BOT][INFO] | Activated channels function call `is_activated` (Message from line 24 @ cogs/gemini.py)"
                    )
                return bool(activated.get(str(channel_id), False))
        except FileNotFoundError:
            with open(activation_path, "w") as E:
                E.write("{}")
                E.close()

    @commands.Cog.listener("on_message")
    async def listen(self, message: Message):
        channel_id = message.channel.id
        ctx = await self.bot.get_context(message)

        if message.author.id == self.bot.user.id:
            return

        if ctx.valid:
            return

        if self.bot.user.mentioned_in(message) or self.is_activated(channel_id):
            pass
        else:
            return

        async with message.channel.typing():
            await asyncio.sleep(2)

        try:
            response = await Gemini.generate_response(
                message, await self.bot.get_context(message)
            )

            if type(response) == tuple:
                print("Voice mode on!")
                text = await message.reply(file=response[1])
                await ManagedMessages.add_to_message_list(
                    channel_id=channel_id,
                    message_id=text.id,
                    message=f"{CommonCalls.load_character_details()['name']}: {response[0]}",
                    mention_author=False,
                )
                return

            if response == "[]":
                return await message.reply(
                    CommonCalls.config()["error_message"], mention_author=False
                )

            chunks = [response[i : i + 2000] for i in range(0, len(response), 2000)]

            for chunk in chunks:
                try:
                    text = await message.reply(
                        chunk, mention_author=False, allowed_mentions=allowed_mentions
                    )
                    await ManagedMessages.add_to_message_list(
                        channel_id=channel_id,
                        message_id=text.id,
                        message=f"{CommonCalls.load_character_details()['name']}: {text.content}",
                        mention_author=False,
                    )
                except Exception as E:
                    print(f"Error replying response: {E}")

        except Exception as E:
            debug_mode = CommonCalls.config().get("debugMode")
            if debug_mode == "on":
                return await message.reply(
                    f"""{CommonCalls.config()["error_message"]}\nFault located in cogs/gemini @ L84 , error message @ L65.\nException:\n{E}\n-# Why did *I* get this? Learn more at <insert docs link>#debugMode""",
                    mention_author=False,
                )
            else:
                return await message.reply(
                    CommonCalls.config()["error_message"], mention_author=False
                )

    @commands.Cog.listener("on_reaction_add")
    async def on_rxn_add(self, reaction: Reaction, user: Member):
        channel_id = reaction.message.channel.id

        match reaction.emoji:

            case "🔇":
                await ManagedMessages.remove_from_message_list(
                    channel_id, reaction.message.id
                )
                debug_mode = CommonCalls.config().get("debugMode")
                if debug_mode == "on":
                    print(f"Removed message ID ({reaction.message.id}) from STM")

            case _:

                if (
                    reaction.message.author.id is not self.bot.user.id
                    and not reaction.is_custom_emoji()
                ):
                    return

                if channel_id not in ManagedMessages.context_window:
                    ManagedMessages.context_window[channel_id] = []
                    print(reaction.emoji)

                await ManagedMessages.add_to_message_list(
                    channel_id,
                    reaction.message.id,
                    f"{user.name} reacted with '{reaction.emoji}' to your message '{reaction.message.content}'",
                )


def setup(bot: commands.Bot):
    bot.add_cog(GeminiCog(bot))
