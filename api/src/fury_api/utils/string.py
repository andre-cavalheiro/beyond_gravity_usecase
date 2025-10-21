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


def slugify(text: str) -> str:
    """Convert text to a slug.

    Args:
        text (str): text to slugify

    Returns:
        str: slugified text
    """
    return text.lower().replace(" ", "-")


def random_password(length: int = 8, exclude: Sequence[str] | None = None) -> str:
    """Generate a random password.

    Args:
        length (int, optional): length of the password. Defaults to 8.
        exclude (Sequence[str] | None, optional): characters to exclude. Defaults to None.

    Returns:
        str: random password
    """
    chars_groups = cycle(
        (
            tuple(c for c in string.ascii_lowercase if exclude is None or c not in exclude),
            tuple(c for c in string.ascii_uppercase if exclude is None or c not in exclude),
            tuple(c for c in string.digits if exclude is None or c not in exclude),
            tuple(c for c in string.punctuation if exclude is None or c not in exclude),
        )
    )
    return "".join(random.choice(next(chars_groups)) for _ in range(length))  # noqa: S311
