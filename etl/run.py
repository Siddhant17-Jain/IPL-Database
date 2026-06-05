"""Single entrypoint for the data core: build -> validate -> export.

    python -m etl.run

Wipes and rebuilds data/ipl.duckdb from ipl_json/, so the database is always
reproducible from source as new seasons are added.
"""

from __future__ import annotations

import sys

from . import build_db, export, validate


def main(json_dir: str = "ipl_json") -> int:
    build_db.build(json_dir=json_dir)

    print("Validating ...")
    for line in validate.validate():
        print("  " + line)

    export.export()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
