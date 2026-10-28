# ASTOS MAP — isolar
> Gerado por `astos` em 2026-10-28 23:38 UTC. 6 arquivos · 4 dependências · 26 chamadas inter-arquivo · langs: python.
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
- `isolar/cli.py` [python] deg=3 :: dep: `isolar/core.py`, `isolar/utils.py` :: entry :: def: _banner():L55, _print_result():L63, _show_info():L71, _ask():L101, _ask_yes_no():L106, _ask_path():L114, _ask_audio_format():L123, _ask_track():L135, _ask_bitrate():L146, _flow_audio():L161, _flow_video():L175, _flow_cut():L181 (+9) :: calls: cyan()>`isolar/utils.py`, bold()>`isolar/utils.py`, dim()>`isolar/utils.py`, green()>`isolar/utils.py`, human_size()>`isolar/utils.py`, get_media_info()>`isolar/utils.py`, format_time()>`isolar/utils.py`, red()>`isolar/utils.py`
- `isolar/core.py` [python] deg=2 :: dep: `isolar/utils.py` :: def: get_info():L64, describe_media():L69, _validate_source():L89, _resolve_target():L98, isolate_audio():L128, isolate_video():L193, cut_media():L217, _reencode_args():L299 :: calls: get_media_info()>`isolar/utils.py`, format_time()>`isolar/utils.py`, human_size()>`isolar/utils.py`, MediaNotFoundError()>`isolar/utils.py`, resolve_output_path()>`isolar/utils.py`, warn()>`isolar/utils.py`, IsolarError()>`isolar/utils.py`, run_ffmpeg()>`isolar/utils.py`
- `isolar/utils.py` [python] deg=2 :: def: IsolarError:L43, FFmpegNotFoundError:L47, FFmpegError:L51, FFmpegError.__init__():L54, MediaNotFoundError:L59, InvalidTimeError:L63, _supports_color():L71, _paint():L82, bold():L86, red():L90, green():L94, yellow():L98 (+19)
- `isolar/__main__.py` [python] deg=1 :: dep: `isolar/cli.py` :: entry
- `deploy.py` [python] deg=0 :: entry :: def: _run():L38, _load_env_file():L54, _mask():L69, read_version():L73, clean_artifacts():L85, build():L93, twine_check():L103, upload():L113, push_github():L140, main():L173
- `isolar/__init__.py` [python] deg=0

## RISKS (onde o bug provavelmente mora — comece por aqui)
entrypoints: `isolar/cli.py`, `isolar/__main__.py`, `deploy.py`
órfãos (deg=0, possível morto): `isolar/__init__.py`
