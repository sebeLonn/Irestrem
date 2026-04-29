import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class BreakRecord:
    timestamp: float
    duration_seconds: int


class SessionTracker:
    # Break intervals (minutes) per proximity status — closer = more frequent
    BREAK_INTERVALS = {
        'too_close': 8,
        'close': 12,
        'good': 20,
        'far': 25,
        'no_face': 20,
    }
    BREAK_DURATION_SECONDS = 20

    def __init__(self):
        self.session_start = time.time()
        self.breaks: List[BreakRecord] = []
        self.current_status = 'no_face'
        # Rolling 5-minute history sampled ~1/sec
        self._history: deque = deque(maxlen=300)
        self._lock = threading.Lock()

        self.last_break_time = time.time()
        self.in_break = False
        self._break_start: Optional[float] = None

    def update_status(self, status: str) -> None:
        with self._lock:
            self.current_status = status
            self._history.append((time.time(), status))

    # --- Break interval ---

    def get_dominant_status(self) -> str:
        with self._lock:
            if not self._history:
                return 'good'
            counts: dict = {}
            for _, s in self._history:
                counts[s] = counts.get(s, 0) + 1
        return max(counts, key=counts.get)

    def get_break_interval_minutes(self) -> int:
        return self.BREAK_INTERVALS.get(self.get_dominant_status(), 20)

    # --- Countdown ---

    def get_time_until_break(self) -> float:
        interval_s = self.get_break_interval_minutes() * 60
        elapsed = time.time() - self.last_break_time
        return max(0.0, interval_s - elapsed)

    def get_break_progress(self) -> float:
        interval_s = self.get_break_interval_minutes() * 60
        elapsed = time.time() - self.last_break_time
        return min(1.0, elapsed / interval_s)

    def check_break_needed(self) -> bool:
        return self.get_time_until_break() <= 0 and not self.in_break

    # --- Break control ---

    def start_break(self) -> None:
        with self._lock:
            self.in_break = True
            self._break_start = time.time()

    def complete_break(self) -> None:
        with self._lock:
            if self._break_start:
                duration = int(time.time() - self._break_start)
                self.breaks.append(BreakRecord(time.time(), duration))
            self.in_break = False
            self._break_start = None
            self.last_break_time = time.time()

    def skip_break(self) -> None:
        with self._lock:
            self.in_break = False
            self._break_start = None
            self.last_break_time = time.time()

    def get_break_timer(self) -> Optional[float]:
        """Seconds remaining in the current break, or None if not in break."""
        if not self.in_break or self._break_start is None:
            return None
        elapsed = time.time() - self._break_start
        return max(0.0, self.BREAK_DURATION_SECONDS - elapsed)

    # --- Session stats ---

    def get_session_duration(self) -> float:
        return time.time() - self.session_start

    @property
    def breaks_taken(self) -> int:
        return len(self.breaks)
