"""
OLD: Use modules/DeepContext for additional functionality
"""

import json
import datetime

from discord.ext import commands
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    SafetySetting,
    GenerateContentResponse,
)
from modules.ManagedMessages import ManagedMessages
from modules.Voice import VoiceCalls
from modules.CommonCalls import CommonCalls

context_window = ManagedMessages.context_window

client = genai.Client(api_key=CommonCalls.config()["gemini_api_key"])


class AIAgent:

    async def classify(text):
        """
        Description:
        This function uses the Google Gemini API to classify text input from discord, based on the message it categorizes it into events.

        Arguments:
        text : str

        Returns:
        clean_json : dict
        """
        json_format = """{"category" : general-category-type}"""
        remind_json = """{"category" : general-category-type, "datetime" : yyyy-mm-dd hh:mm:ss, "reason" : the reason why the reminder is made}"""
        system_instruction = f"""
        You are an AI Agent, your first task is classifying the following chunk of text into one of the following action categories
        make sure to analyze this very carefully and answer carefully.
        
        voice-call-initialize : When the user would like initialize a voice call with the user (keywords like call, speak and talk)
        voice-call-end : When the user would like to end a voice call with the user (keywords like later, nice speaking and bye)

        normal-chat-normal: When theres nothing interesting occuring in the current chat, just regular conversation
        interesting-chat-good : When the conversation is dicussing something that falls within the likes {CommonCalls.load_character_details()["likes"]}
        interesting-chat-bad  : When the conversation is discussing something that falls within the dislikes {CommonCalls.load_character_details()["dislikes"]}

        reminder-start : When the message is asking you to set a reminder the current date time is {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}, modify the returned JSON as such {remind_json} (keywords like "remind me")
        reminder-cancel : When the message is asking you to cancel a reminder. (keywords like "cancel reminder")

        Return the classified text in the following json format:
        {json_format}
        """

        response: GenerateContentResponse = await client.aio.models.generate_content(
            contents=text,
            model=CommonCalls.config()["aiModel"],
            config=GenerateContentConfig(
                safety_settings=[
                    SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold=CommonCalls.config().get("filterHateSpeech"),
                    ),
                    SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold=CommonCalls.config()["filterHarassment"],
                    ),
                    SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold=CommonCalls.config()["filterSexuallyExplicit"],
                    ),
                    SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold=CommonCalls.config()["filterDangerous"],
                    ),
                ],
                system_instruction=system_instruction,
                response_mime_type="application/json",
            ),
        )

        if CommonCalls.clean_json(response.text.lower())["category"] in [
            "voice-call-initialize",
            "voice-call-end",
            "normal-chat-normal",
            "interesting-chat-good",
            "interesting-chat-bad",
            "none-none",
        ]:
            # Checks if the json keys are valid
            return CommonCalls.clean_json(response.text)

        else:
            return CommonCalls.clean_json(response.text)

    async def categorize(ai_function: dict, ctx: commands.Context):
        """
        Description:
        This function maps out the events with their functions.\n
        Depending on the function name this function will also append additional arguments

        Args:
        ai_function : str
        ctx : commands.Context

        Returns:
        N/A
        """
        try:
            category = ai_function["category"]
            match category:

                case "voice-call-initialize":
                    await VoiceCalls.start_recording(ctx)
                    return {"kill": 1, "reason": category}  # for future logging

                case "voice-call-end":
                    await VoiceCalls.stop_recording(ctx)

                case "reminder-start":  # START EXAMPLE
                    reminder_reason = ai_function.get("reason")
                    reminder_date = ai_function.get("datetime", None)
                    reminder_channel = ctx.channel.id
                    reminder_message_author = ctx.author.id
                    # await Reminder.add_reminder(
                    #     reminder_name=reminder_reason,
                    #     reminder_time=reminder_date,
                    #     reminder_channel_id=reminder_channel,
                    #     reminder_message_author=reminder_message_author,
                    # )
                    # END EXAMPLE
                case _:
                    debug_mode = CommonCalls.config().get("debugMode")
                    if debug_mode == "on":
                        print(ai_function)

        except KeyError:
            return print("BAD")
