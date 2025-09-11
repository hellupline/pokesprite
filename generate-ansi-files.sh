#!/bin/bash

set -eu

uv run python3 -c 'import pokesprite.main; pokesprite.main.generate_ansi_files()'
