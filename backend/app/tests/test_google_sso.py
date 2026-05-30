import pytest
from fastapi import HTTPException

from app.domains.platform import google_sso


def test_local_demo_google_sso_remains_available(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "local")
    monkeypatch.setattr(google_sso.settings, "google_token_verifier_mode", "demo")

    verifier = google_sso.get_google_token_verifier()

    assert isinstance(verifier, google_sso.DemoGoogleTokenVerifier)


def test_production_rejects_demo_google_sso(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "production")
    monkeypatch.setattr(google_sso.settings, "google_token_verifier_mode", "demo")

    with pytest.raises(HTTPException) as exc:
        google_sso.get_google_token_verifier()

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "google_sso_demo_forbidden"


def test_production_rejects_missing_google_client_id(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "production")
    monkeypatch.setattr(google_sso.settings, "google_token_verifier_mode", "google")
    monkeypatch.setattr(google_sso.settings, "google_client_id", "")

    with pytest.raises(HTTPException) as exc:
        google_sso.get_google_token_verifier()

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "missing_google_client_id"


def test_unknown_google_verifier_mode_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "local")
    monkeypatch.setattr(google_sso.settings, "google_token_verifier_mode", "typo")

    with pytest.raises(HTTPException) as exc:
        google_sso.get_google_token_verifier()

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "invalid_google_verifier_mode"


def test_production_google_sso_accepts_valid_configuration(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "production")
    monkeypatch.setattr(google_sso.settings, "google_token_verifier_mode", "google")
    monkeypatch.setattr(google_sso.settings, "google_client_id", "google-client-id")
    monkeypatch.setattr(
        google_sso.settings,
        "google_callback_url",
        "https://app.example.com/auth/google/callback",
    )

    verifier = google_sso.get_google_token_verifier()
    callback_state = google_sso.issue_google_callback_state()
    google_sso.verify_google_callback_state(callback_state)

    assert isinstance(verifier, google_sso.GoogleAuthTokenVerifier)


def test_production_google_sso_rejects_invalid_callback_state(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "production")

    with pytest.raises(HTTPException) as exc:
        google_sso.verify_google_callback_state("not-a-valid-state-token")

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "invalid_google_callback_state"


def test_production_google_sso_rejects_missing_callback_state(monkeypatch) -> None:
    monkeypatch.setattr(google_sso.settings, "environment", "production")

    with pytest.raises(HTTPException) as exc:
        google_sso.verify_google_callback_state(None)

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "invalid_google_callback_state"
