from setuptools import setup

APP = ['teacher_app.py']
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'AppIcon.icns',
    'plist': {
        'CFBundleName': 'TeacherDashboard',
        'CFBundleDisplayName': 'Teacher Dashboard',
        'CFBundleIdentifier': 'com.irestrem.teacher',
        'CFBundleVersion': '1.2.0',
        'NSHighResolutionCapable': True,
    },
    'packages': ['attention_server', 'teacher_dashboard'],
    'includes': ['tkinter', 'tkinter.ttk', 'threading', 'json',
                 'urllib.request', 'http.server', 'socket', 'datetime'],
    'excludes': ['cv2', 'numpy', 'matplotlib', 'scipy', 'pandas', 'PIL'],
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
