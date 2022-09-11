import sys
import textwrap
import time
from typing import Any, Dict, List, Optional

import requests
import tomli
from semver import VersionInfo


def _get_latest_version_info() -> VersionInfo:
    with open("pyproject.toml", "br") as f:
        obj = tomli.load(f)

    version = obj["tool"]["poetry"]["dependencies"]["pyright"]
    if version == "*":
        return VersionInfo(1, 1, 249)

    return VersionInfo.parse(version)


def _get_pyright_versions(token: Optional[str]) -> List[VersionInfo]:
    per_page = 100
    page = 0

    version_infos: List[VersionInfo] = []

    headers = {
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with requests.Session() as session:
        while True:
            page += 1
            url = f"https://api.github.com/repos/microsoft/pyright/tags?per_page={per_page}&page={page}"
            response = session.get(url, headers=headers)
            response_obj = response.json()
            if isinstance(response_obj, dict):
                if "message" in response_obj and response_obj["message"].startswith(
                    "API rate limit exceeded"
                ):
                    raise ValueError(f"{response_obj['message']} response={response.text}")

            sub_tags: List[Dict[str, Any]] = response_obj  # type: ignore
            if len(sub_tags) == 0:
                break

            for tag in sub_tags:
                try:
                    version_infos.append(VersionInfo.parse(tag["name"]))
                except Exception:
                    print(f'Failed to parse version "{tag["name"]}"')

            time.sleep(1)

    return sorted(version_infos, key=lambda x: x)


def _to_command(version_info: VersionInfo) -> str:
    version = version_info.__str__()
    return textwrap.dedent(
        f"""
        # {version}
        dasel put string -f pyproject.toml -p toml '.tool.poetry.dependencies.pyright' '{version}'
        poetry update
        git add pyproject.toml poetry.lock
        git commit -m "Update pyright version to {version}"
        git tag -a "{version}" -m "pyright {version}"

        """
    )[1:]


def _output(version_infos: List[VersionInfo], output_file_path: str):
    with open(output_file_path, "w") as f:
        f.write(
            textwrap.dedent(
                """
                #!/bin/sh

                set -eux

                git checkout "main"

                """
            )[1:]
        )

        f.writelines(_to_command(version_info) for version_info in version_infos)

        if len(version_infos) > 0:
            f.write(
                textwrap.dedent(
                    """
                    # git push
                    git push origin main
                    git push origin --tags
                    """
                )[1:]
            )


def main(output_file_path: str, access_token: Optional[str]) -> int:
    latest_version_info = _get_latest_version_info()

    version_infos = _get_pyright_versions(access_token)

    version_infos = list(filter(lambda x: x > latest_version_info, version_infos))

    _output(version_infos, output_file_path)

    return 0


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    access_token = sys.argv[2] if len(sys.argv) > 2 else None

    assert output_path is not None
    sys.exit(main(output_path, access_token))
