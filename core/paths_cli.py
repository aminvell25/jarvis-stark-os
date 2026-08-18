"""Percorsi della piattaforma, per chi non e' Python.

Il lato Electron ha bisogno del percorso del socket, e **non deve sapere che
cos'e' `$XDG_RUNTIME_DIR`**. Oggi e' POSIX, domani su Windows sara' una named
pipe (§23): l'unico posto che conosce la differenza resta `core/platform/`
(invariante 29). Questo modulo e' la finestrella da cui lo si chiede.

    uv run python -m core.paths_cli --socket
    uv run python -m core.paths_cli --config-dir
"""

from __future__ import annotations

import argparse

from core.platform import paths as platform_paths

CAMPI = {
    "socket": lambda p: p.socket_path(),
    "runtime-dir": lambda p: p.runtime_dir(),
    "config-dir": lambda p: p.config_dir(),
    "data-dir": lambda p: p.data_dir(),
    "workspace": lambda p: p.workspace(),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gruppo = ap.add_mutually_exclusive_group(required=True)
    for nome in CAMPI:
        gruppo.add_argument(f"--{nome}", action="store_true")
    args = ap.parse_args()

    p = platform_paths()
    for nome, leggi in CAMPI.items():
        if getattr(args, nome.replace("-", "_")):
            print(leggi(p))
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
