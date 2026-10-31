"""Utilidades de sistema, FFmpeg, tempos e terminal para o isolar."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

__all__ = [
    "IsolarError",
    "FFmpegNotFoundError",
    "FFmpegError",
    "MediaNotFoundError",
    "InvalidTimeError",
    "check_dependencies",
    "get_media_info",
    "detect_media_kind",
    "list_media",
    "run_ffmpeg",
    "parse_time",
    "format_time",
    "resolve_output_path",
    "human_size",
    "bold",
    "cyan",
    "dim",
    "green",
    "red",
    "yellow",
    "warn",
    "success",
]


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------

class IsolarError(Exception):
    """Erro base do isolar."""


class FFmpegNotFoundError(IsolarError):
    """FFmpeg/FFprobe não encontrado no PATH do sistema."""


class FFmpegError(IsolarError):
    """O FFmpeg retornou um erro durante a execução."""

    def __init__(self, message: str, cmd: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.cmd = cmd or []


class MediaNotFoundError(IsolarError):
    """Arquivo de mídia inexistente ou ilegível."""


class InvalidTimeError(IsolarError):
    """Tempo informado em formato inválido ou incoerente."""


# ---------------------------------------------------------------------------
# Cores e feedback no terminal
# ---------------------------------------------------------------------------

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


_COLOR = _supports_color()


def _paint(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR and text else text


def bold(text: str) -> str:
    return _paint("1", text)


def red(text: str) -> str:
    return _paint("31", text)


def green(text: str) -> str:
    return _paint("32", text)


def yellow(text: str) -> str:
    return _paint("33", text)


def cyan(text: str) -> str:
    return _paint("36", text)


def dim(text: str) -> str:
    return _paint("2", text)


def warn(message: str) -> None:
    print(yellow(f"⚠ {message}"))


def success(message: str) -> None:
    print(green(f"✔ {message}"))


# ---------------------------------------------------------------------------
# Verificação de dependências
# ---------------------------------------------------------------------------

_INSTALL_HINT = """
O isolar precisa do FFmpeg (e do ffprobe) instalados e visíveis no PATH.

Como instalar:
  • Windows       : winget install Gyan.FFmpeg   (ou: choco install ffmpeg)
  • macOS         : brew install ffmpeg
  • Debian/Ubuntu : sudo apt install ffmpeg
  • Fedora        : sudo dnf install ffmpeg
  • Arch          : sudo pacman -S ffmpeg
  • Outros        : https://ffmpeg.org/download.html

