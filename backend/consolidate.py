"""
Consolida BR (XPerformance) + EUA (XP Global) numa carteira unica em R$,
classificada nas categorias do assessor, e monta o modelo que alimenta o
dashboard (totais por categoria, meta vs real, ativos, series historicas).
"""
from __future__ import annotations

from parser_br import parse_pdf_br
from parser_us import parse_pdf_us, us_holdings_flat_from_pdf
from us_data import us_holdings_flat
from categorias import CATEGORIAS, CATEGORIA_ORDEM, classificar

MESES_ABREV = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def consolidar(pdf_br_path: str, *, usd_brl: float | None = None,
               bitcoin_brl: float = 0.0, pdf_us_path: str | None = None) -> dict:
    br = parse_pdf_br(pdf_br_path)

    # fonte EUA: PDF do XP Global (preferido) ou dados embutidos (fallback)
    validacao_us = []
    rate_pdf = None
    if pdf_us_path:
        us_parsed = parse_pdf_us(pdf_us_path)
        us_flat = us_holdings_flat_from_pdf(us_parsed)
        validacao_us = us_parsed.get("validacao", [])
        rate_pdf = us_parsed.get("usd_brl_pdf")
    else:
        us_flat = us_holdings_flat()

    if usd_brl is None:
        usd_brl = rate_pdf or 5.30

    ativos = []

    # ---- BR (ja em R$) ----
    for h in br["holdings"]:
        cat = classificar(h["nome"], origem="BR", estrategia=h["estrategia"])
        ativos.append({
            "nome": h["nome"],
            "categoria": cat,
            "origem": "BR",
            "subgrupo": h["estrategia"],
            "valor_brl": h["saldo"],
            "valor_orig": h["saldo"],
            "moeda": "BRL",
            "qtd": h["qtd"],
            "rent_mes": h["rent_mes"],
            "rent_ano": h["rent_ano"],
        })

    # ---- EUA (USD -> BRL) ----
    for h in us_flat:
        cat = classificar(h["nome"], origem="US",
                          ticker=h.get("ticker", ""), grupo_us=h.get("grupo_us", ""))
        pos = h.get("posicao", 0.0) or 0.0
        ativos.append({
            "nome": h["nome"],
            "ticker": h.get("ticker"),
            "categoria": cat,
            "origem": "US",
            "subgrupo": h.get("grupo_us", ""),
            "valor_brl": pos * usd_brl,
            "valor_orig": pos,
            "moeda": "USD",
            "qtd": h.get("qtd"),
        })

    # ---- Bitcoin (externo, manual) ----
    if bitcoin_brl and bitcoin_brl > 0:
        ativos.append({
            "nome": "Bitcoin", "categoria": "BITCOIN", "origem": "MANUAL",
            "subgrupo": "Cripto", "valor_brl": bitcoin_brl,
            "valor_orig": bitcoin_brl, "moeda": "BRL", "qtd": None,
        })

    patrimonio_total = sum(a["valor_brl"] for a in ativos)
    patrimonio_br = sum(a["valor_brl"] for a in ativos if a["origem"] == "BR")
    patrimonio_us = sum(a["valor_brl"] for a in ativos if a["origem"] == "US")

    # ---- agrega por categoria ----
    categorias = []
    for cat_id in CATEGORIA_ORDEM:
        meta = CATEGORIAS[cat_id]
        itens = [a for a in ativos if a["categoria"] == cat_id]
        total = sum(a["valor_brl"] for a in itens)
        pct = (total / patrimonio_total * 100) if patrimonio_total else 0.0
        categorias.append({
            "id": cat_id,
            "label": meta["label"],
            "cor": meta["cor"],
            "meta_pct": meta["meta"],
            "real_pct": round(pct, 2),
            "valor_brl": round(total, 2),
            "gap_pct": round(pct - meta["meta"], 2),
            "n_ativos": len(itens),
        })

    for a in ativos:
        a["valor_brl"] = round(a["valor_brl"], 2)
        a["pct_carteira"] = round(a["valor_brl"] / patrimonio_total * 100, 2) if patrimonio_total else 0.0

    # ---- series ----
    rent_series = _serie_rentabilidade(br["historico_mensal"])
    patr_series = _serie_patrimonio(br["evolucao_patrimonial"])

    return {
        "data_referencia": br["data_referencia"],
        "usd_brl": usd_brl,
        "usd_brl_pdf": rate_pdf,
        "fonte_eua": "pdf" if pdf_us_path else "embutido",
        "validacao_eua": validacao_us,
        "patrimonio_total": round(patrimonio_total, 2),
        "patrimonio_br": round(patrimonio_br, 2),
        "patrimonio_us": round(patrimonio_us, 2),
        "patrimonio_us_usd": round(patrimonio_us / usd_brl, 2) if usd_brl else 0,
        "rentabilidade_resumo": br["rentabilidade_resumo"],
        "categorias": categorias,
        "ativos": sorted(ativos, key=lambda a: (-a["valor_brl"])),
        "serie_rentabilidade": rent_series,
        "serie_patrimonio": patr_series,
    }


def _serie_rentabilidade(hist):
    """Carteira composta vs CDI composto (base 100 -> acumulado %)."""
    out = []
    cart, cdi = 1.0, 1.0
    for r in hist:
        if r["portfolio"] is None:
            continue
        cart *= (1 + r["portfolio"] / 100.0)
        if r.get("cdi") is not None:
            cdi *= (1 + r["cdi"] / 100.0)
        out.append({
            "label": f'{MESES_ABREV[r["mes"]]}/{str(r["ano"])[2:]}',
            "carteira_mes": r["portfolio"],
            "cdi_mes": round(r["cdi"], 4) if r.get("cdi") is not None else None,
            "carteira_acum": round((cart - 1) * 100, 2),
            "cdi_acum": round((cdi - 1) * 100, 2),
        })
    return out


def _serie_patrimonio(evol):
    out = []
    for r in evol:
        out.append({
            "label": f'{MESES_ABREV[r["mes"]]}/{str(r["ano"])[2:]}',
            "patrimonio": round(r["patrimonio_final"], 2),
            "rent": r["rent"],
        })
    return out


if __name__ == "__main__":
    import json, sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else \
        "/Users/lucianorosa/Downloads/XPerformance - 7605585 - Ref.29.05.pdf"
    rate = float(sys.argv[2]) if len(sys.argv) > 2 else 5.30
    btc = float(sys.argv[3]) if len(sys.argv) > 3 else 58382.51
    data = consolidar(pdf, usd_brl=rate, bitcoin_brl=btc)
    print(f"Data ref: {data['data_referencia']}  | USD/BRL: {rate}")
    print(f"PATRIMÔNIO TOTAL: R$ {data['patrimonio_total']:,.2f}")
    print(f"  BR:  R$ {data['patrimonio_br']:,.2f}")
    print(f"  EUA: R$ {data['patrimonio_us']:,.2f}  (US$ {data['patrimonio_us_usd']:,.2f})")
    print("\nPor categoria (real vs meta):")
    for c in data["categorias"]:
        bar = "#" * int(c["real_pct"] / 1.5)
        print(f"  {c['label']:24} {c['real_pct']:5.2f}%  (meta {c['meta_pct']:4.1f}%  gap {c['gap_pct']:+5.2f})  R$ {c['valor_brl']:>14,.2f}  {bar}")
    soma = sum(c["real_pct"] for c in data["categorias"])
    print(f"  {'soma %':24} {soma:5.2f}%")
    print(f"\nAtivos: {len(data['ativos'])} | série rent: {len(data['serie_rentabilidade'])} | série patr: {len(data['serie_patrimonio'])}")
