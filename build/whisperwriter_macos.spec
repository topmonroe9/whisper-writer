# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for WhisperWriter macOS .app bundle (Apple Silicon / Intel).

Builds a menu-bar (LSUIElement) application that includes local transcription
(PyTorch CPU, faster-whisper, ctranslate2, vosk) plus the cloud API clients.

Build with:  bash build/build_macos.sh
(The build script generates assets/ww-logo.icns and runs PyInstaller on this spec.)
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))


def _read_version():
    """Read the project version from pyproject.toml (best effort)."""
    try:
        with open(os.path.join(PROJECT_ROOT, 'pyproject.toml'), 'r') as f:
            for line in f:
                if line.strip().startswith('version'):
                    return line.split('=')[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return '0.0.0'


VERSION = _read_version()

# Use the generated .icns if present; otherwise fall back to PyInstaller's default.
ICON_PATH = os.path.join(PROJECT_ROOT, 'assets', 'ww-logo.icns')
if not os.path.exists(ICON_PATH):
    ICON_PATH = None

# Collect ctranslate2 native libraries
ctranslate2_binaries = collect_dynamic_libs('ctranslate2')

# Collect sounddevice / PortAudio data
sounddevice_data = collect_data_files('sounddevice')
_sounddevice_data = collect_data_files('_sounddevice_data')

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'src', 'entry_point.py')],
    pathex=[os.path.join(PROJECT_ROOT, 'src')],
    binaries=ctranslate2_binaries,
    datas=[
        (os.path.join(PROJECT_ROOT, 'assets', 'ww-logo.png'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'microphone.png'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'pencil.png'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'assets', 'beep.wav'), 'assets'),
        (os.path.join(PROJECT_ROOT, 'src', 'config_schema.yaml'), 'src'),
    ] + sounddevice_data + _sounddevice_data,
    hiddenimports=[
        # pynput macOS backend
        'pynput._util.darwin',
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        # keyring macOS backend
        'keyring.backends.macOS',
        # sounddevice native data
        'sounddevice',
        '_sounddevice_data',
        # audio
        'webrtcvad',
        'soundfile',
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
        # Exclude CUDA-specific torch packages (macOS is CPU/MPS only)
        'torch.cuda',
    ],
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
    upx=False,  # UPX corrupts macOS Mach-O binaries and breaks code signing
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # build for the host architecture (arm64 on Apple Silicon)
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WhisperWriter',
)

app = BUNDLE(
    coll,
    name='WhisperWriter.app',
    icon=ICON_PATH,
    bundle_identifier='com.whisperwriter.app',
    info_plist={
        # Run as a menu-bar agent with no Dock icon.
        'LSUIElement': True,
        'CFBundleName': 'WhisperWriter',
        'CFBundleDisplayName': 'WhisperWriter',
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'NSHighResolutionCapable': True,
        # macOS permission prompts (TCC). Without these the app is denied silently.
        'NSMicrophoneUsageDescription':
            'WhisperWriter needs microphone access to transcribe your speech.',
        'NSAppleEventsUsageDescription':
            'WhisperWriter uses keyboard simulation to insert transcribed text.',
    },
)
