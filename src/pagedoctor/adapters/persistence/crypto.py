from cryptography.fernet import Fernet


class FindingCipher:
    # Encrypts the finding-text columns at rest (§9.2). Lives in the persistence adapter so
    # ciphertext never crosses a port — the domain only ever handles plaintext models.

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("ascii"))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
