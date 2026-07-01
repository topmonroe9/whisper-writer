import subprocess
import os
import signal
import sys
import time
from pynput.keyboard import Controller as PynputController, Key as PynputKey

from utils import ConfigManager

def run_command_or_exit_on_failure(command):
    """
    Run a shell command and exit if it fails.

    Args:
        command (list): The command to run as a list of strings.
    """
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        exit(1)

class InputSimulator:
    """
    A class to simulate keyboard input using various methods.
    """

    def __init__(self):
        """
        Initialize the InputSimulator with the specified configuration.
        """
        self.input_method = ConfigManager.get_config_value('post_processing', 'input_method')
        self.dotool_process = None

        if self.input_method in ('pynput', 'clipboard'):
            self.keyboard = PynputController()
        elif self.input_method == 'dotool':
            self._initialize_dotool()

    def _initialize_dotool(self):
        """
        Initialize the dotool process for input simulation.
        """
        self.dotool_process = subprocess.Popen("dotool", stdin=subprocess.PIPE, text=True)
        assert self.dotool_process.stdin is not None

    def _terminate_dotool(self):
        """
        Terminate the dotool process if it's running.
        """
        if self.dotool_process:
            os.kill(self.dotool_process.pid, signal.SIGINT)
            self.dotool_process = None

    def release_held_modifiers(self):
        """Release any physically held modifier keys to prevent interference with typing."""
        if hasattr(self, 'keyboard') and self.keyboard:
            for mod_key in (PynputKey.ctrl_l, PynputKey.ctrl_r,
                            PynputKey.shift_l, PynputKey.shift_r,
                            PynputKey.alt_l, PynputKey.alt_r,
                            PynputKey.cmd_l, PynputKey.cmd_r):
                try:
                    self.keyboard.release(mod_key)
                except Exception:
                    pass

    def typewrite(self, text):
        """
        Simulate typing the given text. Uses clipboard for long text and keystrokes for short text.

        Args:
            text (str): The text to type.
        """
        # Get the character threshold from config, default to 1000 if not set
        char_threshold = ConfigManager.get_config_value('post_processing', 'clipboard_threshold') or 1000
        
        # Use clipboard for long text
        if len(text) > char_threshold:
            self._paste_with_clipboard_preservation(text)
            return

        # Use regular keystroke simulation for shorter text
        interval = ConfigManager.get_config_value('post_processing', 'writing_key_press_delay')
        if self.input_method == 'clipboard':
            self._typewrite_clipboard(text)
        elif self.input_method == 'pynput':
            self._typewrite_pynput(text, interval)
        elif self.input_method == 'ydotool':
            self._typewrite_ydotool(text, interval)
        elif self.input_method == 'dotool':
            self._typewrite_dotool(text, interval)

    @staticmethod
    def _setup_win32_clipboard():
        """Configure ctypes function signatures for Win32 clipboard API."""
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p

        return user32, kernel32

    @staticmethod
    def get_clipboard():
        """Return the clipboard text content, cross-platform. None on failure."""
        if sys.platform == 'win32':
            return InputSimulator._win32_get_clipboard()
        elif sys.platform == 'darwin':
            return InputSimulator._macos_get_clipboard()
        return None

    @staticmethod
    def set_clipboard(text):
        """Set the clipboard text content, cross-platform."""
        if sys.platform == 'win32':
            InputSimulator._win32_set_clipboard(text)
        elif sys.platform == 'darwin':
            InputSimulator._macos_set_clipboard(text)

    @staticmethod
    def _macos_get_clipboard():
        """Get clipboard text on macOS via pbpaste. Returns None on failure."""
        try:
            result = subprocess.run(['pbpaste'], capture_output=True)
            if result.returncode == 0:
                return result.stdout.decode('utf-8')
        except Exception:
            pass
        return None

    @staticmethod
    def _macos_set_clipboard(text):
        """Set clipboard text on macOS via pbcopy."""
        try:
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        except Exception:
            pass

    def _send_paste_shortcut(self):
        """Send the OS paste shortcut: Cmd+V on macOS, Ctrl+V elsewhere."""
        if sys.platform == 'win32':
            import ctypes

            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002
            user32 = ctypes.windll.user32

            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        else:
            # macOS pastes with Cmd+V; Linux with Ctrl+V.
            modifier = PynputKey.cmd if sys.platform == 'darwin' else PynputKey.ctrl
            keyboard = getattr(self, 'keyboard', None) or PynputController()
            keyboard.press(modifier)
            keyboard.press('v')
            keyboard.release('v')
            keyboard.release(modifier)

    def _paste_via_clipboard(self, text):
        """Insert text by setting the clipboard and sending the paste shortcut,
        restoring the user's previous clipboard contents afterwards.

        Native on Windows (Ctrl+V) and macOS (Cmd+V). On other platforms,
        falls back to character-by-character typing.
        """
        if sys.platform not in ('win32', 'darwin'):
            interval = ConfigManager.get_config_value('post_processing', 'writing_key_press_delay')
            if self.input_method in ('pynput', 'clipboard'):
                self._typewrite_pynput(text, interval)
            elif self.input_method == 'ydotool':
                self._typewrite_ydotool(text, interval)
            elif self.input_method == 'dotool':
                self._typewrite_dotool(text, interval)
            return

        old_clipboard = self.get_clipboard()
        try:
            self.set_clipboard(text)
            time.sleep(0.05)
            self._send_paste_shortcut()
            time.sleep(0.2)
        finally:
            if old_clipboard is not None:
                try:
                    self.set_clipboard(old_clipboard)
                except Exception:
                    pass

    @staticmethod
    def _win32_set_clipboard(text):
        """Set clipboard content using Windows API."""
        import ctypes

        user32, kernel32 = InputSimulator._setup_win32_clipboard()

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        encoded = text.encode('utf-16-le') + b'\x00\x00'
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        ptr = kernel32.GlobalLock(h)
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(h)

        if user32.OpenClipboard(0):
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_UNICODETEXT, h)
            user32.CloseClipboard()
        else:
            kernel32.GlobalFree(h)

    @staticmethod
    def _win32_get_clipboard():
        """Get clipboard text content using Windows API. Returns None on failure."""
        import ctypes

        user32, kernel32 = InputSimulator._setup_win32_clipboard()

        CF_UNICODETEXT = 13
        result = None

        if user32.OpenClipboard(0):
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if handle:
                ptr = kernel32.GlobalLock(handle)
                if ptr:
                    result = ctypes.wstring_at(ptr)
                    kernel32.GlobalUnlock(handle)
            user32.CloseClipboard()
        return result

    def _typewrite_clipboard(self, text):
        """
        Insert text by pasting from the clipboard.
        Uses the OS clipboard directly — no external dependencies,
        works with any keyboard layout, and handles Unicode correctly.
        Native on Windows (Ctrl+V) and macOS (Cmd+V); falls back to pynput elsewhere.
        """
        if sys.platform not in ('win32', 'darwin'):
            print("Warning: 'clipboard' input method is Windows/macOS only. Falling back to pynput.")
            return self._typewrite_pynput(text, 0.005)

        self._paste_via_clipboard(text)

    def _paste_with_clipboard_preservation(self, text):
        """
        Paste text using the clipboard while preserving original clipboard content.
        Used for long text that exceeds the clipboard_threshold.
        Native on Windows/macOS, falls back to regular typing on other platforms.

        Args:
            text (str): The text to paste.
        """
        self._paste_via_clipboard(text)

    def _typewrite_pynput(self, text, interval):
        """
        Simulate typing using pynput.

        Args:
            text (str): The text to type.
            interval (float): The interval between keystrokes in seconds.
        """
        for char in text:
            self.keyboard.press(char)
            self.keyboard.release(char)
            time.sleep(interval)

    def _typewrite_ydotool(self, text, interval):
        """
        Simulate typing using ydotool.

        Args:
            text (str): The text to type.
            interval (float): The interval between keystrokes in seconds.
        """
        cmd = "ydotool"
        run_command_or_exit_on_failure([
            cmd,
            "type",
            "--key-delay",
            str(interval * 1000),
            "--",
            text,
        ])

    def _typewrite_dotool(self, text, interval):
        """
        Simulate typing using dotool.

        Args:
            text (str): The text to type.
            interval (float): The interval between keystrokes in seconds.
        """
        assert self.dotool_process and self.dotool_process.stdin
        self.dotool_process.stdin.write(f"typedelay {interval * 1000}\n")
        self.dotool_process.stdin.write(f"type {text}\n")
        self.dotool_process.stdin.flush()

    def cleanup(self):
        """
        Perform cleanup operations, such as terminating the dotool process.
        """
        if self.input_method == 'dotool':
            self._terminate_dotool()
