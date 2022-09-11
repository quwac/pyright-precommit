import os
import sys
from copy import deepcopy
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import List, Tuple

import pyright.cli

_PYRIGHT_CONFIG_FILE_NAMES = ["pyrightconfig.json", "pyproject.toml"]


@dataclass(frozen=True)
class _ParamFile:
    target_python_file_path: Path
    config_file_path: Path


def _to_params(arguments: List[str]) -> Tuple[List[str], List[_ParamFile]]:  # noqa: CCR001
    start_index = 0
    index = len(arguments) - 1
    while index >= 0:
        arg = arguments[index]
        if not os.path.exists(arg):
            start_index = index + 1
            break
        index -= 1
    if index >= 0:
        params_pyright: List[str] = arguments[0:start_index]
        file_paths: List[str] = arguments[start_index:]
    else:
        params_pyright: List[str] = []
        file_paths: List[str] = deepcopy(arguments)

    params_file: List[_ParamFile] = []

    for arg in file_paths:
        path = Path(arg)

        if not (path.exists() and path.is_file()):
            continue

        parent = path.parent
        while parent.exists():
            added = False
            for config_file_name in _PYRIGHT_CONFIG_FILE_NAMES:
                config_file_path = parent / config_file_name
                if config_file_path.exists() and config_file_path.is_file():
                    params_file.append(_ParamFile(path, config_file_path))
                    added = True
                    break
            if added:
                break
            else:
                parent = parent.parent

    return params_pyright, params_file


def main(file_paths: List[str]) -> int:
    pyright_params, params = _to_params(file_paths)

    # Group by same config file.
    pyright_config_file_path_and_params = list(groupby(params, lambda x: x.config_file_path))

    error = False
    for pyproject_toml_path, params in pyright_config_file_path_and_params:
        pyproject_toml_parent = pyproject_toml_path.parent.absolute()
        command = (
            [
                "pyright",
                "-p",
                pyproject_toml_parent.__str__(),
            ]
            + pyright_params
            + [param.target_python_file_path.absolute().__str__() for param in params]
        )

        print(f"command={' '.join(command)}")
        error &= pyright.cli.main(command[1:])

    return 1 if error else 0


def entrypoint():
    sys.exit(main(sys.argv[1:]))
