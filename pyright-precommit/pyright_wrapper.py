import os
import subprocess
import sys
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyright.cli

_PYRIGHT_CONFIG_FILE_NAMES = ["pyrightconfig.json", "pyproject.toml"]


class _Pyright:
    def __init__(self, args: List[str]) -> None:
        self.args = args

    def execute(self) -> int:
        raise NotImplementedError()


class _PreinstalledPyright(_Pyright):
    def execute(self) -> int:
        print(f"PreinstalledPyright args={self.args}")
        return pyright.cli.main(self.args)


class _UserSpecifiedPyright(_Pyright):
    def __init__(self, pyright_path: str, uses_poetry_run: bool, args: List[str]) -> None:
        super().__init__(args)
        self.pyright_path = pyright_path
        self.uses_poetry_run = uses_poetry_run

    def execute(self) -> int:
        if self.uses_poetry_run:
            args = ["poetry", "run"] + [self.pyright_path] + self.args
        else:
            args = [self.pyright_path] + self.args
        print(f"UserSpecifiedPyright args={args}")
        proc = subprocess.Popen(args, shell=True)

        while True:
            do_not_break = False
            stdout = proc.stdout
            if stdout:
                lines = stdout.readlines()
                for line in lines:
                    sys.stdout.write(line.decode("utf-8"))
                    do_not_break = True

            returncode = proc.poll()
            if not do_not_break and returncode is not None:
                return returncode


@dataclass(frozen=True)
class _ParamFile:
    target_python_file_path: str
    config_file_path: str


@dataclass(frozen=True)
class _WrapperParam:
    pyright_path: Optional[str]
    uses_poetry_run: bool
    disable_subproject_search: bool
    files: List[_ParamFile]

    def __post_init__(self):
        if self.pyright_path is not None:
            path = Path(self.pyright_path)
            assert path.exists() and path.is_file(), f"Executable pyright not found at '{path}'"


def _parse_wrapper_params(arguments: List[str]) -> Tuple[Optional[str], bool, bool, List[str]]:
    pyright_path: Optional[str] = None
    uses_poetry_run = False
    disable_subproject_search = False
    index = 0

    new_args = []
    while index < len(arguments):
        argument = arguments[index]
        if argument.lower() == "--pyright-path":
            pyright_path = arguments[index + 1]
            index += 1
        elif argument.lower() == "--uses-poetry-run":
            uses_poetry_run = True
        elif argument.lower() == "--disable-subproject-search":
            disable_subproject_search = True
        else:
            new_args.append(argument)

        index += 1

    return pyright_path, uses_poetry_run, disable_subproject_search, new_args


def _to_params(arguments: List[str]) -> Tuple[List[str], _WrapperParam]:
    pyright_path, use_poetry_run, disable_subproject_search, arguments = _parse_wrapper_params(
        arguments
    )

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
                    params_file.append(
                        _ParamFile(
                            path.absolute().__str__(),
                            config_file_path.absolute().__str__(),
                        )
                    )
                    added = True
                    break
            if added:
                break
            else:
                parent = parent.parent

    return params_pyright, _WrapperParam(
        pyright_path, use_poetry_run, disable_subproject_search, params_file
    )


def main(args: List[str]) -> int:
    pyright_params, wrapper_param = _to_params(args)

    # Group by same config file.
    config_file_path_to_files: Dict[str, List[_ParamFile]] = OrderedDict()
    for file in wrapper_param.files:
        if file.config_file_path not in config_file_path_to_files:
            config_file_path_to_files[file.config_file_path] = []
        config_file_path_to_files[file.config_file_path].append(file)

    error = False
    for pyproject_toml_path, files in config_file_path_to_files.items():
        files = sorted(files, key=lambda file: file.target_python_file_path)
        assert len(files) > 0
        pyproject_toml_parent = Path(pyproject_toml_path).parent.absolute()
        args = (
            (
                [
                    "-p",
                    pyproject_toml_parent.__str__(),
                ]
                if not wrapper_param.disable_subproject_search
                else []
            )
            + pyright_params
            + [file.target_python_file_path for file in files]
        )

        if wrapper_param.pyright_path is not None:
            pyright_command = _UserSpecifiedPyright(
                pyright_path=wrapper_param.pyright_path,
                uses_poetry_run=wrapper_param.uses_poetry_run,
                args=args,
            )
        else:
            pyright_command = _PreinstalledPyright(args=args)

        error &= pyright_command.execute() == 0

    return 1 if error else 0


def entrypoint():
    sys.exit(main(sys.argv[1:]))
