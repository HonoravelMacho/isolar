#!/usr/bin/env python3
"""Pipeline de publicação do isolar: build + twine check + upload no PyPI.

Uso:
    python deploy.py --check        apenas build + `twine check` (não publica)
    python deploy.py                build + check + upload no PyPI
    python deploy.py --yes          idem, sem pedir confirmação
    python deploy.py --skip-build   reenvia o que já está em dist/
    python deploy.py --push         também envia commits/tag ao GitHub

Credenciais (lidas nesta ordem de preferência):
    1. Variáveis de ambiente  PYPI_TOKEN / GITHUB_TOKEN
    2. Arquivo .env na raiz   (PYPI_TOKEN / GITHUB_TOKEN)  → twine via TWINE_*
    3. Arquivo .pypirc        (fallback do twine, modo padrão)

⚠️  Tokens ficam só em arquivos ignorados pelo git (.env / .pypirc).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent
GIT_REPO = "github.com/HonoravelMacho/isolar.git"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(
    cmd: Sequence[str],
    *,
    env: Optional[Dict[str, str]] = None,
    check: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    printable = " ".join(cmd)
    if not quiet:
        print(f"\n$ {printable}")
    proc = subprocess.run(list(cmd), cwd=ROOT, env=env)
    if check and proc.returncode != 0:
        raise SystemExit(f"✖ Comando falhou (código {proc.returncode}): {printable}")
    return proc


def _load_env_file() -> Dict[str, str]:
    data: Dict[str, str] = {}
    env_path = ROOT / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return data


def _mask(token: str) -> str:
    return f"{token[:8]}...{token[-4:]}" if len(token) > 14 else "***"


def read_version() -> str:
    text = (ROOT / "isolar" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("✖ Versão não encontrada em isolar/__init__.py")
    return match.group(1)


# ---------------------------------------------------------------------------
# Etapas do pipeline
# ---------------------------------------------------------------------------

def clean_artifacts() -> None:
    print("\n→ Limpando artefatos antigos (dist/, build/, *.egg-info)...")
    for folder in ("dist", "build"):
        shutil.rmtree(ROOT / folder, ignore_errors=True)
    for egg_info in ROOT.glob("*.egg-info"):
        shutil.rmtree(egg_info, ignore_errors=True)


def build() -> None:
    print("\n→ Compilando pacote (sdist + wheel)...")
    proc = _run([sys.executable, "-m", "build"], check=False)
    if proc.returncode != 0:
        raise SystemExit(
            "✖ Falha no build. Instale as ferramentas de publicação:\n"
            "    pip install --upgrade build twine"
        )


def twine_check() -> None:
    print("\n→ Validando distribuição (twine check)...")
    files = sorted(str(p) for p in (ROOT / "dist").glob("*") if p.is_file())
    if not files:
        raise SystemExit("✖ Nada em dist/ para validar.")
    _run([sys.executable, "-m", "twine", "check", *files])
    for path in files:
        print(f"   • {os.path.basename(path)}")


def upload() -> None:
    print("\n→ Enviando para o PyPI...")
    files = sorted(str(p) for p in (ROOT / "dist").glob("*") if p.is_file())
    if not files:
        raise SystemExit("✖ Nada em dist/ para publicar.")

    env = os.environ.copy()
    cmd: List[str] = [sys.executable, "-m", "twine", "upload", "--non-interactive"]

    token = os.environ.get("PYPI_TOKEN") or _load_env_file().get("PYPI_TOKEN")
    if token:
        # Token via variáveis de ambiente (não aparece na linha de comando).
        env["TWINE_USERNAME"] = "__token__"
        env["TWINE_PASSWORD"] = token
        print(f"   autenticando com token {_mask(token)} (.env / ambiente)")
    else:
        # Fallback: ~/.pypirc ou o .pypirc local da raiz do projeto.
        local = ROOT / ".pypirc"
        cmd += ["--config-file", str(local if local.exists() else "~/.pypirc")]
        print("   autenticando via .pypirc")

    cmd += files
    proc = subprocess.run(cmd, cwd=ROOT, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"✖ twine upload falhou (código {proc.returncode}).")


def push_github(version: str) -> None:
    print("\n→ Enviando para o GitHub...")
    env = _load_env_file()
    token = os.environ.get("GITHUB_TOKEN") or env.get("GITHUB_TOKEN")

    inside = _run(["git", "rev-parse", "--is-inside-work-tree"], check=False)
    if inside.returncode != 0:
        raise SystemExit(
            "✖ Este diretório não é um repositório git. Execute:\n"
            "    git init && git add -A && git commit -m 'primeiro commit'\n"
            "e rode o deploy.py --push novamente."
        )

    remote = _run(["git", "remote", "get-url", "origin"], check=False)
    if remote.returncode != 0:
        url = f"https://{token}@{GIT_REPO}" if token else f"https://{GIT_REPO}"
        _run(["git", "remote", "add", "origin", url], quiet=True)
        print("   remote 'origin' configurado.")
    else:
        print("   remote 'origin' já existe — reutilizando.")

    _run(["git", "add", "-A"], check=False)
    _run(["git", "commit", "-m", f"release v{version}"], check=False)

    tag = f"v{version}"
    _run(["git", "tag", tag], check=False)
    _run(["git", "push", "origin", "HEAD", "--tags"], check=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Publica o isolar no PyPI.")
    parser.add_argument("--check", action="store_true", help="build + twine check, sem publicar")
    parser.add_argument("--skip-build", action="store_true", help="reusa o que já está em dist/")
    parser.add_argument("--yes", action="store_true", help="não pede confirmação")
    parser.add_argument("--push", action="store_true", help="também envia commits/tag ao GitHub")
    args = parser.parse_args()

    version = read_version()

    if not args.skip_build:
        clean_artifacts()
        build()

    twine_check()

    if args.check:
        print(f"\n✔ Pacote isolar v{version} pronto para publicar! Rode: python deploy.py")
        return

    if not args.yes:
        try:
            answer = input(f"Publicar isolar v{version} no PyPI? [s/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            answer = ""
        if answer not in ("s", "sim", "y", "yes"):
            print("✖ Publicação cancelada.")
            return

    upload()
    print(f"\n✔ isolar v{version} publicado! https://pypi.org/project/isolar/{version}/")

    if args.push:
        push_github(version)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✖ Cancelado pelo usuário.")
        sys.exit(1)
