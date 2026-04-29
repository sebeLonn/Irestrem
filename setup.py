from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'AppIcon.icns',
    'plist': {
        'CFBundleName': 'Irestrem',
        'CFBundleDisplayName': 'Irestrem',
        'CFBundleIdentifier': 'com.irestrem.app',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSCameraUsageDescription':
            'Irestrem uses the camera to measure your distance from the screen.',
    },
    'packages': ['cv2', 'PIL', 'numpy', 'detector', 'tracker', 'notifier', 'ui'],
    'includes': ['tkinter', 'queue', 'threading', 'platform', 'subprocess',
                 'pathlib', 'collections', 'dataclasses'],
    'excludes': ['matplotlib', 'scipy', 'pandas'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
