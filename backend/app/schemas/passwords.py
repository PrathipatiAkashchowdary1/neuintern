MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt ignores (or, in newer versions, rejects) anything past 72 bytes


def validate_new_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long (72 bytes maximum).")
    if value.strip() == "":
        raise ValueError("Password cannot be only spaces.")
    return value
