"""Permite executar o pacote via `python -m isolar`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
