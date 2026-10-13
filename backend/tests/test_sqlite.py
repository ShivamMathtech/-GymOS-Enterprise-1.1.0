"""Storage-specific checks against a real disposable SQLite file."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import json
import os
import sqlite3
import subprocess
import sys
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def sqlite_only():
    from app.db import engine

    if engine.dialect.name != "sqlite":
        pytest.skip("SQLite storage-specific check")


def test_fractional_and_large_money_remain_exact(owner, member):
    from app.db import engine

    c = owner["client"]
    for total, payments in [("0.30", ["0.10", "0.20"]), ("9999999999.99", ["9999999999.99"])]:
        r = c.post(
            "/api/v1/invoices",
            json={
                "member_id": member["id"],
                "lines": [{"description": "Exact decimal", "quantity": 1, "unit_price": total}],
            },
        )
        assert r.status_code == 201, r.text
        invoice = r.json()
        for amount in payments:
            p = c.post(
                "/api/v1/payments",
                json={"invoice_id": invoice["id"], "amount": amount, "method": "cash", "idempotency_key": str(uuid4())},
            )
            assert p.status_code == 201, p.text
        result = c.get("/api/v1/invoices/" + invoice["id"]).json()
        assert result["net_paid"] == total and result["balance"] == "0.00"
        with engine.connect() as connection:
            value, kind = connection.execute(
                text("SELECT total, typeof(total) FROM invoices WHERE id=:id"), {"id": invoice["id"]}
            ).one()
            assert kind == "integer" and value == int(Decimal(total) * 100)


def test_timestamps_roundtrip_to_utc(owner, subscription):
    from app import models as m
    from app.db import SessionLocal
    from app.db_types import UTCDateTime
    from app.db import engine

    c = owner["client"]
    response = c.post(
        "/api/v1/payments",
        json={
            "invoice_id": subscription["invoice"]["id"],
            "amount": "1.00",
            "method": "cash",
            "idempotency_key": str(uuid4()),
        },
    )
    assert response.status_code == 201, response.text
    with SessionLocal() as db:
        payment = db.get(m.Payment, response.json()["id"])
        assert payment.created_at.tzinfo is not None
        assert payment.created_at.utcoffset().total_seconds() == 0
    value = datetime.fromisoformat("2026-10-13T14:30:00+05:30")
    column = UTCDateTime()
    saved = column.process_bind_param(value, engine.dialect)
    loaded = column.process_result_value(saved, engine.dialect)
    assert loaded == datetime(2026, 10, 13, 9, tzinfo=timezone.utc)
    report = c.get("/api/v1/reports/dashboard")
    assert report.status_code == 200 and Decimal(report.json()["cash_collected"]) == 1


def test_foreign_keys_and_tenant_composite_keys_are_enforced(owner, member):
    from app import models as m
    from app.db import SessionLocal, engine

    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
    with SessionLocal.begin() as db:
        other = m.Organization(name="Other tenant", slug="other-" + uuid4().hex)
        db.add(other)
        db.flush()
        other_id = other.id
    with SessionLocal() as db:
        target = db.get(m.Member, member["id"])
        target.org_id = other_id
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    assert owner["client"].get("/api/v1/members/" + member["id"]).status_code == 200


def test_partial_attendance_index_allows_new_completed_visits(owner, member, subscription):
    c = owner["client"]
    payment = c.post(
        "/api/v1/payments",
        json={
            "invoice_id": subscription["invoice"]["id"],
            "amount": "1062.00",
            "method": "cash",
            "idempotency_key": str(uuid4()),
        },
    )
    assert payment.status_code == 201, payment.text
    payload = {"member_id": member["id"], "branch_id": owner["branch"]["id"]}
    visits = []
    for _ in range(2):
        visit = c.post("/api/v1/attendance/check-in", json=payload)
        assert visit.status_code == 201, visit.text
        visits.append(visit.json()["id"])
        assert c.post("/api/v1/attendance/" + visits[-1] + "/check-out").status_code == 200
    assert len(set(visits)) == 2


def test_live_backup_restore_and_new_process_read(owner, subscription, tmp_path):
    from app.config import settings

    c = owner["client"]
    paid = c.post(
        "/api/v1/payments",
        json={
            "invoice_id": subscription["invoice"]["id"],
            "amount": "1062.00",
            "method": "cash",
            "idempotency_key": str(uuid4()),
        },
    )
    assert paid.status_code == 201, paid.text
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    env = dict(os.environ, DATABASE_URL=settings().database_url)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/backup.py"), str(backup)],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/restore.py"), str(backup), "--sqlite-file", str(restored)],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    with sqlite3.connect(restored) as connection:
        amount = connection.execute("SELECT amount FROM payments WHERE id=?", (paid.json()["id"],)).fetchone()[0]
        assert amount == 106200
    env["DATABASE_URL"] = "sqlite:///" + str(restored)
    env["PYTHONPATH"] = str(ROOT / "backend")
    code = "from app.db import SessionLocal; from app.models import Payment; import sys; db=SessionLocal(); row=db.get(Payment,sys.argv[1]); assert str(row.amount)=='1062.00'; assert row.created_at.tzinfo is not None; db.close()"
    subprocess.run(
        [sys.executable, "-c", code, paid.json()["id"]],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    # A restore refuses to overwrite an existing destination.
    refused = subprocess.run(
        [sys.executable, str(ROOT / "scripts/restore.py"), str(backup), "--sqlite-file", str(restored)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
    )
    assert refused.returncode != 0
