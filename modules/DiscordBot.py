"""
This is the API for discord interactions.
"""

import os
import random

from discord import Message
from discord.ext import commands
from discord.file import VoiceMessage
from modules.Memories import Memories
from modules.Knowledge import Knowledge
from modules.BotModel import read_prompt, BotModel, headless_BotModel
from modules.ManagedMessages import ManagedMessages, headless_ManagedMessages
from modules.AIAgent import AIAgent
from modules.CommonCalls import CommonCalls
from modules.Voice import VoiceMessages
from modules.AudioUtils import AudioUtils

context_window = ManagedMessages().context_window
memories = Memories()


class Gemini:

    async def generate_response(message: Message, ctx: commands.Context):
        """Accepts discord.Message object and auto-handles everything"""

        message = ctx.message
        guild_id = ctx.guild.id
        channel_id = ctx.message.channel.id  # declare channel id for the context window
        message_id = ctx.message.id  # declare message id
        attachments = ctx.message.attachments  # declare message attachments
        config = CommonCalls.config()
        voice_mode_trigger_chance = config["voiceChance"]
        voice_response = False
        if (
            random.random() < float(voice_mode_trigger_chance)
            and config["voiceMessages"] == "on"
        ):
            voice_response = True

        if channel_id not in context_window:
            context_window[channel_id] = (
                []
            )  # if channel id isnt present in context window, make a new key

        message_in_list = await ManagedMessages.add_to_message_list(
            channel_id,
            message_id,
            f"{ctx.message.author.display_name}: {ctx.message.content}",
        )
        # appends the message to the context window, "user: message"
        # auto manages context window size

        remembered_memories = await memories.compare_memories(
            guild_id, channel_id, message.content
        )

        if isinstance(remembered_memories, list):
            _fix_memory = remembered_memories
            print("This is a list, DEBUG:")
            print("remembered_memories = list")
            print("index 0 of remembered_memories: ", remembered_memories[0])
            print("correcting type to dict. slashing any value after the first index")
            remembered_memories = _fix_memory[0]
            print("corrected remembered:", remembered_memories)
            print("type of: ", type(remembered_memories))

        print("Remembered Memories:", remembered_memories)
        print("Remembered Memories type:", type(remembered_memories))

        if remembered_memories["is_similar"]:
            prompt = read_prompt(
                message,
                memories.fetch_and_sort_entries(guild_id).get(
                    remembered_memories.get("similar_phrase")
                ),
            )
        else:
            prompt = read_prompt(message)

        if attachments and attachments[0].filename.lower().endswith(
            (
                ".png",
                ".jpg",
                ".webp",
                ".heic",
                ".heif",
                ".mp4",
                ".mpeg",
                ".mov",
                ".wmv",
            )
        ):
            # Checks if file type is one supported by Google Gemini
            save_name = str(message.id) + " " + message.attachments[0].filename.lower()
            await message.attachments[0].save(save_name)  # Saves attachment

            file = await BotModel.upload_attachment(save_name)
            response = await BotModel.generate_content(prompt, channel_id, file)

            if voice_response:
                print("Voice mode triggered by random_chance")
                file_name = await VoiceMessages.record_with_elevenlabs(
                    text=response, save_file=f"tts_rsp_{message_id}.mp3"
                )

                duration, waveform = AudioUtils.get_audio_metadata(file_name)
                return (
                    response,
                    VoiceMessage(
                        fp=file_name,
                        duration_secs=duration,
                        waveform=waveform,
                    ),
                )

            # uploads using FileAPI

            await ManagedMessages.add_to_message_list(
                channel_id,
                message_id,
                f"{message.author.display_name}: {message.content}",
            )

            os.remove(save_name)
            await BotModel.delete_attachment(file.name)
            return response

        # Add text file and audio support soon
        elif attachments and attachments[0].filename.lower().endswith(
            (".wav", ".mp3", ".aiff", ".aac", ".flac")
        ):
            # Audio handling

            save_name = str(message.id) + " " + message.attachments[0].filename.lower()
            await message.attachments[0].save(save_name)
            # Download the file

            file = await BotModel.upload_attachment(save_name)
            response = await BotModel.generate_content(
                prompt=prompt, channel_id=channel_id, attachment=file
            )
            if voice_response:
                print("Voice mode triggered by random_chance")
                file_name = await VoiceMessages.record_with_elevenlabs(
                    text=response, save_file=f"tts_rsp_{message_id}.mp3"
                )

                duration, waveform = AudioUtils.get_audio_metadata(file_name)
                return (
                    response,
                    VoiceMessage(
                        fp=file_name,
                        duration_secs=duration,
                        waveform=waveform,
                    ),
                )

            os.remove(save_name)
            await BotModel.delete_attachment(file.name)
            return response

        elif attachments and attachments[0].filename.lower().endswith(".ogg"):

            save_name = str(message.id) + " " + message.attachments[0].filename.lower()
            await message.attachments[0].save(save_name)
            file = await BotModel.upload_attachment(save_name)
            stt_response = await BotModel.speech_to_text(audio_file=file)

            # Remove initial message appended.
            await ManagedMessages.remove_from_message_list(channel_id, message_in_list)

            await ManagedMessages.add_to_message_list(
                channel_id, message_id, f"{message.author.display_name}: {stt_response}"
            )
            # Add message from Voice note to list

            response = await BotModel.generate_content(
                prompt=prompt, channel_id=channel_id
            )

            if (
                config["voiceMessages"] == "on" and config["voiceMessageConvo"] == "on"
            ):  # TODO change the name of that
                # this means the global setting voice messages is on and the user would like to do voice message to voice message
                # so lets implement this now, lets first start off by generalizing voice call.py
                file_name = await VoiceMessages.record_with_elevenlabs(
                    text=response, save_file=f"tts_rsp_{message_id}.mp3"
                )

                duration, waveform = AudioUtils.get_audio_metadata(file_name)
                return (
                    response,
                    VoiceMessage(
                        fp=file_name,
                        duration_secs=duration,
                        waveform=waveform,
                    ),
                )

            os.remove(save_name)
            await BotModel.delete_attachment(file.name)
            return response

        else:
            if config["deepContext"] == "on":
                category = await AIAgent.classify(message.content)  # AGENT HOOK
                await AIAgent.categorize(category, ctx)  # AGENT HOOK

            response = await BotModel.generate_content(
                prompt, channel_id
            )  # DISCORDBOT.PY

            if (
                config["voiceMessages"] == "on" and config["voiceMessageConvo"] == "on"
            ):  # TODO change the name of that
                # this means the global setting voice messages is on and the user would like to do voice message to voice message
                # so lets implement this now, lets first start off by generalizing voice call.py
                file_name = await VoiceMessages.record_with_elevenlabs(
                    text=response, save_file=f"tts_rsp_{message_id}.mp3"
                )

                duration, waveform = AudioUtils.get_audio_metadata(file_name)
                return (
                    response,
                    VoiceMessage(
                        fp=file_name,
                        duration_secs=duration,
                        waveform=waveform,
                    ),
                )
            return response


class headless_Gemini:

    async def generate_response(guild_id, channel_id, author_name, author_content):

        if author_content in []:
            pass

        if channel_id not in context_window:
            context_window[channel_id] = (
                []
            )  # if channel id isnt present in context window, make a new key

        await headless_ManagedMessages.add_to_message_list(
            channel_id=channel_id, text=f"{author_name} : {author_content}"
        )

        remembered_memories = await memories.compare_memories(
            guild_id, channel_id, author_content
        )

        if isinstance(remembered_memories, list):
            remembered_memories = remembered_memories[
                0
            ]  # this is to fix the issue of remembered memories returning a list instead of a dictionary

        if remembered_memories["is_similar"]:
            prompt = read_prompt(
                memory=remembered_memories["similar_phrase"], author_name=author_name
            )
        else:
            prompt = read_prompt(author_name=author_name)

        response = await headless_BotModel.generate_content(
            channel_id=channel_id, prompt=prompt
        )
        return response
