#!/usr/bin/env bash
# The gate. Runs every test suite that exists so far; add new suites here.
set -euo pipefail
cd "$(dirname "$0")/.."

ran=0

# Counter and server tests (Python, standard library unittest).
if compgen -G "server/**/test_*.py" >/dev/null || compgen -G "server/test_*.py" >/dev/null; then
  python3 -m unittest discover -s server -p 'test_*.py' -t .
  ran=1
fi

# Plugin tests, once plugin/package.json defines "test".
if [[ -f plugin/package.json ]] && grep -q '"test"' plugin/package.json; then
  (cd plugin && npm test --silent)
  ran=1
fi

# Samples must never contain a real Hackattic access token.
if grep -rEn 'access_token=[A-Za-z0-9_-]{8,}' samples/ 2>/dev/null | grep -v 'access_token=REDACTED'; then
  echo "gate: unredacted Hackattic access token in samples/" >&2
  exit 1
fi

if (( ran == 0 )); then
  echo "gate: ok (no component tests yet)"
else
  echo "gate: ok"
fi
