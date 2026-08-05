import pandas as pd
import geopandas as gpd
import json
import re
import unicodedata

NO_DATA = "Sin datos"    # placeholder classification for geometries with no CSV match yet;
                         # a renderer can special-case this single string to paint a
                         # feature gray instead of a real Desierto/Semibosque/Semidesierto color

CSV_PATH = '../output/b_geomatched.csv'
LEVEL_1_PATH = '../output/c_level_1.geojson'
LEVEL_2_PATH = '../output/c_level_2.geojson'
OUTPUT_PATH = '../output/data.json'


# --- generic helpers ---
 
def normalize_name(name):
    """Normalize a name into plain lowercase ascii, ready to be dropped into a KEY string
    (the actual slug, e.g. 'amazonas', or 'atabapo__amazonas', is assembled later by the
    caller — this function only cleans up one name at a time). WHY: names in the geojson
    /CSV have accents, spaces, and sometimes parentheses (e.g. 'Ciudad Autónoma', 'Alto
    Orinoco (La Esmeralda)'), none of which are safe inside a KEY used as an identifier
    (URLs, file names, JS object access).
 
    Three steps:
    1. NFKD-normalize: splits each accented letter into a plain base letter plus a
       separate accent mark, e.g. 'á' becomes the two characters 'a' + '´'.
    2. Drop every accent mark left over from step 1 (unicodedata.combining(c) is nonzero
       only for those marks), keeping just the plain letters, e.g. 'a' + '´' -> 'a'.
    3. Replace any run of characters that isn't a-z/A-Z/0-9 (spaces, parentheses,
       punctuation) with a single dash, then trim stray leading/trailing dashes, and
       lowercase the result, e.g. 'Ciudad Autonoma' -> 'ciudad-autonoma'.
    """
    decomposed = unicodedata.normalize('NFKD', name)
    without_accents = ''.join(c for c in decomposed if not unicodedata.combining(c))
    dashed = re.sub(r'[^A-Za-z0-9]+', '-', without_accents).strip('-')
    return dashed.lower()
 
def nullable_int(value):
    """Convert a pandas number to a plain int, or None if it's NaN. WHY: some
    medios_urbanos/rurales/plurales cells are blank in the CSV, which pandas reads as
    float('nan'). JSON has no NaN, so it must become an explicit null instead of being
    written out as the invalid token 'NaN'."""
    return None if pd.isna(value) else int(value)
 
def nullable_float(value):
    """Same as nullable_int, but keeps the value as a float. WHY: used for
    filtro_bosque_pct, which is a percentage, not a whole count, so it shouldn't be
    truncated to an int."""
    return None if pd.isna(value) else float(value)
 
def total(values):
    """Sum whatever numbers are present, treating a missing (None) value as 0. WHY:
    while the survey data is still incomplete, these state/country aggregates are just
    a development preview, not the live map."""
    return sum(v for v in values if v is not None)
 
def ratio_pop_medios(poblacion, medios_total):
    """Population per media outlet (poblacion / medios_total).
    Returns None instead of dividing by zero when medios_total is 0."""
    return round(poblacion / medios_total, 1) if medios_total else None
 
def classification_stats(classifications):
    """Count how many times each classification label appears in a list (this includes
    the NO_DATA placeholder, since an unmatched geometry is a category of its own, not an
    absence to skip over) and turn those counts into a fraction of the list. This is
    what produces the CLASSIFICATION_COUNTS/CLASSIFICATION_PCT aggregates for the country
    and each state, mirroring the reference project's structure, while still accounting
    for every geometry — surveyed or not."""
    if not classifications:
        return {}, {}
    counts = pd.Series(classifications).value_counts().to_dict()
    n = len(classifications)
    pct = {cat: round(count / n, 3) for cat, count in counts.items()}
    return counts, pct
 
def centroid_dict(geometry):
    """{"xc": ..., "yc": ...} for a shapely geometry's centroid, rounded for a tidy
    output file. WHY: matches the reference project's CENTROID field, letting a map
    place one marker per state/municipio without re-deriving geometry client-side."""
    point = geometry.centroid
    return {"xc": round(point.x, 6), "yc": round(point.y, 6)}
 
 
