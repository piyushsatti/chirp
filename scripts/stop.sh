#!/usr/bin/env bash
set -eu

plugin_root="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONPATH="${plugin_root}/src${PYTHONPATH:+:${PYTHONPATH}}"
chirp_data="${CHIRP_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/chirp}"
exec "${CHIRP_PYTHON:-${chirp_data}/venv/bin/python}" -m chirp hook
