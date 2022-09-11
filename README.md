# pyright-precommit

Pyright pre-commit hooks that can be applied to subprojects.

## How to use

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/quwac/pyright-precommit
    rev: 1.1.270  # Pyright version you need. Check https://github.com/microsoft/pyright/releases
    hooks:
      - id: pyright
```
