#!/bin/bash

set -eu

uv run python3 -c 'import pokesprite.pokemon; pokesprite.pokemon.generate_pokemon_sprite_ansi_files()'
