from __future__ import annotations

from fraud_v2.security.secrets import scan_secrets


def test_secret_scan_detects_real_looking_tokens(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "settings.py"
    fake_secret = "sk-" + "thisisarealisticlookingsecretvaluethatislongenough"
    source.write_text(
        f'OPENAI_API_KEY="{fake_secret}"\n',
        encoding="utf-8",
    )

    report = scan_secrets(tmp_path)

    assert report.passed is False
    assert report.findings[0].code == "OPENAI_API_KEY"
    assert report.findings[0].path == "settings.py"
    assert "..." in report.findings[0].masked_secret


def test_secret_scan_allows_documented_local_placeholders(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "README.md"
    source.write_text(
        "FRAUD_API_TOKEN=dev-token-change-me\n"
        "FRAUD_JWT_SECRET=replace-with-local-only-secret-32b-min\n",
        encoding="utf-8",
    )

    report = scan_secrets(tmp_path)

    assert report.passed is True
    assert report.findings == []
