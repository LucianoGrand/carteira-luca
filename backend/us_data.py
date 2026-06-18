"""
Posicao EUA (XP Global) - transcrita dos prints enviados (ref. 29/05).
Substituida pelo parser automatico quando o PDF do XP Global chegar.
Valores em USD. 'posicao' = valor de mercado atual.
"""

US_POSITION = {
    "data_referencia": "29/05/2026",
    "equities": [  # Renda Variavel
        {"ticker": "META", "nome": "Meta Platforms",      "qtd": 13.44994, "preco_medio": 223.44, "aplicado": 3005.25, "posicao": 7630.42},
        {"ticker": "LNG",  "nome": "Cheniere Energy",     "qtd": 14.60534, "preco_medio": 230.01, "aplicado": 3359.33, "posicao": 3379.82},
        {"ticker": "SMH",  "nome": "VanEck Semiconductor ETF", "qtd": 31.81369, "preco_medio": 246.58, "aplicado": 7844.48, "posicao": 19842.83},
        {"ticker": "AAPL", "nome": "Apple",               "qtd": 54.95835, "preco_medio": 149.41, "aplicado": 8211.60, "posicao": 16258.88},
        {"ticker": "AEP",  "nome": "American Electric Power", "qtd": 68.43673, "preco_medio": 98.63, "aplicado": 6750.05, "posicao": 8779.06},
        {"ticker": "NEE",  "nome": "NextEra Energy",      "qtd": 109.04511, "preco_medio": 69.87, "aplicado": 7618.90, "posicao": 9346.26},
        {"ticker": "JNJ",  "nome": "Johnson & Johnson",   "qtd": 52.11224, "preco_medio": 151.79, "aplicado": 7910.10, "posicao": 12193.22},
        {"ticker": "JPM",  "nome": "JPMorgan Chase",      "qtd": 50.00917, "preco_medio": 140.48, "aplicado": 7025.25, "posicao": 16676.56},
    ],
    "mutual_funds": [  # Fundos
        {"ticker": "BRTFZ", "nome": "BlackRock Global World Technology (A2)", "qtd": 64.94, "preco_atual": 156.74, "preco_medio": 112.87, "aplicado": 7330.00, "posicao": 10178.70},
        {"ticker": "PIMXZ", "nome": "PIMCO GIS Income (E)",                   "qtd": 586.556, "preco_atual": 17.97, "preco_medio": 17.77, "aplicado": 10425.00, "posicao": 10540.41},
        {"ticker": "JJJXZ", "nome": "JP Morgan Standard Money Market (A)",    "qtd": 1.246, "preco_atual": 16555.05, "preco_medio": 16400.57, "aplicado": 20435.11, "posicao": 20627.59},
        {"ticker": "MGLOZ", "nome": "Morgan Stanley Global Opportunity (A)",  "qtd": 47.337, "preco_atual": 167.79, "preco_medio": 166.25, "aplicado": 7870.00, "posicao": 7942.68},
        {"ticker": "JTTTZ", "nome": "JP Morgan US Growth (A)",                "qtd": 134.375, "preco_atual": 102.09, "preco_medio": 98.38, "aplicado": 13220.00, "posicao": 13718.34},
        {"ticker": "JEUIZ", "nome": "JP Morgan Global High Yield Bond (A)",   "qtd": 54.624, "preco_atual": 247.22, "preco_medio": 240.28, "aplicado": 13125.00, "posicao": 13504.15},
    ],
    "bonds": [  # Renda Fixa
        {"ticker": "VALEBZ", "nome": "Vale SA",                  "qtd": 5, "preco_medio": 865.00, "preco_atual": 954.24, "vencimento": "08/07/2030", "posicao": 4771.20},
        {"ticker": "FORDBZ", "nome": "Ford Motor Co",            "qtd": 6, "preco_medio": 1083.18, "preco_atual": 1087.56, "vencimento": "16/07/2031", "posicao": 6525.36},
        {"ticker": "MOVIBZ", "nome": "Movida Participacoes SA",  "qtd": 5, "preco_medio": 785.00, "preco_atual": 856.50, "vencimento": "08/02/2031", "posicao": 4282.50},
        {"ticker": "AEGEABZ","nome": "AEGEA Saneamento e Participacoes", "qtd": 5, "preco_medio": 1013.18, "preco_atual": 938.18, "vencimento": "20/05/2029", "posicao": 4690.90},
        {"ticker": "XPBZ",   "nome": "XP Inc",                   "qtd": 6, "preco_medio": 1029.78, "preco_atual": 1019.68, "vencimento": "02/07/2029", "posicao": 6118.08},
    ],
    "cash": 5568.80,
}


def us_holdings_flat():
    """Lista plana de ativos EUA (USD) com sub-grupo de origem."""
    out = []
    for h in US_POSITION["equities"]:
        out.append({**h, "grupo_us": "Equities"})
    for h in US_POSITION["mutual_funds"]:
        out.append({**h, "grupo_us": "Mutual Funds"})
    for h in US_POSITION["bonds"]:
        out.append({**h, "grupo_us": "Bonds"})
    out.append({"ticker": "CASH", "nome": "Cash (saldo USD)",
                "posicao": US_POSITION["cash"], "grupo_us": "Cash"})
    return out
