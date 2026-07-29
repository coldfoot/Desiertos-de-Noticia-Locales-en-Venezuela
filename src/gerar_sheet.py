"""
Lê a planilha de origem do IPYS, limpa com o limpeza.py e escreve na
nossa planilha destino, na aba CONSOLIDADO.
"""

import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from limpeza import limpar_aba
from agregar import escrever_agregacoes

STATUS_COL = "_status"


def conectar():
    creds = Credentials.from_service_account_file(
        config.CREDENTIALS_FILE, scopes=config.SCOPES
    )
    return gspread.authorize(creds)


def ler_origem(gc):
    """Lê todas as abas de estado da origem e devolve os registros limpos."""
    sh = gc.open_by_key(config.ORIGEM_SHEET_ID)
    registros = []
    pendentes = []
    for ws in sh.worksheets():
        if ws.title in config.ABAS_IGNORAR:
            continue
        linhas = ws.get_all_values()
        regs = limpar_aba(ws.title, linhas)
        if regs:
            registros.extend(regs)
        else:
            pendentes.append(ws.title)
    return registros, pendentes


def abrir_aba_destino(gc):
    sh = gc.open_by_key(config.DESTINO_SHEET_ID)
    try:
        return sh.worksheet(config.ABA_DESTINO)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=config.ABA_DESTINO, rows=1000, cols=40)

def ler_destino_atual(ws):
    """Lê o que já existe no destino. Devolve (header, {chave: linha_dict})."""
    valores = ws.get_all_values()
    if not valores:
        return [], {}
    header = valores[0]
    existentes = {}
    for linha in valores[1:]:
        d = {header[i]: (linha[i] if i < len(linha) else "")
             for i in range(len(header))}
        chave = d.get("unidade_original", "").strip()
        if chave:
            existentes[chave] = d
    return header, existentes


def montar_saida(registros, header_atual, existentes):
    reservadas = set(config.COLUNAS) | {STATUS_COL}
    cols_equipe = [c for c in header_atual if c and c not in reservadas]

    header = config.COLUNAS + cols_equipe + [STATUS_COL]

    chaves_origem = set()
    linhas = []

    for r in registros:
        chave = r["unidade_original"]
        chaves_origem.add(chave)
        antigo = existentes.get(chave, {})
        linha = [_txt(r.get(c)) for c in config.COLUNAS]
        linha += [antigo.get(c, "") for c in cols_equipe]
        linha += ["ok"]
        linhas.append(linha)

    for chave, antigo in existentes.items():
        if chave in chaves_origem:
            continue
        linha = [antigo.get(c, "") for c in config.COLUNAS]
        linha += [antigo.get(c, "") for c in cols_equipe]
        linha += ["fora_da_origem"]
        linhas.append(linha)

    return header, linhas


def _txt(v):
    return "" if v is None else str(v)


def escrever(ws, header, linhas):
    ws.clear()
    ws.update(range_name="A1", values=[header] + linhas, value_input_option="RAW")


def main():
    if not config.DESTINO_SHEET_ID:
        raise SystemExit("Falta DESTINO_SHEET_ID no .env")

    gc = conectar()

    registros, pendentes = ler_origem(gc)
    ws = abrir_aba_destino(gc)
    header_atual, existentes = ler_destino_atual(ws)
    header, linhas = montar_saida(registros, header_atual, existentes)
    escrever(ws, header, linhas)

    escrever_agregacoes(gc, registros)

    from collections import Counter
    cats = Counter(r["categoria_definitiva"] for r in registros
                   if r["categoria_definitiva"])
    print(f"Unidades escritas : {len(registros)}")
    print(f"Estados com dados : {len({r['estado'] for r in registros})}")
    print(f"Abas sem dados    : {pendentes}")
    print("Categoria definitiva:")
    for c, n in cats.most_common():
        print(f"    {c:14s} {n}")
    print(f"\nPronto. Confere as abas CONSOLIDADO, ESTADOS e CATEGORIAS.")


if __name__ == "__main__":
    main()