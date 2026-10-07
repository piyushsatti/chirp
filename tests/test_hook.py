"""Behavioral tests for the agreed Stop protocol; never play real audio."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chirp import hook

ROOT = Path(__file__).resolve().parents[1]


class ExtractionTests(unittest.TestCase):
    def test_missing_marker(self):
        self.assertIsNone(hook.extract_speech("An ordinary final answer."))

    def test_only_exact_delimiter_matches(self):
        for message in (
            "---speech---\noutline",
            "answer\n---speech---",
            "answer\r\n---speech---\r\noutline",
            "answer\n ---speech---\noutline",
        ):
            with self.subTest(message=message):
                self.assertIsNone(hook.extract_speech(message))

    def test_present_preserves_suffix_verbatim(self):
        self.assertEqual(
            hook.extract_speech("Long answer.\n---speech---\n  Café.\nCaveat.\n"),
            "  Café.\nCaveat.\n",
        )

    def test_last_marker_wins(self):
        self.assertEqual(
            hook.extract_speech("answer\n---speech---\nfirst\n---speech---\nlast"),
            "last",
        )

    def test_empty_suffix_is_present(self):
        self.assertEqual(hook.extract_speech("answer\n---speech---\n"), "")


class ProtocolTests(unittest.TestCase):
    def invoke(self, payload, run):
        output = io.StringIO()
        errors = io.StringIO()
        with (
            patch.object(sys, "stdin", io.StringIO(json.dumps(payload))),
            patch.object(sys, "stdout", output),
            patch.object(sys, "stderr", errors),
            patch.object(hook.subprocess, "run", run),
        ):
            code = hook.main()
        self.assertEqual(code, 0)
        return json.loads(output.getvalue()), errors.getvalue()

    def test_missing_blocks_same_original_agent_without_audio(self):
        with patch.object(hook.subprocess, "run") as run:
            result, errors = self.invoke({"last_assistant_message": "answer"}, run)
        self.assertEqual(result["decision"], "block")
        self.assertIn("same original agent", result["reason"])
        self.assertIn("full conversation context", result["reason"])
        self.assertIn("caveats", result["reason"])
        run.assert_not_called()
        self.assertEqual(errors, "")

    def test_nullable_codex_message_blocks(self):
        with patch.object(hook.subprocess, "run") as run:
            result, _ = self.invoke({"last_assistant_message": None}, run)
        self.assertEqual(result["decision"], "block")
        run.assert_not_called()

    def test_present_waits_passes_only_suffix_and_redirects_all_audio_output(self):
        def fake_audio(command, **kwargs):
            self.assertEqual(command, [sys.executable, "-m", "chirp", "speak"])
            self.assertEqual(kwargs["input"], "Spoken caveat.\n")
            self.assertIs(kwargs["stdout"], sys.stderr)
            self.assertIs(kwargs["stderr"], sys.stderr)
            # The hook has not emitted its successful completion before audio returns.
            self.assertEqual(sys.stdout.getvalue(), "")
            print("native/audio diagnostics", file=kwargs["stdout"])
            return subprocess.CompletedProcess(command, 0)

        result, errors = self.invoke(
            {"last_assistant_message": "Answer\n---speech---\nSpoken caveat.\n"},
            fake_audio,
        )
        self.assertEqual(result, {})
        self.assertEqual(errors, "native/audio diagnostics\n")

    def test_audio_failure_still_returns_empty_object_without_blocking(self):
        result, errors = self.invoke(
            {"last_assistant_message": "answer\n---speech---\noutline"},
            lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1),
        )
        self.assertEqual(result, {})
        self.assertIn("audio exited with status 1", errors)

    def test_no_retry_flag_changes_the_two_branches(self):
        for active in (False, True):
            with patch.object(hook.subprocess, "run") as run:
                result, _ = self.invoke(
                    {"last_assistant_message": "answer", "stop_hook_active": active},
                    run,
                )
            self.assertEqual(result["decision"], "block")

    def test_real_launcher_missing_marker_stdout_is_only_json(self):
        process = subprocess.run(
            ["bash", str(ROOT / "scripts" / "stop.sh")],
            input=json.dumps({"last_assistant_message": "Answer"}),
            text=True,
            capture_output=True,
            env={**os.environ, "CHIRP_PYTHON": sys.executable},
            cwd="/tmp",
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["decision"], "block")
        self.assertEqual(process.stderr, "")

    def test_real_audio_child_native_stdout_cannot_corrupt_protocol(self):
        with tempfile.TemporaryDirectory(prefix="chirp-test-") as directory:
            stub = Path(directory)
            (stub / "piper.py").write_text(
                "import os\nfrom types import SimpleNamespace\n"
                "class PiperVoice:\n"
                "    @staticmethod\n"
                "    def load(path, use_cuda=False):\n"
                "        return PiperVoice()\n"
                "    def synthesize(self, text):\n"
                "        assert text == 'Only this suffix.\\n'\n"
                "        os.write(1, b'native stdout log\\n')\n"
                "        yield SimpleNamespace(sample_rate=22050, "
                "sample_channels=1, audio_int16_bytes=b'\\0\\0')\n"
            )
            (stub / "sounddevice.py").write_text(
                "class RawOutputStream:\n"
                "    def __init__(self, **kwargs): pass\n"
                "    def __enter__(self): return self\n"
                "    def __exit__(self, *args): pass\n"
                "    def write(self, data): pass\n"
            )
            process = subprocess.run(
                ["bash", str(ROOT / "scripts" / "stop.sh")],
                input=json.dumps(
                    {"last_assistant_message": "\n---speech---\nOnly this suffix.\n"}
                ),
                text=True,
                capture_output=True,
                env={
                    **os.environ,
                    "CHIRP_PYTHON": sys.executable,
                    "CHIRP_MODEL": "unused-test-model",
                    "PYTHONPATH": directory,
                },
                cwd="/tmp",
                check=False,
            )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout, "{}\n")
        self.assertEqual(process.stderr, "native stdout log\n")


if __name__ == "__main__":
    unittest.main()
