"""
App da Carteira (Luca) - FastAPI.

Memória: banco de dados (Supabase/Postgres em produção, SQLite local).
Acesso: protegido por senha única (env APP_PASSWORD).

  GET  /login            -> tela de login
  POST /api/login        -> valida senha -> sessão
  GET  /logout           -> encerra sessão
  GET  /                 -> dashboard (protegido)
  GET  /atualizar        -> tela de upload (protegido)
  GET  /api/portfolio    -> último snapshot consolidado (protegido)
  POST /api/update       -> recebe PDFs -> consolida -> salva no banco (protegido)
  GET  /api/usd          -> cotação USD/BRL (protegido)
"""
from __future__ import annotations
import os
import shutil
import secrets
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import db
from consolidate import consolidar

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
STORAGE = BASE / "storage"
FRONT = ROOT / "frontend"
UPLOADS = STORAGE / "uploads"
STORAGE.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)

APP_PASSWORD = os.environ.get("APP_PASSWORD", "luca2026")
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(16)

app = FastAPI(title="Carteira Luca")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 24 * 14)


@app.on_event("startup")
def _startup():
    db.init_db()
    # migra snapshots em arquivo (se houver) para o banco, 1x
    if db.count_snapshots() == 0:
        db.import_json_files()


# ---- auth ----
def require_api(request: Request):
    if not request.session.get("auth"):
        raise HTTPException(401, "Não autenticado.")


def _logged(request: Request) -> bool:
    return bool(request.session.get("auth"))


@app.get("/login")
def login_page(request: Request):
    if _logged(request):
        return RedirectResponse("/")
    return FileResponse(FRONT / "login.html")


@app.post("/api/login")
async def api_login(request: Request, senha: str = Form(...)):
    if secrets.compare_digest(senha, APP_PASSWORD):
        request.session["auth"] = True
        return {"ok": True}
    raise HTTPException(401, "Senha incorreta.")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


# ---- dados ----
def fetch_usd_brl(default=5.30) -> float:
    try:
        import requests
        r = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=6)
        return round(float(r.json()["USDBRL"]["bid"]), 4)
    except Exception:
        return default


@app.get("/api/usd", dependencies=[Depends(require_api)])
def api_usd():
    return {"usd_brl": fetch_usd_brl()}


@app.get("/api/portfolio", dependencies=[Depends(require_api)])
def api_portfolio():
    data = db.get_latest()
    if not data:
        return JSONResponse({"empty": True,
                             "msg": "Nenhuma carteira ainda. Faça o primeiro upload em /atualizar."})
    return data


@app.get("/api/snapshots", dependencies=[Depends(require_api)])
def api_snapshots():
    return db.list_snapshots()


@app.post("/api/update", dependencies=[Depends(require_api)])
async def api_update(
    pdf_br: UploadFile = File(...),
    pdf_us: UploadFile = File(None),
    usd_brl: float = Form(None),
    bitcoin_brl: float = Form(0.0),
):
    if not pdf_br.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie o relatório BR em PDF (XPerformance).")
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    dest = UPLOADS / f"br_{stamp}.pdf"
    with dest.open("wb") as f:
        shutil.copyfileobj(pdf_br.file, f)

    us_path = None
    if pdf_us is not None and pdf_us.filename:
        if not pdf_us.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "O relatório EUA (XP Global) deve ser PDF.")
        up = UPLOADS / f"us_{stamp}.pdf"
        with up.open("wb") as f:
            shutil.copyfileobj(pdf_us.file, f)
        us_path = str(up)

    try:
        data = consolidar(str(dest), usd_brl=usd_brl, bitcoin_brl=bitcoin_brl,
                          pdf_us_path=us_path)
    except Exception as e:
        raise HTTPException(422, f"Não consegui ler o PDF: {e}")

    key = db.save_snapshot(data)
    return {"ok": True, "data_referencia": data.get("data_referencia"),
            "patrimonio_total": data["patrimonio_total"],
            "fonte_eua": data["fonte_eua"], "usd_brl": data["usd_brl"],
            "validacao_eua": data["validacao_eua"], "snapshot": key}


# ---- frontend (protegido) ----
@app.get("/")
def index(request: Request):
    if not _logged(request):
        return RedirectResponse("/login")
    return FileResponse(FRONT / "index.html")


@app.get("/atualizar")
def atualizar(request: Request):
    if not _logged(request):
        return RedirectResponse("/login")
    return FileResponse(FRONT / "atualizar.html")


app.mount("/static", StaticFiles(directory=FRONT), name="static")
