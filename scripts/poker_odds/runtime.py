"""Locate and launch the installed Anki runtime without installing packages."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def default_profile() -> Path:
    """Use a conventional profile path; the CLI refuses to create a missing profile."""
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/Anki2/User 1'
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')) / 'Anki2/User 1'
    return Path.home() / '.local/share/Anki2/User 1'


def open_package(package: Path, profile: Path) -> None:
    launcher = shutil.which('anki')
    if not launcher:
        raise RuntimeError(f'Package created at {package}, but Anki launcher is not on PATH')
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    if env.get('WAYLAND_DISPLAY'):
        # Native Wayland avoids relying on X11 credentials from a different session.
        env.setdefault('ANKI_WAYLAND', '1')
    log_path = package.with_suffix('.import.log')
    with log_path.open('w') as log:
        process = subprocess.Popen(
            [launcher, '-b', str(profile.parent), '-p', profile.name, str(package)],
            env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        code = process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # Starting the primary GUI is intentionally long-lived; verification is separate.
        return
    if code:
        raise RuntimeError(f'Anki exited with code {code}; package is ready, details: {log_path}')


def ensure_anki_python(entrypoint: Path) -> None:
    if importlib.util.find_spec('anki'):
        return
    roots = [Path('/usr/local/share/anki'), Path('/opt/anki')]
    launcher = shutil.which('anki')
    if launcher:
        roots.insert(0, Path(launcher).resolve().parent)
    candidates = []
    if os.environ.get('ANKI_PYTHON') and os.environ.get('ANKI_PACKAGES'):
        candidates.append((Path(os.environ['ANKI_PYTHON']), Path(os.environ['ANKI_PACKAGES'])))
    for root in roots:
        candidates.extend((p, root / 'app_packages') for p in sorted((root / 'python/bin').glob('python3*'))
                          if re.fullmatch(r'python3(?:\.\d+)?', p.name))
    for interpreter, packages in candidates:
        if interpreter.is_file() and (packages / 'anki').is_dir():
            env = os.environ.copy()
            env['PYTHONPATH'] = str(packages)
            os.execve(str(interpreter), [str(interpreter), str(entrypoint.resolve()), *sys.argv[1:]], env)
    raise RuntimeError('Anki Python not found. Set ANKI_PYTHON and ANKI_PACKAGES to the installed bundle.')
