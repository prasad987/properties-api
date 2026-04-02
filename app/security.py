import bcrypt


def _to_bcrypt_bytes(password: str) -> bytes:
    # bcrypt limits password length to 72 bytes.
    pw = password.encode("utf-8")
    if len(pw) > 72:
        pw = pw[:72]
    return pw


def hash_password(password: str) -> str:
    pw_bytes = _to_bcrypt_bytes(password)
    # rounds=12 is a reasonable default for a dev setup; increase for production.
    hashed: bytes = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = _to_bcrypt_bytes(password)
    return bcrypt.checkpw(pw_bytes, password_hash.encode("utf-8"))

