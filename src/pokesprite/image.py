from typing import IO

import numpy as np
from PIL import Image

TRANSPARENCY_THRESHOLD = 128

ImageArray = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]
ImageRowArray = np.ndarray[tuple[int, int], np.dtype[np.uint8]]
ImagePixelArray = np.ndarray[tuple[int], np.dtype[np.uint8]]
Color = tuple[int, int, int]


def get_image_array(buf: IO[bytes], transparency_color: Color | None = None) -> ImageArray:
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


def set_transparent_color(array: ImageArray, color: Color) -> ImageArray:
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


def fix_alpha_channel(array: ImageArray, threshold: int = TRANSPARENCY_THRESHOLD) -> ImageArray:
    """
    Set alpha to 0 if below threshold, 255 if above.

    Args:
        array (ImageArray): Input image array with shape (H, W, 4).
        threshold (int): Alpha threshold for transparency.

    Returns:
        ImageArray: Modified image array with fixed alpha channel.

    """
    mask = array[:, :, 3] < threshold
    array[:, :, 3] = np.where(mask, 0, 255)
    return array


def trim_array(array: ImageArray, threshold: int = TRANSPARENCY_THRESHOLD) -> ImageArray:
    """
    Crops image to bounding box of pixels above alpha threshold.

    Args:
        array (ImageArray): Input image array with shape (H, W, 4).
        threshold (int): Minimum alpha value to consider a pixel as non-transparent.

    Returns:
        ImageArray: Cropped image array.

    """
    mask = array[:, :, 3] > threshold
    ys, xs = np.where(mask)
    y_min, y_max = ys.min(), ys.max()  # pyright: ignore[reportAny]
    x_min, x_max = xs.min(), xs.max()  # pyright: ignore[reportAny]
    upper = max(y_min, 0)  # pyright: ignore[reportAny]
    left = max(x_min, 0)  # pyright: ignore[reportAny]
    lower = min(array.shape[0], y_max)  # pyright: ignore[reportAny]
    right = min(array.shape[1], x_max)  # pyright: ignore[reportAny]
    return array[upper:lower, left:right]
