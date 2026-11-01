# coding: utf-8

from enum import Enum


class SizeMismatchMode(Enum):
    """How to handle a source image that doesn't match the target dimensions."""

    REJECT = "reject"
    SCALE = "scale"       # Lanczos-resize to target (ignores aspect ratio)
    CENTER_CROP = "crop"  # Center-crop; requires source >= target on both axes
