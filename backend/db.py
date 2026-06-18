"""
Camada de banco de dados (memória da carteira).

- Em produção (Render): usa Postgres do Supabase via env DATABASE_URL.
- Local: cai pra SQLite (arquivo storage/carteira.db) automaticamente.

Cada upload mensal vira uma linha em 'snapshots' (chave ano-mês), guardando o
JSON consolidado completo. Assim o histórico persiste e a série consolidada
pode ser montada a partir dos próprios snapshots.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import (create_engine, MetaData, Table, Column, String, Float,
                        DateTime, Text, select, delete)
from sqlalchemy.engine import make_url

BASE = Path(__file__).resolve().parent
STORAGE = BASE / "storage"
STORAGE.mkdir(exist_ok=True)


def _normalize_url(url: str) -> str:
    # Supabase/Heroku dão "postgres://" — SQLAlchemy quer "postgresql+psycopg2://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    ENGINE = create_engine(_normalize_url(DATABASE_URL), pool_pre_ping=True)
else:
    ENGINE = create_engine(f"sqlite:///{STORAGE / 'carteira.db'}")

metadata = MetaData()

snapshots = Table(
    "snapshots", metadata,
    Column("ano_mes", String(7), primary_key=True),      # ex: 2026-05
    Column("data_referencia", String(20)),
    Column("patrimonio_total", Float),
    Column("usd_brl", Float),
    Column("payload", Text),                              # JSON consolidado completo
    Column("criado_em", DateTime(timezone=True)),
)


def init_db():
    metadata.create_all(ENGINE)


def _key_from_ref(ref: str | None) -> str:
    try:
        dt = datetime.strptime(ref, "%d/%m/%Y")
        return f"{dt.year:04d}-{dt.month:02d}"
    except (ValueError, TypeError):
        return datetime.now().strftime("%Y-%m")


def save_snapshot(data: dict) -> str:
    """Insere/atualiza o snapshot do mês. Retorna a chave ano-mês."""
    key = _key_from_ref(data.get("data_referencia"))
    data["_gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    row = {
        "ano_mes": key,
        "data_referencia": data.get("data_referencia"),
        "patrimonio_total": data.get("patrimonio_total"),
        "usd_brl": data.get("usd_brl"),
        "payload": json.dumps(data, ensure_ascii=False),
        "criado_em": datetime.now(timezone.utc),
    }
    with ENGINE.begin() as conn:
        conn.execute(delete(snapshots).where(snapshots.c.ano_mes == key))
        conn.execute(snapshots.insert().values(**row))
    return key


def list_snapshots() -> list[dict]:
    with ENGINE.connect() as conn:
        rows = conn.execute(
            select(snapshots.c.ano_mes, snapshots.c.data_referencia,
                   snapshots.c.patrimonio_total)
            .order_by(snapshots.c.ano_mes)
        ).all()
    return [{"ano_mes": r.ano_mes, "data_referencia": r.data_referencia,
             "patrimonio_total": r.patrimonio_total} for r in rows]


def get_latest() -> dict | None:
    with ENGINE.connect() as conn:
        r = conn.execute(
            select(snapshots.c.payload).order_by(snapshots.c.ano_mes.desc()).limit(1)
        ).first()
    return json.loads(r.payload) if r else None


def get_all_payloads() -> list[dict]:
    with ENGINE.connect() as conn:
        rows = conn.execute(
            select(snapshots.c.payload).order_by(snapshots.c.ano_mes)
        ).all()
    return [json.loads(r.payload) for r in rows]


def count_snapshots() -> int:
    with ENGINE.connect() as conn:
        return len(conn.execute(select(snapshots.c.ano_mes)).all())


def import_json_files():
    """Migra snapshots antigos (arquivos JSON em storage/) para o banco, 1x."""
    files = sorted(STORAGE.glob("snapshot_*.json"))
    migrados = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            save_snapshot(data)
            migrados += 1
        except Exception:
            pass
    return migrados
