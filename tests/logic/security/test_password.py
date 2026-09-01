import bcrypt

from crm_be.logic.security.password import hash_password, verify_password


def test_hash_password_returns_str() -> None:
    hashed = hash_password("password123")

    assert isinstance(hashed, str)


def test_hash_password_returns_different_hash_for_same_password() -> None:
    hashed_a = hash_password("password123")
    hashed_b = hash_password("password123")

    assert hashed_a != hashed_b


def test_hash_password_output_is_verifiable_by_bcrypt() -> None:
    hashed = hash_password("password123")

    assert bcrypt.checkpw(b"password123", hashed.encode("utf-8"))


def test_verify_password_returns_true_for_correct_password() -> None:
    hashed = hash_password("password123")

    assert verify_password("password123", hashed) is True


def test_verify_password_returns_false_for_incorrect_password() -> None:
    hashed = hash_password("password123")

    assert verify_password("wrong-password", hashed) is False


def test_verify_password_returns_false_for_different_hash() -> None:
    hashed_a = hash_password("password123")
    hash_password("another-password")

    assert verify_password("another-password", hashed_a) is False
