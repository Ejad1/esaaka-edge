#!/usr/bin/env bash
# Isolated environment for the MMS speech benchmark (the global torchaudio on this machine is broken, so we do not touch it).
set -e
V=/d/Esaaka/hack_nation/data/venv_speech
python -m venv "$V"
"$V/Scripts/python.exe" -m pip install -q --upgrade pip
"$V/Scripts/python.exe" -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu
"$V/Scripts/python.exe" -m pip install -q "transformers>=5.0" jiwer soundfile pyarrow scipy safetensors requests huggingface_hub numpy pandas psutil
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "$V/Scripts/python.exe" experiments/speech/mms_benchmark.py 300m
