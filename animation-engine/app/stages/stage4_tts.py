from pathlib import Path
import os
import azure.cognitiveservices.speech as speechsdk

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
AUDIO_DIR = OUTPUTS_DIR / "audio"

def tts_generate(script, video_id: str, scene_ids: list):
    output_dir = AUDIO_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    speech_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not region:
        raise RuntimeError("Azure Speech key or region not set")

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=region
    )
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"

    # Build lookup: normalise scene_ids that may or may not have the "scene_" prefix
    script_map = {
        (f"scene_{s['scene_id']}" if not str(s["scene_id"]).startswith("scene_") else s["scene_id"]): s["script"]
        for s in script
    }

    for entry in scene_ids:
        # Support both plain strings (legacy) and (disk_index, scene_id) tuples
        if isinstance(entry, (list, tuple)):
            _, scene_id = entry
        else:
            scene_id = entry

        if scene_id not in script_map:
            print(f"[tts] No script found for {scene_id} — skipping audio generation.")
            # Generate a silent 6-second WAV so mux_audio doesn't fail
            audio_path = output_dir / f"{scene_id}.wav"
            _generate_silence(audio_path, duration=6)
            continue

        text = script_map[scene_id]
        audio_path = output_dir / f"{scene_id}.wav"

        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=str(audio_path)
        )

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        result = synthesizer.speak_text_async(text).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"TTS failed for {scene_id}")

        print(f"[✓] Generated audio for {scene_id}")


def _generate_silence(path: Path, duration: int = 6):
    """Write a silent WAV file using ffmpeg as a fallback for skipped scenes."""
    import subprocess
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=16000:cl=mono:d={duration}",
            "-ar", "16000",
            "-ac", "1",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(f"[tts] Generated silent audio → {path}")


