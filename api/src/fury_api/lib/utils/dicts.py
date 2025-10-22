import json
from typing import Any


def dict_renamer(d: dict[str, Any], field_mapping: dict[str, str], ignore_missing: bool = False) -> dict[str, Any]:
    """Renames the keys of a dictionary.

    Args:
        d (dict): The dictionary to rename.
        field_mapping (dict): A mapping of old keys to new keys.
        ignore_missing (bool, optional): Whether to ignore missing keys. Defaults to False.

    Returns:
        dict: The renamed dictionary.
    """
    renamed = {}
    for k, v in d.items():
        if k in field_mapping:
            renamed[field_mapping[k]] = v
        elif not ignore_missing:
            renamed[k] = v
    return renamed


def merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Recursively merges dict2 into dict1.

    For each key in dict2, if the key is also in dict1 and both values are dicts, merge them.
    Otherwise, set dict1's key to dict2's value.

    Args:
        dict1 (dict[str, Any]): The dictionary to be merged into.
        dict2 (dict[str, Any]): The dictionary to merge.

    Returns:
        dict[str, Any]: The merged dictionary.
    """
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            merge_dicts(dict1[key], value)
        else:
            dict1[key] = value
    return dict1
