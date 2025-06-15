from discord.ext import commands
from discord import Member, VoiceState
from modules.Voice import VoiceCalls, connections


class voicechannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if (
            member.id == self.bot.user.id
        ):  # THIS IS TEMPORARY, IF YOU SEE THIS REPLACE THAT ID WITH YOUR BOTS ID
            return

        if (
            before.channel is not None and after.channel is None
        ):  # Detects if someone leaves
            print("PRE update connections", connections)
            del connections[member.guild.id]
            print("POST update connections", connections)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(voicechannel(bot))
