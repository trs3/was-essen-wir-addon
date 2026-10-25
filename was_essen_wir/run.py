"""Read Supervisor options, prepare its persistent directory and drop root."""
import json
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit


def read_options(path: Path) -> dict[str, str]:
    options = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(options, dict):
        raise ValueError('Die App-Optionen müssen ein Objekt sein.')
    origin = options.get('public_origin', '')
    secure = options.get('cookie_secure', False)
    if not isinstance(origin, str) or type(secure) is not bool:
        raise ValueError('public_origin muss Text und cookie_secure ein Wahrheitswert sein.')
    origin = origin.strip()
    if origin:
        url = urlsplit(origin)
        # Accessing port also validates malformed/non-numeric port values.
        url.port
        if (url.scheme not in ('http', 'https') or not url.hostname
                or url.username is not None or url.password is not None
                or url.path or url.query or url.fragment
                or any(c.isspace() or ord(c) < 32 for c in origin)):
            raise ValueError('public_origin muss eine HTTP(S)-Adresse ohne Pfad sein, z. B. https://essen.example.net')
        if secure and url.scheme != 'https':
            raise ValueError('cookie_secure benötigt eine HTTPS-Adresse.')
    return {'PUBLIC_ORIGIN': origin, 'COOKIE_SECURE': str(secure).lower()}


def prepare_data(directory: Path) -> None:
    directory.mkdir(exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Das Datenverzeichnis muss ein echtes Verzeichnis sein.')
    # Do not recursively chown Supervisor-owned options or unrelated files.
    for path in (directory, *(directory / name for name in (
            'essen.sqlite3', 'essen.sqlite3-wal', 'essen.sqlite3-shm'))):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if path != directory and not stat.S_ISREG(info.st_mode):
            raise ValueError(f'Keine reguläre Datenbankdatei: {path.name}')
        if os.geteuid() == 0:
            os.chown(path, 10001, 10001, follow_symlinks=False)
        os.chmod(path, 0o700 if path == directory else 0o600)


def main() -> None:
    os.umask(0o077)
    directory = Path('/data')
    os.environ.update(read_options(directory / 'options.json'))
    os.environ['DATABASE_PATH'] = str(directory / 'essen.sqlite3')
    prepare_data(directory)
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    os.execvp('uvicorn', ['uvicorn', 'backend.main:app', '--host', '0.0.0.0',
                         '--port', '8000', '--workers', '1', '--no-proxy-headers'])


if __name__ == '__main__':
    main()
