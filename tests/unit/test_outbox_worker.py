import pytest

from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator
from fraud_v2.workers.outbox import DryRunEventPublisher, OutboxWorker


class FailingPublisher:
    def publish(self, topic, event) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError(f"publish failed for {topic}:{event.idempotency_key}")


def test_sqlite_store_enqueues_one_outbox_message_per_new_event(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = SyntheticFraudGenerator().generate(users=10).events[0]

    store.add_event(event)
    store.add_event(event)

    assert store.outbox_counts() == {"PENDING": 1}


def test_outbox_worker_publishes_pending_messages(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = SyntheticFraudGenerator().generate(users=10).events[0]
    store.add_event(event)
    publisher = DryRunEventPublisher()

    report = OutboxWorker(store, publisher).run_once()

    assert report.scanned == 1
    assert report.published == 1
    assert store.outbox_counts() == {"PUBLISHED": 1}
    assert publisher.published == [("fraud.events", event.idempotency_key)]


def test_outbox_worker_dead_letters_after_max_attempts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = SyntheticFraudGenerator().generate(users=10).events[0]
    store.add_event(event)
    worker = OutboxWorker(store, FailingPublisher(), max_attempts=2)

    first = worker.run_once()
    second = worker.run_once()

    assert first.failed == 1
    assert second.dead_lettered == 1
    assert store.outbox_counts() == {"DEAD_LETTER": 1}


def test_outbox_worker_does_not_hide_non_runtime_errors(tmp_path) -> None:  # type: ignore[no-untyped-def]
    class BrokenPublisher:
        def publish(self, topic, event) -> None:  # type: ignore[no-untyped-def]
            raise ValueError("programming error")

    store = SQLiteStore(tmp_path / "fraud.sqlite")
    event = SyntheticFraudGenerator().generate(users=10).events[0]
    store.add_event(event)

    with pytest.raises(ValueError, match="programming error"):
        OutboxWorker(store, BrokenPublisher()).run_once()
