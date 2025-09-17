import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from pokesprite.ansi import array_to_blocks_art_large
from pokesprite.ansi import array_to_blocks_art_small
from pokesprite.dots import array_to_dots_art
from pokesprite.image import Box
from pokesprite.image import Color
from pokesprite.image import get_image_array
from pokesprite.pokemon import show_pokemon_list
from pokesprite.pokemon import show_pokemon_sprite
from pokesprite.pokemon import show_random_pokemon_sprite

argparser = ArgumentParser(
    prog="pokesprite",
    description="Generate ANSI art from Pokémon sprites.",
    usage="%(prog)s [options]",
)
_ = argparser.add_argument(
    "--filename",
    action="extend",
    nargs="+",
    type=str,
    help="Image files to convert to ansi art (e.g. 'image.png').",
    dest="filenames",
)
_ = argparser.add_argument(
    "--style",
    action="store",
    default="blocks",
    type=str,
    choices=["blocks", "dots"],
    help="art style to use: 'blocks' (default) or 'dots'.",
)
_ = argparser.add_argument(
    "--box-area",
    action="store",
    type=str,
    help="Crop the image using the given left, upper, right, and lower pixel coordinates (format: LxUxRxD).",
)
_ = argparser.add_argument(
    "--transparency-color-hex",
    action="store",
    type=str,
    help="Set a specific RGB color as transparent in the image (format: AABBCC).",
)
_ = argparser.add_argument(
    "--large",
    action="store_true",
    help="Display the image in large ANSI art (default is small, only valid for blocks style).",
)
_ = argparser.add_argument(
    "--name",
    action="store",
    type=str,
    help="Name of the Pokémon to display (e.g. 'ampharos' or 'ampharos-mega').",
)
_ = argparser.add_argument(
    "--random",
    action="store_true",
    help="Display a random Pokémon.",
)
_ = argparser.add_argument(
    "--list",
    action="store_true",
    help="List all available Pokémon forms.",
)
_ = argparser.add_argument(
    "--shiny",
    action="store_true",
    help="Display the shiny version of the Pokémon (only valid with --name or --random).",
)
_ = argparser.add_argument(
    "--show-name",
    action="store_true",
    help="Show the name of the random Pokémon.",
)


@dataclass()
class Namespace:
    """
    Represents a namespace for command-line args.

    Attributes:
        filename (list[str] | None): List of filenames.
        style (str | None): Art Style.
        box_area (str | None): Box area to crop the image.
        transparency_color_hex (str | None): Hex color code to mark as transparency color.
        large (bool): Whether to display in large ANSI art.
        name (str | None): Whether to select a Pokémon sprite.
        random (bool): Whether to select a random Pokémon sprite.
        list (bool): Whether to list all available Pokémon forms.
        shiny (bool): Whether to use shiny Pokémon sprite.
        show_name (bool): Whether to show the Pokémon name below the sprite.

    """

    filenames: list[str] | None = None
    style: Literal["blocks", "dots"] = "blocks"
    box_area: str | None = None
    transparency_color_hex: str | None = None
    large: bool = False
    name: str | None = None
    random: bool = False
    list: bool = False
    shiny: bool = False
    show_name: bool = False


