<div align="center">

# 🎧 ISOLAR

[![PyPI](https://img.shields.io/pypi/v/isolar?color=orange&label=PyPI)](https://pypi.org/project/isolar/)
[![Status](https://img.shields.io/badge/status-est%C3%A1vel-brightgreen)](https://pypi.org/project/isolar/)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-requerido-informational)](https://ffmpeg.org/)

**Isole áudio e vídeo na velocidade da luz — sem recodificar, sem fricção, sem enrolação.**

`isolar` é uma CLI interativa que usa o FFmpeg por baixo dos panos para extrair áudio,
remover faixas de som e cortar mídias em milissegundos.

[Instalação](#-instalação) · [Uso](#-uso) · [Flags](#-flags-disponíveis) · [Como funciona](#-como-funciona-por-dentro) · [FAQ](#-faq)

</div>

---

## ✨ Destaques

- 🎵 **Isolar áudio** — extrai a faixa de áudio de qualquer vídeo (MP3, M4A, AAC, WAV, FLAC, OGG, OPUS, WMA, AIFF...).
- 🎬 **Isolar vídeo** — remove o som do vídeo, gerando um arquivo mudo.
- ✂️ **Fast Cut** — corta/apara mídia com **cópia direta de stream** (`-c copy`): **_ultrarrápido_** e **sem perda de qualidade**.
- 🖥️ **Dois modos de uso** — menu interativo numérico no terminal **ou** flags diretas para automação/scripting.
- 📁 **Zero mochilão** — os arquivos gerados são salvos na pasta de trabalho atual (`cwd`) do terminal, automaticamente.
- 🧠 **Proteção de arquivos** — nunca sobrescreve nada: se o nome existir, salva com sufixo ` (1)`, ` (2)`...
- 📊 **Barra de progresso** limpa no terminal enquanto o FFmpeg trabalha.
- 🩺 **Verificação inteligente** — detecta se o FFmpeg está instalado e ensina como instalar se não estiver.

---

## 🚀 Instalação

### 1. Instale o FFmpeg (dependência do sistema)

O `isolar` é um drinque sobre o FFmpeg — você precisa dele no sistema:

| SO | Comando |
|---|---|
| **Windows** | `winget install Gyan.FFmpeg` *ou* `choco install ffmpeg` |
| **macOS** | `brew install ffmpeg` |
| **Debian / Ubuntu** | `sudo apt install ffmpeg` |
| **Fedora** | `sudo dnf install ffmpeg` |
| **Arch** | `sudo pacman -S ffmpeg` |

Confira com: `ffmpeg -version`

### 2. Instale o isolar via pip

```bash
pip install isolar
```

Pronto! ✅ Agora basta chamar `isolar` no terminal.

> 💡 O `isolar` também detecta FFmpeg que você já tenha, então não faz ruído se tudo estiver no PATH.

---

## 📺 Uso — Menu interativo

Basta rodar:

```bash
isolar
```

```
╔════════════════════════════════════════════════╗
║ 🎧 ISOLAR v0.0.1                               ║
║ isole áudio e vídeo na velocidade da luz ✨    ║
╚════════════════════════════════════════════════╝

O que você quer isolar hoje?
  1) 🎵 Isolar áudio   extrai o áudio de um vídeo
  2) 🎬 Isolar vídeo   gera um vídeo sem som
  3) ✂  Cortar/aparar  corte ultrarrápido (stream copy)
  4) ℹ  Info da mídia  duração, codecs, tamanho...
  0) ✖ Sair

Escolha uma opção [0-4]:
```

Exemplo de sessão:

```
Escolha uma opção [0-4]: 1
📁 Caminho do arquivo [ ]: ~/Videos/seriado.mp4
Formato [1]: 1
✔ Pronto! Arquivo salvo em: /caminho/atual/seriado_audio.mp3
```

## ⌨️ Uso — Linha de comando (flags)

### 🎵 Isolar áudio (`isolar audio`)

```bash
isolar audio video.mp4                  # → video_audio.mp3 (padrão)
isolar audio video.mp4 -f flac          # → sem perdas
isolar audio video.mp4 -f m4a -b 320k   # → M4A 320 kbps
isolar audio video.mp4 -f copy          # → copia o áudio sem recodificar nada
isolar audio video.mp4 -t 1             # → usa a 2ª faixa de áudio
```

### 🎬 Isolar vídeo (`isolar video`)

```bash
isolar video clip.mkv                   # → clip_mudo.mkv, sem faixa de som
```

### ✂️ Cortar / aparar (`isolar cut`)

```bash
isolar cut video.mp4 -s 10 -d 45              # 45s a partir do segundo 10
isolar cut video.mp4 -s 00:01:30 -e 00:03:00  # entre 1:30 e 3:00
isolar cut video.mp4 -s 1m30s -d 2m           # tempos também em formato legível
isolar cut video.mp4 -s 10 -e 20 --reencode   # corte exato ao frame
```

### ℹ️ Info da mídia (`isolar info`)

```bash
isolar info video.mp4
```

```
  Arquivo: video.mp4
  Container: mov,mp4,m4a,3g2,mj2
  Duração: 00:12:34
  Tamanho: 1.2 GB
  Vídeo: h264 · 1920x1080
  Áudio: aac · 44100 Hz · 2 canal(is)
```

---

## 🏳️ Flags disponíveis

| Comando / Flag | O que faz | Exemplo |
|---|---|---|
| `isolar` | Abre o **menu interativo** | `isolar` |
| `isolar audio <arquivo>` | Extrai o áudio | `isolar audio video.mp4` |
| ├── `-f, --format` | Formato de saída: `mp3` `m4a` `aac` `wav` `flac` `ogg` `opus` `wma` `aiff` `copy` | `isolar audio v.mp4 -f flac` |
| ├── `-b, --bitrate` | Bitrate nos formatos com perdas (padrão `192k`) | `isolar audio v.mp4 -b 320k` |
| ├── `-t, --track` | Índice da faixa de áudio (começa em 0) | `isolar audio v.mp4 -t 1` |
| ├── `-o, --output` | Arquivo/pasta de saída (padrão: `cwd`) | `isolar audio v.mp4 -o ~/Musica` |
| `isolar video <arquivo>` | Gera vídeo mudo (sem faixa de áudio) | `isolar video clip.mkv` |
| `isolar cut <arquivo>` | Corte/aparar via **stream copy** | `isolar cut v.mp4 -s 5 -d 10` |
| ├── `-s, --start` | Ponto de início | `-s 90` · `-s 1:30` · `-s 00:01:30.500` · `-s 1m30s` |
| ├── `-e, --end` | Ponto de fim | `-e 00:03:00` |
| ├── `-d, --duration` | Duração do recorte | `-d 45` · `-d 2m` |
| ├── `--reencode` | Corte exato ao frame (recodifica, mais lento) | `isolar cut v.mp4 -s 10 -e 20 --reencode` |
| ├── `-o, --output` | Arquivo/pasta de saída | `isolar cut v.mp4 -s 5 -e 9 -o corte.mp4` |
| `isolar info <arquivo>` | Mostra codecs, duração e tamanho | `isolar info v.mp4` |
| `-V, --version` | Mostra a versão e sai | `isolar --version` |
| `-h, --help` | Mostra a ajuda completa | `isolar --help` |

> 💡 Sem posição obrigatória! `isolar audio` (sem arquivo) pede o caminho interativamente.

---

## 📊 Formatos suportados na extração (`isolar audio`)

Tudo que o FFmpeg sabe embalar:

| Formato | Codec | Perdas? | Controle de bitrate |
|---|---|---|---|
| `mp3` | libmp3lame | ✅ | ✅ |
| `m4a` | AAC | ✅ | ✅ |
| `aac` | AAC (stream cru) | ✅ | ✅ |
| `wav` | PCM s16le | ❌ | — |
| `flac` | FLAC | ❌ | — |
| `ogg` | Vorbis | ✅ | ✅ |
| `opus` | libopus | ✅ | ✅ |
| `wma` | Windows Media | ✅ | ✅ |
| `aiff` | PCM s16be | ❌ | — |
| `copy` | o mesmo do arquivo | ❌ (identidade byte a byte) | não precisa |

> 💡 **modo copy**: faz a cópia sem recodificação, no container adequado ao codec já presente
> (AAC → `.m4a`, MP3 → `.mp3`, Opus → `.opus`, FLAC → `.flac`...). É o modo mais honesto possível.

---

## 🧠 Como funciona (por dentro)

### Corte *fast cut* com stream copy

O `isolar cut` monta no FFmpeg:

```
ffmpeg -ss INÍCIO -i entrada -t DURAÇÃO -c copy saída
```

O `-ss` **antes** do `-i` busca no próprio demuxer (sem decodificar) e o `-c copy`
replica os pacotes comprimidos **sem recodificar nenhum frame**. Resultado: corte em
milissegundos, mesmo em arquivos de GBs, com a qualidade intacta.

O `isolar` ainda lê o progresso em tempo real com `-progress pipe:1` e ffprobe
(de duração) para desenhar a barra de progresso com o `tqdm`.

### Arquivos de saída

Todos os produto do `isolar` são salvos na **pasta de trabalho atual**:

| Operação | Nome automático |
|---|---|
| Extração de áudio | `<nome>_audio.<formato>` |
| Vídeo sem som | `<nome>_mudo.<container>` |
| Corte/aparado | `<nome>_corte.<container>` |

Se o arquivo de destino já existir, o `isolar` **não sobrescreve**: salva como
`<nome> (1).<ext>`, ` (2)`, ...

---

## ❓ FAQ

**— O corte não começou exatamente no segundo que eu pedi. Por quê?**
No modo *fast cut*, vídeos comprimidos (H.264 etc.) só podem ser cortados em
**keyframes**. O FFmpeg recua até o keyframe anterior ao ponto pedido (é o mesmo
comportamento de ferramentas pagas). Precisa de precisão de frame? Use o
`--reencode`.

**— Posso escolher onde os arquivos vão?**
Sim: `-o` aceita **pasta** (`isolar cut v.mp4 ... -o ~/Musicas/`) ou **caminho
completo** (`-o ~/Musicas/abertura.mp3`). Sem `-o`, tudo cai no `cwd`.

**— O FFmpeg não está no PATH.**
O `isolar` detecta e te ensina: instale conforme [Instalação](#-instalação) e reabra o terminal.

**— Conserva metadados?**
No `audio -f copy` sim, pois é cópia integral da faixa. Nas recodificações, o
FFmpeg mapeia os metadados padrões do container.

---

## 📦 Nota para o PyPI (long_description)

Este `README.md` **é também a descrição longa do pacote** no PyPI (long_description)
— declarado em `pyproject.toml` via:

```toml
readme = "README.md"   # → long_description
```

O badge de versão aponta direto para a página do projeto na PyPI.

---

## 🤝 Contribuindo

Achei um bug? Abra uma [issue](https://github.com/HonoravelMacho/isolar/issues).
PRs são bem-vindos! Estrutura do projeto:

```
isolar/
├── isolar/
│   ├── __init__.py     # versão e metadados
│   ├── __main__.py     # python -m isolar
│   ├── cli.py          # argparse + menu interativo
│   ├── core.py         # operações de mídia (FFmpeg)
│   └── utils.py        # ffprobe, progresso, cores, tempos
├── deploy.py           # pipeline de build + twine + push
├── pyproject.toml      # empacotamento moderno (setuptools)
├── LICENSE             # MIT
└── README.md           # você está aqui ✨
```

## 📜 Licença

Distribuído sob a [Licença MIT](LICENSE) — use, estude, modifique e compartilhe livremente.

---

<div align="center">

**isolar** © 2026 · [HonoravelMacho](https://github.com/HonoravelMacho) · feito com 🎧 e FFmpeg

</div>
