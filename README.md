# pokesprite

Show Pokémon sprites as ANSI art in your terminal.

## Features

- Display Pokémon sprites as colorful ANSI art in your terminal.
- Supports both small (half-block) and large (full-block) sprite formats.
- Show regular or shiny variants.
- List all available Pokémon forms.
- Display a random Pokémon.
- Show the name of the Pokémon alongside its sprite.

## Installation

Requires Python 3.13+. Install with [uv](https://github.com/astral-sh/uv):

```sh
uv pip install .
```

## Usage

Run the CLI:

```sh
pokesprite --help
```

### Options

- `--list` — List all available Pokémon forms.
- `--random` — Display a random Pokémon.
- `--show-name` — Show the name of the random Pokémon.
- `--large` — Display the large version of the sprite (default: small).
- `--shiny` — Display the shiny version of the sprite (default: regular).
- `--name <form>` — Display a specific Pokémon (e.g. `ampharos` or `ampharos-mega`).

### Example

```sh
pokesprite --name ampharos --large --shiny --show-name
```

## Development

To generate ANSI art files from the sprite repository:

```sh
./generate-ansi-files.sh
```

## License

MIT
