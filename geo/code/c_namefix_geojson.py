# Fixes the level_1 and level_2 geojson naming conventions 
# based on the CSV output consolidado_matched.csv

import geopandas as gpd
import pandas as pd
from pprint import pprint
from tabulate import tabulate


def build_naming_pairs(df, code_col, name_col):
    """
    Build a code -> name lookup from the matched CSV rows (one name per code).
    """
    naming_pairs = df.drop_duplicates(subset=[code_col])
    return dict(zip(naming_pairs[code_col], naming_pairs[name_col]))

def apply_naming_pairs(df, code_col, name_col, naming_pairs):
    """
    Overwrite gdf[name_col] with naming_pairs[gdf[code_col]] wherever a match exists.
    Unmatched rows keep their original value, tagged with " <inherited>".
    """
    df_ = df.copy()
    df_[name_col] = df_[code_col].map(naming_pairs).fillna(df_[name_col] + " <inherited>")

    return df_

def main():
    df = pd.read_csv("../output/b_geomatched.csv")
    lv1_gdf = gpd.read_file("../input/level-1.geojson")
    lv2_gdf = gpd.read_file("../input/level-2.geojson")

    lv1_naming_pairs = build_naming_pairs(df, 'level_1_code', 'estado')
    lv1_gdf = apply_naming_pairs(lv1_gdf, 'code', 'name', lv1_naming_pairs)
    print(tabulate(lv1_gdf.drop(columns=['geometry']), headers='keys'))

    lv2_naming_pairs = build_naming_pairs(df, 'level_2_code', 'unidade')
    lv2_gdf = apply_naming_pairs(lv2_gdf, 'code', 'name', lv2_naming_pairs)
    pprint(lv2_naming_pairs)
    print(tabulate(lv2_gdf.drop(columns=['geometry']), headers='keys'))

    lv1_gdf.to_file("../output/c_level_1.geojson")
    lv2_gdf.to_file("../output/c_level_2.geojson")



if __name__ == "__main__":
	main()