def main() -> None:
    """
    Entry point for the pokesprite CLI tool.

    Parses command-line arguments, validates required inputs, and processes each input file
    according to the selected style ('blocks' or 'dots'). Displays help and exits if no filenames
    are provided.

    Steps:
        1. Parse arguments using argparser.
        2. If no filenames are provided, print help and exit.
        3. For each filename:
            a. Parse box area and transparency color from arguments.
            b. If style is 'blocks', call show_blocks with relevant parameters.
            c. If style is 'dots', call show_dots with relevant parameters.
    """
    args = argparser.parse_args(namespace=Namespace())
    if args.name:
        show_pokemon_sprite(
            args.name,
            show_name=args.show_name,
            style=args.style,
            size="large" if args.large else "small",
            color="shiny" if args.shiny else "regular",
        )
        return
    if args.random:
        show_random_pokemon_sprite(
            show_name=args.show_name,
            style=args.style,
            size="large" if args.large else "small",
            color="shiny" if args.shiny else "regular",
        )
        return
    if args.list:
        show_pokemon_list()
        return
    if args.filenames:
        for filename in map(Path, args.filenames):
            box_area = parse_box_area_or_quit(args.box_area)
            transparency_color = parse_color_hex_or_quit(args.transparency_color_hex)
            if args.style == "blocks":
                show_blocks(
                    filename,
                    box_area=box_area,
                    transparency_color=transparency_color,
                    large=args.large,
                )
            if args.style == "dots":
                show_dots(
                    filename,
                    box_area=box_area,
                    transparency_color=transparency_color,
                )
        return
    argparser.print_help()
    sys.exit(1)


def show_blocks(
    path: Path,
    box_area: Box | None = None,
    transparency_color: Color | None = None,
    large: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """
    Display an image as ANSI art in the terminal.

    Args:
        path (Path): Path to the image file.
        box_area (Box | None, optional): Area of the image to display. Defaults to None.
        transparency_color (Color | None, optional): Color to treat as transparent. Defaults to None.
        large (bool, optional):
            If True, displays the image in large ANSI art format.
            If False, uses small format.
            Defaults to False.

    Returns:
        None

    """
    with path.open(mode="rb") as f:
        image_data = BytesIO(f.read())
    image_array = get_image_array(
        image_data,
        box_area=box_area,
        transparency_color=transparency_color,
    )
    if large:
        print(array_to_blocks_art_large(image_array), end="")  # noqa: T201
        return
    print(array_to_blocks_art_small(image_array), end="")  # noqa: T201


def show_dots(
    path: Path,
    box_area: Box | None = None,
    transparency_color: Color | None = None,
) -> None:
    """
    Display an image as dots art in the terminal.

    Args:
        path (Path): Path to the image file.
        box_area (Box | None): Optional area to crop the image.
        transparency_color (Color | None): Optional color to treat as transparent.

    Returns:
        None

    """
    with path.open(mode="rb") as f:
        image_data = BytesIO(f.read())
    image_array = get_image_array(
        image_data,
        resize_factor=2,
        box_area=box_area,
        transparency_color=transparency_color,
    )
    print(array_to_dots_art(image_array), end="")  # noqa: T201


def parse_color_hex_or_quit(value: str | None) -> Color | None:
    """
    Parse a hex color string in the format 'AABBCC' and return its RGB components.

    Args:
        value (str | None): The hexadecimal color string to parse, or None, e.g., 'AABBCC'.

    Returns:
        Color | None: A tuple (r, g, b) if parsing succeeds, or None if value is None.

    Exits:
        If the value is not 6 characters long, prints an error and exits the program.

    """
    if value is None:
        return None
    if len(value) != 6:  # noqa: PLR2004
        print("Color must be in format AABBCC")  # noqa: T201
        sys.exit(1)
    r = int(value[0:2], base=16)
    g = int(value[2:4], base=16)
    b = int(value[4:6], base=16)
    return (r, g, b)


def parse_box_area_or_quit(value: str | None) -> Box | None:
    """
    Parse a area string in the format 'LxUxRxD' into a tuple of four integers.

    Args:
        value (str | None): The area string to parse, or None.

    Returns:
        Box | None: A tuple (left, upper, right, lower) if parsing succeeds, or None if value is None.

    Exits:
        If the value is not in the correct format, prints an error and exits the program.

    """
    if value is None:
        return None
    try:
        left, upper, right, lower = [int(v) for v in value.split("x")]
    except ValueError:
        print("Area must be in format LxUxRxD")  # noqa: T201
        sys.exit(1)
    return (left, upper, right, lower)


if __name__ == "__main__":
    main()
