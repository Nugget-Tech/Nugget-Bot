from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from discord.ext import commands
import json
import os


def create_app(bot: commands.Bot):
    app = FastAPI()

    @app.get("/logs")
    async def cmdline_view():
        raise NotImplementedError

    @app.get("/health")
    async def health():
        return {"status": "ok"}  # Make this more descriptive

    @app.post("/event")
    async def event_trigger(request: Request):
        data: dict = await request.json()
        match data.get("type"):
            case "update_config":
                config = data.get("config")
                print("[SPINE SERVER] [CRITICAL] | Analyzing config")
                print(config)
                print("updating config keys... please hold")
                config_path = f"data/{os.getenv('BOT_ID')}-config.json"

                # Read existing config
                existing_config = {}
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r") as f:
                            existing_config = json.load(f)
                    except json.JSONDecodeError:
                        print(
                            "[SPINE SERVER] [WARNING] | Existing config file is invalid JSON"
                        )

                # Update only the provided keys
                existing_config.update(config)

                # Save updated config
                with open(config_path, "w") as f:
                    json.dump(existing_config, f, indent=4)
                return {"status": "config updated"}

            case "update_personality":
                personality = data.get("personality")
                print("[SPINE SERVER] [CRITICAL] | Analyzing personality")
                print(f"Type: {type(personality)}")
                print(personality)
                print("updating personality keys... please hold")
                prompt_path = f"data/{os.getenv('BOT_ID')}-prompt.json"

                # Read existing personality
                existing_personality = {}
                if os.path.exists(prompt_path):
                    try:
                        with open(prompt_path, "r") as f:
                            existing_personality = json.load(f)
                    except json.JSONDecodeError:
                        print(
                            "[SPINE SERVER] [WARNING] | Existing personality file is invalid JSON"
                        )

                # Update only the provided keys
                existing_personality.update(personality)

                # Save updated personality
                with open(prompt_path, "w") as f:
                    json.dump(existing_personality, f, indent=4)
                return {"status": "personality updated"}

            case "update_memory":
                memory = data.get("memory")
                print("[SPINE SERVER] [CRITICAL] | Analyzing memory")
                print("data:", data)
                print("memory:", memory)

                # The memory data should be a dict with guild_id as key
                if not isinstance(memory, dict) or len(memory) != 1:
                    return {"status": "error", "message": "Invalid memory format"}

                # Get the guild_id (key) and memories (value) from the incoming data
                guild_id = next(iter(memory.keys()))
                new_memories = memory[guild_id]
                print(new_memories)

                if not isinstance(new_memories, list) or not new_memories:
                    return {"status": "error", "message": "Invalid memories format"}

                print(f"[SPINE SERVER] [CRITICAL] | Guild ID: {guild_id}")
                print(f"Type: {type(memory)}")
                print(memory)
                print("updating memory keys... please hold")
                memories_path = f"data/{os.getenv('BOT_ID')}-memories.json"

                # Read existing memories
                existing_memories = {}
                if os.path.exists(memories_path):
                    try:
                        with open(memories_path, "r") as f:
                            existing_memories = json.load(f)
                    except json.JSONDecodeError:
                        print(
                            "[SPINE SERVER] [WARNING] | Existing memory file is invalid JSON"
                        )

                # Initialize guild array if it doesn't exist
                if guild_id not in existing_memories:
                    existing_memories[guild_id] = []

                # For each new memory in the array
                for new_memory in new_memories:
                    memory_id = new_memory.get("memory_id")
                    if not memory_id:
                        continue  # Skip memories without memory_id

                    # Find and update existing memory or append new one
                    memory_updated = False
                    for i, existing_memory in enumerate(existing_memories[guild_id]):
                        if existing_memory.get("memory_id") == memory_id:
                            existing_memories[guild_id][i] = new_memory
                            memory_updated = True
                            break

                    if not memory_updated:
                        existing_memories[guild_id].append(new_memory)

                # Save updated memories
                with open(memories_path, "w") as f:
                    json.dump(existing_memories, f, indent=4)

                return {"status": "memory updated"}

            case "delete_memory":
                memory = data.get("memory")
                print("[SPINE SERVER] [CRITICAL] | Analyzing memory deletion request")
                print("data:", data)
                print("memory:", memory)

                # The memory data should be a dict with guild_id as key
                if not isinstance(memory, dict) or len(memory) != 1:
                    return {"status": "error", "message": "Invalid memory format"}

                # Get the guild_id (key) and memories (value) from the incoming data
                guild_id = next(iter(memory.keys()))
                memories_to_delete = memory[guild_id]

                if not isinstance(memories_to_delete, list) or not memories_to_delete:
                    return {"status": "error", "message": "Invalid memories format"}

                print(f"[SPINE SERVER] [CRITICAL] | Guild ID: {guild_id}")
                memories_path = f"data/{os.getenv('BOT_ID')}-memories.json"

                # Read existing memories
                existing_memories = {}
                if os.path.exists(memories_path):
                    try:
                        with open(memories_path, "r") as f:
                            existing_memories = json.load(f)
                    except json.JSONDecodeError:
                        print(
                            "[SPINE SERVER] [WARNING] | Existing memory file is invalid JSON"
                        )
                        return {
                            "status": "error",
                            "message": "Failed to read memories file",
                        }

                if guild_id not in existing_memories:
                    print("[SPINE SERVER] [WARNING] | Guild ID is not registered.")
                    return {"status": "error", "message": "Guild not found in memories"}

                # Get the memory IDs to delete
                memory_ids_to_delete = [
                    m.get("memory_id") for m in memories_to_delete if m.get("memory_id")
                ]
                if not memory_ids_to_delete:
                    return {
                        "status": "error",
                        "message": "No valid memory IDs provided",
                    }

                # Filter out the memories that match the memory_ids
                existing_memories[guild_id] = [
                    mem
                    for mem in existing_memories[guild_id]
                    if mem.get("memory_id") not in memory_ids_to_delete
                ]

                # If the guild has no memories left, consider removing the guild entry
                if not existing_memories[guild_id]:
                    del existing_memories[guild_id]

                # Save updated memories
                with open(memories_path, "w") as f:
                    json.dump(existing_memories, f, indent=4)

                return {"status": "memories deleted"}

            case _:
                return {"status": "unknown event"}

    @app.get("/memories")
    def memory_ret():
        memory_path = f"./data/{os.getenv('BOT_ID')}-memories.json"
        with open(memory_path, "r") as memories:
            loaded_memories = json.load(memories)
            return JSONResponse(loaded_memories)

    @app.post("/memories")
    def memory_set():
        memory_path = f"./data/{os.getenv('BOT_ID')}-memories.json"
        with open(memory_path, "r") as memories:
            loaded_memories = json.load(memories)
            return JSONResponse(loaded_memories)

    @app.get("/guilds")
    def guilds_ret():
        guilds = []
        for guild in bot.guilds:
            guilds.append({"id": guild.id, "name": guild.name, "icon": guild.icon.key})
        return JSONResponse(guilds)

    @app.get("/bot-details")
    def bot_details():
        return JSONResponse(
            {
                "bot_name": bot.user.name,
                "bot_id": bot.user.id,
                "bot_avatar_url": bot.user.avatar.url,
            }
        )

    return app


async def start_web(bot, config):
    from uvicorn import Config, Server

    app = create_app(bot, config)
    server = Server(
        Config(app, host="0.0.0.0", port=8000, loop="asyncio", log_level="info")
    )
    await server.serve()
