from backend.features.auth.application.schemas import GoogleIdentity


def test_google_identity_uses_only_the_stable_subject_and_profile_data() -> None:
    identity = GoogleIdentity(subject="  google-subject  ", name="  Mathis  ")

    assert identity.subject == "google-subject"
    assert identity.name == "Mathis"
