"""Teacher credential and in-memory session helpers."""

import argparse
import getpass
import hashlib
import hmac
import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path


SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
PASSWORD_ITERATIONS = 310_000
CREDENTIALS_FILE = Path(
    os.environ.get("TEACHER_CREDENTIALS_FILE", Path(__file__).with_name("teachers.json"))
)

_sessions = {}
_sessions_lock = threading.Lock()


def _read_teachers():
    with CREDENTIALS_FILE.open(encoding="utf-8") as credentials_file:
        payload = json.load(credentials_file)
    if not isinstance(payload, dict) or not isinstance(payload.get("teachers"), list):
        raise ValueError("Credential file must contain a teachers list")
    teachers = payload["teachers"]
    if any(not isinstance(teacher, dict) for teacher in teachers):
        raise ValueError("Each teacher credential must be an object")
    return teachers


def hash_password(password):
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return {
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
        "iterations": PASSWORD_ITERATIONS,
    }


def authenticate_teacher(username, password):
    teachers = _read_teachers()
    matching_teacher = next(
        (teacher for teacher in teachers if teacher.get("username") == username),
        None,
    )

    if matching_teacher is None:
        hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), b"\0" * 16, PASSWORD_ITERATIONS
        )
        return False

    try:
        salt = bytes.fromhex(matching_teacher["salt"])
        expected_hash = bytes.fromhex(matching_teacher["password_hash"])
        iterations = int(matching_teacher["iterations"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid teacher credential entry") from error

    if not 100_000 <= iterations <= 1_000_000:
        raise ValueError("Invalid password hash iteration count")

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def add_teacher(username, password):
    username = username.strip()
    if not username or not password:
        raise ValueError("Username and password must not be empty")

    try:
        teachers = _read_teachers()
    except FileNotFoundError:
        teachers = []

    if any(teacher.get("username", "").casefold() == username.casefold()
           for teacher in teachers):
        raise ValueError("That teacher username already exists")

    teachers.append({"username": username, **hash_password(password)})
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=CREDENTIALS_FILE.parent, prefix=".teachers-", suffix=".json"
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as credentials_file:
            json.dump({"teachers": teachers}, credentials_file, indent=2)
            credentials_file.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, CREDENTIALS_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def create_session(username):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = time.monotonic() + SESSION_TTL_SECONDS
    with _sessions_lock:
        now = time.monotonic()
        expired_sessions = [
            session_hash
            for session_hash, (_, expiry) in _sessions.items()
            if expiry <= now
        ]
        for session_hash in expired_sessions:
            del _sessions[session_hash]
        _sessions[token_hash] = (username, expires_at)
    return token


def get_session_username(token):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _sessions_lock:
        session = _sessions.get(token_hash)
        if session is None:
            return None
        username, expires_at = session
        if expires_at <= time.monotonic():
            del _sessions[token_hash]
            return None
        return username


def revoke_session(token):
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _sessions_lock:
        _sessions.pop(token_hash, None)


def main():
    parser = argparse.ArgumentParser(description="Add a teacher login")
    parser.add_argument("username")
    args = parser.parse_args()

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")

    try:
        add_teacher(args.username, password)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Added teacher {args.username.strip()}")


if __name__ == "__main__":
    main()