import io
import os
import asyncio
import discord

from elevenlabs.client import ElevenLabs
from elevenlabs import stream
from typing import Dict
from discord.ext import commands


from modules.BotModel import BotModel
from modules.CommonCalls import CommonCalls
from modules.DiscordBot import headless_Gemini

# store active voice connections per guild
connections: Dict[int, discord.VoiceClient] = {}


class ElevenLabsAudio:
    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)

    def generate_audio(self, text: str, voice: str = "Antoni") -> bytes:
        """
        Generate raw audio bytes from ElevenLabs.
        """
        tts = self.client.generate(
            text=text, voice=voice, model="eleven_multilingual_v2"
        )
        return stream(tts)

    async def stream_to_discord(
        self, voice_client: discord.VoiceClient, audio_bytes: bytes
    ):
        """
        Play the given audio bytes in a Discord voice channel.
        """
        buf = io.BytesIO(audio_bytes)
        voice_client.play(discord.FFmpegPCMAudio(buf, pipe=True))
        # wait until playback finishes
        while voice_client.is_playing():
            await asyncio.sleep(1)

    def save_to_mp3(self, audio_bytes: bytes, filename: str):
        """
        Save the raw audio bytes into an MP3 file on disk.
        """
        with open(filename, "wb") as f:
            f.write(audio_bytes)


class DiscordVoiceManager:
    def __init__(self, audio_generator: ElevenLabsAudio):
        self.audio = audio_generator

    async def start_recording(self, ctx: commands.Context):
        voice = ctx.author.voice
        if not voice:
            await ctx.send("You aren't in a voice channel!")
            return

        # join or reuse
        if ctx.guild.id in connections and connections[ctx.guild.id].is_connected():
            vc = connections[ctx.guild.id]
        else:
            try:
                vc = await voice.channel.connect()
            except discord.ClientException:
                await ctx.send("I couldn't connect. Check my permissions.")
                return
            connections[ctx.guild.id] = vc

        vc.start_recording(
            discord.sinks.WaveSink(), self._once_done, ctx.channel, vc, ctx
        )
        await ctx.send("Listening...")
        await asyncio.sleep(float(CommonCalls.config()["recording-time"]))
        vc.stop_recording()

    async def stop_recording(self, ctx: commands.Context):
        vc = connections.get(ctx.guild.id)
        if vc and vc.is_connected():
            await vc.disconnect()
            del connections[ctx.guild.id]
            await ctx.send("Disconnected from voice.")
        else:
            await ctx.send("I’m not in a voice channel.")

    async def _once_done(
        self,
        sink: discord.sinks,
        channel: discord.TextChannel,
        voice_client: discord.VoiceClient,
        ctx: commands.Context,
    ):
        # for each speaker
        for user_id, audio in sink.audio_data.items():
            fname = f"./{user_id}.{sink.encoding}"
            with open(fname, "wb") as f:
                audio.file.seek(0)
                f.write(audio.file.read())

            # upload & transcribe
            file = await BotModel.upload_attachment(fname)
            stt = await BotModel.speech_to_text(audio_file=file)

            # generate response
            resp = await headless_Gemini.generate_response(
                channel_id=channel.id, author_name=ctx.author, author_content=stt
            )

            # play back
            audio_bytes = self.audio.generate_audio(text=resp)
            await self.audio.stream_to_discord(voice_client, audio_bytes)

            # cleanup
            os.remove(fname)
            await BotModel.delete_attachment(file.name)

            # restart if still connected
            if voice_client.is_connected():
                vc = connections.get(ctx.guild.id)
                vc.start_recording(
                    discord.sinks.WaveSink(), self._once_done, channel, vc, ctx
                )
                await asyncio.sleep(float(CommonCalls.config()["recording-time"]))
                vc.stop_recording()