Depois de instalar, feche e reabra o terminal e tente novamente."""


def _tool(name: str) -> str:
    """Caminho absoluto de um utilitário do FFmpeg ou erro amigável."""
    path = shutil.which(name)
    if not path:
        raise FFmpegNotFoundError(f"O utilitário '{name}' não foi encontrado no sistema.")
    return path


def check_dependencies() -> Dict[str, str]:
    """Garante que ffmpeg e ffprobe estão disponíveis no PATH do sistema.

    Retorna um dicionário com os caminhos ou levanta ``FFmpegNotFoundError``
    com instruções de instalação para cada sistema operacional.
    """
    tools = ("ffmpeg", "ffprobe")
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise FFmpegNotFoundError(
            f"Dependência não encontrada: {', '.join(missing)}.\n{_INSTALL_HINT}"
        )
    return {tool: shutil.which(tool) or "" for tool in tools}


# ---------------------------------------------------------------------------
# Informações da mídia (ffprobe)
# ---------------------------------------------------------------------------

def get_media_info(path: Union[str, "os.PathLike[str]"]) -> Dict[str, Any]:
    """Coleta duração, codecs, tamanho e demais metadados via ffprobe."""
    src = Path(path)
    if not src.is_file():
        raise MediaNotFoundError(f"Arquivo não encontrado: {src}")

    ffprobe = _tool("ffprobe")
    cmd = [
        ffprobe, "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(src),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        raise FFmpegError(f"Falha ao executar o ffprobe: {exc}", cmd=cmd) from exc
    if proc.returncode != 0:
        raise FFmpegError(
            "Não foi possível ler as informações deste arquivo:\n" + (proc.stderr or "").strip(),
            cmd=cmd,
        )

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise FFmpegError(f"Saída inválida do ffprobe: {exc}", cmd=cmd) from exc

    streams = data.get("streams") or []
    fmt = data.get("format") or {}

    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    video = next((s for s in streams if s.get("codec_type") == "video"), None)

    duration: Optional[float] = None
    for value in (
        fmt.get("duration"),
        audio.get("duration") if audio else None,
        video.get("duration") if video else None,
    ):
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        break

    def _int(key: str) -> Optional[int]:
        try:
            return int(fmt.get(key))
        except (TypeError, ValueError):
            return None

    is_cover = False
    if video is not None:
        is_cover = bool((video.get("disposition") or {}).get("attached_pic", 0))

    return {
        "path": src,
        "duration": duration,
        "size": _int("size") or src.stat().st_size,
        "bit_rate": _int("bit_rate"),
        "format_name": fmt.get("format_name", ""),
        "has_audio": audio is not None,
        "audio_codec": (audio or {}).get("codec_name"),
        "audio_sample_rate": (
            int(audio["sample_rate"])
            if audio and str(audio.get("sample_rate", "")).isdigit()
            else None
        ),
        "audio_channels": (audio or {}).get("channels"),
        "has_video": video is not None and not is_cover,
        "video_codec": (video or {}).get("codec_name"),
        "width": (video or {}).get("width"),
        "height": (video or {}).get("height"),
        "nb_streams": len(streams),
        "audio_streams": sum(1 for s in streams if s.get("codec_type") == "audio"),
    }


# ---------------------------------------------------------------------------
# Descoberta de mídia (para o menu interativo)
# ---------------------------------------------------------------------------

_VIDEO_EXTS = frozenset({
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".gif",
    ".mpg", ".mpeg", ".ts", ".m2ts", ".mts", ".3gp", ".3g2", ".ogv",
    ".mxf", ".vob", ".divx", ".asf",
})

_AUDIO_EXTS = frozenset({
    ".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".oga", ".opus",
    ".wma", ".aiff", ".aif", ".ac3", ".dts", ".amr",
})

# Imagens não são "mídia" no isolar cut, mas entram no conversor.
_IMAGE_EXTS = frozenset({
    ".jpg", ".jpeg", ".jfif", ".png", ".webp", ".bmp", ".tif", ".tiff",
    ".avif", ".heic", ".heif",
})


def list_media(directory: Optional[Union[str, Path]] = None, kind: str = "video") -> List[Path]:
    """Arquivos de mídia da pasta informada (padrão: cwd), ordenados por nome.

    ``kind``: ``"video"`` | ``"audio"`` | ``"image"`` | ``"media"`` (vídeo + áudio)
    | ``"all"`` (tudo, usado pelo conversor).
    """
    folder = Path(directory or Path.cwd()).expanduser()
    if kind == "video":
        exts = _VIDEO_EXTS
    elif kind == "audio":
        exts = _AUDIO_EXTS
    elif kind == "image":
        exts = _IMAGE_EXTS
    elif kind == "all":
        exts = _VIDEO_EXTS | _AUDIO_EXTS | _IMAGE_EXTS
    else:
        exts = _VIDEO_EXTS | _AUDIO_EXTS
    try:
        files = sorted(
            (p for p in folder.iterdir()
             if p.is_file()
             and not p.name.startswith(".")
             and p.suffix.lower() in exts),
            key=lambda p: p.name.lower(),
        )
    except OSError:
        return []
    return files


def detect_media_kind(
    src: Union[str, Path],
    info: Optional[Dict[str, Any]] = None,
) -> str:
    """Classifica o arquivo como ``"video"`` | ``"audio"`` | ``"image"``.

    A extensão fala primeiro (imagens carregam um stream "de vídeo" no probe,
    mas não são vídeos) e o ffprobe desempata o resto (vídeos mudos, áudios
    com capa, etc.). Sem identificação, assume vídeo.
    """
    path = Path(src)
    if (path.suffix or "").lower() in _IMAGE_EXTS:
        return "image"
    meta = info if info is not None else get_media_info(path)
    if meta["has_video"]:
        return "video"
    if meta["has_audio"]:
        return "audio"
    return "video"


# ---------------------------------------------------------------------------
# Tempos
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(
    r"^(?:(\d+(?:\.\d+)?)\s*h)?\s*(?:(\d+(?:\.\d+)?)\s*m)?\s*(?:(\d+(?:\.\d+)?)\s*s?)$"
)


def parse_time(value: Union[str, int, float]) -> float:
    """Converte o tempo informado no CLI para segundos.

    Formatos aceitos: ``90`` | ``90.5`` | ``1:30`` | ``00:01:30`` |
    ``00:01:30.500`` | ``1h2m3s`` | ``2m`` | ``45s``
    """
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds < 0:
            raise InvalidTimeError(f"Tempo negativo não é aceito: {value}")
        return seconds

    text = str(value).strip().lower().replace(",", ".")
    if not text:
        raise InvalidTimeError("O tempo informado está vazio.")

    seconds = 0.0
    invalid = InvalidTimeError(
        f"Tempo inválido: '{value}'. Use, por ex.: 90, 1:30, 00:01:30.5 ou 1h2m3s"
    )

    if re.search(r"[a-z]", text):  # formato 1h2m3s / 45s
        match = _WORD_RE.match(text)
        if not match or all(part is None for part in match.groups()):
            raise invalid
        hours, minutes, secs = (
            float(part) if part is not None else 0.0 for part in match.groups()
        )
        seconds = hours * 3600 + minutes * 60 + secs
    else:  # formato 90 / 1:30 / 00:01:30.5
        parts = text.split(":")
        if len(parts) > 3 or any(part == "" for part in parts):
            raise invalid
        for part in parts:
            try:
                seconds = seconds * 60 + float(part)
            except ValueError:
                raise invalid from None

    if seconds < 0:
        raise InvalidTimeError(f"Tempo negativo não é aceito: {value}")
    return seconds


def format_time(seconds: Optional[float]) -> str:
    """Formata segundos como ``HH:MM:SS`` (com ``.mmm`` quando houver sobra)."""
    if seconds is None:
        return "—"
    total = int(seconds)
    ms = int(round((seconds - total) * 1000))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    base = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{base}.{ms:03d}" if ms else base


# ---------------------------------------------------------------------------
# Arquivos de saída
# ---------------------------------------------------------------------------

def resolve_output_path(directory: Union[str, Path], stem: str, ext: str) -> Path:
    """Escolhe um caminho livre na pasta de destino, sem sobrescrever nada."""
    ext = ext.strip(".").lower()
    target_dir = Path(directory).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    candidate = target_dir / f"{stem}.{ext}"
    counter = 1
    while candidate.exists():
        candidate = target_dir / f"{stem} ({counter}).{ext}"
        counter += 1
    return candidate


def human_size(num_bytes: Optional[Union[int, float]]) -> str:
    """Formata bytes em uma string legível (KB, MB, GB...)."""
    if num_bytes is None:
        return "?"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
# Barra de progresso
# ---------------------------------------------------------------------------

class _Progress:
    """Barra/spinner de progresso (tqdm quando disponível; terminal puro senão)."""

    SPINNER = "-\\|/"

    def __init__(self, total: Optional[float], desc: str) -> None:
        self._desc = desc
        self._total = total
        self._frame = 0
        self._last_pct = -1.0
        self._bar: Any = None
        self._use_bar = False
        try:
            from tqdm import tqdm  # type: ignore
            self._bar = tqdm(
                total=round(total, 2) if total else None,
                desc=desc,
                unit="s",
                ncols=95,
                bar_format=(
                    "{desc}: {percentage:3.0f}%|{bar}| "
                    "{n:.1f}s/{total:.1f}s [{elapsed}<{remaining}]"
                ),
            )
        except Exception:
            self._bar = None
        self._use_bar = self._bar is not None

    def update(self, seconds: float) -> None:
        cap = min(seconds, self._total) if self._total else seconds
        if self._bar is not None:
            delta = cap - self._bar.n
            if delta > 0:
                self._bar.update(delta)
            return

        self._frame = (self._frame + 1) % len(self.SPINNER)
        if self._total:
            pct = cap / self._total * 100
            if pct - self._last_pct >= 1.0:
                self._last_pct = pct
                sys.stdout.write(f"\r{self.SPINNER[self._frame]} {self._desc}: {pct:5.1f}%")
        else:
            sys.stdout.write(f"\r{self.SPINNER[self._frame]} {self._desc}...")
        sys.stdout.flush()

    def finish(self) -> None:
        if self._bar is not None:
            self._bar.close()
            self._bar = None
        elif self._total:
            sys.stdout.write(f"\r{self._desc}: 100% \n")

    def close(self) -> None:
        if self._use_bar:
            if self._bar is not None:
                self._bar.close()
                self._bar = None
        else:
            sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# Executor do FFmpeg
# ---------------------------------------------------------------------------

def run_ffmpeg(
    args: List[str],
    total_duration: Optional[float] = None,
    desc: str = "Processando",
) -> None:
    """Executa o FFmpeg com barra de progresso extraída do próprio encoder.

    ``args`` são os argumentos do FFmpeg **sem** o binário
    (ex.: ``['-i', 'in.mp4', '-vn', 'out.mp3']``).
    """
    ffmpeg = _tool("ffmpeg")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-nostats",
        "-progress", "pipe:1",
        "-y",
        *args,
    ]

    stderr_lines: List[str] = []

    def _drain(stream: Any) -> None:
        try:
            for line in stream:
                stderr_lines.append(line)
        except Exception:
            pass

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise FFmpegError(f"Falha ao iniciar o FFmpeg: {exc}", cmd=cmd) from exc

    err_thread = threading.Thread(target=_drain, args=(proc.stderr,), daemon=True)
    err_thread.start()
    progress = _Progress(total_duration, desc)

    try:
        for line in proc.stdout or []:
            line = line.strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")

            seconds: Optional[float] = None
            if key in ("out_time_us", "out_time_ms"):
                # Ambas as chaves reportam microssegundos (chave legada inclusa).
                try:
                    seconds = float(value) / 1_000_000
                except ValueError:
                    seconds = None
            elif key == "out_time" and re.match(r"^\d+:", value):
                try:
                    hours, minutes, secs = value.split(":")
                    seconds = int(hours) * 3600 + int(minutes) * 60 + float(secs)
                except ValueError:
                    seconds = None

            if seconds is not None and seconds >= 0:
                progress.update(seconds)
            if key == "progress" and value == "end":
                progress.finish()

        proc.wait()
    except KeyboardInterrupt:
        proc.kill()
        progress.close()
        raise
    finally:
        progress.close()

    err_thread.join(timeout=2)

    if proc.returncode != 0:
        message = "O FFmpeg retornou um erro."
        details = "".join(stderr_lines).strip()
        if details:
            message += "\n" + "\n".join(details.splitlines()[-15:])
        raise FFmpegError(message, cmd=cmd)
