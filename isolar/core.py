"""Operações de isolamento de mídia do isolar (camada FFmpeg)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from . import utils
from .utils import (
    IsolarError,
    InvalidTimeError,
    MediaNotFoundError,
    detect_media_kind,
    format_time,
    get_media_info,
    human_size,
    parse_time,
    resolve_output_path,
    run_ffmpeg,
    warn,
)

__all__ = [
    "AUDIO_FORMATS",
    "VIDEO_FORMATS",
    "IMAGE_FORMATS",
    "isolate_audio",
    "isolate_video",
    "cut_media",
    "convert_media",
    "detect_media_kind",
    "describe_media",
    "get_info",
]


# Formatos de áudio suportados na extração (todos parseados pelo FFmpeg).
AUDIO_FORMATS: Dict[str, Dict[str, Any]] = {
    "mp3":  {"ext": "mp3",  "codec": ["-c:a", "libmp3lame"], "bitrate": True,  "label": "MP3 — máxima compatibilidade"},
    "m4a":  {"ext": "m4a",  "codec": ["-c:a", "aac"],        "bitrate": True,  "label": "M4A (AAC) — Apple/iTunes"},
    "aac":  {"ext": "aac",  "codec": ["-c:a", "aac"],        "bitrate": True,  "label": "AAC cru — stream sem container"},
    "wav":  {"ext": "wav",  "codec": ["-c:a", "pcm_s16le"],  "bitrate": False, "label": "WAV — sem compressão"},
    "flac": {"ext": "flac", "codec": ["-c:a", "flac"],       "bitrate": False, "label": "FLAC — sem perdas"},
    "ogg":  {"ext": "ogg",  "codec": ["-c:a", "libvorbis"],  "bitrate": True,  "label": "OGG (Vorbis) — uso geral"},
    "opus": {"ext": "opus", "codec": ["-c:a", "libopus"],    "bitrate": True,  "label": "Opus — moderno e leve"},
    "wma":  {"ext": "wma",  "codec": ["-c:a", "wmav2"],      "bitrate": True,  "label": "WMA — Windows Media"},
    "aiff": {"ext": "aiff", "codec": ["-c:a", "pcm_s16be"],  "bitrate": False, "label": "AIFF — sem compressão (Apple)"},
    "copy": {"ext": "",     "codec": ["-c:a", "copy"],       "bitrate": False, "label": "copy — cópia direta, zero recodificação"},
}

# Container ideal para a cópia direta, a partir do codec de origem.
_COPY_CONTAINERS: Dict[str, str] = {
    "aac": "m4a",
    "mp3": "mp3",
    "opus": "opus",
    "vorbis": "ogg",
    "flac": "flac",
    "alac": "m4a",
    "ac3": "ac3",
    "eac3": "eac3",
    "dts": "dts",
    "pcm_s16le": "wav",
    "pcm_s16be": "aiff",
    "pcm_f32le": "wav",
    "wmav2": "wma",
}

# ---------------------------------------------------------------------------
# Catálogos do conversor (o arsenal completo do FFmpeg, curado)
# ---------------------------------------------------------------------------

# Vídeo → vídeo. ``quality`` mapeia a mesma sensação (alta/média/compacta)
# para o parâmetro certo de cada encoder (CRF, qscale ou bitrate).
VIDEO_FORMATS: Dict[str, Dict[str, Any]] = {
    "mp4": {
        "ext": "mp4", "video": ["libx264", "-preset", "veryfast"],
        "qflag": "-crf", "quality": {"alta": "18", "media": "22", "compacta": "28"},
        "pixfmt": "yuv420p", "mux": ["-movflags", "+faststart"],
        "audio": ["aac", "-b:a", "192k"],
        "label": "MP4 (H.264 + AAC) — máxima compatibilidade",
    },
    "mkv": {
        "ext": "mkv", "video": ["libx264", "-preset", "veryfast"],
        "qflag": "-crf", "quality": {"alta": "18", "media": "22", "compacta": "28"},
        "audio": ["aac", "-b:a", "192k"],
        "label": "MKV (Matroska) — formato livre, aceita de tudo",
    },
    "mov": {
        "ext": "mov", "video": ["libx264", "-preset", "veryfast"],
        "qflag": "-crf", "quality": {"alta": "18", "media": "22", "compacta": "28"},
        "pixfmt": "yuv420p", "mux": ["-movflags", "+faststart"],
        "audio": ["aac", "-b:a", "192k"],
        "label": "MOV (QuickTime) — Apple e editores de vídeo",
    },
    "webm": {
        "ext": "webm", "video": ["libvpx-vp9"],
        "qflag": "-crf", "qextra": ["-b:v", "0"],
        "quality": {"alta": "25", "media": "33", "compacta": "40"},
        "speed": ["-cpu-used", "4", "-row-mt", "1"],
        "audio": ["libopus", "-b:a", "160k"],
        "label": "WebM (VP9 + Opus) — aberto e leve para a web",
    },
    "avi": {
        "ext": "avi", "video": ["mpeg4", "-vtag", "xvid"],
        "qflag": "-q:v", "quality": {"alta": "3", "media": "5", "compacta": "8"},
        "audio": ["libmp3lame", "-b:a", "192k"],
        "label": "AVI (Xvid + MP3) — legado que toca em tudo",
    },
    "wmv": {
        "ext": "wmv", "video": ["wmv2"],
        "qflag": "-b:v", "quality": {"alta": "3000k", "media": "1500k", "compacta": "800k"},
        "audio": ["wmav2", "-b:a", "128k"],
        "label": "WMV — Windows Media Player",
    },
    "mpg": {
        "ext": "mpg", "video": ["mpeg2video"], "pixfmt": "yuv420p",
        "qflag": "-b:v", "quality": {"alta": "6000k", "media": "4000k", "compacta": "2000k"},
        "audio": ["mp2", "-b:a", "192k"],
        "label": "MPG (MPEG-2) — DVDs e TV antiga",
    },
    "flv": {
        "ext": "flv", "video": ["libx264", "-preset", "veryfast"],
        "qflag": "-crf", "quality": {"alta": "19", "media": "23", "compacta": "28"},
        "pixfmt": "yuv420p", "mux": ["-movflags", "+faststart"],
        "audio": ["aac", "-b:a", "128k"],
        "label": "FLV — streaming legado (Flash)",
    },
    "gif": {
        "ext": "gif",
        "label": "GIF animado — paleta otimizada (12 fps, até 480 px)",
    },
    "copy": {
        "ext": "mkv",
        "label": "troca de container sem recodificar (MKV aceita quase tudo)",
    },
}

# Imagem → imagem. ``video`` aqui são os codecs de imagem + ajustes fixos.
IMAGE_FORMATS: Dict[str, Dict[str, Any]] = {
    "jpg": {
        "ext": "jpg", "video": ["mjpeg", "-q:v", "3"],
        "label": "JPG/JPEG — fotos comprimidas (boa qualidade)",
    },
    "png": {
        "ext": "png", "video": ["png"],
        "label": "PNG — sem perdas, mantém transparência",
    },
    "webp": {
        "ext": "webp", "video": ["libwebp", "-quality", "85"],
        "label": "WebP — web moderno, arquivo pequeno",
    },
    "bmp": {
        "ext": "bmp", "video": ["bmp"],
        "label": "BMP — bitmap cru (Windows)",
    },
    "tiff": {
        "ext": "tiff", "video": ["tiff"],
        "label": "TIFF — profissional sem perdas",
    },
    "gif": {
        "ext": "gif", "video": ["gif"],
        "label": "GIF — imagem estática (1 frame)",
    },
}

# Mesma sensação de qualidade, nomes alternativos aceitos.
_QUALITY_ALIASES: Dict[str, str] = {
    "alta": "alta", "high": "alta",
    "media": "media", "média": "media",
    "medio": "media", "médio": "media", "medium": "media",
    "compacta": "compacta", "compacto": "compacta", "baixa": "compacta", "low": "compacta",
}


def _normalize_quality(quality: str) -> str:
    """Normaliza o pedido de qualidade (alta/média/compacta) para a chave interna."""
    return _QUALITY_ALIASES.get(str(quality or "media").lower().strip(), "media")


def _convert_target_error(fmt: str, kind: str) -> IsolarError:
    """Erro amigável quando o formato pedido não combina com o tipo de arquivo."""
    if kind == "video" and fmt in AUDIO_FORMATS:
        return IsolarError(
            f"'{fmt}' é um formato de áudio — para extrair o áudio de um vídeo, "
            f"use 'isolar audio <arquivo> -f {fmt}'."
        )
    if kind == "audio" and (fmt in VIDEO_FORMATS or fmt in IMAGE_FORMATS):
        return IsolarError(
            f"Áudios não viram {'vídeos' if fmt in VIDEO_FORMATS else 'imagens'}. "
            "Opções para áudio: " + ", ".join(AUDIO_FORMATS) + "."
        )
    if kind == "image":
        return IsolarError(
            f"Formato de imagem desconhecido: '{fmt}'. Opções: "
            + ", ".join(IMAGE_FORMATS) + "."
        )
    return IsolarError(
        f"Formato desconhecido: '{fmt}'. Opções para vídeo: "
        + ", ".join(VIDEO_FORMATS) + "."
    )


def get_info(input_path: Union[str, Path]) -> Dict[str, Any]:
    """Atalho exposto da leitura de metadados (usado pela CLI/menu)."""
    return get_media_info(_validate_source(input_path))


def describe_media(info: Dict[str, Any]) -> str:
    """Resumo de uma mídia em uma linha (menu interativo e `isolar info`)."""
    bits: List[str] = []
    if info["has_video"]:
        bits.append(f"vídeo {info['video_codec']}")
        if info["width"] and info["height"]:
            bits.append(f"{info['width']}x{info['height']}")
    if info["has_audio"]:
        bits.append(f"áudio {info['audio_codec']}")
        if info["audio_streams"] > 1:
            bits.append(f"{info['audio_streams']} faixas")
    bits.append(f"duração {format_time(info['duration'])}")
    bits.append(human_size(info["size"]))
    return " · ".join(bits)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

def _validate_source(input_path: Union[str, Path]) -> Path:
    """Aceita o caminho com/sem aspas e garante que o arquivo existe."""
    raw = str(input_path or "").strip().strip('"').strip("'")
    src = Path(raw).expanduser()
    if not src.is_file():
        raise MediaNotFoundError(f"Arquivo não encontrado: {raw or '(nada informado)'}")
    return src


def _resolve_target(
    output: Optional[Union[str, Path]],
    stem: str,
    ext: str,
) -> Path:
    """Resolve o arquivo de saída; por padrão salva no cwd atual do terminal."""
    if not output:
        return resolve_output_path(Path.cwd(), stem, ext)

    raw = str(output).strip().strip('"').strip("'")
    given = Path(raw).expanduser()
    is_dir = (
        raw.endswith(("/", "\\")) or
        (given.exists() and given.is_dir()) or
        (not given.suffix and not given.exists())
    )
    if is_dir:
        return resolve_output_path(given, stem, ext)

    if given.exists():
        warn(f"'{given.name}' já existe — salvando com sufixo para não sobrescrever.")
        return resolve_output_path(given.parent, given.stem, ext)
    given.parent.mkdir(parents=True, exist_ok=True)
    return given


# ---------------------------------------------------------------------------
# 1) Isolar áudio
# ---------------------------------------------------------------------------

def isolate_audio(
    input_path: Union[str, Path],
    fmt: str = "mp3",
    bitrate: str = "192k",
    track: int = 0,
    output: Optional[Union[str, Path]] = None,
) -> Path:
    """Extrai a faixa de áudio de um arquivo de vídeo/áudio.

    ``fmt`` aceita mp3, m4a, aac, wav, flac, ogg, opus, wma, aiff ou ``copy``
    (embala a faixa original sem recodificar nada).
    """
    src = _validate_source(input_path)
    fmt = (fmt or "mp3").lower().strip()
    if fmt not in AUDIO_FORMATS:
        raise IsolarError(
            f"Formato desconhecido: '{fmt}'. Opções: {', '.join(AUDIO_FORMATS)}"
        )

    info = get_media_info(src)
    if not info["has_audio"]:
        raise IsolarError(f"'{src.name}' não possui faixa de áudio.")
    if track >= info["audio_streams"]:
        raise IsolarError(
            f"O arquivo tem {info['audio_streams']} faixa(s) de áudio "
            f"(índices 0 a {info['audio_streams'] - 1}); você pediu a nº {track}."
        )

    stream_map = ["-map", f"0:a:{track}"]

    # ----- modo cópia direta: embala o codec original sem recodificar -----
    if fmt == "copy":
        container = _COPY_CONTAINERS.get(info["audio_codec"] or "")
        if container:
            target = _resolve_target(output, f"{src.stem}_audio", container)
            run_ffmpeg(
                ["-i", str(src), "-vn", *stream_map, "-c:a", "copy", str(target)],
                total_duration=info["duration"],
                desc="Copiando áudio",
            )
            return target
        warn(
            f"Codec '{info['audio_codec']}' não tem container direto para cópia — "
            "recodificando para MP3."
        )
        fmt = "mp3"

    spec = AUDIO_FORMATS[fmt]
    encode = list(spec["codec"])
    if spec["bitrate"]:
        encode += ["-b:a", bitrate or "192k"]

    target = _resolve_target(output, f"{src.stem}_audio", spec["ext"])
    run_ffmpeg(
        ["-i", str(src), "-vn", *stream_map, *encode, str(target)],
        total_duration=info["duration"],
        desc=f"Extraindo {fmt.upper()}",
    )
    return target


# ---------------------------------------------------------------------------
# 2) Isolar vídeo (sem áudio)
# ---------------------------------------------------------------------------

def isolate_video(
    input_path: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
) -> Path:
    """Remove a faixa de áudio, gerando um vídeo mudo com o mesmo container."""
    src = _validate_source(input_path)
    info = get_media_info(src)
    if not info["has_video"]:
        raise IsolarError(f"'{src.name}' não possui faixa de vídeo.")

    ext = (src.suffix or ".mp4").lstrip(".").lower() or "mp4"
    target = _resolve_target(output, f"{src.stem}_mudo", ext)
    run_ffmpeg(
        ["-i", str(src), "-map", "0:v:0", "-an", "-c:v", "copy", str(target)],
        total_duration=info["duration"],
        desc="Removendo áudio",
    )
    return target


# ---------------------------------------------------------------------------
# 3) Cortar / aparar (fast cut)
# ---------------------------------------------------------------------------

def cut_media(
    input_path: Union[str, Path],
    start: Optional[Union[str, float]] = None,
    end: Optional[Union[str, float]] = None,
    duration: Optional[Union[str, float]] = None,
    reencode: bool = False,
    output: Optional[Union[str, Path]] = None,
) -> Path:
    """Recorta um trecho da mídia entre ``start``/``end`` ou ``start``/``duration``.

    Por padrão usa cópia direta de stream (``-c copy``): milissegundos de
    execução, sem recodificação e sem perda de qualidade. Com ``reencode=True``
    recodifica para obter corte exato ao frame (lento).
    """
    if start is None and end is None and duration is None:
        raise IsolarError(
            "Informe ao menos um recorte: -s/--start, -e/--end ou -d/--duration."
        )

    src = _validate_source(input_path)
    info = get_media_info(src)
    if not info["has_video"] and not info["has_audio"]:
        raise IsolarError(f"'{src.name}' não tem faixas de áudio ou vídeo válidas.")

    start_s = parse_time(start) if start is not None else 0.0
    end_s = parse_time(end) if end is not None else None
    dur_s = parse_time(duration) if duration is not None else None

    if end_s is not None and end_s <= start_s:
        raise InvalidTimeError(
            f"--end ({format_time(end_s)}) deve ser maior que --start ({format_time(start_s)})."
        )
    if dur_s is not None and dur_s <= 0:
        raise InvalidTimeError(f"--duration deve ser positiva ({duration}).")
    if end_s is not None and dur_s is not None:
        warn("Os flags --end e --duration foram informados juntos: usando --duration.")

    media_duration = info["duration"]
    if media_duration:
        if start_s >= media_duration:
            raise InvalidTimeError(
                f"--start ({format_time(start_s)}) é maior que a duração da mídia "
                f"({format_time(media_duration)})."
            )
        if end_s is not None and end_s > media_duration:
            warn(
                f"--end ({format_time(end_s)}) maior que a duração "
                f"({format_time(media_duration)}): cortando até o fim."
            )
            end_s = media_duration

    cut_len = dur_s if dur_s is not None else (
        end_s - start_s if end_s is not None else None
    )

    ext = (src.suffix or ".mp4").lstrip(".").lower() or "mp4"
    target = _resolve_target(output, f"{src.stem}_corte", ext)

    if reencode:
        # -ss DEPOIS de -i: decodifica e posiciona com precisão de frame.
        seek = ["-i", str(src), "-ss", f"{start_s:.6f}"]
        encode = _reencode_args(ext, info)
        desc = "Recodificando corte"
    else:
        # -ss ANTES de -i + -c copy: seek no demuxer, corte em milissegundos.
        seek = ["-ss", f"{start_s:.6f}", "-i", str(src)]
        encode = ["-c", "copy", "-avoid_negative_ts", "make_zero"]
        desc = "Corte ultrarrápido"

    args = [*seek]
    if cut_len is not None:
        args += ["-t", f"{cut_len:.6f}"]
    args += [*encode, str(target)]

    total = cut_len if cut_len is not None else (
        (media_duration or 0) - start_s if media_duration and media_duration > start_s
        else None
    )
    run_ffmpeg(args, total_duration=total, desc=desc)
    return target


def _reencode_args(ext: str, info: Dict[str, Any]) -> List[str]:
    """Codecs de recodificação escolhidos a partir do container e das faixas."""
    if not info["has_video"]:
        audio_codecs = {
            "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
            "m4a": ["-c:a", "aac", "-b:a", "192k"],
            "aac": ["-c:a", "aac", "-b:a", "192k"],
            "wav": ["-c:a", "pcm_s16le"],
            "flac": ["-c:a", "flac"],
            "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
            "opus": ["-c:a", "libopus", "-b:a", "160k"],
            "wma": ["-c:a", "wmav2", "-b:a", "192k"],
            "aiff": ["-c:a", "pcm_s16be"],
        }
        return audio_codecs.get(ext, ["-c:a", "aac", "-b:a", "192k"])

    video_codecs = {
        "webm": ["-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0"],
    }
    video = video_codecs.get(ext, ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])

    if info["has_audio"]:
        audio = ["-c:a", "libopus", "-b:a", "160k"] if ext == "webm" \
            else ["-c:a", "aac", "-b:a", "192k"]
    else:
        audio = ["-an"]
    return [*video, *audio]


# ---------------------------------------------------------------------------
# 4) Conversão de formatos (vídeo, áudio e imagem)
# ---------------------------------------------------------------------------

def convert_media(
    input_path: Union[str, Path],
    fmt: Optional[str] = None,
    quality: str = "media",
    bitrate: str = "192k",
    output: Optional[Union[str, Path]] = None,
) -> Path:
    """Converte a mídia entre formatos, detectando o tipo automaticamente.

    ``kind`` (vídeo, áudio ou imagem) sai do ``detect_media_kind`` e o
    ``fmt`` é validado contra o catálogo correspondente (``VIDEO_FORMATS``,
    ``AUDIO_FORMATS`` ou ``IMAGE_FORMATS``). Em vídeos, ``fmt="copy"`` só
    troca o container (remux MKV) sem recodificar nada; ``fmt="gif"``
    gera GIF animado com paleta otimizada.
    """
    src = _validate_source(input_path)
    info = get_media_info(src)
    kind = detect_media_kind(src, info)

    if kind == "image":
        catalog, escopo = IMAGE_FORMATS, "imagem"
    elif kind == "audio":
        catalog, escopo = AUDIO_FORMATS, "áudio"
    else:
        catalog, escopo = VIDEO_FORMATS, "vídeo"

    fmt = str(fmt or "").lower().strip()
    if not fmt:
        raise IsolarError(
            f"Formato de saída não informado. Para {escopo}, opções válidas: "
            + ", ".join(catalog) + "."
        )
    if fmt not in catalog:
        raise _convert_target_error(fmt, kind)

    src_ext = (src.suffix or "").lstrip(".").lower()
    if fmt == src_ext and fmt != "copy":
        warn(f"Origem e destino são ambos {fmt.upper()} — o arquivo será apenas recodificado.")

    # Ao reconverter um arquivo gerado pelo isolar, reaproveita o nome base
    # (senão acumularia "_convertido_convertido...").
    stem = src.stem
    if stem.endswith("_convertido"):
        stem = stem[: -len("_convertido")]
    sufixo = f"{stem}_convertido"
    desc = f"Convertendo para {fmt.upper()}"

    # ----- imagem → imagem -----
    if kind == "image":
        spec = IMAGE_FORMATS[fmt]
        target = _resolve_target(output, sufixo, spec["ext"])
        run_ffmpeg(
            ["-i", str(src), "-c:v", *spec["video"], "-frames:v", "1", str(target)],
            total_duration=None,
            desc=desc,
        )
        return target

    # ----- áudio → áudio (mesma mecânica do isolate_audio, sem -vn) -----
    if kind == "audio":
        if fmt == "copy":
            container = _COPY_CONTAINERS.get(info["audio_codec"] or "")
            if container:
                target = _resolve_target(output, sufixo, container)
                run_ffmpeg(
                    ["-i", str(src), "-vn", "-c:a", "copy", str(target)],
                    total_duration=info["duration"],
                    desc="Remuxando áudio",
                )
                return target
            warn(
                f"Codec '{info['audio_codec']}' não tem container direto para cópia — "
                "recodificando para MP3."
            )
            fmt = "mp3"
        spec = AUDIO_FORMATS[fmt]
        encode = list(spec["codec"])
        if spec["bitrate"]:
            encode += ["-b:a", bitrate or "192k"]
        target = _resolve_target(output, sufixo, spec["ext"])
        run_ffmpeg(
            ["-i", str(src), "-vn", *encode, str(target)],
            total_duration=info["duration"],
            desc=desc,
        )
        return target

    # ----- vídeo → vídeo / REMUX -----
    if fmt == "copy":
        # Cópia direta de TODOS os streams para o Matroska, que aceita
        # praticamente qualquer combinação de codecs (vídeo, áudio e legendas).
        target = _resolve_target(output, sufixo, "mkv")
        run_ffmpeg(
            [
                "-i", str(src),
                "-map", "0:v:0", "-map", "0:a:0?", "-map", "0:s?",
                "-c", "copy", "-avoid_negative_ts", "make_zero",
                str(target),
            ],
            total_duration=info["duration"],
            desc="Remuxando para MKV",
        )
        return target

    spec = VIDEO_FORMATS[fmt]

    # ----- vídeo → gif animado (paleta de dois passes no mesmo comando) -----
    if fmt == "gif":
        width = min(480, info["width"] or 480)
        vf = (
            f"fps=12,scale={width}:-2:flags=lanczos,"
            "split[a][b];[a]palettegen[p];[b][p]paletteuse"
        )
        target = _resolve_target(output, sufixo, "gif")
        run_ffmpeg(
            ["-i", str(src), "-vf", vf, "-an", "-sn", str(target)],
            total_duration=info["duration"],
            desc=desc,
        )
        return target

    # ----- vídeo → vídeo (recodificação) -----
    vcodec = spec["video"]
    vid = ["-c:v", vcodec[0], *vcodec[1:]]
    qmap = spec.get("quality") or {}
    if qmap:
        q = qmap.get(_normalize_quality(quality))
        if q is not None:
            vid += spec.get("qextra", []) + [spec["qflag"], q]
    vid += spec.get("speed", [])
    if spec.get("pixfmt"):
        vid += ["-pix_fmt", spec["pixfmt"]]

    audio = ["-c:a", *spec["audio"]] if info["has_audio"] else ["-an"]
    target = _resolve_target(output, sufixo, spec["ext"])
    run_ffmpeg(
        ["-i", str(src), "-sn", *vid, *audio, *spec.get("mux", []), str(target)],
        total_duration=info["duration"],
        desc=desc,
    )
    return target
