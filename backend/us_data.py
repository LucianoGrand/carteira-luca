"""
Posicao EUA (XP Global) - FALLBACK apenas.

Em uso normal, a posicao EUA vem do upload do PDF do XP Global (parser_us.py),
e o app guarda tudo no banco de dados. Este arquivo so e usado como fallback
quando NENHUM PDF EUA foi enviado — por isso fica vazio (sem dados de cliente).
"""

US_POSITION = {
    "data_referencia": None,
    "equities": [],
    "mutual_funds": [],
    "bonds": [],
    "cash": 0.0,
}


def us_holdings_flat():
    """Lista plana de ativos EUA (USD). Vazio no fallback."""
    out = []
    for h in US_POSITION["equities"]:
        out.append({**h, "grupo_us": "Equities"})
    for h in US_POSITION["mutual_funds"]:
        out.append({**h, "grupo_us": "Mutual Funds"})
    for h in US_POSITION["bonds"]:
        out.append({**h, "grupo_us": "Bonds"})
    if US_POSITION["cash"]:
        out.append({"ticker": "CASH", "nome": "Cash (saldo USD)",
                    "posicao": US_POSITION["cash"], "grupo_us": "Cash"})
    return out
