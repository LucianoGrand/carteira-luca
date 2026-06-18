"""
Parser do relatório XPerformance (XP Investimentos) - posição BR.

Extrai do PDF:
  - patrimonio_total_bruto (R$)
  - data_referencia
  - rentabilidade resumo (mes/ano/12m/24m) do portfolio e benchmarks
  - historico mensal do portfolio (% e %CDI) por ano
  - evolucao patrimonial mensal (12 meses)
  - composicao por estrategia
  - posicao detalhada de cada ativo (estrategia, saldo, qtd, %aloc, rent...)

O PDF tem camada de texto limpa, entao usamos coordenadas das palavras
(extract_words) para mapear colunas de forma robusta.
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field, asdict

import pdfplumber

logging.disable(logging.WARNING)

# ---------------------------------------------------------------------------
# Helpers de numero (formato brasileiro: 1.334.222,90  /  -0,12%)
# ---------------------------------------------------------------------------
def br_to_float(s: str | None):
    if s is None:
        return None
    s = s.strip().replace("R$", "").replace("%", "").replace("\xa0", " ").strip()
    if s in ("", "-", "--"):
        return None
    neg = s.startswith("-")
    s = s.lstrip("+-").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _num_in_line(line: str):
    """Todos os numeros (R$ ou %) de uma linha, em ordem."""
    return re.findall(r"-?R?\$?\s?-?[\d.]+,\d+%?|-?[\d.]+,\d+%?", line)


# ---------------------------------------------------------------------------
# Estrutura de saida
# ---------------------------------------------------------------------------
@dataclass
class Holding:
    estrategia: str
    nome: str
    saldo: float
    qtd: float | None
    aloc: float | None          # % de alocacao (0-100)
    rent_mes: float | None = None
    cdi_mes: float | None = None
    rent_ano: float | None = None
    cdi_ano: float | None = None
    rent_24m: float | None = None
    cdi_24m: float | None = None


# Estrategias reconhecidas no relatorio (linhas de subtotal / cabecalho de grupo)
ESTRATEGIAS = [
    "Pós Fixado", "Inflação", "Pré Fixado", "Multimercado",
    "Renda Variável Brasil", "Renda Variável Global", "Fundos Listados",
    "Caixa", "Proventos",
]

# Fronteiras de coluna por borda direita (x1) das palavras numericas
# name: x1<=225 | saldo<=300 | qtd<=362 | aloc<=412 | rent_mes<=470 |
# cdi_mes<=525 | rent_ano<=582 | cdi_ano<=635 | rent_24<=700 | cdi_24<=760
COL_BOUNDS = [
    (300, "saldo"), (362, "qtd"), (412, "aloc"), (470, "rent_mes"),
    (525, "cdi_mes"), (582, "rent_ano"), (635, "cdi_ano"),
    (700, "rent_24m"), (770, "cdi_24m"),
]
NAME_MAX_X1 = 225


def _cluster_lines(words, tol=3.5):
    lines = []
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        placed = False
        for ln in lines:
            if abs(ln["top"] - w["top"]) <= tol:
                ln["words"].append(w)
                placed = True
                break
        if not placed:
            lines.append({"top": w["top"], "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
    lines.sort(key=lambda ln: ln["top"])
    return lines


def _col_of(x1):
    for bound, name in COL_BOUNDS:
        if x1 <= bound:
            return name
    return None


# Rotulos de classe que a XP imprime quebrados sob o nome do fundo.
_CLASS_TAGS = ["RF CP", "Multimercado CP RL", "Condominal", "RF RL", "CP RL", "RF"]
NAME_ABSORB_DIST = 9.0   # pt de distancia vertical p/ colar fragmentos de nome


def _clean_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _parse_line(ln):
    """Separa uma linha clusterizada em (name_words, cols)."""
    name_words, cols = [], {}
    for w in ln["words"]:
        if w["x1"] <= NAME_MAX_X1:
            name_words.append((w["x0"], w["text"]))
        else:
            c = _col_of(w["x1"])
            if c:
                cols.setdefault(c, []).append(w["text"])
    name = " ".join(t for _, t in sorted(name_words))
    return name, cols


def _is_noise(name: str) -> bool:
    low = name.lower()
    return ("posição detalhada" in low or "estratégia" == low.strip()
            or "mês atual" in low or "relatório informativo" in low
            or "precificação" in low or low.startswith("*aviso")
            or low.startswith("relatório"))


def parse_posicao_detalhada(pdf):
    holdings: list[Holding] = []
    cur_estrategia = None

    for page in pdf.pages:
        txt = page.extract_text() or ""
        if "POSIÇÃO DETALHADA DOS ATIVOS" not in txt:
            continue
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        lines = []
        for ln in _cluster_lines(words):
            name, cols = _parse_line(ln)
            saldo = br_to_float(" ".join(cols.get("saldo", []))) if "saldo" in cols else None
            lines.append({"top": ln["top"], "name": name, "cols": cols, "saldo": saldo})

        value_idx = [i for i, l in enumerate(lines)
                     if l["saldo"] is not None and l["cols"].get("aloc")]
        consumed = set()

        for i in value_idx:
            vl = lines[i]
            # fragmentos de nome: a propria linha + linhas-so-nome proximas
            frags = [(vl["top"], vl["name"])]
            for j, l in enumerate(lines):
                if j in consumed or l["saldo"] is not None or not l["name"]:
                    continue
                if _is_noise(l["name"]):
                    consumed.add(j)
                    continue
                if abs(l["top"] - vl["top"]) <= NAME_ABSORB_DIST:
                    frags.append((l["top"], l["name"]))
                    consumed.add(j)
            frags.sort()
            full_name = _clean_name(" ".join(t for _, t in frags if t))

            if not full_name or _is_noise(full_name):
                continue
            if full_name in ESTRATEGIAS:
                cur_estrategia = full_name
                continue

            cols = vl["cols"]
            qtd_raw = " ".join(cols.get("qtd", [])).strip()
            holdings.append(Holding(
                estrategia=cur_estrategia or "",
                nome=full_name,
                saldo=vl["saldo"],
                qtd=_parse_qtd(qtd_raw),
                aloc=br_to_float(" ".join(cols.get("aloc", []))),
                rent_mes=br_to_float(" ".join(cols.get("rent_mes", []))),
                cdi_mes=br_to_float(" ".join(cols.get("cdi_mes", []))),
                rent_ano=br_to_float(" ".join(cols.get("rent_ano", []))),
                cdi_ano=br_to_float(" ".join(cols.get("cdi_ano", []))),
                rent_24m=br_to_float(" ".join(cols.get("rent_24m", []))),
                cdi_24m=br_to_float(" ".join(cols.get("cdi_24m", []))),
            ))
    return holdings


def _parse_qtd(s: str):
    """Quantidade vem como 42660.43 ou 884.5 ou 31000 (ponto = decimal aqui)."""
    s = s.strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return br_to_float(s)


# ---------------------------------------------------------------------------
# Cabecalho: patrimonio, data, rentabilidade resumo
# ---------------------------------------------------------------------------
def parse_header(pdf):
    out = {}
    full = "\n".join((p.extract_text() or "") for p in pdf.pages[:6])

    m = re.search(r"Data de Referência\s*\n[\d]+\s+[^\n]*?\n?\s*(\d{2}/\d{2}/\d{4})", full)
    if not m:
        m = re.search(r"(\d{2}/\d{2}/\d{4})", full)
    out["data_referencia"] = m.group(1) if m else None

    m = re.search(r"PATRIMÔNIO TOTAL BRUTO:.*?\n\s*R\$\s*([\d.]+,\d{2})", full, re.S)
    out["patrimonio_total"] = br_to_float(m.group(1)) if m else None

    # tabela de rentabilidade (Portfolio / CDI / Ibovespa / IPCA / Dolar)
    ref = {}
    for label in ["Portfólio", "CDI", "Ibovespa", "IPCA", "Dólar"]:
        m = re.search(rf"^{re.escape(label)}\s+(-?[\d.]+,\d+%)\s+(-?[\d.]+,\d+%)\s+(-?[\d.]+,\d+%)\s+(-?[\d.]+,\d+%)",
                      full, re.M)
        if m:
            ref[label] = {
                "mes": br_to_float(m.group(1)), "ano": br_to_float(m.group(2)),
                "m12": br_to_float(m.group(3)), "m24": br_to_float(m.group(4)),
            }
    out["rentabilidade_resumo"] = ref
    return out


# ---------------------------------------------------------------------------
# Evolucao patrimonial mensal (pagina "EVOLUÇÃO PATRIMONIAL POR PERÍODO")
# ---------------------------------------------------------------------------
MESES = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,
         "jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}


def parse_evolucao_patrimonial(pdf):
    rows = []
    for page in pdf.pages:
        txt = page.extract_text() or ""
        if "EVOLUÇÃO PATRIMONIAL POR PERÍODO" not in txt:
            continue
        for line in txt.split("\n"):
            m = re.match(r"^([a-z]{3})\.?/(\d{2})\s+(.*)$", line.strip())
            if not m:
                continue
            mes = MESES.get(m.group(1))
            if not mes:
                continue
            nums = _num_in_line(m.group(3))
            if len(nums) < 7:
                continue
            rows.append({
                "ano": 2000 + int(m.group(2)), "mes": mes,
                "patrimonio_inicial": br_to_float(nums[0]),
                "movimentacoes": br_to_float(nums[1]),
                "ir": br_to_float(nums[2]),
                "iof": br_to_float(nums[3]),
                "patrimonio_final": br_to_float(nums[4]),
                "ganho": br_to_float(nums[5]),
                "rent": br_to_float(nums[6]),
                "cdi_pct": br_to_float(nums[7]) if len(nums) > 7 else None,
            })
    rows.sort(key=lambda r: (r["ano"], r["mes"]))
    return rows


# ---------------------------------------------------------------------------
# Composicao por estrategia (saldo + %)
# ---------------------------------------------------------------------------
def parse_composicao(pdf):
    comp = []
    for page in pdf.pages:
        txt = page.extract_text() or ""
        if "ESTRATÉGIA: COMPOSIÇÃO" not in txt:
            continue
        for line in txt.split("\n"):
            m = re.match(r"^(.*?)\s*\(([\d.]+,\d+)%\)\s+R\$\s*([\d.]+,\d+)\s+(.*)$", line.strip())
            if not m:
                continue
            nome = re.sub(r"^[\d.,]+%\s*", "", m.group(1).strip()).strip()
            if not nome or nome.lower().startswith("total"):
                continue
            comp.append({
                "estrategia": nome,
                "pct": br_to_float(m.group(2)),
                "saldo": br_to_float(m.group(3)),
            })
        break
    return comp


def parse_historico_mensal(pdf):
    """Pagina 'RENTABILIDADE HISTÓRICA (POR ANO)': % mensal do portfolio e %CDI."""
    series = []
    for page in pdf.pages:
        txt = page.extract_text() or ""
        if "RENTABILIDADE HISTÓRICA (POR ANO)" not in txt:
            continue
        lines = [l.strip() for l in txt.split("\n")]
        for i, line in enumerate(lines):
            if not line.startswith("Portfólio"):
                continue
            port = line.split()[1:13]            # 12 meses (com "-" preservado)
            if len(port) < 12:
                continue
            year = None
            cdi = []
            for k in range(i + 1, min(i + 4, len(lines))):
                ym = re.match(r"^(20\d{2})$", lines[k])
                if ym:
                    year = int(ym.group(1))
                if lines[k].startswith("%CDI"):
                    cdi = lines[k].split()[1:13]
                    break
            if not year:
                continue
            for mes in range(12):
                p = br_to_float(port[mes]) if mes < len(port) else None
                c = br_to_float(cdi[mes]) if mes < len(cdi) else None
                if p is None:
                    continue
                # CDI mensal derivado: rent_portfolio / (%CDI/100)
                cdi_mes = (p / (c / 100.0)) if (c not in (None, 0)) else None
                series.append({"ano": year, "mes": mes + 1,
                               "portfolio": p, "pct_cdi": c, "cdi": cdi_mes})
        break
    series.sort(key=lambda r: (r["ano"], r["mes"]))
    return series


def parse_pdf_br(path: str) -> dict:
    with pdfplumber.open(path) as pdf:
        header = parse_header(pdf)
        holdings = parse_posicao_detalhada(pdf)
        evol = parse_evolucao_patrimonial(pdf)
        comp = parse_composicao(pdf)
        hist = parse_historico_mensal(pdf)
    return {
        **header,
        "composicao": comp,
        "holdings": [asdict(h) for h in holdings],
        "evolucao_patrimonial": evol,
        "historico_mensal": hist,
    }


if __name__ == "__main__":
    import sys, json
    p = sys.argv[1] if len(sys.argv) > 1 else \
        "/Users/lucianorosa/Downloads/XPerformance - 7605585 - Ref.29.05.pdf"
    data = parse_pdf_br(p)
    print("data_ref:", data["data_referencia"])
    print("patrimonio:", data["patrimonio_total"])
    print("\nrentabilidade_resumo:")
    for k, v in data["rentabilidade_resumo"].items():
        print(f"  {k:12} {v}")
    print(f"\ncomposicao ({len(data['composicao'])}):")
    for c in data["composicao"]:
        print(f"  {c['estrategia']:28} {c['pct']:6}%  R$ {c['saldo']:,.2f}")
    print(f"\nholdings ({len(data['holdings'])}):")
    tot = 0
    for h in data["holdings"]:
        tot += h["saldo"] or 0
        print(f"  [{h['estrategia']:22}] {h['nome'][:42]:42} R$ {h['saldo']:>13,.2f}  qtd={h['qtd']}  aloc={h['aloc']}")
    print(f"\nsoma holdings: R$ {tot:,.2f}")
    print(f"evolucao_patrimonial: {len(data['evolucao_patrimonial'])} meses")
