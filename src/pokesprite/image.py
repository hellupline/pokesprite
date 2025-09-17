from typing import IO

import numpy as np
from PIL import Image

TRANSPARENCY_THRESHOLD = 128

ImageArray = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]
ImageRowArray = np.ndarray[tuple[int, int], np.dtype[np.uint8]]
ImagePixelArray = np.ndarray[tuple[int], np.dtype[np.uint8]]
Color = tuple[int, int, int]
Box = tuple[int, int, int, int]


def get_image_array(
    buf: IO[bytes],
    resize_factor: int | None = None,
    box_area: Box | None = None,
    transparency_color: Color | None = None,
) -> ImageArray:
    """
    Load and process an image from a byte buffer.

    This function performs several operations:
    - Loads the image from the provided byte buffer.
    - Converts the image to RGBA format.
    - Optionally crops the image to the specified box area.
    - Optionally resizes the image by the given resize_factor.
    - Optionally sets a specific color as transparent.
    - Fixes the alpha channel of the image.
    - Trims transparent edges from the image.

    Args:
        buf (IO[bytes]): Buffer containing image data in bytes.
        resize_factor (int | None): Optional factor to resize the image dimensions.
        box_area (Box | None): Optional box area (left, upper, right, lower) to crop the image.
        transparency_color (Color | None): Optional RGB color to set as transparent.

    Returns:
        ImageArray: The processed image as a NumPy array.

    """
    image = Image.open(buf).convert("RGBA")
    if box_area is not None:
        image = image.crop(box_area)
    if resize_factor is not None:
        size = (image.width * resize_factor, image.height * resize_factor)
        image = image.resize(size, resample=Image.Resampling.HAMMING)
    array = np.array(image)
    if transparency_color is not None:
        array = set_transparent_color(array, color=transparency_color)
    array = fix_alpha_channel(array)
    return trim_array(array)


def set_transparent_color(array: ImageArray, color: Color) -> ImageArray:
    """
    Set the alpha channel to zero for all pixels in the image array that match the given RGB color.

    Args:
        array (ImageArray): Input image array with shape (H, W, 4).
        color (tuple[int, int, int]): RGB color to be made transparent.

    Returns:
        ImageArray: Modified image array with specified color made transparent.

    """
    rgb = array[:, :, :3]
    mask = np.all(rgb == color, axis=-1)  # pyright: ignore[reportAny]
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
    alpha = array[:, :, 3]
    mask = alpha < threshold
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
    alpha = array[:, :, 3]
    mask = alpha > threshold
    ys, xs = np.where(mask)
    y_min, y_max = ys.min(), ys.max()  # pyright: ignore[reportAny]
    x_min, x_max = xs.min(), xs.max()  # pyright: ignore[reportAny]
    upper = max(y_min, 0)  # pyright: ignore[reportAny]
    left = max(x_min, 0)  # pyright: ignore[reportAny]
    lower = min(array.shape[0], y_max) + 1  # pyright: ignore[reportAny]
    right = min(array.shape[1], x_max) + 1  # pyright: ignore[reportAny]
    return array[upper:lower, left:right]
