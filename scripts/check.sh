#!/usr/bin/env sh
set -eu
PYTHONPATH=src uv run python -m unittest discover -s tests -v
PYTHONPATH=src uv run python examples/create_entity.py >/dev/null
