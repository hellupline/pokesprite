import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np

from pokesprite.ansi import array_to_ansi_art_large
from pokesprite.ansi import array_to_ansi_art_small
from pokesprite.image import Box
from pokesprite.image import Color
from pokesprite.image import get_image_array
from pokesprite.pokemon import show_pokemon_list
from pokesprite.pokemon import show_pokemon_sprite
from pokesprite.pokemon import show_random_pokemon_sprite

ImageArray = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]
ImageRowArray = np.ndarray[tuple[int, int], np.dtype[np.uint8]]
ImagePixelArray = np.ndarray[tuple[int], np.dtype[np.uint8]]


argparser = ArgumentParser(
    prog="pokesprite",
    description="Generate ANSI art from Pokémon sprites.",
    usage="%(prog)s [options]",
)
_ = argparser.add_argument(
    "--random",
    help="Display a random Pokémon.",
    action="store_true",
    default=False,
)
_ = argparser.add_argument(
    "--name",
    help="Name of the Pokémon to display (e.g. 'ampharos' or 'ampharos-mega').",
    action="store",
    type=str,
)
_ = argparser.add_argument(
    "--list",
    help="List all available Pokémon forms.",
    action="store_true",
    default=False,
)
_ = argparser.add_argument(
    "--show-name",
    help="Show the name of the random Pokémon.",
    action="store_true",
    default=False,
)
_ = argparser.add_argument(
    "--large",
    help="Display the large version of the sprite (default: small).",
    action="store_true",
    default=False,
)
_ = argparser.add_argument(
    "--shiny",
    help="Display the shiny version of the sprite (default: regular).",
    action="store_true",
    default=False,
)
_ = argparser.add_argument(
    "--filename",
    help="Filename of any image to display as ANSI art.",
    action="store",
    type=str,
)
_ = argparser.add_argument(
    "--transparency-color-hex",
    help="Set a specific RGB color as transparent in the image (format: AABBCC).",
    action="store",
    type=str,
)
_ = argparser.add_argument(
    "--box-area",
    help="Crop the image using the given left, upper, right, and lower pixel coordinates (format: LxUxRxD).",
    action="store",
    type=str,
)


@dataclass()
class Namespace:
    """
    Represents configuration options for a sprite namespace.

    Attributes:
        random (bool): Whether to select randomly.
        name (str | None): The name of the namespace.
        list (bool): Whether to display as a list.
        show_name (bool): Whether to show the name.
        large (bool): Whether to use large sprites.
        shiny (bool): Whether to use shiny sprites.
        filename (str | None): The filename associated with the namespace.
        transparency_color (str | None): The transparency color in AABBCC format.
        box_area (str | None): The area dimensions in LxUxRxD format.

    """

    random: bool = False
    name: str | None = None
    list: bool = False
    show_name: bool = False
    large: bool = False
    shiny: bool = False
    filename: str | None = None
    transparency_color_hex: str | None = None
    box_area: str | None = None


def main() -> None:
    """
    Entry point for the pokesprite CLI application.

    Parses command-line arguments and executes the corresponding action:
        - Shows a random Pokémon if --random is specified.
        - Shows a specific Pokémon if --name is provided.
        - Lists all Pokémon if --list is specified.
        - Displays a custom image if --filename is provided.
        - Raises an error if no valid action is specified.

    Raises:
        ValueError: If no action is specified.

    """
    args = argparser.parse_args(namespace=Namespace())
    if args.random:
        show_random_pokemon_sprite(
            args.show_name,
            size="large" if args.large else "small",
            color="shiny" if args.shiny else "regular",
        )
        return
    if args.name:
        show_pokemon_sprite(
            args.name,
            args.show_name,
            size="large" if args.large else "small",
            color="shiny" if args.shiny else "regular",
        )
        return
    if args.list:
        show_pokemon_list()
        return
    if args.filename:
        show_custom_image(
            Path(args.filename),
            transparency_color_hex=args.transparency_color_hex,
            box_area_txt=args.box_area,
            large=args.large,
        )
        return
    argparser.print_help()
    sys.exit(1)


def show_custom_image(
    path: Path,
    transparency_color_hex: str | None = None,
    box_area_txt: str | None = None,
    large: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """
    Display a custom image in the terminal as ANSI art.

    Args:
        path (Path): Path to the image file.
        transparency_color_hex (str | None): Optional hex color string (AABBCC) for transparency.
        box_area_txt (str | None): Optional crop area string in format 'LxUxRxD'.
        large (bool): If True, displays the image in large ANSI art; otherwise, small.

    Returns:
        None

    Exits:
        If color or crop parsing fails, prints an error and exits the program.

    """
    transparency_color = parse_color_hex_or_quit(transparency_color_hex)
    box_area = parse_box_area_or_quit(box_area_txt)
    with path.open(mode="rb") as f:
        image_data = BytesIO(f.read())
    image_array = get_image_array(
        image_data,
        transparency_color=transparency_color,
        box_area=box_area,
    )
    if large:
        print(array_to_ansi_art_large(image_array), end="")  # noqa: T201
        return
    print(array_to_ansi_art_small(image_array), end="")  # noqa: T201
    return


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
