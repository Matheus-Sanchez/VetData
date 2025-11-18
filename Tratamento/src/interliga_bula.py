import pandas as pd
import re

# Função para normalizar nomes de produtos (remover espaços extras, etc)
def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    return str(nome).strip().lower()

# Função para extrair número da dosagem
def extrair_dosagem(dose_str):
    if pd.isna(dose_str):
        return None
    # Extrai números e unidades (mg, ml, %, etc)
    match = re.search(r'(\d+\.?\d*)\s*(mg|ml|%|g)', str(dose_str).lower())
    if match:
        return float(match.group(1)), match.group(2)
    return None

# Função para normalizar peso
def normalizar_peso(peso):
    if pd.isna(peso):
        return None
    try:
        # Remove espaços e converte para float
        peso_str = str(peso).replace(',', '.').strip()
        # Extrai apenas números
        match = re.search(r'(\d+\.?\d*)', peso_str)
        if match:
            return float(match.group(1))
    except:
        pass
    return None

# Função principal para encontrar correspondências
def encontrar_id_correspondente(row, df_referencia):
    produto = normalizar_nome(row.get('produto', ''))
    dose = row.get('dose', '')
    peso = normalizar_peso(row.get('peso', ''))
    
    # Busca na tabela de referência
    for idx, ref_row in df_referencia.iterrows():
        ref_produto = normalizar_nome(ref_row.get('produto', ''))
        ref_dose = ref_row.get('dose', '')
        
        # Verifica se o nome do produto é similar
        if produto and ref_produto and produto in ref_produto or ref_produto in produto:
            # Verifica dosagem se disponível
            dose_match = True
            if dose and ref_dose:
                dose_info = extrair_dosagem(dose)
                ref_dose_info = extrair_dosagem(ref_dose)
                if dose_info and ref_dose_info:
                    dose_match = (dose_info[0] == ref_dose_info[0] and 
                                 dose_info[1] == ref_dose_info[1])
            
            # Verifica peso se disponível
            peso_match = True
            if peso and 'peso_min' in ref_row and 'peso_max' in ref_row:
                peso_min = normalizar_peso(ref_row['peso_min'])
                peso_max = normalizar_peso(ref_row['peso_max'])
                if peso_min and peso_max:
                    peso_match = peso_min <= peso <= peso_max
            
            if dose_match and peso_match:
                return ref_row.get('id', None)
    
    return None

# Exemplo de uso:
# df_principal = pd.read_excel('tabela_principal.xlsx')
# df_referencia = pd.read_excel('tabela_referencia.xlsx')

# Adiciona coluna de ID na tabela principal
# df_principal['id_referencia'] = df_principal.apply(
#     lambda row: encontrar_id_correspondente(row, df_referencia), 
#     axis=1
# )

# Salva resultado
# df_principal.to_excel('tabela_com_ids.xlsx', index=False)

print("Script pronto! Para usar:")
print("1. Carregue suas tabelas com pd.read_excel() ou pd.read_csv()")
print("2. Aplique a função encontrar_id_correspondente()")
print("3. Salve o resultado")