"""Local maintenance operations; requires access to the database directory."""
import getpass
import secrets
import sqlite3
import sys
from pathlib import Path
from . import db
from .main import password_hash, put


def main():
    if len(sys.argv)==3 and sys.argv[1]=='backup':
        destination=Path(sys.argv[2])
        if destination.exists():raise SystemExit('Zieldatei existiert bereits. Einen neuen Dateinamen wählen.')
        db.init()
        source=db.connect()
        target=sqlite3.connect(destination)
        try:
            source.backup(target)
            target.close()
            destination.chmod(0o600)
        finally:
            source.close()
        print('SQLite-Sicherung erstellt.')
    elif len(sys.argv)==2 and sys.argv[1]=='password':
        password=getpass.getpass('Neue gemeinsame PIN / Passwort: ')
        if len(password)<6 or len(password)>256:raise SystemExit('Bitte 6 bis 256 Zeichen verwenden.')
        if getpass.getpass('Wiederholen: ')!=password:raise SystemExit('Eingaben stimmen nicht überein.')
        db.init()
        with db.transaction(True) as c:
            salt=secrets.token_hex(16)
            put(c,'salt',salt);put(c,'password_hash',password_hash(password,salt))
            c.execute('DELETE FROM sessions');c.execute('DELETE FROM attempts')
        print('Zugang aktualisiert. Alle Geräte bitte erneut anmelden.')
    else:
        raise SystemExit('Aufruf: python -m backend.admin backup /data/backup.sqlite3 | password')

if __name__=='__main__':main()
