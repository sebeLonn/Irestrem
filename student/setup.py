from setuptools import setup

APP = ['student_client.py']
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'AppIcon.icns',
    'plist': {
        'CFBundleName': 'AttentionMonitor',
        'CFBundleDisplayName': 'Attention Monitor',
        'CFBundleIdentifier': 'com.irestrem.student',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSCameraUsageDescription':
            'Attention Monitor uses your camera to detect whether you are looking at the screen.',
    },
    'packages': ['cv2', 'numpy', 'attention_monitor'],
    'includes': ['tkinter', 'queue', 'threading', 'json', 'urllib.request',
                 'dataclasses', 'collections'],
    'excludes': ['matplotlib', 'scipy', 'pandas', 'PIL', 'Pillow'],
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
