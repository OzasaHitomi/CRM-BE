import pytest

from pydantic import ValidationError

from crm_be.core.config.base import CoreSettings


def test_seed_profile_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_PROFILE", raising=False)

    with pytest.raises(ValidationError):
        CoreSettings(
            cookie_secure=False,
            secret_key="test-secret",
            _env_file=None,
        )  # type: ignore[call-arg]


def test_cookie_secure_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COOKIE_SECURE", raising=False)

    with pytest.raises(ValidationError):
        CoreSettings(
            seed_profile="none",
            secret_key="test-secret",
            _env_file=None,
        )  # type: ignore[call-arg]


def test_rejects_unknown_seed_profile() -> None:
    with pytest.raises(ValidationError):
        CoreSettings(
            seed_profile="staging",  # type: ignore[arg-type]
            cookie_secure=True,
            secret_key="test-secret",
            _env_file=None,
        )


@pytest.mark.parametrize("cookie_secure", [False, True])
def test_accepts_explicit_cookie_secure(cookie_secure: bool) -> None:
    settings = CoreSettings(
        seed_profile="none",
        cookie_secure=cookie_secure,
        secret_key="test-secret",
        _env_file=None,
    )

    assert settings.cookie_secure is cookie_secure
