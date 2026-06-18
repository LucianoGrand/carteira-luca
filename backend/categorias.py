"""
Categorias da carteira (visao do assessor) + metas de alocacao + regras
de classificacao de cada ativo nessas categorias.

Metas vindas da planilha original (colunas J/K).
"""

# id -> (rotulo exibido, meta % 0-100, cor)
CATEGORIAS = {
    "ACOES_BR":     {"label": "Ações Brasil",          "meta": 12.0, "cor": "#2E7D32"},
    "STOCKS":       {"label": "Stocks (EUA)",          "meta": 20.0, "cor": "#1565C0"},
    "FIIS":         {"label": "Fundos Imobiliários",   "meta": 15.0, "cor": "#6A1B9A"},
    "RF_BR":        {"label": "Renda Fixa Brasil",     "meta": 26.0, "cor": "#00838F"},
    "RF_EUA":       {"label": "Renda Fixa EUA",        "meta":  8.0, "cor": "#4527A0"},
    "FUNDOS":       {"label": "Fundos Multimercado",   "meta": 11.0, "cor": "#EF6C00"},
    "BITCOIN":      {"label": "Bitcoin",               "meta":  4.0, "cor": "#F9A825"},
    "EMERGENCIA":   {"label": "Reserva de Emergência", "meta":  4.0, "cor": "#558B2F"},
    "OPORTUNIDADE": {"label": "Reserva de Oportunidade", "meta": 0.0, "cor": "#9E9D24"},
    "SALDO":        {"label": "Saldo / Proventos",     "meta":  0.0, "cor": "#757575"},
}
CATEGORIA_ORDEM = list(CATEGORIAS.keys())


def _norm(s: str) -> str:
    return (s or "").lower()


# Regras por palavra-chave no nome (tem prioridade sobre a estrategia).
# (substring, categoria)
REGRAS_NOME = [
    # Reservas (precisam vir antes das regras de RF)
    ("trend di",                  "EMERGENCIA"),
    ("trend investback",          "EMERGENCIA"),
    ("v8 cash",                   "OPORTUNIDADE"),
    ("standard money market",     "OPORTUNIDADE"),
    # EUA - acoes / fundos de acao
    ("blackrock",                 "STOCKS"),
    ("morgan stanley global",     "STOCKS"),
    ("us growth",                 "STOCKS"),
    ("trend bolsa americana",     "STOCKS"),
    # EUA - renda fixa (fundos)
    ("pimco",                     "RF_EUA"),
    ("high yield bond",           "RF_EUA"),
]

# Tickers EUA de acao -> STOCKS
TICKERS_STOCKS = {"META", "LNG", "SMH", "AAPL", "AEP", "NEE", "JNJ", "JPM"}

# Classificacao por ticker dos fundos/bonds EUA (robusto a nome corrompido no PDF).
TICKER_CATEGORIA = {
    "BRTFZ": "STOCKS",        # BlackRock Global World Technology
    "MGLOZ": "STOCKS",        # Morgan Stanley Global Opportunity
    "JTTTZ": "STOCKS",        # JP Morgan US Growth
    "PIMXZ": "RF_EUA",        # PIMCO GIS Income
    "JEUIZ": "RF_EUA",        # JP Morgan Global High Yield Bond
    "JJJXZ": "OPORTUNIDADE",  # JP Morgan Standard Money Market
}

# Nomes "limpos" por ticker (PDF as vezes corrompe a fonte).
TICKER_NOME = {
    "BRTFZ": "BlackRock Global World Technology (A2)",
    "PIMXZ": "PIMCO GIS Income (E)",
    "JJJXZ": "JP Morgan Standard Money Market (A)",
    "MGLOZ": "Morgan Stanley Global Opportunity (A)",
    "JTTTZ": "JP Morgan US Growth (A)",
    "JEUIZ": "JP Morgan Global High Yield Bond (A)",
}

# Estrategia BR -> categoria default
ESTRATEGIA_PARA_CATEGORIA = {
    "Renda Variável Brasil": "ACOES_BR",
    "Renda Variável Global": "STOCKS",
    "Fundos Listados":       "FIIS",
    "Multimercado":          "FUNDOS",
    "Pós Fixado":            "RF_BR",
    "Inflação":              "RF_BR",
    "Pré Fixado":            "RF_BR",
    "Caixa":                 "SALDO",
    "Proventos":             "SALDO",
}


def classificar(nome: str, *, origem: str, estrategia: str = "",
                ticker: str = "", grupo_us: str = "") -> str:
    """Retorna o id da categoria para um ativo. 'origem' = 'BR' ou 'US'."""
    n = _norm(nome)
    for sub, cat in REGRAS_NOME:
        if sub in n:
            return cat
    if origem == "US":
        if ticker in TICKER_CATEGORIA:
            return TICKER_CATEGORIA[ticker]
        if ticker in TICKERS_STOCKS:
            return "STOCKS"
        if grupo_us == "Equities":
            return "STOCKS"
        if grupo_us == "Bonds":
            return "RF_EUA"
        if grupo_us == "Cash":
            return "SALDO"
        if grupo_us == "Mutual Funds":
            return "RF_EUA"   # fallback p/ fundo EUA nao mapeado
    if origem == "BR":
        return ESTRATEGIA_PARA_CATEGORIA.get(estrategia, "RF_BR")
    return "SALDO"
