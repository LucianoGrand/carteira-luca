"""
Parser do relatorio XP Global (Investimento Internacional) em PDF.

O PDF (gerado via Imprimir->Salvar como PDF do portal web) tem texto, mas:
  - colunas variam por secao (Equities / Mutual Funds / Bonds / Cash);
  - nomes de fundos quebram em varias linhas;
  - uma linha ocasional vem com os digitos "grudados" (sem virgula).
Por isso trabalhamos por linhas clusterizadas e extraimos a POSICAO
(valor de mercado, em USD) de cada ativo + ticker/nome.

Saida: dict no mesmo formato de us_data.US_POSITION.
"""
from __future__ import annotations
import re
import logging
import pdfplumber

logging.disable(logging.WARNING)

TICKER_RE = re.compile(r"^[A-Z]{2,6}\d?$")
DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
# token monetario US$ (com virgula normal OU grudado sem virgula)
USD_RE = re.compile(r"US\$\s?-?[\d.]*\d(?:,\d+)?")

SECOES = [
    ("Equities", "equities"),
    ("Mutual Funds", "mutual_funds"),
    ("Bonds", "bonds"),
    ("Cash", "cash"),
]


def _money(tok: str):
    """Converte 'US$ 247,22' ou 'US$24722' (grudado) -> float."""
    s = tok.replace("US$", "").replace(" ", "").replace("\xa0", "")
    if "," in s:                         # formato normal pt-BR
        return float(s.replace(".", "").replace(",", "."))
    digits = re.sub(r"\D", "", s)        # grudado: 2 ultimos digitos = centavos
    return int(digits) / 100 if digits else None


def _usd_tokens(text: str):
    return [_money(t) for t in USD_RE.findall(text)]


