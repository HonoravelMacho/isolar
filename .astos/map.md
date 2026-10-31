# ASTOS MAP — isolar
> Gerado por `astos` em 2026-10-31 16:59 UTC. 6 arquivos · 4 dependências · 30 chamadas inter-arquivo · langs: python.
> Se desatualizado: `astos -f` (atualiza sem abrir o navegador). Detalhe: `.astos/graph.json`. Visual humano: `.astos/index.html`. 3D só regenera com `astos` (sem `-f`).
> Queries baratas (use em vez de grep): `astos q --symbol X` · `astos q --cap camera` · `astos trace --from A --to B` · `astos impact --file F` · `astos caps` · `astos hubs` · `astos risks` · `astos slice <pasta>` · `astos changed` · `astos status` · `astos explain --symbol X` · `astos hotspots` · `astos dead` · `astos tests --file X`.

## HUBS (maior degree centrality)
- `isolar/cli.py` [python] deg=3 — dep: `isolar/core.py`, `isolar/utils.py`
- `isolar/core.py` [python] deg=2 — dep: `isolar/utils.py`
- `isolar/utils.py` [python] deg=2
- `isolar/__main__.py` [python] deg=1 — dep: `isolar/cli.py`
- `deploy.py` [python] deg=0
- `isolar/__init__.py` [python] deg=0

## ARQUIVOS
- `isolar/cli.py` [python] deg=3 :: dep: `isolar/core.py`, `isolar/utils.py` :: ●changed :: entry :: def: _banner():L62, _print_result():L70, _show_info():L78, _ask():L108, _ask_yes_no():L113, _ask_path():L121, _pick_file():L148, _ask_audio_format():L181, _ask_track():L193, _ask_bitrate():L204, _ask_convert_format():L215, _ask_video_quality():L235 (+15) :: calls: cyan()>`isolar/utils.py`, bold()>`isolar/utils.py`, dim()>`isolar/utils.py`, green()>`isolar/utils.py`, human_size()>`isolar/utils.py`, get_media_info()>`isolar/utils.py`, format_time()>`isolar/utils.py`, red()>`isolar/utils.py`
- `isolar/core.py` [python] deg=2 :: dep: `isolar/utils.py` :: ●changed :: def: _normalize_quality():L175, _convert_target_error():L180, get_info():L203, describe_media():L208, _validate_source():L228, _resolve_target():L237, isolate_audio():L267, isolate_video():L332, cut_media():L356, _reencode_args():L438, convert_media():L471 :: calls: IsolarError()>`isolar/utils.py`, get_media_info()>`isolar/utils.py`, format_time()>`isolar/utils.py`, human_size()>`isolar/utils.py`, MediaNotFoundError()>`isolar/utils.py`, resolve_output_path()>`isolar/utils.py`, warn()>`isolar/utils.py`, run_ffmpeg()>`isolar/utils.py`
- `isolar/utils.py` [python] deg=2 :: ●changed :: def: IsolarError:L45, FFmpegNotFoundError:L49, FFmpegError:L53, FFmpegError.__init__():L56, MediaNotFoundError:L61, InvalidTimeError:L65, _supports_color():L73, _paint():L84, bold():L88, red():L92, green():L96, yellow():L100 (+21)
- `isolar/__main__.py` [python] deg=1 :: dep: `isolar/cli.py` :: entry
- `deploy.py` [python] deg=0 :: entry :: def: _run():L38, _load_env_file():L54, _mask():L69, read_version():L73, clean_artifacts():L85, build():L93, twine_check():L103, upload():L113, push_github():L140, main():L173
- `isolar/__init__.py` [python] deg=0 :: ●changed

## RISKS (onde o bug provavelmente mora — comece por aqui)
entrypoints: `isolar/cli.py`, `isolar/__main__.py`, `deploy.py`
órfãos (deg=0, possível morto): `isolar/__init__.py`

## CHANGED (sujos no git — debugue aqui primeiro)
- `isolar/cli.py`
- `isolar/core.py`
- `isolar/utils.py`
- `isolar/__init__.py`