# --- one builder per output level ---
 
def build_small_units(level_2_gdf, by_level_2_code):
    """One entry per level-2 geometry feature (municipio/parroquia, matched or not).
 
    Args:
        level_2_gdf: GeoDataFrame from c_level_2.geojson (code, name, parent_code,
            parent_name, geometry — one row per municipio/parroquia).
        by_level_2_code: dict of level_2_code -> matching b_geomatched.csv row (as a
            dict of column -> value), missing a key entirely for unsurveyed codes.
    """
    small_units = []
    for _, feat in level_2_gdf.iterrows():
        code = feat['code']
        match = by_level_2_code.get(code)
        parent_key = normalize_name(feat['parent_name'])
        basic_info = {
            "NAME": feat['name'],
            "LEVEL": "small_unit",
            "KEY": f"{normalize_name(feat['name'])}__{parent_key}",
            "PARENT": parent_key,
            "COUNTRY": "venezuela",
            "LEVEL_1_CODE": feat['parent_code'],
            "LEVEL_2_CODE": code,
            "HAS_DATA": match is not None,
        }
        if match:
            basic_info.update({
                "SURVEY_NAME": match['unidade'],
                "TIPO_UNIDAD": match['tipo_unidade'],
                "POPULATION": int(match['poblacion']),
                "SIZE_CATEGORY": match['tamano'],
                "MEDIOS_TOTAL": int(match['medios_total']),
                "MEDIOS_URBANOS": nullable_int(match['medios_urbanos']),
                "MEDIOS_RURALES": nullable_int(match['medios_rurales']),
                "MEDIOS_PLURALES": nullable_int(match['medios_plurales']),
                "CLASSIFICATION": match['categoria_definitiva'],
                "CLASSIFICATION_PRELIMINARY": match['categoria_preliminar'],
                "FOREST_FILTER_PCT": nullable_float(match['filtro_bosque_pct']),
                "RATIO_POP_MEDIOS": ratio_pop_medios(match['poblacion'], match['medios_total']),
            })
        else:
            basic_info.update({
                "SURVEY_NAME": None,
                "TIPO_UNIDAD": None,
                "POPULATION": None,
                "SIZE_CATEGORY": None,
                "MEDIOS_TOTAL": None,
                "MEDIOS_URBANOS": None,
                "MEDIOS_RURALES": None,
                "MEDIOS_PLURALES": None,
                "CLASSIFICATION": NO_DATA,
                "CLASSIFICATION_PRELIMINARY": None,
                "FOREST_FILTER_PCT": None,
                "RATIO_POP_MEDIOS": None,
            })
        small_units.append({"BASIC_INFO": basic_info, "CENTROID": centroid_dict(feat.geometry)})
    return small_units
 
