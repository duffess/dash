"""Encrypted SQLite/PostgreSQL backups. No real operation without explicit CLI.

Restore always writes a NEW file, never over an existing database.
PostgreSQL uses the production Compose service's local admin identity.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import uuid
from cryptography.fernet import Fernet

MAX_BYTES = 128 * 1024 * 1024


def private_file(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def encrypt_backup(raw, key):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Empty or oversized backup")
    fernet = Fernet(key)
    cipher = fernet.encrypt(raw)
    if fernet.decrypt(cipher) != raw:
        raise RuntimeError("Backup verification failed")
    return cipher


def restore_file(backup, destination, key):
    backup, destination = Path(backup), Path(destination)
    if backup.stat().st_size > MAX_BYTES * 2 or destination.exists():
        raise ValueError("Oversized backup or destination already exists")
    raw = Fernet(key).decrypt(backup.read_bytes())
    if len(raw) > MAX_BYTES:
        raise ValueError("Oversized restored database")
    private_file(destination, raw)


def snapshot_sqlite(source, destination):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError("SQLite source missing")
    # Read-only URI avoids accidentally creating an empty source database.
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db, sqlite3.connect(destination) as backup:
        db.backup(backup)
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite backup integrity failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sqlite", type=Path)
    parser.add_argument("--postgres-compose", type=Path)
    parser.add_argument("--compose-env", type=Path)
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--restore-to", type=Path)
    args = parser.parse_args()
    key = args.key_file.read_bytes().strip()
    Fernet(key)
    if args.restore:
        if not args.restore_to:
            raise ValueError("New restore destination required")
        restore_file(args.restore, args.restore_to, key)
        print("Backup decifrado para arquivo novo. Verifique integridade e restaure em banco isolado antes de produção.")
        return
    if not args.output_dir or bool(args.sqlite) == bool(args.postgres_compose):
        raise ValueError("Select exactly one database source and output directory")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, mode=0o700, exist_ok=True)
    if args.key_file.resolve().parent == output or output in args.key_file.resolve().parents:
        raise ValueError("Backup key must not be stored beside encrypted backups")
    with tempfile.TemporaryDirectory(prefix=".dash-backup-", dir=output) as scratch:
        plain = Path(scratch) / "snapshot"
        if args.sqlite:
            snapshot_sqlite(args.sqlite, plain)
        else:
            command = ["docker", "compose"]
            if args.compose_env:
                command += ["--env-file", str(args.compose_env)]
            command += ["-f", str(args.postgres_compose), "exec", "-T", "db", "pg_dump", "--username=postgres",
                        "--dbname=dashflow", "--format=custom"]
            def dump_limit():
                import resource
                resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
            if os.name != "posix":
                raise ValueError("Run PostgreSQL backup on the Linux deployment host")
            with plain.open("xb") as stream:
                subprocess.run(command, stdout=stream, stderr=subprocess.DEVNULL, check=True,
                               timeout=180, preexec_fn=dump_limit)
        os.chmod(plain, 0o600)
        if plain.stat().st_size > MAX_BYTES:
            raise ValueError("Backup exceeds configured 128MiB limit")
        cipher = encrypt_backup(plain.read_bytes(), key)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        private_file(output / ("dash-" + stamp + "-" + uuid.uuid4().hex + ".fernet"), cipher)
    print("Backup cifrado criado e leitura verificada. Faça cópia externa e ensaio de restauração.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Backup/restauração interrompido. Verifique chave, permissões, espaço e origem. Nenhum segredo foi exibido.") from None
