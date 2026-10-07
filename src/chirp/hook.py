"""The synchronous Stop protocol, with no state between invocations."""

import json
import subprocess
import sys

MARKER = "\n---speech---\n"
CONTINUATION = (
    "Continue this response as the same original agent, using the full conversation "
    "context. Append the exact delimiter '\\n---speech---\\n' (a newline, "
    "---speech--- on its own line, then a newline), followed by a concise, natural "
    "spoken outline of your answer. Preserve its core meaning, important caveats, "
    "uncertainty, and any action needed from the user. Write the outline yourself; "
    "do not call another model or agent to summarize. Put the delimiter and spoken "
    "outline at the end of your assistant message."
)


def extract_speech(message: str) -> str | None:
    """Return the unmodified suffix after the last exact marker."""
    position = message.rfind(MARKER)
    return None if position == -1 else message[position + len(MARKER) :]


def main() -> int:
    payload = json.load(sys.stdin)
    speech = extract_speech(payload.get("last_assistant_message") or "")
    if speech is None:
        print(json.dumps({"decision": "block", "reason": CONTINUATION}))
        return 0

    # A separate local process keeps Python and native audio output off stdout.
    # Waiting here preserves synchronous Stop semantics through playback.
    try:
        result = subprocess.run(
            [sys.executable, "-m", "chirp", "speak"],
            input=speech,
            text=True,
            encoding="utf-8",
            stdout=sys.stderr,
            stderr=sys.stderr,
            check=False,
        )
        if result.returncode:
            print(
                f"chirp: audio exited with status {result.returncode}",
                file=sys.stderr,
            )
    except OSError as error:
        print(f"chirp: could not start audio: {error}", file=sys.stderr)

    print("{}")
    return 0
