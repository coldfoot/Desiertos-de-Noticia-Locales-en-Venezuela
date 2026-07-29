"""
Gera as abas:
  ESTADOS    : uma linha por estado, com somas e a contagem por categoria.
  CATEGORIAS : uma linha por categoria, para toda a Venezuela, com
               quantas unidades e quanta população em cada uma.
"""

import gspread

import config

ABA_ESTADOS = "ESTADOS"
ABA_CATEGORIAS = "CATEGORIAS"
CANONICAS = ["Desierto", "Semidesierto", "Semibosque", "Bosque"]


def _soma(regs, campo):
    """Soma um campo numérico ignorando os None. Vazio se ninguém tem valor."""
    vals = [r[campo] for r in regs if r.get(campo) is not None]
    return sum(vals) if vals else ""


def _por_estado(registros):
    header = ["estado", "unidades", "poblacion", "medios_total",
              "medios_plurales", "medios_urbanos", "medios_rurales"] + CANONICAS
    linhas = []
    for estado in sorted({r["estado"] for r in registros}):
        regs = [r for r in registros if r["estado"] == estado]
        contagem = {c: 0 for c in CANONICAS}
        for r in regs:
            cat = r.get("categoria_definitiva")
            if cat in contagem:
                contagem[cat] += 1
        linha = [
            estado,
            len(regs),
            _soma(regs, "poblacion"),
            _soma(regs, "medios_total"),
            _soma(regs, "medios_plurales"),
            _soma(regs, "medios_urbanos"),
            _soma(regs, "medios_rurales"),
        ] + [contagem[c] for c in CANONICAS]
        linhas.append(linha)
    return header, linhas


def _por_categoria(registros):
    header = ["categoria", "unidades", "pct_unidades",
              "poblacion", "pct_poblacion", "medios_total"]
    total_u = len(registros)
    total_pob = sum(r["poblacion"] for r in registros if r["poblacion"] is not None)
    linhas = []

    rotulos = CANONICAS + ["(sin categoría)"]
    for cat in rotulos:
        if cat == "(sin categoría)":
            regs = [r for r in registros if not r.get("categoria_definitiva")]
        else:
            regs = [r for r in registros if r.get("categoria_definitiva") == cat]
        if not regs and cat == "(sin categoría)":
            continue
        u = len(regs)
        pob = sum(r["poblacion"] for r in regs if r["poblacion"] is not None)
        pct_u = round(100 * u / total_u, 1) if total_u else ""
        pct_pob = round(100 * pob / total_pob, 1) if total_pob else ""
        linhas.append([cat, u, pct_u, pob, pct_pob, _soma(regs, "medios_total")])

    linhas.append(["Total", total_u, 100.0 if total_u else "",
                   total_pob, 100.0 if total_pob else "",
                   _soma(registros, "medios_total")])
    return header, linhas


def _escrever_aba(sh, titulo, header, linhas):
    try:
        ws = sh.worksheet(titulo)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=titulo, rows=200, cols=20)
    ws.clear()
    ws.update(range_name="A1", values=[header] + linhas, value_input_option="RAW")


def escrever_agregacoes(gc, registros):
    sh = gc.open_by_key(config.DESTINO_SHEET_ID)
    h1, l1 = _por_estado(registros)
    _escrever_aba(sh, ABA_ESTADOS, h1, l1)
    h2, l2 = _por_categoria(registros)
    _escrever_aba(sh, ABA_CATEGORIAS, h2, l2)