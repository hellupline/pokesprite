from collections.abc import Iterable

import numpy as np

from pokesprite.image import ImageArray
from pokesprite.image import ImagePixelArray
from pokesprite.image import ImageRowArray

ANSI_RESET_CODE = "\033[0m"
UPPER_BLOCK = "▀"
LOWER_BLOCK = "▄"
EMPTY_BLOCK = " "
SOLID_BLOCK = "██"
WIDE_EMPTY_BLOCK = "  "


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
