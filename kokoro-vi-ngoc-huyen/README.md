---
language:
- vi
license: apache-2.0
base_model: hexgrad/Kokoro-82M
tags:
- text-to-speech
- kokoro
- vietnamese
- vig2p
- ngoc-huyen
---

# Kokoro Vietnamese - Ngọc Huyền

Kokoro Vietnamese TTS finetuned for the Ngọc Huyền voice. This repository is inference-only: it includes the converted Kokoro model, voicepack, config, and the patched Vietnamese Kokoro inference frontend.

## Files

| File | Purpose |
| --- | --- |
| `model/kokoro_vi_ngoc_huyen.pth` | Converted Kokoro inference checkpoint |
| `voices/ngoc_huyen.pt` | Ngọc Huyền voicepack |
| `config.json` | Kokoro model config with Vietnamese vocab |
| `kokoro/` | Patched Kokoro inference package |
| `infer.py` | CLI and Python API |
| `app.py` | Gradio demo |

## Install

```bash
git clone https://huggingface.co/dinhthuan/kokoro-vi-ngoc-huyen
cd kokoro-vi-ngoc-huyen
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI

```bash
python infer.py \
  --text "Xin chào, tôi là giọng đọc Ngọc Huyền." \
  --output outputs/demo.wav \
  --device cuda \
  --print-phonemes
```

Use CPU:

```bash
python infer.py \
  --text "Tường nhà khách được sơn lại vào sáng nay." \
  --output outputs/cpu.wav \
  --device cpu
```

## Python API

```python
import soundfile as sf
from infer import KokoroVietnameseTTS

tts = KokoroVietnameseTTS(device="cuda")
sample_rate, audio, phonemes = tts.synthesize(
    "Xin chào, tôi là giọng đọc Ngọc Huyền.",
    speed=1.0,
)

sf.write("outputs/demo.wav", audio, sample_rate)
print(phonemes)
```

## Gradio

```bash
python app.py
```

## Vietnamese G2P

This model uses `vig2p==0.1.0` for Vietnamese grapheme-to-phoneme conversion through the patched `KPipeline(lang_code="v")` frontend. The frontend preserves Vietnamese onset contrasts such as `t/th`, `tr/ch`, `s/x`, and `d/gi`, maps Vietnamese tone markers into Kokoro-compatible symbols, and keeps the same text-to-phoneme path used during training.

## Voice

Ngọc Huyền
