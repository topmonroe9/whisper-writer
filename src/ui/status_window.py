import sys
import os
import math
import time
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QRectF, QPointF
from PyQt5.QtGui import (QFont, QPixmap, QIcon, QPainter, QColor, QPen, QBrush,
                         QPainterPath, QLinearGradient)
from PyQt5.QtWidgets import QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow
from utils import ConfigManager

# --- Modern palette -----------------------------------------------------------
ACCENT_1 = QColor(122, 162, 255)   # light blue
ACCENT_2 = QColor(86, 120, 240)    # deep blue
WARN_1 = QColor(255, 110, 110)     # red (no sound)
WARN_2 = QColor(229, 72, 72)
AMBER = QColor(240, 170, 70)       # slow / "taking a while"
TEXT_PRIMARY = '#EAEEF7'
TEXT_SECONDARY = '#8B93A8'


class IconBadge(QWidget):
    """
    A small circular badge that shows an animated microphone (while recording)
    or a rotating spinner (while transcribing / processing). Purely decorative,
    but it makes the panel feel alive and modern.
    """
    SIZE = 48

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._mode = 'mic'          # 'mic' | 'busy' | 'warning'
        self._spin = 0.0
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)       # ~30 fps

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.update()

    def _tick(self):
        self._spin = (self._spin + 5.5) % 360.0
        self._pulse += 0.09
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        full = QRectF(self.rect())
        circle = full.adjusted(3, 3, -3, -3)
        cx, cy = circle.center().x(), circle.center().y()

        warning = self._mode == 'warning'
        c1, c2 = (WARN_1, WARN_2) if warning else (ACCENT_1, ACCENT_2)

        # Soft pulsing glow ring behind the badge (only while recording).
        if self._mode == 'mic':
            glow = 0.5 + 0.5 * math.sin(self._pulse)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(c1.red(), c1.green(), c1.blue(), int(30 + 55 * glow)))
            p.drawEllipse(full)

        grad = QLinearGradient(circle.topLeft(), circle.bottomRight())
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(circle)

        if self._mode == 'busy':
            self._draw_spinner(p, cx, cy)
        else:
            self._draw_mic(p, cx, cy)

    def _draw_mic(self, p, cx, cy):
        white = QColor(255, 255, 255, 240)
        cap_w = self.SIZE * 0.20
        cap_h = self.SIZE * 0.32
        cap = QRectF(cx - cap_w / 2, cy - cap_h / 2 - self.SIZE * 0.06, cap_w, cap_h)
        p.setPen(Qt.NoPen)
        p.setBrush(white)
        p.drawRoundedRect(cap, cap_w / 2, cap_w / 2)

        pen = QPen(white)
        pen.setWidthF(2.0)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        ar = cap_w * 1.05
        arc_rect = QRectF(cx - ar, cap.center().y() - ar * 0.2, ar * 2, ar * 1.6)
        p.drawArc(arc_rect, 200 * 16, 140 * 16)
        stem_top = cap.bottom()
        stem_bottom = cy + self.SIZE * 0.22
        p.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bottom))
        p.drawLine(QPointF(cx - self.SIZE * 0.11, stem_bottom),
                   QPointF(cx + self.SIZE * 0.11, stem_bottom))

    def _draw_spinner(self, p, cx, cy):
        pen = QPen(QColor(255, 255, 255, 70))
        pen.setWidthF(3.2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        rad = self.SIZE * 0.26
        ring = QRectF(cx - rad, cy - rad, rad * 2, rad * 2)
        p.drawEllipse(ring)
        pen.setColor(QColor(255, 255, 255, 240))
        p.setPen(pen)
        start = int(-self._spin * 16)
        p.drawArc(ring, start, 110 * 16)


class AudioLevelWidget(QWidget):
    """Animated equalizer-style meter that reacts to the live microphone level."""
    NUM_BARS = 23

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setMinimumWidth(220)
        self._target = 0.0
        self._level = 0.0
        self._bars = [0.0] * self.NUM_BARS
        self._phase = 0.0
        self._warning = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def start(self):
        self._target = 0.0
        self._level = 0.0
        self._bars = [0.0] * self.NUM_BARS
        if not self._timer.isActive():
            self._timer.start(33)
        self.show()
        self.update()

    def stop(self):
        self._timer.stop()
        self._target = 0.0
        self._level = 0.0
        self._bars = [0.0] * self.NUM_BARS
        self.update()

    def set_level(self, level):
        self._target = max(0.0, min(1.0, level))

    def set_warning(self, on):
        if self._warning != on:
            self._warning = on
            self.update()

    def _animate(self):
        # Snappy attack, gentle release.
        if self._target > self._level:
            self._level += (self._target - self._level) * 0.6
        else:
            self._level += (self._target - self._level) * 0.22

        # Perceptual boost so quiet speech still moves the bars noticeably,
        # while a truly silent mic reads ~0 (silence detection uses raw level).
        vis = min(1.0, (self._level ** 0.7) * 1.5)

        self._phase += 0.45
        n = self.NUM_BARS
        center = (n - 1) / 2.0
        for i in range(n):
            dist = abs(i - center) / center if center else 0.0
            envelope = 1.0 - 0.38 * (dist ** 1.6)
            wobble = (0.55
                      + 0.45 * math.sin(self._phase * (0.8 + 0.10 * i) + i * 0.9)
                      + 0.18 * math.sin(self._phase * 1.7 - i * 0.5))
            wobble = max(0.15, min(1.25, wobble))
            target = vis * envelope * wobble
            target = max(target, vis * 0.12)
            if target > self._bars[i]:
                self._bars[i] += (target - self._bars[i]) * 0.7
            else:
                self._bars[i] += (target - self._bars[i]) * 0.32
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        n = self.NUM_BARS
        gap = 3
        bar_w = max(2.0, (w - gap * (n - 1)) / n)
        c1, c2 = (WARN_1, WARN_2) if self._warning else (ACCENT_1, ACCENT_2)
        mid_y = h / 2.0
        p.setPen(Qt.NoPen)
        for i in range(n):
            val = self._bars[i]
            bar_h = max(2.0, val * (h - 2))
            x = i * (bar_w + gap)
            y = mid_y - bar_h / 2.0
            t = min(1.0, val * 1.3)
            c = QColor(
                int(c2.red() + (c1.red() - c2.red()) * t),
                int(c2.green() + (c1.green() - c2.green()) * t),
                int(c2.blue() + (c1.blue() - c2.blue()) * t),
                int(120 + 135 * t),
            )
            p.setBrush(QBrush(c))
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w / 2, bar_w / 2)


