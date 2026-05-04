from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.models.train import train_baseline
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator, load_events_jsonl

app = typer.Typer(no_args_is_help=True)


@app.command()
def generate(
    users: int = typer.Option(120, min=10),
    output: Path = Path("data/synthetic/tiny/events.jsonl"),
) -> None:
    dataset = SyntheticFraudGenerator().generate(users=users)
    dataset.write_jsonl(output)
    print({"events": len(dataset.events), "output": str(output)})


@app.command()
def load(
    input_path: Path = typer.Argument(...),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
) -> None:
    events = load_events_jsonl(input_path)
    store = SQLiteStore(db_path)
    inserted = store.add_events(events)
    print({"inserted": inserted, "db": str(db_path)})


@app.command()
def score(
    user_id: str,
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
) -> None:
    store = SQLiteStore(db_path)
    events = store.list_events()
    if not events:
        raise typer.BadParameter("database has no events; run generate and load first")
    request = DecisionRequest(
        target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
        as_of=max(event.occurred_at for event in events),
    )
    decision = DecisionEngine(store).score(request)
    print(decision.model_dump(mode="json"))


@app.command()
def train(
    events_path: Path = Path("data/synthetic/tiny/events.jsonl"),
    output_dir: Path = Path("data/models/baseline"),
) -> None:
    report = train_baseline(events_path, output_dir)
    print(report)