def _cluster(words, tol=3.0):
    lines = []
    for w in sorted(words, key=lambda w: (round(w["top"], 1), w["x0"])):
        for ln in lines:
            if abs(ln["top"] - w["top"]) <= tol:
                ln["words"].append(w); break
        else:
            lines.append({"top": w["top"], "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
        ln["text"] = " ".join(w["text"] for w in ln["words"])
    return lines


def _alpha_prefix(text: str):
    """Palavras (nome) antes do 1o numero/US$ da linha."""
    out = []
    for tok in text.split():
        if tok.startswith("US$") or re.match(r"^[+\-]?[\d.]+,?\d*%?$", tok):
            break
        out.append(tok)
    return " ".join(out)


def parse_pdf_us(path: str) -> dict:
    all_lines = []
    rate = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for ln in _cluster(page.extract_words()):
                all_lines.append(ln)
                m = re.search(r"1 dólar = R\$ ([\d.,]+)", ln["text"])
                if m:
                    rate = float(m.group(1).replace(".", "").replace(",", "."))

    # marca inicio de cada secao (cabecalho tem o rotulo + US$ do subtotal)
    sec_bounds = []
    seen = set()
    for i, ln in enumerate(all_lines):
        for label, key in SECOES:
            if key in seen:
                continue
            if re.search(rf"{re.escape(label)}.*US\$\s?[\d.]+,\d+", ln["text"]):
                sec_bounds.append((i, key, ln["text"]))
                seen.add(key)
                break
    sec_bounds.sort()

    result = {"data_referencia": None, "equities": [], "mutual_funds": [],
              "bonds": [], "cash": 0.0, "usd_brl_pdf": rate, "validacao": []}
    subtotais = {}

    for idx, (start, key, htext) in enumerate(sec_bounds):
        end = sec_bounds[idx + 1][0] if idx + 1 < len(sec_bounds) else len(all_lines)
        block = all_lines[start + 1:end]
        sub_toks = _usd_tokens(htext)
        subtotal = sub_toks[-1] if sub_toks else None
        subtotais[key] = subtotal

        if key == "cash":
            result["cash"] = subtotal or 0.0
            continue

        data_idx = [j for j, ln in enumerate(block)
                    if "US$" in ln["text"] and "%" in ln["text"]
                    and _usd_tokens(ln["text"])]

        for j in data_idx:
            ln = block[j]
            usd = _usd_tokens(ln["text"])
            posicao = usd[0] if key == "bonds" else usd[-1]

            ticker = None
            if key != "bonds":   # bonds nao tem ticker (so nome)
                for k in range(j - 1, max(j - 4, -1), -1):
                    if TICKER_RE.match(block[k]["text"].strip()):
                        ticker = block[k]["text"].strip(); break

            # nome: prefixo inline + linhas-texto a <=11pt (acima/abaixo)
            pref = _alpha_prefix(ln["text"])
            above, below = [], []
            for k in range(max(j - 3, 0), min(j + 4, len(block))):
                if k == j:
                    continue
                t = block[k]["text"].strip()
                if not t or TICKER_RE.match(t) or "US$" in t or "%" in t \
                   or DATE_RE.search(t) or t.lower().startswith(("ativo", "preço")) \
                   or _is_noise_us(t):
                    continue
                if abs(block[k]["top"] - ln["top"]) <= 11.0:
                    (above if block[k]["top"] < ln["top"] else below).append(t)
            nome = " ".join(above + ([pref] if pref else []) + below).strip()
            if ticker and ticker in TICKER_NOME_MAP:
                nome = TICKER_NOME_MAP[ticker]
            if not nome:
                nome = ticker or ""
            result[key].append({"ticker": ticker, "nome": nome,
                                "posicao": round(posicao, 2)})

        # validacao: soma dos ativos vs subtotal do cabecalho
        soma = round(sum(x["posicao"] for x in result[key]), 2)
        if subtotal and abs(soma - subtotal) > 1.0:
            falta = round(subtotal - soma, 2)
            result["validacao"].append({
                "secao": key, "subtotal_pdf": subtotal, "soma_lida": soma,
                "diferenca": falta,
                "msg": f"Seção {key}: li US$ {soma:,.2f} mas o subtotal é US$ {subtotal:,.2f} "
                       f"(faltam US$ {falta:,.2f} — provável corte de página no PDF)."})

    result["usd_total_pdf"] = round(sum(v for v in subtotais.values() if v), 2)
    return result


GRUPO_US = {"equities": "Equities", "mutual_funds": "Mutual Funds", "bonds": "Bonds"}


def us_holdings_flat_from_pdf(parsed: dict):
    """Lista plana de ativos EUA (USD) a partir do PDF parseado."""
    out = []
    for key, grupo in GRUPO_US.items():
        for h in parsed.get(key, []):
            out.append({"ticker": h.get("ticker"), "nome": h["nome"],
                        "posicao": h["posicao"], "grupo_us": grupo})
    if parsed.get("cash"):
        out.append({"ticker": "CASH", "nome": "Cash (saldo USD)",
                    "posicao": parsed["cash"], "grupo_us": "Cash"})
    return out


# nome limpo por ticker (importado de categorias p/ evitar nome corrompido)
try:
    from categorias import TICKER_NOME as TICKER_NOME_MAP
except Exception:
    TICKER_NOME_MAP = {}


def _is_noise_us(t: str) -> bool:
    low = t.lower()
    return ("luciano rosa" in low or low == "lm" or "marcelo" in low
            or low.startswith("pesquisar") or "portfólio internacional" in low)


if __name__ == "__main__":
    import sys, json
    p = sys.argv[1] if len(sys.argv) > 1 else \
        "/Users/lucianorosa/Downloads/XP Investimentos - Investimento Global.pdf"
    d = parse_pdf_us(p)
    print("USD/BRL no PDF:", d["usd_brl_pdf"])
    tot = 0
    for key in ["equities", "mutual_funds", "bonds"]:
        sub = sum(x["posicao"] for x in d[key])
        tot += sub
        print(f"\n== {key}  (US$ {sub:,.2f}) ==")
        for x in d[key]:
            print(f"   {str(x['ticker']):7} {x['nome'][:46]:46} US$ {x['posicao']:>12,.2f}")
    tot += d["cash"]
    print(f"\n== cash: US$ {d['cash']:,.2f} ==")
    print(f"\nTOTAL lido: US$ {tot:,.2f}  | TOTAL subtotais PDF: US$ {d['usd_total_pdf']:,.2f}")
    if d["validacao"]:
        print("\n⚠ VALIDAÇÃO:")
        for v in d["validacao"]:
            print("  -", v["msg"])
    else:
        print("\n✓ Todas as seções batem com os subtotais.")
