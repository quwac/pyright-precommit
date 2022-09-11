#!/bin/bash

set -eux

pyright_version=$1

# Pyright version check
page=$(curl "https://github.com/microsoft/pyright/releases/tag/$pyright_version")
if [ "$page" == "Not Found" ]; then
    echo "Pyright $pyright_version not found."
    exit 1
fi

# Current branch check
is_main_branch=$(git branch | grep -E "^\* main")
if [ "$is_main_branch" == "" ]; then
    echo "Current branch is not 'main'."
    exit 2
fi

# Replace pyright version in pyproject.toml and update poetry.lock
dasel put string -f pyproject.toml -p toml '.tool.poetry.dependencies.pyright' "$pyright_version"
poetry update

# Git commit, tag and push
temp_branch_name="feature/temp_$pyright_version"
git checkout -b "$temp_branch_name"
git add .
git commit -m "Update pyright version to $pyright_version"
git tag -a "$pyright_version" -m "For pyright $pyright_version"
git push origin "$pyright_version"
git checkout main
git branch -D "$temp_branch_name"
