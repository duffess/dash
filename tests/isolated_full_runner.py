"""Full offline integration suite. Only the reviewed Linux sandbox may run it."""
import base64
import errno
import hashlib
import os
from pathlib import Path
import resource
import socket
import sys
import unittest


def main():
    if sys.platform!='linux' or os.environ.get('DASH_FULL_OFFLINE_SANDBOX')!='1' or os.getuid()==0:
        raise SystemExit('Use the full isolated launcher, never the host environment.')
    if Path.cwd()!=Path('/scratch') or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise SystemExit('Unsafe execution context')
    if any(Path(path).exists() for path in ['/source/.env','/source/dashflow.db','/source/.venv','/mnt','/proc']):
        raise SystemExit('Forbidden host surfaces')
    try:
        socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except OSError as error:
        if error.errno!=errno.EPERM:
            raise
    else:
        raise SystemExit('External network was not denied')
    for path in ['/source/forbidden-write','/deps/forbidden-write','/python/forbidden-write']:
        try:
            Path(path).write_text('dummy')
        except OSError as error:
            if error.errno not in [errno.EROFS,errno.EACCES,errno.EPERM]:
                raise
        else:
            raise SystemExit('Read-only control missing')
    if resource.getrlimit(resource.RLIMIT_NPROC)[1]>64 or resource.getrlimit(resource.RLIMIT_FSIZE)[1]>16*1024*1024:
        raise SystemExit('Resource bounds missing')
    os.environ.update(DATABASE_URL='sqlite://',SECRET_KEY='dummy-offline-jwt-secret-at-least-32-characters',
                      TOKEN_ENCRYPTION_KEY=base64.urlsafe_b64encode(hashlib.sha256(b'dummy-offline-token-key').digest()).decode(),
                      APP_ENV='test',RATE_LIMIT_ENABLED='false',DEMO_AI_ENABLED='false')
    sys.path[:0]=['/deps','/source','/source/tests']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('/source/tests',pattern='test_*.py'))
    if not result.wasSuccessful():
        return 1
    # Also exercise the full migration chain on an empty, throwaway database.
    from alembic import command
    from alembic.config import Config
    import sqlite3
    os.environ['DATABASE_URL']='sqlite:////scratch/migration-check.sqlite'
    config=Config('/source/alembic.ini')
    config.set_main_option('script_location','/source/alembic')
    command.upgrade(config,'head')
    with sqlite3.connect('/scratch/migration-check.sqlite') as database:
        assert database.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert database.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='f132bd742153'
        assert database.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='oauth_attempts'").fetchone()[0]==1
    print('Full migration chain and database integrity: OK (throwaway database only).')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
