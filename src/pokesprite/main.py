import importlib.resources
import json
import random
import sys
from argparse import ArgumentParser
from collections.abc import Iterable
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import IO
from typing import Any
from typing import Literal
from zipfile import Path as ZipPath
from zipfile import ZipFile

import numpy as np
import requests
from PIL import Image


def _mkdir(path: Path) -> Path:
    """
    Create a directory at the given path, including any necessary parent directories.

    Args:
        path (Path): The directory path to create.

    Returns:
        Path: The created directory path.

    """
    path.mkdir(parents=True, exist_ok=True)
    return path


ANSI_RESET_CODE = "\033[0m"
UPPER_BLOCK = "▀"
LOWER_BLOCK = "▄"
EMPTY_BLOCK = " "
SOLID_BLOCK = "██"
WIDE_EMPTY_BLOCK = "  "
TRANSPARENCY_THRESHOLD = 128

REPO_URL = "https://github.com/msikma/pokesprite/archive/refs/heads/master.zip"


MODULE_DATA_ROOT = _mkdir(Path(str(importlib.resources.files(__name__) / "data")))
DATA_ROOT = _mkdir(Path("data"))
SPRITES_REPO_ZIP_PATH = DATA_ROOT / "sprites.zip"
SPRITES_PATH = DATA_ROOT / "sprites"
POKEMON_DATABASE_PATH = MODULE_DATA_ROOT / "pokemon.json"
TXT_PATH = MODULE_DATA_ROOT / "txt"
TXT_SMALL_PATH = TXT_PATH / "small"
TXT_LARGE_PATH = TXT_PATH / "large"


ImageArray = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]
ImageRowArray = np.ndarray[tuple[int, int], np.dtype[np.uint8]]
ImagePixelArray = np.ndarray[tuple[int], np.dtype[np.uint8]]


