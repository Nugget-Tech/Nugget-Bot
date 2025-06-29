import json
import asyncio

from modules.ManagedMessages import ManagedMessages, headless_ManagedMessages
from modules.CommonCalls import CommonCalls
from discord import Message

from google.genai.types import (
    File,
    GenerateContentResponse,
    SafetySetting,
    GenerateContentConfig,
)
from google import genai


context_window = ManagedMessages().context_window

client = genai.Client(api_key=CommonCalls.config()["gemini_api_key"])


def read_prompt(message: Message = None, memory: str = None, author_name: str = None):
    """
    Description:
    This function reads the prompt from `prompt.json` and formats the values correctly

    Arguments:
    message : discord.Message = None
    memory : str = None
    author_name : str = None

    Returns:
    prompt : str | prompt_with_memory : str
    """

    personality_traits: dict = CommonCalls.load_character_details().get(
        "personality_traits"
    )
    system_note: dict = CommonCalls.load_character_details().get(
        "system_note", "No system note extension given. DO NOT MAKE ONE UP."
    )
    conversation_examples: dict = CommonCalls.load_character_details().get(
        "conversation_examples", []
    )
    bot_name = personality_traits.get("name", "unknown_bot")
    role = personality_traits.get("role", "unknown_role")
    age = personality_traits.get("age", "unknown_age")
    description = personality_traits.get("description", "no description provided")
    likes = personality_traits.get("likes", "N/A")
    dislikes = personality_traits.get("dislikes", "N/A")

    # If memory is present, append to the prompt | TODO : append to prompt for context window
    if memory:
        return f"""
        {system_note}

        You are {bot_name}, a {role}, who is {age} years old, described as {description}.
        People in conversation {bot_name} (you), {author_name}, your job is to respond to the last message of {author_name}.
        You can use the messages in your context window, but do not ever reference them.

        Conversation examples:

        {"\n".join([f"{author_name}: {example['user']}\n{bot_name}: {example['bot']}" for example in conversation_examples])}

        Your likes : {likes}
        
        Your dislikes: {dislikes}

        Context information is below.
        ---------------------
        {memory}
        ---------------------
        Given the context information and not prior knowledge answer using THIS information
        
        From here on out, this is the conversation you will be responding to.
        ---- CONVERSATION ----
"""

    # If not
    return f"""
        {system_note}

        You are {bot_name}, a {role}, who is {age} years old, described as {description}.
        People in conversation {bot_name} (you), {author_name}, your job is to respond to the last message of {author_name}.
        You can use the messages in your context window, but do not ever reference them.
        
        Your likes : {likes}
        
        Your dislikes: {dislikes}
        
        Conversation examples:

        {"\n".join([f"{author_name}: {example['user']}\n{bot_name}: {example['bot']}" for example in conversation_examples])}

        From here on out, this is the conversation you will be responding to.
        ---- CONVERSATION ----
        """


