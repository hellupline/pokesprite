import importlib.resources
import json
import random
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from typing import IO
from typing import Any
from typing import Literal
from zipfile import Path as ZipPath
from zipfile import ZipFile

import requests

from pokesprite.ansi import array_to_ansi_art_large
from pokesprite.ansi import array_to_ansi_art_small
from pokesprite.image import get_image_array


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


POKEMON_SPRITE_REPO_URL = "https://github.com/msikma/pokesprite/archive/refs/heads/master.zip"
POKEMON_MODULE_DATA_ROOT = _mkdir(Path(str(importlib.resources.files(__name__) / "data")))
POKEMON_DATA_ROOT = _mkdir(Path("data"))
POKEMON_SPRITES_REPO_ZIP_PATH = POKEMON_DATA_ROOT / "sprites.zip"
POKEMON_SPRITES_PATH = POKEMON_DATA_ROOT / "sprites"
POKEMON_DATABASE_PATH = POKEMON_MODULE_DATA_ROOT / "pokemon.json"
POKEMON_TXT_PATH = POKEMON_MODULE_DATA_ROOT / "txt"
POKEMON_TXT_SMALL_PATH = POKEMON_TXT_PATH / "small"
POKEMON_TXT_LARGE_PATH = POKEMON_TXT_PATH / "large"


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


def show_random_pokemon_sprite(
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
    show_pokemon_sprite(form, show_name, size, color)


def show_pokemon_sprite(
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
    with (POKEMON_TXT_PATH / size / color / f"{form}.txt").open(mode="r", encoding="utf-8") as f:
        print(f.read())  # noqa: T201


def generate_pokemon_sprite_ansi_files() -> None:
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
    with ZipFile(download_pokemon_sprite_repo_data(POKEMON_SPRITES_REPO_ZIP_PATH)) as zf:
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
            directory = _mkdir(POKEMON_SPRITES_PATH / color)
            txt_small_directory = _mkdir(POKEMON_TXT_SMALL_PATH / color)
            txt_large_directory = _mkdir(POKEMON_TXT_LARGE_PATH / color)
            for form in forms:
                generate_pokemon_sprite_ansi_file(
                    zdirectory / f"{form}.png",
                    directory / f"{form}.png",
                    txt_small_directory / f"{form}.txt",
                    txt_large_directory / f"{form}.txt",
                )


def download_pokemon_sprite_repo_data(path: Path) -> IO[bytes]:
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
        r = requests.request(method="GET", url=POKEMON_SPRITE_REPO_URL, timeout=10)
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


def get_pokemon_sprite_data(zpath: ZipPath, path: Path) -> IO[bytes]:
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


def generate_pokemon_sprite_ansi_file(
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
    image_data = get_pokemon_sprite_data(zipped_filename, sprite_filename)
    image_array = get_image_array(image_data)
    if not txt_small_exists:
        txt_small = array_to_ansi_art_small(image_array)
        with txt_filename_small.open(mode="w", encoding="utf-8") as f:
            _ = f.write(txt_small)
    if not txt_large_exists:
        txt_large = array_to_ansi_art_large(image_array)
        with txt_filename_large.open(mode="w", encoding="utf-8") as f:
            _ = f.write(txt_large)
