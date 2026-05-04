import pytest

from fraud_v2.llm_lab.provider import NoveltyLedger, OfflineStubProvider, provider_from_env


def test_offline_llm_stub_and_ledger(tmp_path) -> None:  # type: ignore[no-untyped-def]
    provider = OfflineStubProvider()
    payload = provider.generate_structured("make a case", {"title": "scenario_spec"})
    ledger = NoveltyLedger(tmp_path / "ledger.jsonl")

    assert not ledger.seen(payload)
    ledger.append(payload, "scenario_spec", "offline-stub", "v1")
    assert ledger.seen(payload)
    assert payload["expected_label"] == "fraud"
    assert payload["signals"]


def test_llm_provider_factory_defaults_to_offline(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    assert isinstance(provider_from_env(), OfflineStubProvider)


def test_llm_provider_factory_requires_key_for_network_provider(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider_from_env("openai")


def test_novelty_ledger_ignores_malformed_lines(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text('{"content_hash":"known"}\nnot-json\n{}\n', encoding="utf-8")

    ledger = NoveltyLedger(ledger_path)

    assert "known" in ledger._hashes()
