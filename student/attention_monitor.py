"""
AttentionMonitor — Gaze & Attention Detection Module
=====================================================
Detects whether a person is looking at the screen during a video call.
Designed as a standalone, embeddable module for video conferencing tools.

Integration example
-------------------
    from attention_monitor import AttentionMonitor

    monitor = AttentionMonitor()

    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        result = monitor.process_frame(frame)
        annotated = monitor.draw_overlay(frame, result)
        # result.is_attending   → bool
        # result.gaze_status    → 'present' | 'looking_away' | 'absent'
        # result.attention_score → 0.0–1.0 rolling average

Standalone demo
---------------
    python3 attention_monitor.py
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Tuple

import cv2
import numpy as np


# ── Result dataclass ────────────────────────────────────────────────────────

@dataclass
class AttentionResult:
    """Attention analysis result for a single video frame."""

    is_attending: bool
    """Smoothed flag — True until away_threshold seconds of continuous absence."""

    gaze_status: str
    """
    'present'      → face visible, eyes detected, facing screen
    'looking_away' → face visible but turned / eyes not visible
    'absent'       → no face detected at all
    """

    confidence: float
    """Detection confidence in [0.0, 1.0]."""

    face_bbox: Optional[Tuple[int, int, int, int]]
    """(x, y, w, h) of the detected face in the input frame, or None."""

    attention_score: float
    """Rolling mean of 'present' frames over the last history_window seconds."""

    away_duration_s: float
    """Seconds of continuous inattention in the current absence streak."""

    total_absent_s: float
    """Cumulative seconds not attending since the session started / last reset."""

    eyes_detected: int
    """Number of eyes detected inside the face bounding box (0, 1, or 2)."""


# ── Core module ─────────────────────────────────────────────────────────────

class AttentionMonitor:
    """
    Per-student gaze and attention monitor.

    Embeddable in any application that can supply BGR video frames.
    Requires only OpenCV and NumPy — no extra models or network access.

    Parameters
    ----------
    history_window : float
        Seconds of history used for the rolling ``attention_score`` (default 60 s).
    away_threshold : float
        Seconds of continuous inattention before ``is_attending`` flips False.
        Suppresses single-frame blips (default 2 s).
    fps_hint : float
        Expected frame rate; pre-sizes the internal history deque.

    Teacher-side integration pattern
    ---------------------------------
    One ``AttentionMonitor`` instance per student.  Feed each student's decoded
    video frame into ``process_frame()``.  The returned ``AttentionResult`` is
    safe to read from any thread after the call returns.
    """

    STATUS_LABELS: dict[str, str] = {
        'present':      'Looking at screen',
        'looking_away': 'Not looking at screen',
        'absent':       'Not at desk',
    }

    # BGR colour per status (for draw_overlay)
    STATUS_BGR: dict[str, tuple] = {
        'present':      (80, 200, 80),
        'looking_away': (0,  140, 255),
        'absent':       (60,  60, 230),
    }

    # Majority-vote buffer size (frames).  At ~15 detections/s this equals ~1.3 s.
    # Status only flips when this many raw samples agree → eliminates per-frame noise.
    SMOOTH_WINDOW = 20

    def __init__(
        self,
        history_window: float = 60.0,
        away_threshold: float = 3.0,
        fps_hint:        float = 30.0,
    ) -> None:
        self.history_window = history_window
        self.away_threshold = away_threshold

        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self._eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self._profile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml'
        )

        maxlen = int(history_window * fps_hint * 2)
        self._history: Deque[Tuple[float, bool]] = deque(maxlen=maxlen)

        # Majority-vote buffer: raw per-frame status strings
        self._status_buffer: deque = deque(maxlen=self.SMOOTH_WINDOW)
        # Last face box seen; kept across frames so the overlay doesn't flicker
        self._last_face_bbox: Optional[Tuple[int, int, int, int]] = None

        self._away_since:    Optional[float] = None
        self._total_absent:  float           = 0.0
        self._session_start: float           = time.monotonic()

    # ── Public API ──────────────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray) -> AttentionResult:
        """
        Analyse one BGR video frame and return an AttentionResult.

        Safe to call from a background thread.  Do not share a single
        AttentionMonitor instance across multiple student streams.

        Parameters
        ----------
        frame : np.ndarray
            BGR image as returned by ``cv2.VideoCapture.read()``.
        """
        now = time.monotonic()
        raw_status, raw_conf, face_bbox, eyes_n = self._detect_gaze(frame)

        # Keep last known face bbox so the overlay box doesn't flicker
        if face_bbox is not None:
            self._last_face_bbox = face_bbox
        displayed_bbox = self._last_face_bbox

        # Majority vote: fill buffer, then pick the most common raw status
        self._status_buffer.append(raw_status)
        counts: dict[str, int] = {}
        for s in self._status_buffer:
            counts[s] = counts.get(s, 0) + 1
        gaze_status = max(counts, key=counts.get)

        # Confidence = raw detection confidence × buffer agreement fraction
        agreement  = counts[gaze_status] / len(self._status_buffer)
        confidence = raw_conf * agreement

        is_present = (gaze_status == 'present')

        # Track away duration and accumulate absent time
        if is_present:
            if self._away_since is not None:
                self._total_absent += now - self._away_since
                self._away_since = None
        else:
            if self._away_since is None:
                self._away_since = now

        away_s = (now - self._away_since) if self._away_since else 0.0

        # Update rolling history; prune entries older than the window
        self._history.append((now, is_present))
        cutoff = now - self.history_window
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        score = (
            sum(p for _, p in self._history) / len(self._history)
            if self._history else 1.0
        )

        is_attending = is_present or (away_s < self.away_threshold)

        return AttentionResult(
            is_attending    = is_attending,
            gaze_status     = gaze_status,
            confidence      = confidence,
            face_bbox       = displayed_bbox,
            attention_score = score,
            away_duration_s = away_s,
            total_absent_s  = self._total_absent,
            eyes_detected   = eyes_n,
        )

    def draw_overlay(self, frame: np.ndarray, result: AttentionResult) -> np.ndarray:
        """
        Return a copy of *frame* annotated with gaze status.

        Host applications (e.g. a teacher dashboard) can call this to annotate
        each student's video tile with their attention status.

        Parameters
        ----------
        frame : np.ndarray
            The original BGR frame to annotate.
        result : AttentionResult
            The result returned by the most recent ``process_frame()`` call.
        """
        out   = frame.copy()
        color = self.STATUS_BGR.get(result.gaze_status, (150, 150, 150))

        if result.face_bbox:
            x, y, w, h = result.face_bbox
            cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)

        lines = [
            self.STATUS_LABELS.get(result.gaze_status, result.gaze_status),
            f'Attention: {int(result.attention_score * 100)}%',
        ]
        if result.away_duration_s >= 2.0:
            lines.append(f'Away: {int(result.away_duration_s)}s')

        for i, text in enumerate(lines):
            y_pos = 22 + i * 22
            cv2.putText(out, text, (8, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(out, text, (8, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color,   1, cv2.LINE_AA)

        return out

    def get_session_stats(self) -> dict:
        """
        Return session-level attention statistics as a plain dict.

        Suitable for JSON serialisation, logging, or display in a teacher dashboard.

        Keys
        ----
        session_duration_s      : total elapsed seconds since start / last reset
        rolling_attention_pct   : attention % over the last ``history_window`` seconds
        total_absent_s          : cumulative seconds of inattention
        overall_attention_pct   : session-wide (total_present / total_elapsed) × 100
        """
        now     = time.monotonic()
        elapsed = max(now - self._session_start, 1e-6)
        rolling = (
            sum(p for _, p in self._history) / len(self._history)
            if self._history else 1.0
        )
        total_abs = self._total_absent + (
            (now - self._away_since) if self._away_since else 0.0
        )
        return {
            'session_duration_s':    round(elapsed, 1),
            'rolling_attention_pct': round(rolling * 100, 1),
            'total_absent_s':        round(total_abs, 1),
            'overall_attention_pct': round(
                max(0.0, (elapsed - total_abs) / elapsed) * 100, 1
            ),
        }

    def reset(self) -> None:
        """Reset all history and counters. Call at the start of a new class session."""
        self._history.clear()
        self._status_buffer.clear()
        self._last_face_bbox = None
        self._away_since     = None
        self._total_absent   = 0.0
        self._session_start  = time.monotonic()

    # ── Internal gaze detection ─────────────────────────────────────────────

    def _detect_gaze(
        self, frame: np.ndarray
    ) -> Tuple[str, float, Optional[Tuple[int, int, int, int]], int]:
        """
        Return (gaze_status, confidence, face_bbox, eyes_detected).

        Detection pipeline
        ------------------
        1. Frontal face cascade — detects forward-facing faces.
        2. Face frontality check — very narrow bbox → head turned sideways.
        3. Eye cascade within face ROI — open eyes confirm screen-facing gaze.
        4. Profile face cascade fallback — confirms lateral head rotation.
        5. No face → absent.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        # 1. Frontal face
        frontal = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if len(frontal) > 0:
            x, y, w, h = max(frontal, key=lambda f: f[2] * f[3])

            # 2. Frontality proxy: w/h < 0.40 means the head is significantly rotated.
            #    Frontal cascade already biases toward forward-facing faces, so this
            #    threshold only catches extreme rotations.
            frontality = w / max(h, 1)
            if frontality < 0.40:
                return 'looking_away', 0.60, (x, y, w, h), 0

            # 3. Eye detection — used for confidence scoring only, NOT as a hard gate.
            #    Haar eye cascade is noisy (lighting, glasses, blinks) so making it a
            #    binary gate causes constant false "looking_away" flips.
            roi = gray[y : y + h, x : x + w]
            eyes = self._eye_cascade.detectMultiScale(
                roi,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(20, 20),
            )
            n_eyes = min(int(len(eyes)), 2)

            confidence = min(0.70 + 0.08 * n_eyes + 0.07 * min(frontality, 1.0), 0.98)
            return 'present', confidence, (x, y, w, h), n_eyes

        # 4. Profile face (person is looking to the side)
        profile = self._profile_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(50, 50),
        )
        if len(profile) > 0:
            x, y, w, h = max(profile, key=lambda f: f[2] * f[3])
            return 'looking_away', 0.65, (x, y, w, h), 0

        # 5. No face at all
        return 'absent', 0.80, None, 0


# ── Standalone demo ─────────────────────────────────────────────────────────

def _run_demo() -> None:
    """Open the default webcam and display live attention annotations."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print('Error: cannot open camera.')
        return

    monitor = AttentionMonitor()
    print('AttentionMonitor — live demo')
    print('Press Q to quit and see session statistics.')

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame   = cv2.flip(frame, 1)
        result  = monitor.process_frame(frame)
        display = monitor.draw_overlay(frame, result)

        cv2.imshow('AttentionMonitor', display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    stats = monitor.get_session_stats()
    print('\n── Session Statistics ─────────────────────────────')
    for key, val in stats.items():
        unit = 's' if key.endswith('_s') else ('%' if key.endswith('_pct') else '')
        print(f'  {key:<32} {val}{unit}')


if __name__ == '__main__':
    _run_demo()
