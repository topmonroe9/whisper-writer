# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for WhisperWriter Full build (~2-3 GB).

Includes everything from the API build PLUS:
  - PyTorch (CPU-only)
  - faster-whisper
  - ctranslate2
  - vosk

CUDA is NOT bundled. Users with NVIDIA GPUs install system CUDA separately.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

# Collect ctranslate2 native libraries
ctranslate2_binaries = collect_dynamic_libs('ctranslate2')

# Collect sounddevice data
sounddevice_data = collect_data_files('sounddevice')
_sounddevice_data = collect_data_files('_sounddevice_data')

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'src', 'entry_point.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'src')],
    binaries=ctranslate2_binaries,
    datas=[
        (os.path.join(PROJECT_ROOT, 'assets', 'ww-logo.png'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'ww-logo.ico'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'microphone.png'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'pencil.png'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'beep.wav'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'src', 'config_schema.yaml'), 'src'),
    ] + sounddevice_data + _sounddevice_data,
    hiddenimports=[
        # pynput backend
        'pynput._util.win32',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        # keyring
        'keyring.backends.Windows',
        # sounddevice native data
        'sounddevice',
        '_sounddevice_data',
        # audio
        'webrtcvad',
        'soundfile',
        # Windows COM
        'comtypes',
        'comtypes.stream',
        'pycaw',
        'pycaw.pycaw',
        # API clients
        'openai',
        'anthropic',
        'groq',
        'google.generativeai',
        'google.api_core',
        'google.auth',
        # YAML
        'yaml',
        # Other
        'srt',
        'audioplayer',
        'keyring',
        'requests',
        'numpy',
        'tqdm',
        # PyQt5
        'PyQt5.sip',
        # Local transcription
        'torch',
        'torchaudio',
        'faster_whisper',
        'ctranslate2',
        'vosk',
        'ollama',
    ] + collect_submodules('faster_whisper') + collect_submodules('ctranslate2'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'notebook',
        'IPython',
        'jupyter',
        'pytest',
        'black',
        'flake8',
        # Exclude CUDA-specific torch packages to keep CPU-only
        'torch.cuda',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WhisperWriter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'assets', 'ww-logo.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WhisperWriter',
)
