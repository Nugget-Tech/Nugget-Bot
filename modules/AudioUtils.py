import os
import json
import base64
import subprocess


class AudioUtils:
    # Convert to OGG (Opus)
    def convert_any_opus(voice_uri, ogg_filename):
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                voice_uri,
                "-c:a",
                "libopus",
                "-b:a",
                "64k",
                "-ar",
                "48000",
                ogg_filename,
            ],
            check=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )

    # Get duration and dummy waveform
    def get_audio_metadata(file_path):
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-hide_banner",
                "-select_streams",
                "a:0",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                file_path,
            ],
            capture_output=True,
            text=True,
        )
        duration = float(json.loads(result.stdout)["format"]["duration"])
        waveform = base64.b64encode(os.urandom(256)).decode("utf-8")  # fake waveform
        return round(duration), waveform
