"""Command entry point; TTS dependencies are loaded only when needed."""

import sys


def main() -> int:
    if sys.argv[1:2] == ["hook"]:
        from .hook import main as hook_main

        return hook_main()

    from .audio import main as audio_main

    return audio_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
