import numpy as np

from pokesprite.image import ImageArray

ANSI_RESET_CODE = "\033[0m"

TRANSPARENCY_THRESHOLD = 127

WEIGHTS = np.array(
    [
        [[1, 1, 1], [1, 1, 1]],
        [[2, 2, 2], [2, 2, 2]],
        [[2, 2, 2], [2, 2, 2]],
        [[1, 1, 1], [1, 1, 1]],
    ],
    dtype=np.uint8,
)


# 0x2800 + bits
DOTS = [
    (0, 0),  # 0x0001
    (0, 1),  # 0x0002
    (0, 2),  # 0x0004
    (1, 0),  # 0x0008
    (1, 1),  # 0x0010
    (1, 2),  # 0x0020
    (0, 3),  # 0x0040
    (1, 3),  # 0x0080
]


def array_to_dots_art(array: ImageArray, threshold: int = TRANSPARENCY_THRESHOLD) -> str:
    """
    Convert an image array to colored braille art for terminal display.

    Each braille character represents a 2x4 block of pixels.
    The function uses the alpha channel to determine transparency and averages the RGB values for each block.
    Only pixels above the transparency threshold are considered visible.

    Args:
        array (ImageArray): The input image array with shape (height, width, 4) (RGBA).
        threshold (int, optional): Alpha threshold for transparency. Defaults to TRANSPARENCY_THRESHOLD.

    Returns:
        str: A string containing ANSI escape codes and braille characters representing the image.

    """
    alpha_channel = array[:, :, 3]
    mask = alpha_channel > threshold
    rgb_array = array[:, :, :3]
    height, width = mask.shape  # pyright: ignore[reportAny]
    result = ""
    for y in range(0, height // 4 * 4, 4):  # pyright: ignore[reportAny]
        for x in range(0, width // 2 * 2, 2):  # pyright: ignore[reportAny]
            r, g, b = np.average(  # pyright: ignore[reportAny]
                rgb_array[y : y + 4, x : x + 2],
                axis=(0, 1),
                weights=WEIGHTS,
            ).astype(int)
            block = 0x2800
            for i, (dx, dy) in enumerate(DOTS):
                if mask[y + dy, x + dx]:
                    block |= 1 << i
            result += f"\033[38;2;{r};{g};{b}m{chr(block)}"
        result += ANSI_RESET_CODE + "\n"
    return result + ANSI_RESET_CODE
