import json
import os

from google import genai
from google.genai.types import (
    GenerateContentConfig,
    SafetySetting,
    GenerateContentResponse,
)
from discord import Message
from modules.ManagedMessages import ManagedMessages
from modules.CommonCalls import CommonCalls
from uuid import uuid4

context_window = ManagedMessages.context_window

client = genai.Client(api_key=CommonCalls.config()["gemini_api_key"])


# JSON storage paths
MEMORIES_FILE = f"data/{CommonCalls.config()['alias']}-memories.json"


class Knowledge:
    def __init__(self):
        self.details = CommonCalls.load_character_details()
        self.character_name = self.details["name"]
        self.role = self.details["role"]
        self.age = self.details["age"]
        self.description = self.details["description"]

    async def summarize_context_window(self, channel_id, retry=3):
        prompt = f"You're a data analyst who's only purpose is to summarize large but concise summaries on text provided to you, try to retain most of the information! Your first task is to summarize this conversation from the perspective of {self.character_name} --- Conversation Start ---\n{'\n'.join(context_window[channel_id])} --- Conversation End ---"

        response: GenerateContentResponse = await client.aio.models.generate_content(
            contents=prompt,
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
            return response.text
        except Exception as E:
            print(f"Error generating response: {E}")
            retry_count = 0
            while retry_count < retry:  # Adjust the retry count as needed
                try:
                    fall_back_response = response.candidates[0].content.parts
                    return fall_back_response
                except Exception as E:
                    print(f"Error generating response (retry {retry_count}): {E}")
                    retry_count += 1
            else:
                return ""

    def fetch_and_sort_entries(self, guild_id):
        # Load the current memories from the JSON file
        memories = self.load_memories()
        print("fetch n sort pre sort: ", memories.keys())
        key = str(guild_id)  # Ensure key consistency

        # Get the memories for the specific channel, sorted by timestamp
        sorted_memories = sorted(memories.get(key, []), key=lambda x: x["timestamp"])
        print("fetch n sort post sort: ", memories.keys())

        # Create a dictionary with special_phrase as the key and memory as the value
        result = {entry["special_phrase"]: entry["memory"] for entry in sorted_memories}
        print("fetch n sort emitted result: ", result)
        return result

    async def compare_memories(self, guild_id, channel_id, message):
        print(
            "Compare Memories function call `Memories.compare_memories` (Message from line 202 @ modules/Memories.py)"
        )
        entries = self.fetch_and_sort_entries(guild_id).keys()
        print("This is entries from compare memories in modules/memories.py", entries)
        system_instruction = """
Objective:
Determine if the provided context or phrase is similar to another given phrase or message based on predefined criteria.

Guidelines:
1. **Content Overlap**: Examine if the majority of content in both messages overlaps.
2. **Contextual Similarity**: Check if the context or the main idea presented in both messages is alike.
3. **Linguistic Patterns**: Identify if similar linguistic patterns, phrases, or keywords are used.
4. **Semantic Similarity**: Evaluate if both messages convey the same meaning even if different words are used.

Instructions:
1. Read the provided messages and phrases.
2. Assess each message based on the provided guidelines.
3. Determine if the messages meet one or more of the following criteria:
    a.The content of both messages overlaps significantly.
    b. The contexts or main ideas of both messages align.
    c. Similar linguistic patterns or keywords are used in both messages.
    d. The overall meaning conveyed by both messages is the same.
    e. Be lenient in your comparison; if a phrase has 2/3 keywords, complete the rest.

If the phrase is similar, provide it in the JSON-type response ONLY. Provide the MOST similar phrase.
Provide your response in this JSON schema:

{
    "is_similar" : true/false,
    "similar_phrase" : the phrase in [Message 2]
}

without ANY formatting, i.e., no backticks '`', no syntax highlighting, no numbered lists.
"""
        message_list = f"""
Context: {"\n".join(context_window[channel_id])}
List of phrases: {", ".join(entries)}
"""
        try:
            unloaded_json = await client.aio.models.generate_content(
                contents=message_list,
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
                    response_mime_type="application/json",
                ),
            )
            clean_json = json.loads(self.clean_json(unloaded_json.text))
            # print(clean_json)
            return clean_json
        except Exception as E:
            print(E)
            return {"is_similar": False, "similar_phrase": None}

    def clean_json(self, json: str):
        if json.startswith("```json") and json.endswith("```"):
            return json[7:-3]
        else:
            return json

    @staticmethod
    def load_memories():
        """Load the memories from the JSON file."""
        if not os.path.exists(MEMORIES_FILE):
            return {}
        with open(MEMORIES_FILE, "r") as file:
            return json.load(file)

    @staticmethod
    def convert_to_serializable(data):
        # Check if data is of RepeatedComposite type and convert it
        if isinstance(data, dict):
            return {
                key: Knowledge.convert_to_serializable(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [Knowledge.convert_to_serializable(item) for item in data]
        else:
            return data

    def save_memories(self, memories):
        serializable_memories = self.convert_to_serializable(memories)
        print(serializable_memories)
        with open(MEMORIES_FILE, "w") as file:
            json.dump(serializable_memories, file, indent=4)


# D:\Python\GEMINI\Gemini-AI-Bot-DONOTRELEASE\bot\spine_server.py
# D:\Python\GEMINI\Gemini-AI-Bot-DONOTRELEASE - Copy\website\security.txt
