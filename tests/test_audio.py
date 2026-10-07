"""Exercise the audio boundary without a real voice or audio output."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

from chirp import audio


def chunk(data, sample_rate=22050, channels=1):
    return SimpleNamespace(
        audio_int16_bytes=data,
        sample_rate=sample_rate,
        sample_width=2,
        sample_channels=channels,
    )


class AudioTests(unittest.TestCase):
    def test_devices_only_lists_output_capable_hardware(self):
        sounddevice = SimpleNamespace(
            query_devices=lambda: [
                {"index": 0, "name": "Microphone", "max_output_channels": 0},
                {"index": 1, "name": "Speakers", "max_output_channels": 2},
                {"index": 3, "name": "USB Headset", "max_output_channels": 2},
            ]
        )
        with patch.dict("sys.modules", {"sounddevice": sounddevice}):
            self.assertEqual(
                audio.output_devices(),
                [{"id": 1, "name": "Speakers"}, {"id": 3, "name": "USB Headset"}],
            )

    def test_piper_loads_cpu_voice_and_passes_exact_text(self):
        chunks = iter([chunk(b"\x00\x00")])
        voice = SimpleNamespace(synthesize=Mock(return_value=chunks))
        voice_class = SimpleNamespace(load=Mock(return_value=voice))
        with patch.dict(
            "sys.modules", {"piper": SimpleNamespace(PiperVoice=voice_class)}
        ):
            self.assertIs(audio.synthesize("Keep this caveat.\n", "voice.onnx"), chunks)
        voice_class.load.assert_called_once_with("voice.onnx", use_cuda=False)
        voice.synthesize.assert_called_once_with("Keep this caveat.\n")

    def test_speak_streams_chunks_in_order_to_selected_output(self):
        events = []

        def chunks():
            for data in (b"\x01\x00", b"\x02\x00"):
                events.append(("synthesize", data))
                yield chunk(data)

        class Stream:
            def __enter__(self):
                events.append("open")
                return self

            def write(self, data):
                events.append(("write", data))

            def __exit__(self, *args):
                events.append("close")

        stream_factory = Mock(return_value=Stream())
        sounddevice = SimpleNamespace(RawOutputStream=stream_factory)
        with (
            patch.dict("sys.modules", {"sounddevice": sounddevice}),
            patch.object(audio, "synthesize", return_value=chunks()),
        ):
            audio.speak("Hello", "voice.onnx", "USB Headset")
        stream_factory.assert_called_once_with(
            samplerate=22050, channels=1, dtype="int16", device="USB Headset"
        )
        self.assertEqual(
            events,
            [
                ("synthesize", b"\x01\x00"),
                "open",
                ("write", b"\x01\x00"),
                ("synthesize", b"\x02\x00"),
                ("write", b"\x02\x00"),
                "close",
            ],
        )

    def test_smoke_measures_pcm_without_importing_sounddevice(self):
        with (
            patch.dict("sys.modules", {"sounddevice": None}),
            patch.object(
                audio,
                "synthesize",
                return_value=iter(
                    [chunk(b"\x00" * 40, 10, 2), chunk(b"\x00" * 20, 10, 2)]
                ),
            ),
        ):
            self.assertEqual(
                audio.smoke("Hello", "voice.onnx"),
                {"bytes": 60, "sample_rate": 10, "duration_seconds": 1.5},
            )

    def test_cli_uses_environment_and_explicit_device_override(self):
        with (
            patch.dict(
                os.environ,
                {
                    "CHIRP_MODEL": "voice.onnx",
                    "CHIRP_DEVICE": "USB Headset",
                },
                clear=True,
            ),
            patch("sys.stdin", io.StringIO("Hello\n")),
            patch.object(audio, "speak") as speak,
        ):
            self.assertEqual(audio.main(["speak", "--device", "3"]), 0)
        speak.assert_called_once_with("Hello\n", "voice.onnx", 3)

    def test_cli_defaults_to_portaudio_output(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("sys.stdin", io.StringIO("Hello")),
            patch.object(audio, "speak") as speak,
        ):
            self.assertEqual(audio.main(["speak", "--model", "voice.onnx"]), 0)
        speak.assert_called_once_with("Hello", "voice.onnx", None)

    def test_cli_smoke_returns_json(self):
        output = io.StringIO()
        result = {"bytes": 44100, "sample_rate": 22050, "duration_seconds": 1.0}
        with (
            patch("sys.stdin", io.StringIO("Hello")),
            patch.object(audio, "smoke", return_value=result),
            redirect_stdout(output),
        ):
            self.assertEqual(audio.main(["smoke", "--model", "voice.onnx"]), 0)
        self.assertEqual(json.loads(output.getvalue()), result)

    def test_cli_uses_installed_voice_without_shell_exports(self):
        with (
            patch.dict(os.environ, {"CHIRP_DATA_DIR": "/tmp/chirp-test"}, clear=True),
            patch("sys.stdin", io.StringIO("Hello")),
            patch.object(audio, "configured_device", return_value=None),
            patch.object(audio, "speak") as speak,
        ):
            self.assertEqual(audio.main(["speak"]), 0)
        speak.assert_called_once_with(
            "Hello", "/tmp/chirp-test/voices/en_US-ljspeech-medium.onnx", None
        )

    def test_device_preference_persists_and_can_reset_to_default(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"CHIRP_DATA_DIR": directory}, clear=True),
            redirect_stdout(io.StringIO()),
        ):
            self.assertIsNone(audio.configured_device())
            self.assertEqual(audio.main(["device", "USB Speakers"]), 0)
            self.assertEqual(audio.configured_device(), "USB Speakers")
            with patch.dict(os.environ, {"CHIRP_DEVICE": "6"}):
                self.assertEqual(audio.configured_device(), "6")
            self.assertEqual(audio.main(["device", "default"]), 0)
            self.assertIsNone(audio.configured_device())

    def test_audio_failure_uses_stderr_and_nonzero_exit(self):
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("sys.stdin", io.StringIO("Hello")),
            patch.object(audio, "speak", side_effect=RuntimeError("No output device")),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            self.assertEqual(audio.main(["speak", "--model", "voice.onnx"]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("No output device", errors.getvalue())

    def test_device_names_and_ids(self):
        self.assertEqual(audio.parse_device("4"), 4)
        self.assertEqual(audio.parse_device("USB Headset"), "USB Headset")
        self.assertIsNone(audio.parse_device(None))


if __name__ == "__main__":
    unittest.main()
