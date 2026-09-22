#!/bin/bash
# Double-click in Finder to start the ICS experiment web app; it opens in your browser.
# Close this window (or press Ctrl+C) to stop it.
cd "$(dirname "$0")" || exit 1

pause_on_error() {
  echo
  echo "$1"
  read -r -p "Press Enter to close this window."
  exit 1
}

# First run, or after the folder layout changed: create or refresh the Python environment.
if ! .venv/bin/python -c "import medsim, experiment, strategies, webapp" >/dev/null 2>&1; then
  echo "Setting up the Python environment (first run only)…"
  if command -v uv >/dev/null 2>&1; then
    { [ -x .venv/bin/python ] || uv venv --python 3.11 .venv; } &&
      uv pip install --python .venv/bin/python -e ".[dev]" ||
      pause_on_error "Setup failed; see the messages above."
  else
    { [ -x .venv/bin/python ] || python3 -m venv .venv; } &&
      .venv/bin/pip install -e ".[dev]" ||
      pause_on_error "Setup failed; see the messages above (Python 3.11 or newer is required)."
  fi
fi

[ -f .env ] || echo "Note: no .env file. Copy .env.example to .env and add OPENROUTER_API_KEY to run experiments."

.venv/bin/python -m webapp "$@" || pause_on_error "The web app stopped with an error."
