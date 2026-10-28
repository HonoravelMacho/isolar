"""CLI completa + menu interativo do isolar."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Union

from . import __version__, core
from .utils import (
    IsolarError,
    InvalidTimeError,
    MediaNotFoundError,
    bold,
    check_dependencies,
    cyan,
    dim,
    format_time,
    get_media_info,
    green,
    human_size,
    list_media,
    red,
    warn,
    yellow,
)

PROG = "isolar"

USAGE_EXAMPLES = """exemplos:
  isolar                                   abre o menu interativo
  isolar audio video.mp4                   extrai o áudio para video_audio.mp3
  isolar audio video.mp4 -f flac           extrai o áudio sem perdas (FLAC)
  isolar audio aula.mp4 -f copy            cópia direta da faixa (sem recodificar)
  isolar video video.mp4                   gera video_mudo.mp4 (sem som)
  isolar cut video.mp4 -s 10 -d 45         recorta 45s a partir do segundo 10
  isolar cut video.mp4 -s 00:01:30 -e 00:03:00
  isolar cut musica.wav -s 30 -e 60 --reencode   corte exato (recodifica)
  isolar info video.mp4                    mostra duração, codecs e tamanho
  isolar --version                         mostra a versão
  isolar --help                            mostra esta ajuda"""

_MENU_ITEMS = [
    ("1", "🎵", "Isolar áudio", "extrai o áudio de um vídeo"),
    ("2", "🎬", "Isolar vídeo", "gera um vídeo sem som"),
    ("3", "✂ ", "Cortar/aparar", "corte ultrarrápido (stream copy)"),
    ("4", "ℹ ", "Info da mídia", "duração, codecs, tamanho..."),
]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def _banner() -> None:
    print()
    print(cyan("  ╔" + "═" * 48))
    print(cyan("  ║ ") + bold(f"🎧 {PROG.upper()}") + dim(f" v{__version__}"))
    print(cyan("  ║ ") + dim("isole áudio e vídeo na velocidade da luz ✨"))
    print(cyan("  ╚" + "═" * 48))


def _print_result(out: Path) -> None:
    size = out.stat().st_size if out.exists() else None
    print()
    print(green(f"✔ Pronto! Arquivo salvo em: {out}"))
    if size is not None:
        print(dim(f"   tamanho: {human_size(size)}"))


def _show_info(src: Path) -> None:
    info = get_media_info(src)
    video = "—"
    if info["has_video"]:
        video = f"{info['video_codec']} · {info['width']}x{info['height']}"
    audio = "—"
    if info["has_audio"]:
        audio = (
            f"{info['audio_codec']} · {info['audio_sample_rate'] or '?'} Hz · "
            f"{info['audio_channels'] or '?'} canal(is)"
        )
    rows = [
        ("Arquivo", str(info["path"])),
        ("Container", info["format_name"] or "?"),
        ("Duração", format_time(info["duration"])),
        ("Tamanho", human_size(info["size"])),
        ("Streams", str(info["nb_streams"])),
        ("Vídeo", video),
        ("Áudio", audio),
        ("Faixas de áudio", str(info["audio_streams"])),
    ]
    print()
    for key, value in rows:
        print(f"  {dim(key + ':')} {value}")


# ---------------------------------------------------------------------------
# Entradas interativas
# ---------------------------------------------------------------------------

def _ask(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    return input(cyan(f"  {question}{suffix}: ")).strip() or default


def _ask_yes_no(question: str, default: bool = True) -> bool:
    suffix = "S/n" if default else "s/N"
    raw = _ask(f"{question} ({suffix})", "").lower()
    if not raw:
        return default
    return raw in ("s", "sim", "y", "yes", "1", "true")


def _ask_path(prompt: str = "📁 Caminho do arquivo") -> Path:
    while True:
        raw = _ask(prompt, "").strip('"').strip("'")
        src = Path(raw).expanduser() if raw else None
        if src is not None and src.is_file():
            return src
        print(red(f"  ✖ Arquivo não encontrado: {raw or '(nada informado)'}"))


_PICK_LABELS = {
    "video": "Vídeos",
    "audio": "Áudios",
    "media": "Arquivos de mídia",
}


def _pick_file(kind: str = "video") -> Path:
    """Lista a mídia da pasta atual e devolve o arquivo escolhido por número.

    ``m`` (ou ``0``) mantém o modo antigo: digitar o caminho manualmente.
    Sem mídia local, cai direto no pedido de caminho.
    """
    files = list_media(Path.cwd(), kind=kind)
    if not files:
        warn(f"Nenhum {_PICK_LABELS[kind].lower()} na pasta atual — informe o caminho manualmente.")
        return _ask_path()

    print(dim(f"  📁 {_PICK_LABELS[kind]} em {Path.cwd()} ({len(files)}):"))
    for index, path in enumerate(files, start=1):
        try:
            size = dim(f" ({human_size(path.stat().st_size)})")
        except OSError:
            size = ""
        print(f"   {index:2d}) {path.name}{size}")
    print(dim("   ── m = digitar caminho manualmente ──"))

    while True:
        try:
            raw = input(cyan("  Escolha o arquivo [1]: ")).strip().lower()
        except EOFError:
            raise
        if raw in ("m", "manual", "0"):
            return _ask_path()
        index = 1 if raw == "" else int(raw) if raw.isdigit() else -1
        if 1 <= index <= len(files):
            return files[index - 1]
        warn(f"Escolha entre 1 e {len(files)} — ou 'm' para digitar o caminho.")


def _ask_audio_format() -> str:
    keys = list(core.AUDIO_FORMATS)
    print(dim("  Formatos suportados (FFmpeg por baixo dos panos):"))
    for index, key in enumerate(keys, start=1):
        print(f"   {index:2d}) {key:<5} — {core.AUDIO_FORMATS[key]['label']}")
    raw = _ask("Formato", "1")
    if raw.isdigit() and 1 <= int(raw) <= len(keys):
        return keys[int(raw) - 1]
    warn("Opção inválida — usando MP3.")
    return "mp3"


def _ask_track(audio_streams: int) -> int:
    if audio_streams <= 1:
        return 0
    raw = _ask(f"Qual faixa de áudio? (1 a {audio_streams})", "1")
    index = int(raw) - 1 if raw.isdigit() else 0
    if not 0 <= index < audio_streams:
        warn("Faixa inválida — usando a primeira.")
        return 0
    return index


def _ask_bitrate(default: str = "192k") -> str:
    raw = _ask("Bitrate (128k/192k/320k...)", default)
    if re.match(r"^\d+k$", raw.lower()):
        return raw.lower()
    if raw.isdigit():
        return f"{raw}k"
    if raw != default:
        warn(f"Bitrate inválido — usando {default}.")
    return default


# ---------------------------------------------------------------------------
# Fluxos do menu interativo
# ---------------------------------------------------------------------------

def _flow_audio() -> None:
    src = _pick_file("video")
    info = get_media_info(src)
    if not info["has_audio"]:
        raise IsolarError(f"'{src.name}' não possui faixa de áudio.")
    track = _ask_track(info["audio_streams"])
    fmt = _ask_audio_format()
    bitrate = "192k"
    if fmt not in ("wav", "flac", "aiff", "copy"):
        bitrate = _ask_bitrate()
    out = core.isolate_audio(src, fmt=fmt, bitrate=bitrate, track=track)
    _print_result(out)


def _flow_video() -> None:
    src = _pick_file("video")
    out = core.isolate_video(src)
    _print_result(out)


def _flow_cut() -> None:
    src = _pick_file("media")
    info = get_media_info(src)
    print(dim(f"  ✦ {core.describe_media(info)}"))
    start = _ask("Início (ex: 10, 1:30, 00:01:30.500)", "0")
    end = _ask("Fim (ex: 01:05:00)", "")
    duration = ""
    if not end:
        duration = _ask("Duração (ex: 60 ou 1m30s)", "")
    fast = _ask_yes_no("Corte rápido sem recodificar (stream copy)", True)
    out = core.cut_media(
        src,
        start=start,
        end=end or None,
        duration=duration or None,
        reencode=not fast,
        )
    _print_result(out)


def _flow_info() -> None:
    _show_info(_pick_file("media"))


# ---------------------------------------------------------------------------
# Menu interativo
# ---------------------------------------------------------------------------

def _interactive() -> int:
    _banner()
    flows: Dict[str, Callable[[], None]] = {
        "1": _flow_audio,
        "2": _flow_video,
        "3": _flow_cut,
        "4": _flow_info,
    }
    while True:
        print()
        print(bold("  O que você quer isolar hoje?"))
        for key, icon, title, hint in _MENU_ITEMS:
            print(f"   {key}) {icon} {title:<15} {dim(hint)}")
        print("   0) ✖ Sair")
        try:
            choice = input(cyan("\n  Escolha uma opção [0-4]: ")).strip().lower()
        except EOFError:
            print()
            return 0

        if choice in ("0", "", "q", "quit", "exit", "sair"):
            print(dim("\n  Até mais! 👋\n"))
            return 0
        if choice not in flows:
            warn("Opção inválida — escolha um número do menu.")
            continue

        try:
            flows[choice]()
        except IsolarError as exc:
            print(red(f"  ✖ {exc}"))
        except KeyboardInterrupt:
            print(yellow("\n  ✋ Operação cancelada — voltando ao menu."))
        print()


# ---------------------------------------------------------------------------
# CLI (flags)
# ---------------------------------------------------------------------------

def _ensure_input(value: Optional[str], prompt: str) -> Union[str, Path]:
    if value:
        return value
    return _ask_path(prompt)


def _run_audio(args: argparse.Namespace) -> int:
    src = _ensure_input(args.input, "📁 Arquivo para extrair o áudio")
    out = core.isolate_audio(
        src,
        fmt=args.format,
        bitrate=args.bitrate,
        track=args.track,
        output=args.output,
    )
    _print_result(out)
    return 0


def _run_video(args: argparse.Namespace) -> int:
    src = _ensure_input(args.input, "📁 Arquivo de vídeo (para remover o áudio)")
    out = core.isolate_video(src, output=args.output)
    _print_result(out)
    return 0


def _run_cut(args: argparse.Namespace) -> int:
    src = _ensure_input(args.input, "📁 Arquivo para cortar")
    out = core.cut_media(
        src,
        start=args.start,
        end=args.end,
        duration=args.duration,
        reencode=args.reencode,
        output=args.output,
    )
    _print_result(out)
    return 0


def _run_info(args: argparse.Namespace) -> int:
    src = _ensure_input(args.input, "📁 Arquivo para inspecionar")
    _show_info(Path(str(src)))
    return 0


_HANDLERS: Dict[str, Callable[[argparse.Namespace], int]] = {
    "audio": _run_audio,
    "video": _run_video,
    "cut": _run_cut,
    "info": _run_info,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "isolar — isole áudio e vídeo na velocidade da luz.\n"
            "Extração de áudio, remoção de faixa de som e cortes ultrarrápidos "
            "(cópia direta de stream) com FFmpeg por baixo dos panos."
        ),
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="mostra a versão do isolar e sai",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="(reservado) modo detalhado",
    )

    sub = parser.add_subparsers(dest="command", metavar="<comando>")

    p_audio = sub.add_parser(
        "audio",
        help="extrai o áudio de um vídeo (mp3, m4a, wav, flac, ogg, opus, copy...)",
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_audio.add_argument("input", nargs="?", help="arquivo de entrada (vídeo)")
    p_audio.add_argument(
        "-f", "--format",
        choices=list(core.AUDIO_FORMATS),
        default="mp3",
        help="formato de saída (padrão: mp3)",
    )
    p_audio.add_argument(
        "-b", "--bitrate",
        default="192k",
        help="bitrate para formatos com perdas (padrão: 192k)",
    )
    p_audio.add_argument(
        "-t", "--track",
        type=int,
        default=0,
        help="índice da faixa de áudio, começando em 0 (padrão: 0)",
    )
    p_audio.add_argument(
        "-o", "--output",
        help="arquivo ou pasta de saída (padrão: pasta de trabalho atual)",
    )

    p_video = sub.add_parser(
        "video",
        help="remove o áudio do vídeo, gerando um arquivo mudo",
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_video.add_argument("input", nargs="?", help="arquivo de vídeo de entrada")
    p_video.add_argument(
        "-o", "--output",
        help="arquivo ou pasta de saída (padrão: pasta de trabalho atual)",
    )

    p_cut = sub.add_parser(
        "cut",
        help="corta/apara a mídia sem recodificar (fast cut, -c copy)",
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_cut.add_argument("input", nargs="?", help="arquivo de mídia de entrada")
    p_cut.add_argument("-s", "--start", default=None, help="ponto de início (ex: 90, 1:30, 00:01:30.5)")
    p_cut.add_argument("-e", "--end", default=None, help="ponto de fim (ex: 00:03:00)")
    p_cut.add_argument("-d", "--duration", default=None, help="duração do recorte (ex: 45, 1m30s)")
    p_cut.add_argument(
        "--reencode",
        action="store_true",
        help="recodifica para um corte exato ao frame (mais lento)",
    )
    p_cut.add_argument(
        "-o", "--output",
        help="arquivo ou pasta de saída (padrão: pasta de trabalho atual)",
    )

    p_info = sub.add_parser(
        "info",
        help="mostra duração, codecs e tamanho da mídia",
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_info.add_argument("input", nargs="?", help="arquivo de mídia de entrada")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:  # noqa: C901
    """Ponto de entrada: flags diretas ou menu interativo quando sem argumentos."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _HANDLERS.get(args.command)  # None → menu interativo

    try:
        check_dependencies()
        if handler is None:
            return _interactive()
        return handler(args)
    except KeyboardInterrupt:
        print(yellow("\n✋ Operação cancelada pelo usuário."))
        return 130
    except EOFError:
        print(yellow("\n✋ Entrada encerrada."))
        return 130
    except (MediaNotFoundError, InvalidTimeError) as exc:
        print(red(f"✖ {exc}"))
        print(dim("   Dica: rode 'isolar --help' para ver os exemplos de uso."))
        return 1
    except IsolarError as exc:
        print(red(f"✖ {exc}"))
        return 1
