import json
from os import PathLike
from pathlib import Path
from typing import Any
import yaml

def read_yaml_file_config(path: str | PathLike[str]) -> Any:
    """Safely parse UTF-8 YAML without validating the resulting request shape."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_json_file_config(path: str | PathLike[str]) -> Any:
    """Parse UTF-8 JSON, propagating file-access and syntax errors."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_file_config(path: str | PathLike[str]) -> Any:
    """Parse .yaml, .yml, or .json using an exact, case-sensitive suffix.

    Return the parsed value without request validation. Unsupported suffixes
    raise ValueError; file-access and parser errors propagate unchanged.
    """
    file_path = Path(path)
    suff = file_path.suffix
    if suff in ['.yaml', '.yml']:
        return read_yaml_file_config(file_path)

    elif suff in ['.json']:
        return read_json_file_config(file_path)

    else:
        raise ValueError("Unknown configuration format")
