"""Local, in-memory Piper synthesis and blocking output through PortAudio."""

import argparse
import json
import os
import sys
from itertools import chain
from pathlib import Path


def output_devices():
    """Return PortAudio IDs and names for devices that can play audio."""
    import sounddevice

    return [
        {"id": device["index"], "name": device["name"]}
        for device in sounddevice.query_devices()
        if device["max_output_channels"] > 0
    ]


def synthesize(text, model):
    """Yield Piper's signed 16-bit PCM chunks using the CPU provider."""
    from piper import PiperVoice

    voice = PiperVoice.load(str(Path(model).expanduser()), use_cuda=False)
    return voice.synthesize(text)


def speak(text, model, device=None):
    """Play synthesis chunks synchronously, with no intermediate audio files."""
    import sounddevice

    chunks = iter(synthesize(text, model))
    first = next(chunks, None)
    if first is None:
        return

    with sounddevice.RawOutputStream(
        samplerate=first.sample_rate,
        channels=first.sample_channels,
        dtype="int16",
        device=device,
    ) as stream:
        for chunk in chain((first,), chunks):
            stream.write(chunk.audio_int16_bytes)


def smoke(text, model):
    """Synthesize and measure PCM without opening any audio device."""
    byte_count = 0
    sample_rate = None
    duration = 0.0
    for chunk in synthesize(text, model):
        size = len(chunk.audio_int16_bytes)
        byte_count += size
        sample_rate = chunk.sample_rate
        duration += size / (
            chunk.sample_rate * chunk.sample_width * chunk.sample_channels
        )
    return {
        "bytes": byte_count,
        "sample_rate": sample_rate,
        "duration_seconds": duration,
    }


def parse_device(value):
    """Keep device names intact, converting numeric IDs for sounddevice."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def data_directory():
    """Locate Chirp's installed runtime, voice, and output preference."""
    return Path(
        os.environ.get(
            "CHIRP_DATA_DIR",
            str(Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")) / "chirp"),
        )
    ).expanduser()


def configured_device():
    if "CHIRP_DEVICE" in os.environ:
        return os.environ["CHIRP_DEVICE"]
    preference = data_directory() / "device"
    return preference.read_text().strip() if preference.exists() else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("devices", help="list output device IDs and names")
    device_command = commands.add_parser(
        "device", help="save output ID/name or default"
    )
    device_command.add_argument("output", help="output ID/name, or 'default'")
    for name, help_text in (
        ("speak", "read stdin and play speech synchronously"),
        ("smoke", "read stdin and synthesize without playback"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument(
            "--model",
            default=os.environ.get(
                "CHIRP_MODEL",
                str(data_directory() / "voices" / "en_US-ljspeech-medium.onnx"),
            ),
            help="Piper .onnx path (default: installed voice or CHIRP_MODEL)",
        )
        if name == "speak":
            command.add_argument(
                "--device",
                default=None,
                help="output ID/name (default: CHIRP_DEVICE or system output)",
            )
    args = parser.parse_args(argv)
    try:
        if args.command == "devices":
            print(json.dumps(output_devices(), ensure_ascii=False, indent=2))
        elif args.command == "device":
            preference = data_directory() / "device"
            preference.parent.mkdir(parents=True, exist_ok=True)
            if args.output == "default":
                preference.unlink(missing_ok=True)
            else:
                preference.write_text(args.output + "\n")
            print(f"Chirp output: {args.output}")
        elif args.command == "smoke":
            print(json.dumps(smoke(sys.stdin.read(), args.model)))
        else:
            device = args.device if args.device is not None else configured_device()
            speak(sys.stdin.read(), args.model, parse_device(device))
    except Exception as exc:
        print(f"chirp audio: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
