import pytest

from backend.features.auth.application.schemas import GoogleIdentity


class TestGoogleIdentitySchema:
    def test_parses_sub_alias_and_normalizes_fields(self) -> None:
        identity = GoogleIdentity(
            sub="  google-sub-1  ",
            email="  MaTHis@Example.com  ",
            name="  Mathis  ",
            email_verified=True,
        )

        assert identity.subject == "google-sub-1"
        assert identity.email == "mathis@example.com"
        assert identity.name == "Mathis"
        assert identity.email_verified is True

    def test_normalizes_blank_name_to_none(self) -> None:
        identity = GoogleIdentity(
            subject="google-sub-1",
            email="mathis@example.com",
            name="   ",
        )

        assert identity.name is None

    def test_raises_for_blank_subject(self) -> None:
        with pytest.raises(ValueError, match="subject must not be empty"):
            GoogleIdentity(subject="   ", email="mathis@example.com")

    def test_raises_for_blank_email(self) -> None:
        with pytest.raises(ValueError, match="email must not be empty"):
            GoogleIdentity(subject="google-sub-1", email="   ")