argparser = ArgumentParser(
    prog="pokesprite",
    description="Generate ANSI art from Pokémon sprites.",
    usage="%(prog)s [options]",
)
_ = argparser.add_argument(
    "--list",
    help="List all available Pokémon forms.",
    action="store_true",
    default=False,
)
_ = argparser.add_argument(
    "--random",
    help="Display a random Pokémon.",
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
    "--name",
    help="Name of the Pokémon to display (e.g. 'ampharos' or 'ampharos-mega').",
    action="store",
    type=str,
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


@dataclass()
class Namespace:
    """
    Represents configuration options for a sprite namespace.

    Attributes:
        list (bool): Whether to display as a list.
        random (bool): Whether to select randomly.
        show_name (bool): Whether to show the name.
        large (bool): Whether to use large sprites.
        shiny (bool): Whether to use shiny sprites.
        name (str | None): The name of the namespace.
        filename (str | None): The filename associated with the namespace.
        transparency_color (str | None): The transparency color in hex format.

    """

    list: bool = False
    random: bool = False
    show_name: bool = False
    large: bool = False
    shiny: bool = False
    name: str | None = None
    filename: str | None = None
    transparency_color_hex: str | None = None


def main() -> None:
    """
    Entry point for the pokesprite CLI application.

    Parses command-line arguments and executes the corresponding action:
        - Lists all Pokémon if --list is specified.
        - Shows a random Pokémon if --random is specified.
        - Shows a specific Pokémon if --name is provided.
        - Raises an error if no valid action is specified.

    Raises:
        ValueError: If no action is specified.

    """
    args = argparser.parse_args(namespace=Namespace())
    if args.list:
        show_pokemon_list()
        return
    if args.random:
        show_random_pokemon(
            args.show_name,
            size="large" if args.large else "small",
            color="shiny" if args.shiny else "regular",
        )
        return
    if args.name:
        show_pokemon(
            args.name,
            args.show_name,
            size="large" if args.large else "small",
            color="shiny" if args.shiny else "regular",
        )
        return
    if args.filename:
        show_custom_image(
            Path(args.filename),
            color_hex=args.transparency_color_hex,
            large=args.large,
        )
        return
    argparser.print_help()
    sys.exit(1)


def show_custom_image(
    path: Path,
    color_hex: str | None = None,
    large: bool = False,  # noqa: FBT001, FBT002
) -> None:
    transparency_color = None
    if color_hex:
        try:
            transparency_color = parse_color_hex(color_hex)
        except ValueError as e:
            (msg,) = e.args  # pyright: ignore[reportAny]
            print(msg)  # noqa: T201  # pyright: ignore[reportAny]
            sys.exit(1)
    with path.open(mode="rb") as f:
        image_data = BytesIO(f.read())
    image_array = get_image_array(image_data, transparency_color=transparency_color)
    if large:
        print(array_to_ansi_art_large(image_array), end="")  # noqa: T201
        return
    print(array_to_ansi_art_small(image_array), end="")  # noqa: T201
    return


def show_pokemon_list() -> None:
    """
    Print the list of all Pokémon forms available in the database.

    Reads the Pokémon database file, extracts all forms, and prints each form to stdout.

    Returns:
        None

    """
    with POKEMON_DATABASE_PATH.open(mode="r", encoding="utf-8") as f:
        data = json.load(f)  # pyright: ignore[reportAny]
    for form in _get_pokemon_forms(data):  # pyright: ignore[reportAny]
        print(form)  # noqa: T201


def show_random_pokemon(
    show_name: bool = True,  # noqa: FBT001, FBT002
    size: Literal["small", "large"] = "small",
    color: Literal["regular", "shiny"] = "regular",
) -> None:
    """
    Display a random Pokémon form.

    Args:
        show_name (bool): Whether to display the Pokémon's name.
        size (Literal["small", "large"]): The size of the Pokémon sprite to show.
        color (Literal["regular", "shiny"]): The color variant of the Pokémon sprite.

    Returns:
        None

    """
    with POKEMON_DATABASE_PATH.open(mode="r", encoding="utf-8") as f:
        data = json.load(f)  # pyright: ignore[reportAny]
    forms = [*_get_pokemon_forms(data)]  # pyright: ignore[reportAny]
    form = random.choice(forms)  # noqa: S311
    show_pokemon(form, show_name, size, color)


def show_pokemon(
    form: str,
    show_name: bool = True,  # noqa: FBT001, FBT002
    size: Literal["small", "large"] = "small",
    color: Literal["regular", "shiny"] = "regular",
) -> None:
    """
    Display the ASCII art of a Pokémon form in the terminal.

    Prints the form name (if show_name is True) and the corresponding ASCII art from a text file.

    Args:
        form (str): The name of the Pokémon form to display.
        show_name (bool): Whether to print the form name before the art.
        size (Literal["small", "large"]): The size of the art to display.
        color (Literal["regular", "shiny"]): The color variant of the art.

    Returns:
        None


    """
    if show_name:
        print(form)  # noqa: T201
    with (TXT_PATH / size / color / f"{form}.txt").open(mode="r", encoding="utf-8") as f:
        print(f.read())  # noqa: T201


def generate_sprite_ansi_files() -> None:
    """
    Extract Pokémon sprite images from a ZIP archive.

    Generates ANSI art files for each form and color variant, and saves them in the appropriate directories.

    Steps:
    1. Opens the sprites ZIP archive.
    2. Loads all Pokémon forms from the JSON database.
    3. For each color variant ('regular', 'shiny'):
        a. Creates output directories for PNG and TXT files.
        b. Iterates over each form and generates ANSI art files from PNG sprites.

    Returns:
        BytesIO: The repository data as a BytesIO object.

    """
    with ZipFile(download_repo_data(SPRITES_REPO_ZIP_PATH)) as zf:
        if zf.filename is None:
            zf.filename = "sprites.zip"  # zipfile.Path needs this to work properly
        forms = [
            *get_pokemon_forms(
                ZipPath(zf, at="pokesprite-master/data/pokemon.json"),
                POKEMON_DATABASE_PATH,
            ),
        ]
        for color in ["regular", "shiny"]:
            zdirectory = ZipPath(zf, at="pokesprite-master/pokemon-gen8/") / color
            directory = _mkdir(SPRITES_PATH / color)
            txt_small_directory = _mkdir(TXT_SMALL_PATH / color)
            txt_large_directory = _mkdir(TXT_LARGE_PATH / color)
            for form in forms:
                generate_sprite_ansi_file(
                    zdirectory / f"{form}.png",
                    directory / f"{form}.png",
                    txt_small_directory / f"{form}.txt",
                    txt_large_directory / f"{form}.txt",
                )


def download_repo_data(path: Path) -> IO[bytes]:
    """
    Download repository data from a remote URL or loads it from a cached file.

    If the file at 'path' does not exist, it fetches the data from REPO_URL,
    writes it to 'path' for caching, and returns the data as a BytesIO object.
    If the file at 'path' exists, it reads the data directly from the cached file.

    Args:
        path (Path): Path to the cached repository data file.

    Returns:
        BytesIO: The repository data as a BytesIO object.

    """
    if not path.exists():
        r = requests.request(method="GET", url=REPO_URL, timeout=10)
        r.raise_for_status()
        data = r.content
        with path.open(mode="wb") as f:
            _ = f.write(data)
    else:
        with path.open(mode="rb") as f:
            data = f.read()
    return BytesIO(data)


def get_pokemon_forms(zpath: ZipPath, path: Path) -> Iterator[str]:
    """
    Load Pokémon forms data from a zip file or a cached file and yields form names.

    If the file at 'path' does not exist, it reads the data from the zip file at 'zpath',
    writes it to 'path' for caching, and loads the data.
    If the file at 'path' exists, it loads the data directly from the cached file.

    Args:
        zpath (ZipPath): Path to the JSON file inside the zip archive.
        path (Path): Path to the cached JSON file.

    Returns:
        Iterator[str]: An iterator over Pokémon form names.

    """
    if not path.exists():
        with zpath.open(mode="r") as f:
            data = json.load(f)  # pyright: ignore[reportAny]
        with path.open(mode="w", encoding="utf-8") as f:
            json.dump(data, f)
    else:
        with path.open(mode="r", encoding="utf-8") as f:
            data = json.load(f)  # pyright: ignore[reportAny]
    return _get_pokemon_forms(data)  # pyright: ignore[reportAny]


def _get_pokemon_forms(data: dict[str, Any]) -> Iterator[str]:  # pyright: ignore[reportExplicitAny]
    """
    Yield all Pokémon form names from the provided data.

    Iterates through each Pokémon entry in the data, and for each form in "gen-8",
    yields the form name. If the form is an alias, it is skipped.
    If the form name is "$", yields the Pokémon's English slug.
    Otherwise, yields the slug combined with the form name.

    Args:
        data (dict[str, Any]): Dictionary containing Pokémon data.

    Yields:
        str: The name of each Pokémon form.

    """
    for pokemon in data.values():  # pyright: ignore[reportAny]
        for form_name, form_info in pokemon["gen-8"]["forms"].items():  # pyright: ignore[reportAny]
            if "is_alias_of" in form_info:
                continue
            if form_name == "$":
                yield pokemon["slug"]["eng"]
            else:
                yield f"{pokemon['slug']['eng']}-{form_name}"


def get_sprite_data(zpath: ZipPath, path: Path) -> IO[bytes]:
    """
    Retrieve sprite image data from a zip file or a cached file.

    If the file at 'path' does not exist, it reads the image data from the zip file at 'zpath',
    writes it to 'path' for caching, and returns the data as a BytesIO object.
    If the file at 'path' exists, it reads the image data directly from the cached file
    and returns it as a BytesIO object.

    Args:
        zpath (ZipPath): Path to the image inside the zip archive.
        path (Path): Path to the cached image file.

    Returns:
        BytesIO: The image data as a BytesIO object.

    """
    if not path.exists():
        with zpath.open(mode="rb") as f:
            img_data = f.read()
        with path.open(mode="wb") as f:
            _ = f.write(img_data)
    else:
        # NOTE:
        # this is cached, so we don't read from the zip file again.
        # we can get rid we dont care about caching.
        with path.open(mode="rb") as f:
            img_data = f.read()
    return BytesIO(img_data)


def generate_sprite_ansi_file(
    zipped_filename: ZipPath,
    sprite_filename: Path,
    txt_filename_small: Path,
    txt_filename_large: Path,
) -> None:
    """
    Generate ANSI art files (small and large) from a sprite image inside a zip archive.

    Checks if the output text files already exist; if not, extracts the sprite image,
    converts it to ANSI art in two formats (small and large), and writes the results
    to the specified text files.

    Args:
        zipped_filename (ZipPath): Path inside the zip archive containing the sprite.
        sprite_filename (Path): Path to the extracted sprite image.
        txt_filename_small (Path): Output path for the small ANSI art text file.
        txt_filename_large (Path): Output path for the large ANSI art text file.

    Returns:
        None

    """
    txt_small_exists = txt_filename_small.exists()
    txt_large_exists = txt_filename_large.exists()
    if txt_small_exists and txt_large_exists:
        return
    image_data = get_sprite_data(zipped_filename, sprite_filename)
    image_array = get_image_array(image_data)
    if not txt_small_exists:
        txt_small = array_to_ansi_art_small(image_array)
        with txt_filename_small.open(mode="w", encoding="utf-8") as f:
            _ = f.write(txt_small)
    if not txt_large_exists:
        txt_large = array_to_ansi_art_large(image_array)
        with txt_filename_large.open(mode="w", encoding="utf-8") as f:
            _ = f.write(txt_large)


def get_image_array(
    buf: IO[bytes],
    transparency_color: tuple[int, int, int] | None = None,
) -> ImageArray:
    """
    Load an image from a byte buffer.

    Processes its alpha channel, trims transparent edges, and returns the image as a NumPy array.

    Args:
        buf (IO[bytes]): A buffer containing image data in bytes.
        transparency_color (tuple[int, int, int] | None): RGB color to set as transparent.
            If None, no color is made transparent.

    Returns:
        ImageArray: The processed image as a NumPy array.

    """
    array = np.array(Image.open(buf).convert("RGBA"))
    if transparency_color is not None:
        array = set_transparent_color(array, color=transparency_color)
    array = fix_alpha_channel(array)
    array = trim_array(array)
    return array  # noqa: RET504


def set_transparent_color(
    array: ImageArray,
    color: tuple[int, int, int],
) -> ImageArray:
    """
    Set the alpha channel to zero for all pixels in the image array that match the given RGB color.

    Args:
        array (ImageArray): Input image array with shape (H, W, 4).
        color (tuple[int, int, int]): RGB color to be made transparent.

    Returns:
        ImageArray: Modified image array with specified color made transparent.

    """
    mask = np.all(array[:, :, :3] == color, axis=-1)  # pyright: ignore[reportAny]
    array[mask, 3] = 0
    return array


def fix_alpha_channel(
    array: ImageArray,
    transparency_threshold: int = TRANSPARENCY_THRESHOLD,
) -> ImageArray:
    """
    Set alpha to 0 if below threshold, 255 if above.

    Args:
        array (ImageArray): Input image array with shape (H, W, 4).
        transparency_threshold (int): Alpha threshold for transparency.

    Returns:
        ImageArray: Modified image array with fixed alpha channel.

    """
    mask = array[:, :, 3] < transparency_threshold
    array[:, :, 3] = np.where(mask, 0, 255)
    return array


def trim_array(
    array: ImageArray,
    transparency_threshold: int = TRANSPARENCY_THRESHOLD,
) -> ImageArray:
    """
    Crops image to bounding box of pixels above alpha threshold.

    Args:
        array (ImageArray): Input image array with shape (H, W, 4).
        transparency_threshold (int): Minimum alpha value to consider a pixel as non-transparent.

    Returns:
        ImageArray: Cropped image array.

    """
    mask = array[:, :, 3] > transparency_threshold
    ys, xs = np.where(mask)
    y_min, y_max = ys.min(), ys.max()  # pyright: ignore[reportAny]
    x_min, x_max = xs.min(), xs.max()  # pyright: ignore[reportAny]
    upper = max(y_min, 0)  # pyright: ignore[reportAny]
    left = max(x_min, 0)  # pyright: ignore[reportAny]
    lower = min(array.shape[0], y_max)  # pyright: ignore[reportAny]
    right = min(array.shape[1], x_max)  # pyright: ignore[reportAny]
    return array[upper:lower, left:right]


def array_to_ansi_art_small(array: ImageArray) -> str:
    """
    Convert a 2D image array into a string of ANSI art using half-block characters.

    Each pair of rows is combined into a single line using upper and lower half-blocks,
    with appropriate ANSI color codes for each pixel pair.

    Args:
        array (ImageArray): 2D array of pixels.

    Returns:
        str: ANSI art string representation using half-blocks.

    """
    result = ""
    for upper_row, lower_row in rows_pair(array):
        for upper_pixel, lower_pixel in zip(upper_row, lower_row, strict=False):
            result += pixel_pair_to_ansi_block(upper_pixel, lower_pixel)
        result += ANSI_RESET_CODE + "\n"
    return result + ANSI_RESET_CODE


def array_to_ansi_art_large(array: ImageArray) -> str:
    """
    Convert a 2D image array into a string of ANSI art using wide blocks.

    Each pixel is represented by either a colored solid block or an empty block,
    depending on its alpha value. The function iterates over each row and pixel,
    applying the appropriate ANSI color code for visible pixels.

    Args:
        array (ImageArray): 2D array of pixels, where each pixel is a tuple (r, g, b, a).

    Returns:
        str: ANSI art string representation of the image.

    """
    row: ImageRowArray
    pixel: ImagePixelArray
    result = ""
    for row in array:
        for pixel in row:
            r, g, b, a = pixel
            if a == 0:
                result += WIDE_EMPTY_BLOCK
            else:
                result += ansi_color_code(r, g, b) + SOLID_BLOCK
        result += ANSI_RESET_CODE + "\n"
    return result + ANSI_RESET_CODE


def rows_pair(arr: ImageArray) -> Iterable[tuple[ImageRowArray, ImageRowArray]]:
    """
    Group the input array of image rows into pairs.

    Args:
        arr (ImageArray): An iterable of image row arrays.

    Returns:
        Iterable[tuple[ImageRowArray, ImageRowArray]]: An iterable of tuples,
        each containing two consecutive image row arrays.

    Notes:
        - If the number of rows is odd, the last row will be omitted.
        - Uses zip and iter to efficiently pair rows without creating intermediate lists.

    """
    return zip(*([iter(arr)] * 2), strict=False)


def pixel_pair_to_ansi_block(upper_pixel: ImagePixelArray, lower_pixel: ImagePixelArray) -> str:
    """
    Convert a pair of image pixels (upper and lower) into a string representing an ANSI block character.

    With appropriate foreground and background colors.

    Args:
        upper_pixel (ImagePixelArray): RGBA values for the upper pixel.
        lower_pixel (ImagePixelArray): RGBA values for the lower pixel.

    Returns:
        str: ANSI escape code string representing the colored block.

    Raises:
        ValueError: If neither pixel is visible (alpha == 0 for both).

    """
    upper_pixel_r, upper_pixel_g, uppper_pixel_b, upper_pixel_a = upper_pixel
    lower_pixel_r, lower_pixel_g, lower_pixel_b, lower_pixel_a = lower_pixel
    if upper_pixel_a == 0 and lower_pixel_a == 0:
        return ANSI_RESET_CODE + EMPTY_BLOCK
    if upper_pixel_a != 0:
        code1 = ansi_color_code(upper_pixel_r, upper_pixel_g, uppper_pixel_b, background=False)
        code2 = ""
        if lower_pixel_a != 0:
            code2 = ansi_color_code(lower_pixel_r, lower_pixel_g, lower_pixel_b, background=True)
        return ANSI_RESET_CODE + code1 + code2 + UPPER_BLOCK
    if lower_pixel_a != 0:
        code2 = ansi_color_code(lower_pixel_r, lower_pixel_g, lower_pixel_b, background=False)
        return ANSI_RESET_CODE + code2 + LOWER_BLOCK
    raise ValueError


def ansi_color_code(r: np.uint8, g: np.uint8, b: np.uint8, background: bool = False) -> str:  # noqa: FBT001, FBT002
    """
    Return an ANSI escape code string for setting the foreground or background color in the terminal.

    Args:
        r (np.uint8): Red component (0-255).
        g (np.uint8): Green component (0-255).
        b (np.uint8): Blue component (0-255).
        background (bool, optional): If True, sets background color; otherwise, sets foreground color.

    Returns:
        str: ANSI escape code for the specified color.

    """
    return f"\033[{48 if background else 38};2;{r};{g};{b}m"


def parse_color_hex(value: str) -> tuple[int, int, int]:
    """
    Parse a hex color string in the format 'AABBCC' and return its RGB components.

    Args:
        value (str): A string representing a hex color, e.g., 'AABBCC'.

    Returns:
        tuple[int, int, int]: A tuple containing the red, green, and blue components as integers.

    Raises:
        ValueError: If the input string is not in the correct format.

    """
    if len(value) != 6:  # noqa: PLR2004
        msg = "Color must be in format AABBCC"
        raise ValueError(msg)
    r = int(value[0:2], base=16)
    g = int(value[2:4], base=16)
    b = int(value[4:6], base=16)
    return (r, g, b)


if __name__ == "__main__":
    main()
