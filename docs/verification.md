# Verification

Chirp has been checked on Linux and macOS. Local CPU synthesis and protocol
behavior are verified. Live-agent continuation and physical playback/listening
remain untested.

| Check | Linux | macOS |
| --- | --- | --- |
| Platform | Ubuntu 26.04, x86_64 | macOS, arm64 |
| Python | 3.13 | 3.12 |
| Unit tests | 23 passed | 23 passed |
| CPU synthesis without playback | Passed | Passed |
| Audio output enumeration | Blocked: PortAudio runtime absent | Passed |
| Claude plugin manifest validation | Passed | Strict validation passed |
| Live-agent Stop continuation | Not tested | Not tested |
| Physical playback/listening | Not tested | Not tested |

Both platforms synthesized speech in memory with the selected
`en_US-ljspeech-medium` voice at 22,050 Hz. These checks confirm that the runtime
can generate PCM; they do not establish perceived audio quality or audibility.

## Test coverage

The 23 tests cover exact and missing markers, nonmatching delimiters, repeated
markers, verbatim and empty suffixes, nullable input, and the instruction to
continue as the same agent. They also exercise synchronous playback order,
device names and numeric IDs, saved output preferences, audio failure handling,
and protocol stdout.

A real child-process test writes to native stdout and verifies that audio logs
reach only stderr. Playback tests use stub streams and never open real speakers.
Ruff, ShellCheck, and Bash syntax checks also pass.

The adapters were checked against the official
[Codex hook contract](https://learn.chatgpt.com/docs/hooks) and
[Claude Stop reference](https://code.claude.com/docs/en/hooks#stop). The Codex
schema accepts a nullable `last_assistant_message` and an empty success object;
a blocking response requires a `reason`. Manifest validation and schema checks
do not establish end-to-end behavior in a live conversation.

## Remaining checks

On Linux, install the PortAudio runtime if absent, then enumerate devices from
the login session that will run the hook. Select the intended output and
explicitly play a sample to confirm audibility. Follow the [installation
instructions](../README.md) for both platforms.

In each client, enable or trust the plugin as required and test a short
conversation. Confirm that a response without the delimiter causes the same
agent to continue, and that the final suffix is spoken through the chosen
output. Stop is a checkpoint; other hooks may continue the conversation after
Chirp runs.
