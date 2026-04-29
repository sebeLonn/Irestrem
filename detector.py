import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DetectionResult:
    distance_cm: Optional[float]
    face_bbox: Optional[Tuple[int, int, int, int]]  # x, y, w, h
    status: str  # 'too_close' | 'close' | 'good' | 'far' | 'no_face'


class FaceDistanceDetector:
    KNOWN_FACE_WIDTH_CM = 14.5
    # Default focal length for typical 640x480 webcam (~2.8mm lens)
    DEFAULT_FOCAL_LENGTH = 600.0

    DISTANCE_THRESHOLDS = {
        'too_close': 40,
        'close': 55,
        'good_max': 80,
    }

    STATUS_COLORS = {
        'too_close': (0, 0, 255),
        'close': (0, 140, 255),
        'good': (0, 200, 0),
        'far': (255, 200, 0),
        'no_face': (150, 150, 150),
    }

    def __init__(self):
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.focal_length = self.DEFAULT_FOCAL_LENGTH

    def calibrate(self, known_distance_cm: float, frame: np.ndarray) -> bool:
        """Calibrate focal length using a known distance."""
        faces = self._detect_faces(frame)
        if len(faces) > 0:
            _, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
            self.focal_length = (w * known_distance_cm) / self.KNOWN_FACE_WIDTH_CM
            return True
        return False

    def _detect_faces(self, frame: np.ndarray):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        return faces if len(faces) > 0 else []

    def _get_status(self, distance_cm: float) -> str:
        t = self.DISTANCE_THRESHOLDS
        if distance_cm < t['too_close']:
            return 'too_close'
        if distance_cm < t['close']:
            return 'close'
        if distance_cm < t['good_max']:
            return 'good'
        return 'far'

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, DetectionResult]:
        faces = self._detect_faces(frame)
        annotated = frame.copy()

        if len(faces) == 0:
            return annotated, DetectionResult(None, None, 'no_face')

        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        distance = (self.KNOWN_FACE_WIDTH_CM * self.focal_length) / w
        status = self._get_status(distance)
        color = self.STATUS_COLORS[status]

        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            annotated, f"{distance:.0f} cm",
            (x, max(y - 10, 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2,
        )

        return annotated, DetectionResult(distance, (x, y, w, h), status)

    def draw_result(self, frame: np.ndarray, result: 'DetectionResult') -> np.ndarray:
        """Draw last detection result onto a frame without re-detecting."""
        annotated = frame.copy()
        if result.face_bbox:
            x, y, w, h = result.face_bbox
            color = self.STATUS_COLORS.get(result.status, (150, 150, 150))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            if result.distance_cm:
                cv2.putText(annotated, f"{result.distance_cm:.0f} cm",
                           (x, max(y - 10, 10)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        return annotated