class BotModel:
    """
    This class deals with how the discord bot generates text and gets different inputs
    NOTE: This class NEEDS discord objects for use-cases without an object use `headless_BotModel`
    """

    # Generate content
    async def generate_content(
        prompt, channel_id=None, attachment: File = None, retry=3
    ):
        """
        Description:
        This function handles asynchronos text generation using Gemini, this also allows for multimodal prompts using a pre-uploaded file

        Arguments:
        prompt : str
        channel_id : int | str = None
        attachment : genai.types.File = None
        retry : int = 3

        Returns:
        response : str
        """

        context = "\n".join(context_window[channel_id])
        prompt_with_context = prompt + "\n" + context

        if attachment:
            media_addon = "Describe this piece of media to yourself in a way that if referenced again, you will be able to answer any potential question asked."

            full_prompt = [prompt_with_context, "\n", media_addon, "\n", attachment]

        else:
            full_prompt = prompt_with_context

        response: GenerateContentResponse = await client.aio.models.generate_content(
            contents=full_prompt,
            model=CommonCalls.config()["aiModel"],
            config=GenerateContentConfig(
                safety_settings=[
                    SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold=CommonCalls.config()["filterHateSpeech"],
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
                temperature=float(CommonCalls.config().get("temperature", 0)),
                top_p=float(CommonCalls.config().get("topP", 0)),
                top_k=float(CommonCalls.config().get("topK", 0)),
            ),
        )

        try:
            text = response.text.strip()
            return text

        except Exception as error:
            print(
                "BotModel.py: Error: While generating a response, this exception occurred",
                error,
            )
            print(response.candidates)

        retry_count = 0
        while retry_count < retry:
            try:
                fall_back_response = response.candidates[0].content.parts[0].text
                return str(fall_back_response).strip()
            except Exception as E:
                print(f"Error generating response (retry {retry_count}): {E}")
                retry_count += 1

        try:
            await ManagedMessages.remove_message_from_index(channel_id, 0)
        except (IndexError, KeyError):
            pass
        return (
            CommonCalls.config()["error_message"]
            or "Sorry, could you please repeat that?"
        )

    async def upload_attachment(attachment):
        """
        Description:
        This function allows for asynchronous attachment uploading via FileAPI

        Arguments:
        attachment

        Returns:
        attachment_media : genai.Types.File | None
        """
        print(
            "[INIT] Uploading Attachment function call `BotModel.upload_attachment` (Message from line 168 @ modules/BotModel.py)"
        )
        attachment_media: File = client.files.upload(file=attachment)

        while True:
            if attachment_media.state.name == "PROCESSING":
                print(
                    "[PROCESSING] Uploading Attachment function call `BotModel.upload_attachment` (Message from line 173 @ modules/BotModel.py)"
                )
                await asyncio.sleep(2)
                attachment_media = client.files.get(
                    name=attachment_media.name
                )  # Update the state
            elif attachment_media.state.name == "ACTIVE":
                print(
                    "[SUCCESS] Uploading Attachment function call `BotModel.upload_attachment` (Message from line 177 @ modules/BotModel.py)"
                )
                return attachment_media
            elif attachment_media.state.name == "FAILED":
                print(
                    "[FAILED] Uploading Attachment function call `BotModel.upload_attachment` (Message from line 180 @ modules/BotModel.py)"
                )
                return None
            else:
                print(f"Unknown state: {attachment_media.state.name}")
                return None

    async def delete_attachment(attachment):
        """
        come on, really?
        """
        client.files.delete(name=attachment)

    async def __generate_reaction(prompt, channel_id, attachment=None):
        """[UNUSED AND BUGGY]"""
        reaction_model = client.models(
            model_name=CommonCalls.config()["aiModel"],
            system_instruction=prompt,
        )

        if attachment:
            prompt_with_image = ["\n".join(context_window[channel_id]), attachment]
            emoji = await reaction_model.generate_content_async(prompt_with_image)

            response = emoji.text or emoji.candidates[0]
            # context_window[channel_id].append(f"You reacted with this emoji {response}")

            return response

        else:
            context = "\n".join(context_window[channel_id])
            emoji = reaction_model.generate_content(context)

            response = emoji.text or emoji.candidates[0]
            # context_window[channel_id].append(f"You reacted with this emoji {response}")

    async def generate_reaction(channel_id, attachment=None):

        if attachment:
            # do some file uploadry and something idk yet thats a TODO
            pass

        prompt = f"""You are in an embedded LLM, 
        you must only respond with ONE character, 
        an emoji, using this emoji react to the conversation going on, 
        if its good, if its bad, in one emoji. - \n\n The conversation [PARTIAL] is as follows {"\n".join(context_window[channel_id])}"""
        response: GenerateContentResponse = await client.aio.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )

        why_prompt = f"""You are in an embedded LLM, 
        you must only respond with a concise, 
        bias free message, in this context you have just reacted to the users message 
        ({"\n".join(context_window[channel_id])}) with {response.text.strip()}, 
        using the data available you must now come up with the reason why you did what you did"""

        why_response: GenerateContentResponse = (
            await client.aio.models.generate_content(
                contents=why_prompt, model=CommonCalls.config()["aiModel"]
            )
        )

        # join this to the context window

    async def speech_to_text(audio_file: File):
        """
        Description:
        This function is used for transcription of audio data provided via voice channels or .ogg files

        Arguments:
        audio_file : genai.Types.File

        Returns:
        response.text : str
        """
        print(
            "Speech To Text function call `speech_to_text` (Message from line 210 @ modules/BotModel.py)"
        )
        system_instruction = """You are now a microphone, you will ONLY return the words in the audio file, DO NOT describe them.\n\n"""
        response: GenerateContentResponse = await client.aio.models.generate_content(
            contents=[system_instruction, audio_file],
            model=CommonCalls.config()["aiModel"],
            config=GenerateContentConfig(
                safety_settings=[
                    SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold=CommonCalls.config()["filterHateSpeech"],
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
            ),
        )

        print("[RESPONSE] Response from STT Module: ", response.text)
        return response.text


class headless_BotModel:
    """
    This class deals use cases that do not provide a discord object (somewhat)"""

    async def generate_content(channel_id: str | int, prompt: str, retry: int = 3):
        """
        Description:
        This function generates text content
        """

        headless_mm = headless_ManagedMessages

        context = "\n".join(headless_mm.context_window[channel_id])
        full_prompt = prompt + "\n" + context
        # TODO HERE REMOVE THIS AND OPTIMIZE BY SENDING VOICE MESSAGE DIRECTLY TO API
        response: GenerateContentResponse = await client.aio.models.generate_content(
            contents=full_prompt,
            model=CommonCalls.config()["aiModel"],
            config=GenerateContentConfig(
                safety_settings=[
                    SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold=CommonCalls.config()["filterHateSpeech"],
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
            ),
        )

        try:
            text = response.text.strip()
            return text

        except Exception as error:
            print(
                "[headless_BotModel] BotModel.py: Error: While generating a response, this exception occurred",
                error,
            )
            print(response.candidates)

        retry_count = 0
        while retry_count < retry:
            try:
                fall_back_response = response.candidates[0].content.parts
                return str(fall_back_response).strip()
            except Exception as E:
                print(f"Error generating response (retry {retry_count}): {E}")
                retry_count += 1

        try:
            await headless_ManagedMessages.remove_message_from_index(channel_id, 0)

        except (IndexError, KeyError):
            pass

        return (
            CommonCalls.config()["error_message"]
            or "Sorry, could you please repeat that?"
        )
