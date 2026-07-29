"""
Lógica de limpeza da base do IPYS.

Não conhece Google nem credencial. Recebe as linhas cruas de cada aba
(estado) e devolve registros limpos.

Regras acordadas:
  - Ignora a aba COMPLETO e qualquer aba vazia.
  - Separa "Estado - Município" em estado + unidade.
  - tipo_unidade = 'parroquia' quando a aba usa essa etiqueta (Caracas),
    senão 'municipio'. Não força Caracas virar município.
  - Urbano/rural ficam None quando a aba não tem essas colunas
    (Caracas, La Guaira), nunca 0.
  - Poblacion e contagens viram inteiro (None se vazio).
  - 'No aplica' no filtro de Bosque vira None; um número vira float.
  - 'Posible bosque' pode aparecer na preliminar, nunca na definitiva.
"""

import re
import unicodedata


def norm(txt):
    """Normaliza encabeçado: minúsculas, sem acento, sem quebra de linha."""
    if txt is None:
        return ""
    t = str(txt).replace("\n", " ").strip().lower()
    t = "".join(c for c in unicodedata.normalize("NFKD", t)
                if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t)


def a_inteiro(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def separar_unidade(valor, estado):
    """Tira o prefixo 'Estado - ' e devolve só o nome da unidade."""
    if valor is None:
        return None
    s = str(valor).strip()
    pref = f"{estado} - "
    if s.startswith(pref):
        return s[len(pref):].strip()
    return re.sub(r"^.*?-\s*", "", s).strip()


def mapear_colunas(headers):
    """Casa cada encabeçado com um campo nosso pelo texto. Devolve {campo: índice}."""
    idx = {}
    for i, h in enumerate(headers):
        n = norm(h)
        if not n:
            continue
        if n in ("municipio", "parroquia"):
            idx["unidade"] = i
            idx["_tipo"] = "parroquia" if n == "parroquia" else "municipio"
        elif n.startswith("poblacion"):
            idx["poblacion"] = i
        elif n.startswith("tamano"):
            idx["tamano"] = i
        elif "zonas urbanas" in n:
            idx["medios_urbanos"] = i
        elif "zonas rurales" in n:
            idx["medios_rurales"] = i
        elif "diversidad de fuentes" in n:
            idx["medios_plurales"] = i
        elif "que cubren" in n or ("que cubre" in n and "zona" not in n):
            idx["medios_total"] = i
        elif "preliminar" in n:
            idx["categoria_preliminar"] = i
        elif "filtro adicional" in n:
            idx["filtro_bosque"] = i
        elif "definitiva" in n:
            idx["categoria_definitiva"] = i
    return idx


def limpar_aba(estado, linhas):
    """
    Recebe o nome do estado (nome da aba) e a lista de linhas cruas
    (a primeira é o cabeçalho). Devolve lista de registros limpos.
    """
    if not linhas:
        return []
    headers = linhas[0]
    idx = mapear_colunas(headers)
    if "unidade" not in idx:
        return []

    tipo = idx.get("_tipo", "municipio")
    registros = []

    for linha in linhas[1:]:
        def val(campo):
            j = idx.get(campo)
            if j is None or j >= len(linha):
                return None
            return linha[j]

        celda = val("unidade")
        if celda is None or str(celda).strip() == "":
            continue

        filtro = val("filtro_bosque")
        if filtro is None or str(filtro).strip().lower() in ("", "no aplica"):
            filtro_val = None
        else:
            try:
                filtro_val = round(float(filtro), 2)
            except (TypeError, ValueError):
                filtro_val = None

        def texto(campo):
            v = val(campo)
            return str(v).strip() if v not in (None, "") else None

        registros.append({
            "estado": estado,
            "unidade": separar_unidade(celda, estado),
            "tipo_unidade": tipo,
            "unidade_original": str(celda).strip(),
            "poblacion": a_inteiro(val("poblacion")),
            "tamano": texto("tamano"),
            "medios_total": a_inteiro(val("medios_total")),
            "medios_urbanos": a_inteiro(val("medios_urbanos")),
            "medios_rurales": a_inteiro(val("medios_rurales")),
            "medios_plurales": a_inteiro(val("medios_plurales")),
            "categoria_preliminar": texto("categoria_preliminar"),
            "filtro_bosque_pct": filtro_val,
            "categoria_definitiva": texto("categoria_definitiva"),
        })

    return registros