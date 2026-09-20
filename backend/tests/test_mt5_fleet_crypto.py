import pytest
from cryptography.fernet import Fernet

from app.mt5_fleet.crypto import CredentialVault, CredentialVaultError, masked_login


def test_vault_round_trip():
    key = Fernet.generate_key().decode("ascii")
    vault = CredentialVault(key, 7)
    encrypted = vault.encrypt("TradePassword-123")
    assert "TradePassword-123" not in encrypted
    assert vault.decrypt(encrypted) == "TradePassword-123"
    assert vault.key_version == 7


def test_invalid_key_fails_closed():
    with pytest.raises(CredentialVaultError):
        CredentialVault("not-a-valid-key")


def test_masked_login():
    assert masked_login("53054439") == "****4439"
