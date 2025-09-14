#!/bin/bash

set -eu

uv run python3 -c 'import pokesprite.main; pokesprite.pokemon.generate_pokemon_sprite_ansi_files()'
