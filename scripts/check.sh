#!/usr/bin/env sh
set -eu
python -m unittest discover -s tests -v
python examples/create_entity.py >/dev/null
