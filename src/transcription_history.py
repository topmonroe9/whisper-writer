import json
import os

from paths import get_history_path
from utils import ConfigManager


class TranscriptionHistory:
    """Maintains a persistent, bounded list of recent transcriptions (newest first).

    The history is stored as a JSON list next to the config file so it survives
    application restarts. The maximum number of retained entries is read from the
    'misc/transcription_history_size' configuration value.
    """

    def __init__(self):
        self._entries = []
        self._load()

    @property
    def max_entries(self):
        size = ConfigManager.get_config_value('misc', 'transcription_history_size')
        if size is None:
            return 25
        try:
            return max(0, int(size))
        except (TypeError, ValueError):
            return 25

    def _load(self):
        """Load history from disk, ignoring a missing or corrupt file."""
        path = get_history_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                self._entries = [str(x) for x in data if str(x).strip()]
                del self._entries[self.max_entries:]
        except Exception as e:
            ConfigManager.console_print(f"Error loading transcription history: {str(e)}")
            self._entries = []

    def _save(self):
        """Persist the current history to disk, ignoring write failures."""
        try:
            with open(get_history_path(), 'w', encoding='utf-8') as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            ConfigManager.console_print(f"Error saving transcription history: {str(e)}")

    def add(self, text):
        """Add a transcription to the top of the history.

        Re-adding an existing entry moves it to the top instead of duplicating it.
        """
        if not text:
            return
        text = text.strip()
        if not text or self.max_entries == 0:
            return

        if text in self._entries:
            self._entries.remove(text)
        self._entries.insert(0, text)
        del self._entries[self.max_entries:]
        self._save()

    def get_all(self):
        """Return a copy of the history entries, newest first."""
        return list(self._entries)

    def clear(self):
        """Remove all history entries."""
        self._entries = []
        self._save()