def build_large_units(level_1_gdf, small_units):
    """One entry per level-1 geometry feature, aggregated from its small_units children.
    Grouping happens here (not in a shared helper) since it's only ever needed once, right
    before building these entries.
 
    Args:
        level_1_gdf: GeoDataFrame from c_level_1.geojson (code, name, geometry — one row
            per state).
        small_units: the list already built by build_small_units, grouped here by
            LEVEL_1_CODE so each state can aggregate its own children.
    """
    children_by_state = {}
    for su in small_units:
        code = su['BASIC_INFO']['LEVEL_1_CODE']
        if code not in children_by_state:
            children_by_state[code] = []
        children_by_state[code].append(su)
 
    large_units = []
    for _, feat in level_1_gdf.iterrows():
        code = feat['code']
        children = children_by_state.get(code, [])
        matched_children = [c for c in children if c['BASIC_INFO']['HAS_DATA']]
        counts, pct = classification_stats([c['BASIC_INFO']['CLASSIFICATION'] for c in children])
        children_count = len(children)
        matched_children_count = len(matched_children)
        has_data = matched_children_count > 0
        population = total(c['BASIC_INFO']['POPULATION'] for c in children)
        medios_total = total(c['BASIC_INFO']['MEDIOS_TOTAL'] for c in children)
        medios_urbanos = total(c['BASIC_INFO']['MEDIOS_URBANOS'] for c in children)
        medios_rurales = total(c['BASIC_INFO']['MEDIOS_RURALES'] for c in children)
        medios_plurales = total(c['BASIC_INFO']['MEDIOS_PLURALES'] for c in children)
        ratio_pop_medios_value = ratio_pop_medios(population, medios_total)
 
        large_units.append({
            "BASIC_INFO": {
                "NAME": feat['name'],
                "LEVEL": "larger_unit",
                "KEY": normalize_name(feat['name']),
                "PARENT": "venezuela",
                "COUNTRY": "venezuela",
                "LEVEL_1_CODE": code,
                "CHILDREN_COUNT": children_count,
                "MATCHED_CHILDREN_COUNT": matched_children_count,
                "HAS_DATA": has_data,
                "POPULATION": population,
                "MEDIOS_TOTAL": medios_total,
                "MEDIOS_URBANOS": medios_urbanos,
                "MEDIOS_RURALES": medios_rurales,
                "MEDIOS_PLURALES": medios_plurales,
                "CLASSIFICATION_COUNTS": counts,
                "CLASSIFICATION_PCT": pct,
                "RATIO_POP_MEDIOS": ratio_pop_medios_value,
            },
            "CENTROID": centroid_dict(feat.geometry),
        })
    return large_units
 
def build_country(large_units, small_units):
    """The single country-level aggregate entry, summed over every small_unit.
 
    Args:
        large_units: the list built by build_large_units, used only for its length
            (LARGE_UNIT_COUNT).
        small_units: the full list built by build_small_units, summed over for the
            country-wide totals.
    """
    all_classifications = [c['BASIC_INFO']['CLASSIFICATION'] for c in small_units]
    counts, pct = classification_stats(all_classifications)
    large_unit_count = len(large_units)
    small_unit_count = len(small_units)
    matched_small_unit_count = sum(c['BASIC_INFO']['HAS_DATA'] for c in small_units)
    population = total(c['BASIC_INFO']['POPULATION'] for c in small_units)
    medios_total = total(c['BASIC_INFO']['MEDIOS_TOTAL'] for c in small_units)
    medios_urbanos = total(c['BASIC_INFO']['MEDIOS_URBANOS'] for c in small_units)
    medios_rurales = total(c['BASIC_INFO']['MEDIOS_RURALES'] for c in small_units)
    medios_plurales = total(c['BASIC_INFO']['MEDIOS_PLURALES'] for c in small_units)
    ratio_pop_medios_value = ratio_pop_medios(population, medios_total)
 
    return [{
        "BASIC_INFO": {
            "NAME": "Venezuela",
            "LEVEL": "country",
            "LARGE_UNIT_COUNT": large_unit_count,
            "SMALL_UNIT_COUNT": small_unit_count,
            "MATCHED_SMALL_UNIT_COUNT": matched_small_unit_count,
            "POPULATION": population,
            "MEDIOS_TOTAL": medios_total,
            "MEDIOS_URBANOS": medios_urbanos,
            "MEDIOS_RURALES": medios_rurales,
            "MEDIOS_PLURALES": medios_plurales,
            "CLASSIFICATION_COUNTS": counts,
            "CLASSIFICATION_PCT": pct,
            "RATIO_POP_MEDIOS": ratio_pop_medios_value,
        }
    }]
 
 
def main():
    df = pd.read_csv(CSV_PATH)
    by_level_2_code = df.set_index('level_2_code').to_dict('index')
 
    level_1_gdf = gpd.read_file(LEVEL_1_PATH)
    level_2_gdf = gpd.read_file(LEVEL_2_PATH)
 
    small_units = build_small_units(level_2_gdf, by_level_2_code)
    large_units = build_large_units(level_1_gdf, small_units)
    country = build_country(large_units, small_units)
 
    data = {"country": country, "large_units": large_units, "small_units": small_units}
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
 
 
if __name__ == "__main__":
    main()
 