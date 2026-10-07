# Chirp

Local spoken outlines for Codex and Claude Code. A synchronous Stop hook asks
the original agent for an outline, then speaks it with CPU-based Piper.

## Install

With Python 3.10+ and Codex available (Python 3.12 and 3.13 are tested):

```sh
git clone https://github.com/piyushsatti/chirp.git
cd chirp
bash scripts/install.sh
```

This installs a persistent Python environment, the `en_US-ljspeech-medium`
voice, and a clean plugin copy under `~/.local/share/chirp`. It registers the
local Codex marketplace and installs `chirp@chirp-local`. Start a fresh Codex
session and review/enable Chirp in `/hooks`; installation does not replace
Codex's hook trust review. No shell exports are needed for the default desktop
setup.

For Claude Code, install the runtime and open Claude with the installed plugin:

```sh
bash scripts/install.sh runtime
claude --plugin-dir ~/.local/share/chirp/plugin
```

Linux needs the PortAudio runtime (`libportaudio2` on Ubuntu/Debian). The
installer does not install system packages. The separate administrator command
below has not been run during development:

```sh
sudo apt-get install --no-install-recommends libportaudio2
```

Use a login session with access to the intended speakers. SSH/headless sessions
may expose no output devices. On macOS, sounddevice's wheel includes PortAudio.
Audio plays on the machine running the hook; there is no remote audio transport.

Optional install settings: `CHIRP_PYTHON=/path/to/python3.12` selects Python when
the environment is first created. `CHIRP_DATA_DIR` changes the storage location;
otherwise Chirp uses `$XDG_DATA_HOME/chirp` when set, or `~/.local/share/chirp`.
The commands here assume the default location. A custom location must also be
available through the same environment setting when the client runs.

## Choose an output

Chirp uses the current default output until you save a preference. List outputs,
then choose an enumerated name or numeric ID:

```sh
~/.local/share/chirp/venv/bin/chirp devices
~/.local/share/chirp/venv/bin/chirp device 'MacBook Pro Speakers'
```

The choice is saved for future hooks, including desktop-launched sessions.
Names must identify one output; numeric IDs can change after reconnecting a
device. To return to the current default:

```sh
~/.local/share/chirp/venv/bin/chirp device default
```

`CHIRP_DEVICE` overrides the saved preference. `speak --device 'USB Headset'`
or `speak --device 3` overrides both for that invocation.

## Check speech

Synthesize silently, without opening an audio output:

```sh
printf '%s\n' 'The local speech component is ready.' |
  ~/.local/share/chirp/venv/bin/chirp smoke
```

To explicitly **play audio** through the selected output:

```sh
printf '%s\n' 'This is the selected output device.' |
  ~/.local/share/chirp/venv/bin/chirp speak
```

Setup downloads dependencies and the voice. Subsequent speech uses local files
with no hosted API, key, or model server. PCM stays in memory. `CHIRP_MODEL` or
`--model /absolute/voice.onnx` selects another Piper voice; keep its matching
`.onnx.json` file alongside it.

## Exact behavior and limits

The hook reads `last_assistant_message` from stdin JSON and reverse-finds the
exact string `\n---speech---\n`. If missing, it returns `decision: "block"` with
instructions for the same original agent, using the full conversation context,
to append the delimiter and a concise natural spoken outline preserving core
meaning and caveats. If present, the unmodified suffix goes to local audio; the
hook waits, prints `{}`, and exits 0. Audio errors go to stderr and do not ask
the agent to continue. An empty suffix counts as a present marker.

There is no separate summarizer, microphone, queue, retry state, or server. The
outline remains visible in the conversation. Stop is a checkpoint: other hooks
can continue the conversation afterward, and a later Stop can speak again.
Client continuation limits and trust behavior still apply. See the official
[Codex hooks](https://learn.chatgpt.com/docs/hooks) and
[Claude Stop](https://code.claude.com/docs/en/hooks#stop) references.

Piper is GPL-3.0-or-later. See [engine and voice licenses](docs/licenses.md) for
dependency and voice provenance, and [verification](docs/verification.md) for
tested platforms and remaining live-agent/playback checks.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
ruff check src tests
ruff format --check src tests
shellcheck scripts/stop.sh scripts/install.sh
bash -n scripts/stop.sh
bash -n scripts/install.sh
```

Tests stub playback and never open a real speaker.
