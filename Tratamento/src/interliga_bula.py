import pandas as pd
import re

def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    return str(nome).strip().lower()

def extrair_dosagem(dose_str):
    if pd.isna(dose_str):
        return None
    match = re.search(r'(\d+\.?\d*)\s*(mg|ml|%|g)', str(dose_str).lower())
    if match:
        return float(match.group(1)), match.group(2)
    return None

def normalizar_peso(peso):
    if pd.isna(peso):
        return None
    try:
        peso_str = str(peso).replace(',', '.').strip()
        match = re.search(r'(\d+\.?\d*)', peso_str)
        if match:
            return float(match.group(1))
    except:
        pass
    return None

def encontrar_id_correspondente(row, df_referencia):
    produto = normalizar_nome(row.get('produto', ''))
    dose = row.get('dose', '')
    peso = normalizar_peso(row.get('peso', ''))
    
    for _, ref_row in df_referencia.iterrows():
        ref_produto = normalizar_nome(ref_row.get('produto', ''))
        ref_dose = ref_row.get('dose', '')
        
        if produto and ref_produto and (produto in ref_produto or ref_produto in produto):
            dose_match = True
            if dose and ref_dose:
                dose_info = extrair_dosagem(dose)
                ref_dose_info = extrair_dosagem(ref_dose)
                if dose_info and ref_dose_info:
                    dose_match = (dose_info[0] == ref_dose_info[0] and 
                                  dose_info[1] == ref_dose_info[1])
            
            peso_match = True
            if peso and 'peso_min' in ref_row and 'peso_max' in ref_row:
                peso_min = normalizar_peso(ref_row['peso_min'])
                peso_max = normalizar_peso(ref_row['peso_max'])
                if peso_min and peso_max:
                    peso_match = peso_min <= peso <= peso_max
            
            if dose_match and peso_match:
                return ref_row.get('id', None)
    
    return None


# -------------------------------
# USO REAL
# -------------------------------
df = pd.read_excel("./Dados_limpos/produtos.xlsx")
df_ref = pd.read_excel("../../bula.xlsx")

df["id_correspondente"] = df.apply(
    lambda row: encontrar_id_correspondente(row, df_ref),
    axis=1
)

df.to_excel("resultado_final.xlsx", index=False)

print("Processo finalizado! Arquivo salvo como resultado_final.xlsx")
