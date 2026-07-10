from cryptography.fernet import Fernet

from pagedoctor.adapters.persistence.crypto import FindingCipher

KEY = "hqRJtL1uKChplt01KMGr1zMQqQ9R1xiRa8139J3lo6U="


def test_round_trips_umlauts_and_quotes() -> None:
    cipher = FindingCipher(KEY)
    plaintext = "Sie „gieng“ nach Hause – groß und schön."

    assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_ciphertext_does_not_expose_plaintext() -> None:
    cipher = FindingCipher(KEY)
    plaintext = "Der Hund schläft."

    token = cipher.encrypt(plaintext)

    assert plaintext not in token


def test_a_different_key_cannot_decrypt() -> None:
    other = FindingCipher(Fernet.generate_key().decode("ascii"))
    token = FindingCipher(KEY).encrypt("geheim")

    try:
        other.decrypt(token)
    except Exception:
        return
    raise AssertionError("decryption with the wrong key should fail")
