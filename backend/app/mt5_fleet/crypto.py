from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class CredentialVaultError(RuntimeError):
    pass


class CredentialVault:
    """Encrypt/decrypt MT5 passwords. The key must live outside PostgreSQL."""

    def __init__(self, key: str, key_version: int = 1):
        if not key or len(key.strip()) < 40:
            raise CredentialVaultError("ABUTRON_MT5_CREDENTIAL_KEY is not configured")
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except Exception as exc:
            raise CredentialVaultError("ABUTRON_MT5_CREDENTIAL_KEY is invalid") from exc
        self.key_version = int(key_version)

    def encrypt(self, password: str) -> str:
        if not password:
            raise CredentialVaultError("MT5 password cannot be empty")
        return self._fernet.encrypt(password.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeError) as exc:
            raise CredentialVaultError("Unable to decrypt MT5 credential") from exc


def masked_login(login: str) -> str:
    value = str(login or "")
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"
