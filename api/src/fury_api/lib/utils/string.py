import random
import string
from collections.abc import Sequence
from itertools import cycle

__all__ = ["snake_case_to_camel", "snake_case_to_pascal", "slugify", "random_password"]


def snake_case_to_camel(text: str) -> str:
    """Convert snake case strings to camel case strings.

    Args:
        text (str): snake case string

    Returns:
        str: camel case string
    """
    components = text.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def snake_case_to_pascal(text: str) -> str:
    """Convert snake case strings to pascal case strings.

    Args:
        text (str): snake case string

    Returns:
        str: pascal case string
    """
    components = text.split("_")
    return components[0].title() + "".join(x.title() for x in components[1:])
