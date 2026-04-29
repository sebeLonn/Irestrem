import subprocess
import platform


def send_notification(title: str, message: str, sound: bool = True) -> None:
    system = platform.system()

    if system == 'Darwin':
        sound_clause = 'with sound name "Ping"' if sound else ''
        script = f'display notification "{message}" with title "{title}" {sound_clause}'
        try:
            subprocess.run(['osascript', '-e', script], check=True,
                           capture_output=True, timeout=5)
        except Exception:
            pass

    elif system == 'Linux':
        try:
            subprocess.run(['notify-send', '--urgency=normal', title, message],
                           check=True, timeout=5)
        except Exception:
            pass

    elif system == 'Windows':
        try:
            from plyer import notification
            notification.notify(title=title, message=message, timeout=10)
        except Exception:
            pass


def send_break_reminder(distance_status: str, minutes_worked: float) -> None:
    mins = int(minutes_worked)
    messages = {
        'too_close': (
            "Eye Guardian — Move Back!",
            f"You've been very close to the screen for {mins} min. "
            "Move back and rest your eyes for 20 seconds."
        ),
        'close': (
            "Eye Guardian — Eye Break",
            f"You've been close to the screen for {mins} min. "
            "Look 6 meters away for 20 seconds."
        ),
        'good': (
            "Eye Guardian — 20-20-20 Break",
            f"Great posture! You've worked {mins} min. "
            "Now look at something 6m away for 20 seconds."
        ),
        'far': (
            "Eye Guardian — Eye Break",
            f"You've been working for {mins} min. "
            "Look 6 meters away for 20 seconds to reduce eye strain."
        ),
        'no_face': (
            "Eye Guardian — Eye Break",
            f"You've been at your computer for {mins} min. "
            "Time for a 20-second eye break!"
        ),
    }
    title, message = messages.get(distance_status, messages['good'])
    send_notification(title, message)