class ProgressBarWidget(QWidget):
    """A slim progress bar with determinate and indeterminate (animated) modes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self.setMinimumWidth(220)
        self._fraction = None       # None => indeterminate
        self._indef = 0.0
        self._slow = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._indef = 0.0
        if not self._timer.isActive():
            self._timer.start(33)
        self.show()
        self.update()

    def stop(self):
        self._timer.stop()
        self._fraction = None
        self._slow = False
        self.update()

    def set_indeterminate(self):
        self._fraction = None
        self.update()

    def set_fraction(self, f):
        self._fraction = max(0.0, min(1.0, f))
        self.update()

    def set_slow(self, slow):
        if self._slow != slow:
            self._slow = slow
            self.update()

    def _tick(self):
        if self._fraction is None:
            self._indef = (self._indef + 0.022) % 1.0
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        r = h / 2.0

        # Track
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 28))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Clip subsequent drawing to the rounded track shape.
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(clip)

        c1, c2 = (AMBER, QColor(214, 138, 40)) if self._slow else (ACCENT_1, ACCENT_2)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, c2)
        grad.setColorAt(1.0, c1)
        p.setBrush(QBrush(grad))

        if self._fraction is None:
            chunk = w * 0.32
            x = self._indef * (w + chunk) - chunk
            p.drawRoundedRect(QRectF(x, 0, chunk, h), r, r)
        else:
            fill_w = max(h, self._fraction * w)
            p.drawRoundedRect(QRectF(0, 0, fill_w, h), r, r)


class StatusWindow(BaseWindow):
    statusSignal = pyqtSignal(str, bool)
    closeSignal = pyqtSignal()

    # Card geometry / shadow insets used by paintEvent.
    SHADOW = 18
    RADIUS = 22

    def __init__(self):
        super().__init__('WhisperWriter Status', 470, 138)
        self.initStatusUI()
        self.statusSignal.connect(self.updateStatus)

        # No-sound (silence) detection state
        self.recording_active = False
        self.silence_detection_enabled = False
        self.silence_timeout = 3.0          # seconds without sound before warning
        self.sound_level_threshold = 0.08   # mic level considered "sound present"
        self.last_sound_time = None
        self.silence_warning_active = False
        self._silence_pulse_alpha = 0
        self._silence_pulse_phase = 0.0
        self.silence_timer = QTimer()
        self.silence_timer.timeout.connect(self._checkSilence)
        self.silence_pulse_timer = QTimer()
        self.silence_pulse_timer.timeout.connect(self._updateSilencePulse)

        # Transcription / LLM "busy" progress state
        self.busy_active = False
        self.busy_label = ''
        self.busy_start_time = None
        self.busy_total_seconds = 0.0
        self.busy_fraction = None           # None => indeterminate
        self.busy_last_progress = None
        self.busy_timer = QTimer()
        self.busy_timer.timeout.connect(self._updateBusyStatus)

    def initStatusUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

        # Drop the old "WhisperWriter / ×" title bar that BaseWindow adds — the
        # status panel is a clean, self-contained pill instead.
        first = self.main_layout.takeAt(0)
        if first is not None and first.widget() is not None:
            first.widget().hide()
            first.widget().deleteLater()

        # Content sits inside the painted card (see paintEvent for geometry).
        self.main_layout.setContentsMargins(
            self.SHADOW + 18, 24, self.SHADOW + 20, self.SHADOW + 16
        )
        self.main_layout.setSpacing(0)

        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self.icon_badge = IconBadge()
        root.addWidget(self.icon_badge, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        self.status_label = QLabel('Recording')
        self.status_label.setFont(QFont('Segoe UI', 12, QFont.DemiBold))
        self.status_label.setStyleSheet(f'color: {TEXT_PRIMARY}; background: transparent;')

        self.level_meter = AudioLevelWidget()
        self.progress_bar = ProgressBarWidget()

        self.shortcuts_label = QLabel()
        self.shortcuts_label.setFont(QFont('Segoe UI', 9))
        self.shortcuts_label.setStyleSheet(f'color: {TEXT_SECONDARY}; background: transparent;')
        self.shortcuts_label.hide()

        col.addWidget(self.status_label)
        col.addWidget(self.level_meter)
        col.addWidget(self.progress_bar)
        col.addWidget(self.shortcuts_label)

        root.addLayout(col, 1)
        self.main_layout.addLayout(root)

        self.level_meter.hide()
        self.progress_bar.hide()

    # ----- Window chrome (modern glass card) ----------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        full = QRectF(self.rect())
        card = full.adjusted(self.SHADOW, 10, -self.SHADOW, -self.SHADOW - 6)

        # Soft drop shadow (layered translucent rounded rects).
        for i in range(10, 0, -1):
            sr = card.adjusted(-i, -i + 3, i, i + 5)
            path = QPainterPath()
            path.addRoundedRect(sr, self.RADIUS + i, self.RADIUS + i)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, max(2, 9 - i)))
            p.drawPath(path)

        # Card background gradient.
        grad = QLinearGradient(card.topLeft(), card.bottomLeft())
        if self.silence_warning_active:
            grad.setColorAt(0.0, QColor(48, 33, 38, 247))
            grad.setColorAt(1.0, QColor(33, 24, 30, 247))
        else:
            grad.setColorAt(0.0, QColor(40, 45, 62, 246))
            grad.setColorAt(1.0, QColor(25, 29, 41, 246))
        card_path = QPainterPath()
        card_path.addRoundedRect(card, self.RADIUS, self.RADIUS)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(card_path)

        # Subtle top highlight border for the "glass" feel.
        pen = QPen(QColor(255, 255, 255, 24))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)

        # Pulsing red ring while no sound is detected.
        if self.silence_warning_active:
            pen = QPen(QColor(255, 80, 80, self._silence_pulse_alpha))
            pen.setWidth(2)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(card.adjusted(1, 1, -1, -1), self.RADIUS, self.RADIUS)

    def show(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.height() - self.height() - 110
        self.move(x, y)
        super().show()

    def closeEvent(self, event):
        self.closeSignal.emit()
        super().closeEvent(event)

    # ----- Helpers ------------------------------------------------------------

    def format_key_combo(self, key_combo: str) -> str:
        """Convert key combination to symbolic representation."""
        if not key_combo:
            return ''
        key_map = {
            'ctrl': 'CTRL', 'shift': 'SHIFT', 'alt': 'ALT',
            'space': 'SPACE', 'win': 'WIN', '+': '',
        }
        parts = key_combo.lower().split('+')
        return ''.join(key_map.get(part, part.upper()) for part in parts)

    def _set_status(self, text, color=TEXT_PRIMARY):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f'color: {color}; background: transparent;')

    # ----- Live microphone level + silence detection --------------------------

    @pyqtSlot(float)
    def updateVolume(self, level):
        if not self.recording_active:
            return
        self.level_meter.set_level(level)
        if level >= self.sound_level_threshold:
            self.last_sound_time = time.monotonic()
            if self.silence_warning_active:
                self._exit_silence_warning()

    def _checkSilence(self):
        if not (self.silence_detection_enabled and self.recording_active):
            return
        if self.last_sound_time is None:
            return
        if (time.monotonic() - self.last_sound_time) >= self.silence_timeout \
                and not self.silence_warning_active:
            self._enter_silence_warning()

    def _enter_silence_warning(self):
        self.silence_warning_active = True
        self.level_meter.set_warning(True)
        self.icon_badge.set_mode('warning')
        self._set_status('No sound detected — check your microphone', '#FF8A8A')
        self._silence_pulse_phase = 0.0
        if not self.silence_pulse_timer.isActive():
            self.silence_pulse_timer.start(33)
        self.update()

    def _exit_silence_warning(self):
        self.silence_warning_active = False
        self.level_meter.set_warning(False)
        self.icon_badge.set_mode('mic')
        self.silence_pulse_timer.stop()
        self._silence_pulse_alpha = 0
        self._set_status('Recording')
        self.update()

    def _updateSilencePulse(self):
        self._silence_pulse_phase += 0.18
        self._silence_pulse_alpha = int(70 + 175 * (0.5 + 0.5 * math.sin(self._silence_pulse_phase)))
        self.update()

    def _stop_recording_visuals(self):
        self.recording_active = False
        self.silence_detection_enabled = False
        if hasattr(self, 'silence_timer'):
            self.silence_timer.stop()
        if self.silence_warning_active:
            self._exit_silence_warning()
        if hasattr(self, 'level_meter'):
            self.level_meter.stop()
            self.level_meter.hide()

    # ----- Transcription / LLM progress ("busy") ------------------------------

    @pyqtSlot(float, float)
    def updateTranscriptionProgress(self, processed, total):
        if not self.busy_active:
            return
        self.busy_last_progress = time.monotonic()
        self.busy_total_seconds = total
        if total > 0:
            self.busy_fraction = max(0.0, min(1.0, processed / total))
            self.progress_bar.set_fraction(self.busy_fraction)

    def _start_busy(self, label):
        self.busy_active = True
        self.busy_label = label
        self.busy_start_time = time.monotonic()
        self.busy_last_progress = self.busy_start_time
        self.busy_total_seconds = 0.0
        self.busy_fraction = None
        self.icon_badge.set_mode('busy')
        self.progress_bar.set_indeterminate()
        self.progress_bar.set_slow(False)
        self.progress_bar.start()
        if not self.busy_timer.isActive():
            self.busy_timer.start(150)
        self._updateBusyStatus()

    def _stop_busy(self):
        self.busy_active = False
        self.busy_fraction = None
        self.busy_start_time = None
        if hasattr(self, 'busy_timer'):
            self.busy_timer.stop()
        if hasattr(self, 'progress_bar'):
            self.progress_bar.stop()
            self.progress_bar.hide()

    def _updateBusyStatus(self):
        if not self.busy_active or self.busy_start_time is None:
            return
        now = time.monotonic()
        elapsed = now - self.busy_start_time

        if self.busy_fraction is None:
            slow = elapsed > 10.0
        else:
            slow = (now - self.busy_last_progress) > 6.0 and self.busy_fraction < 0.99
        self.progress_bar.set_slow(slow)

        if slow:
            self._set_status(f'{self.busy_label}: still working… {elapsed:.0f}s (longer than usual)',
                             '#F2B85A')
            return

        dots = '.' * (1 + int(now * 2) % 3)
        if self.busy_fraction is not None:
            pct = int(self.busy_fraction * 100)
            text = f'{self.busy_label} — {pct}%'
            if self.busy_total_seconds > 0:
                done = self.busy_fraction * self.busy_total_seconds
                text += f'   {done:.0f}s / {self.busy_total_seconds:.0f}s'
        else:
            text = f'{self.busy_label}{dots}   {elapsed:.0f}s'
        self._set_status(text)

    # ----- Main status dispatcher ---------------------------------------------

    @pyqtSlot(str, bool)
    def updateStatus(self, status, use_llm=False):
        """Update the status window based on the given status."""
        if status != 'recording':
            self._stop_recording_visuals()
        if status not in ('transcribing', 'processing_llm_cleanup', 'processing_llm_instruction'):
            self._stop_busy()

        if status == 'recording':
            self.icon_badge.set_mode('mic')

            continuous_mode = ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous'
            using_api = ConfigManager.get_config_value('model_options', 'use_api')
            allow_continuous_api = ConfigManager.get_config_value('recording_options', 'allow_continuous_api')

            using_remote_api = using_api
            if use_llm:
                llm_type = ConfigManager.get_config_value('llm_post_processing', 'api_type')
                using_remote_api = using_remote_api or (llm_type != 'ollama')

            # Continuous + remote API but not allowed -> stop immediately.
            if continuous_mode and using_remote_api and not allow_continuous_api:
                self.closeSignal.emit()
                return

            if continuous_mode and using_remote_api:
                # Show the meter, flag the remote-API caveat, but skip the
                # no-sound warning here.
                self._set_status('Continuous recording · remote API', '#F2B85A')
                self.recording_active = True
                self.silence_detection_enabled = False
                self.level_meter.set_warning(False)
                self.level_meter.start()
            else:
                self._set_status('Recording')
                self.recording_active = True
                self.silence_detection_enabled = True
                self.last_sound_time = time.monotonic()
                self.level_meter.set_warning(False)
                self.level_meter.start()
                self.silence_timer.start(120)

            # Friendly shortcut hints.
            activation_key = self.format_key_combo(ConfigManager.get_config_value('recording_options', 'activation_key'))
            cleanup_key = self.format_key_combo(ConfigManager.get_config_value('recording_options', 'llm_cleanup_key'))
            instruction_key = self.format_key_combo(ConfigManager.get_config_value('recording_options', 'llm_instruction_key'))
            self.shortcuts_label.setText(f'⏹ {activation_key}    🧹 {cleanup_key}    💭 {instruction_key}')
            self.shortcuts_label.show()
            self.show()

        elif status == 'transcribing':
            self.shortcuts_label.hide()
            self._start_busy('Transcribing')

        elif status == 'processing_llm_cleanup':
            self.shortcuts_label.hide()
            api_type = ConfigManager.get_config_value('llm_post_processing', 'api_type') or 'LLM'
            self._start_busy(f'Cleaning up with {api_type.upper()}')

        elif status == 'processing_llm_instruction':
            self.shortcuts_label.hide()
            api_type = ConfigManager.get_config_value('llm_post_processing', 'api_type') or 'LLM'
            self._start_busy(f'Processing instruction with {api_type.upper()}')

        if status in ('idle', 'error', 'cancel'):
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    win = StatusWindow()
    win.show()

    # Standalone preview that bypasses ConfigManager: a few seconds of "sound",
    # then silence (red pulse), then a transcription progress run.
    win.recording_active = True
    win.silence_detection_enabled = True
    win.last_sound_time = time.monotonic()
    win.shortcuts_label.setText('⏹ CTRLSHIFTSPACE    🧹 CTRLALTC    💭 CTRLALTI')
    win.shortcuts_label.show()
    win.icon_badge.set_mode('mic')
    win.level_meter.start()
    win.silence_timer.start(120)

    clock = {'t': 0.0}
    state = {'phase': 'rec'}

    def feed():
        clock['t'] += 0.05
        t = clock['t']
        if state['phase'] == 'rec':
            level = 0.0 if t > 4.0 else 0.45 + 0.35 * math.sin(t * 6.0)
            win.updateVolume(level)
            if t > 9.0:
                state['phase'] = 'busy'
                win._stop_recording_visuals()
                win._start_busy('Transcribing')
        elif state['phase'] == 'busy':
            frac = min(1.0, (t - 9.0) / 4.0)
            win.updateTranscriptionProgress(frac * 30.0, 30.0)

    timer = QTimer()
    timer.timeout.connect(feed)
    timer.start(50)

    sys.exit(app.exec_())
