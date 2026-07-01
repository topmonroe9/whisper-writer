# WhisperWriter on macOS

WhisperWriter runs on macOS (Apple Silicon and Intel) as a menu-bar app. This
guide covers running from source, building a `.app` bundle, and — importantly —
granting the system permissions macOS requires.

## 1. Prerequisites

- macOS 12 (Monterey) or newer
- Python 3.12 (e.g. `brew install python@3.12`)

The Windows-only dependencies (`pywin32`, `pycaw`, `comtypes`) are skipped
automatically on macOS via platform markers in `pyproject.toml`.

## 2. Run from source

```bash
git clone <repo-url> whisper-writer
cd whisper-writer

python3.12 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install .

python run.py
```

On Apple Silicon, local transcription (faster-whisper / ctranslate2 / vosk)
runs on the CPU. The CUDA setup logic in `run.py` simply finds no NVIDIA
toolkit and falls back to CPU mode — no action needed. You can also use the
cloud APIs (OpenAI, Groq, Gemini, Anthropic) without any local model.

## 3. Grant permissions (required)

macOS gates global hotkeys, keystroke simulation, and the microphone behind the
privacy system (TCC). WhisperWriter will not work until you allow these.

Open **System Settings → Privacy & Security** and add your app (Terminal/iTerm
when running from source, or `WhisperWriter.app` when running the bundle) under:

- **Input Monitoring** — to detect the global activation hotkey.
- **Accessibility** — to type/paste the transcribed text into other apps.
- **Microphone** — granted via a prompt on first recording; otherwise add it here.

After changing Accessibility or Input Monitoring, fully quit and relaunch the
app (and toggle the checkbox off/on if it was previously granted to a different
build).

## 4. Build the `.app` bundle

From the project root, inside the venv:

```bash
bash build/build_macos.sh          # → dist/WhisperWriter.app
bash build/build_macos.sh --zip    # also produces dist/WhisperWriter-vX.Y.Z-macos-arm64.zip
```

The script:

1. Generates `assets/ww-logo.icns` from `ww-logo.png` (via `sips` + `iconutil`).
2. Runs PyInstaller against `build/whisperwriter_macos.spec`.
3. Ad-hoc code-signs the bundle so it runs on the build machine.

The bundle is a menu-bar app (`LSUIElement`) — no Dock icon. Its `Info.plist`
declares the microphone and Apple Events usage descriptions.

> Distributing to **other** Macs requires a Developer ID identity and
> notarization (replace the `-` in the `codesign` step with your identity and
> run `xcrun notarytool`). An ad-hoc-signed build only runs reliably on the
> machine that produced it.

## 5. Known macOS limitations

- **Hotkey suppression.** On Windows, WhisperWriter suppresses the activation
  keys so they don't leak into the focused app. macOS (via pynput) does not
  support this, so in *hold-to-record* mode the hotkey characters may reach the
  active field. Prefer *press-to-toggle* mode, or use a hotkey combo that isn't
  a normal typing key.
- **Media auto-pause / volume fade.** Per-app volume control (`pycaw`) is
  Windows-only; on macOS these features are no-ops. Recording and transcription
  are unaffected.

## 6. How insertion works on macOS

Transcribed text is inserted via the OS clipboard and **Cmd+V** (your previous
clipboard contents are saved and restored). Short text below
`post_processing.clipboard_threshold` is typed directly with pynput. The tray
**History** submenu inserts past transcriptions the same way.
