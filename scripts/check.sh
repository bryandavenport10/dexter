#!/usr/bin/env sh
set -eu
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 examples/create_entity.py >/dev/null
