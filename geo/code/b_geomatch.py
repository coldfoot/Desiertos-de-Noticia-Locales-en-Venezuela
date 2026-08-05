import pandas as pd
import geopandas as gpd
import json
import re
import unicodedata
from tabulate import tabulate


# NOTES: the correct names are those on the CSV file.
# This, however, still needs to be checked with Dani.


def normalize(s):
    s = s.strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'^(autonomo|parroquia) ', '', s)
    s = re.sub(r'[^a-z0-9 ]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def match_level_1(df):

    df_ = df.copy()

    # --- load data ---
    level_1 = pd.DataFrame(
                f['properties'] for f in 
                json.load(open('../input/level-1.geojson'))['features']
    )

    # --- level 1: simple normalized merge ---
    # "Caracas" in the CSV refers to Distrito Capital's parishes – Distrito Capital is the canon name in the Geojson
    manual_l1_aliases = {'Distrito Capital': 'Caracas'}

    # Replace based on the mapping dict and normalize
    level_1['name_key'] = level_1['name'].replace(manual_l1_aliases).map(normalize) 

    # Also normalize
    df_['estado_key'] = df_['estado'].map(normalize) 


    # Now that both keys are matching we can simply perform a merge and clean the columns
    df_ = df_.merge(level_1[['name_key', 'code']], left_on='estado_key', right_on='name_key', how='left')
    df_ = df_.rename(columns={'code': 'level_1_code'}).drop(columns='name_key')

    # print(tabulate(df_.sample(10), headers='keys', tablefmt='psql', showindex=False))

    return df_


def match_level_2(df):

    df_ = df.copy()

    level_2 = pd.DataFrame(
        f['properties'] for f in 
        json.load(open('../input/level-2.geojson'))['features']
    )

    # --- level 2: simple normalized merge, scoped to the matched state ---
    # csv unidade names look like "Official Name (Capital City)" -> strip the part in parenthesis so we only 
    df_['unidade_key'] = df_['unidade'].str.replace(r'\s*\(.*\)\.?$', '', regex=True).map(normalize)
    level_2['name_key'] = level_2['name'].map(normalize)

    df_ = df_.merge(
        level_2[['parent_code', 'name_key', 'code']], 
        left_on=['level_1_code', 'unidade_key'], # Merges on the level_1_code determined on the previous function and on the normalized key
        right_on=['parent_code', 'name_key'], # Using the parent code and the name key
        how='left'
    )
    df_ = df_.rename(columns={'code': 'level_2_code'}).drop(columns=['name_key', 'parent_code'])

    # --- manual fixes for entries the simple merge can't resolve ---
    # (typos/alternate spellings in the source geojson, or municipios named after their capital city)
    manual_l2_fixes = {
        'Mario Briceño Iragorry (El Limón)': 'VE0508',                     # geojson typo: "Iragorri"
        'Ocumare de la Costa': 'VE0518',                                   # geojson: "Ocumare de la Costa de Oro"
        'Zamora (Villa de Cura)': 'VE0516',                                # geojson: "Ezequiel Zamora"
        'Parroquia San Bernardino': 'VE010115',                            # geojson typo: "San Bernandino"
        'Falcón (Tinaquillo)': 'VE0902',                                   # geojson uses capital city name "Tinaquillo"
        'Antonio Díaz Curiapo (Curiapo)': 'VE1001',                        # geojson: "Antonio Díaz"
        'Esteros de Camaguan': 'VE1201',                                   # geojson: "Camaguan"
        'Adriani (El Vigía)': 'VE1401',                                    # geojson: "Alberto Adriani"
        'Briceño (Torondoy)': 'VE1411',                                    # geojson: "Justo Briceño"
        'Chacón (Canaguá)': 'VE1405',                                      # geojson: "Arzobispo Chacón"
        'Dávila (Bailadores)': 'VE1418',                                   # geojson: "Rivas Dávila"
        'Febres Cordero (Nueva Bolivia)': 'VE1422',                        # geojson: "Tulio Febres Cordero"
        'Noguera (Santa María de Caparo)': 'VE1415',                       # geojson: "Padre Noguera"
        'Parra Olmedo (Tucaní)': 'VE1407',                                 # geojson: "Caracciolo Parra Olmedo"
        'Pinto Salinas (Santa Cruz de Mora)': 'VE1403',                    # geojson: "Antonio Pinto Salinas"
        'Quintero (Santo Domingo)': 'VE1408',                              # geojson: "Cardenal Quintero"
        'Ramos de Lora (Santa Elena de Arenales)': 'VE1414',               # geojson: "Obispo Ramos de Lora"
        'Salas (Arapuey)': 'VE1410',                                       # geojson typo: "Julio Cesar Sala"
        'Marquina (Tabay)': 'VE1419',                                      # geojson: "Santos Marquina"
        'Guaicaipuro (Los Teques)': 'VE1510',                              # geojson: "Bolivariano Guaicaipuro"
        'Santa Bárbara': 'VE1611',                                         # geojson typo: "Santa Babara"
        'Zamora (Punta de Mata)': 'VE1606',                                # geojson: "Ezequiel Zamora"
        'Península de Macanao (Boca de Río)': 'VE1709',                    # geojson: "Macanao"
        'Monseñor José Vicenti de Unda (Chabasquén de Unda)': 'VE1806',    # geojson: "Monseñor José Vicente de Und"
        'Bolívar (Tía Juana)': 'VE2319',                                   # geojson: "Simón Bolívar"
        'Guajira (Sinamaica)': 'VE2315',                                   # geojson: "Indígena Bolivariano Guajira"
        'Padilla (El Toro)': 'VE2301',                                     # geojson: "Almirante Padilla"
        'Pulgar (Pueblo Nuevo-El Chivo)': 'VE2306',                        # geojson: "Francisco Javier Pulgar"
        'Lossada (La Concepción)': 'VE2307',                               # geojson: "Jesús Enrique Lossada"
        'Semprún (Casigua El Cubo)': 'VE2308',                             # geojson: "Jesús María Semprum"
        'Machiques': 'VE2311',                                             # geojson: "Machiques de Perija"
        'Rosario (La Villa del Rosario)': 'VE2316',                        # geojson: "Rosario de Perija"
    }

    df_['level_2_code'] = df_['level_2_code'].fillna(df['unidade'].map(manual_l2_fixes))

    df_ = df_.drop(columns=['estado_key', 'unidade_key'])

    print(tabulate(df_.sample(10), headers='keys', tablefmt='psql', showindex=False))

    return df_


def verify(original_df, processed_df):

    original_shape = original_df.shape
    processed_shape = processed_df.shape
    row_diff = original_shape[0] - processed_shape[0]
    missing_lv1_code = processed_df['level_1_code'].isna().sum()
    missing_lv2_code = processed_df['level_2_code'].isna().sum()
    duplicated_lv2 = processed_df.duplicated(['level_1_code','level_2_code']).sum()

    print("original shape:", original_shape)
    print("processed shape:", processed_shape)
    print("row difference:", row_diff)
    print('missing level_1_code:', missing_lv1_code)
    print('missing level_2_code:', missing_lv2_code)
    print('duplicate level 2 entries:', duplicated_lv2)

    if any([row_diff, missing_lv1_code, missing_lv2_code, duplicated_lv2]):
        raise ValueError("The merge is invalidad. Check keys.")

    return

def save(df):

    # Saves a data.json dictionary to the likeness of the FOPEA / Gabo project
    df.to_csv('../output/b_geomatched.csv', index=False)


def main():

    original_df = pd.read_csv('../output/a_fetched_from_spreadsheet.csv')
    processed_df = match_level_1(original_df)
    processed_df = match_level_2(processed_df)

    verify(original_df, processed_df)

    save(processed_df)


if __name__ == "__main__":
    main()
