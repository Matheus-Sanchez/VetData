"""
Verificador Rápido de Dados
Script simples para identificar problemas rapidamente
"""

import pandas as pd
from pathlib import Path
from collections import Counter

def verificar_medicamentos_unicos(pasta):
    """
    Mostra todos os medicamentos/marcas únicos encontrados
    para verificar se há produtos indesejados
    """
    print("\n" + "="*80)
    print(f"VERIFICANDO: {pasta}")
    print("="*80)
    
    caminho = Path(pasta)
    arquivos = list(caminho.glob("*.xlsx")) + list(caminho.glob("*.xls"))
    
    if not arquivos:
        print(f"❌ Nenhum arquivo encontrado em {pasta}")
        return
    
    todas_marcas = []
    todas_categorias = []
    
    for arquivo in arquivos:
        try:
            df = pd.read_excel(arquivo)
            todas_marcas.extend(df['marca'].dropna().unique().tolist())
            todas_categorias.extend(df['categoria'].dropna().unique().tolist())
        except Exception as e:
            print(f"⚠️  Erro ao ler {arquivo.name}: {e}")
    
    # Contar ocorrências
    contador_marcas = Counter(todas_marcas)
    contador_categorias = Counter(todas_categorias)
    
    print("\n📋 MARCAS/MEDICAMENTOS ENCONTRADOS:")
    print("-" * 80)
    for marca, count in sorted(contador_marcas.items()):
        marca_lower = marca.lower()
        # Destacar se não está na lista de válidos
        medicamentos_validos = [
            'simparic', 'revolution', 'nexgard', 'bravecto', 'frontline',
            'advocate', 'drontal', 'milbemax', 'vermivet', 'rimadyl',
            'onsior', 'maxicam', 'carproflan', 'previcox', 'apoquel',
            'zenrelia', 'synulox', 'baytril'
        ]
        
        # Verificar variações válidas
        variacoes_validas = ['spectra', 'combo', 'plus', 'transdermal']
        e_valido = any(med in marca_lower for med in medicamentos_validos)
        
        if e_valido:
            print(f"  ✅ {marca:<30} ({count} arquivos)")
        else:
            print(f"  ⚠️  {marca:<30} ({count} arquivos) - PODE SER INVÁLIDO")
    
    print("\n📦 CATEGORIAS ENCONTRADAS:")
    print("-" * 80)
    for cat, count in sorted(contador_categorias.items()):
        print(f"  • {cat:<40} ({count} arquivos)")
    
    print("\n" + "="*80)


def verificar_duplicatas_arquivo(arquivo):
    """
    Verifica duplicatas em um arquivo específico
    """
    try:
        df = pd.read_excel(arquivo)
        
        print(f"\n📄 {arquivo.name}")
        print("-" * 80)
        print(f"Total de registros: {len(df)}")
        
        # Duplicatas por produto + quantidade + preço + site
        duplicatas = df.duplicated(
            subset=['produto', 'quantidade', 'preco', 'site'],
            keep=False
        )
        n_duplicatas = duplicatas.sum()
        
        print(f"Duplicatas exatas: {n_duplicatas} ({n_duplicatas/len(df)*100:.1f}%)")
        
        # Mostrar exemplos de duplicatas
        if n_duplicatas > 0:
            print("\nExemplos de duplicatas:")
            df_dup = df[duplicatas].sort_values(['produto', 'quantidade'])
            for i, (idx, row) in enumerate(df_dup.iterrows()):
                if i >= 3:  # Mostrar apenas 3 exemplos
                    print(f"  ... e mais {n_duplicatas - 3}")
                    break
                print(f"  {i+1}. {row['produto']} - {row['quantidade']} - {row['preco']}")
        
        # Verificar registros do mesmo produto com variações
        print("\nVariações do mesmo medicamento:")
        medicamentos_base = df['marca'].value_counts().head(5)
        for med, count in medicamentos_base.items():
            produtos_med = df[df['marca'] == med]['produto'].unique()
            if len(produtos_med) > 1:
                print(f"  {med}: {len(produtos_med)} variações diferentes")
                for prod in produtos_med[:3]:
                    print(f"    - {prod[:60]}...")
                if len(produtos_med) > 3:
                    print(f"    ... e mais {len(produtos_med) - 3}")
        
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")


def menu_principal():
    """Menu interativo para verificação"""
    print("\n" + "="*80)
    print("VERIFICADOR RÁPIDO DE DADOS")
    print("="*80)
    print("\nO que você deseja verificar?")
    print("1. Ver todos os medicamentos encontrados (dados novos)")
    print("2. Ver todos os medicamentos encontrados (dados históricos)")
    print("3. Verificar duplicatas em arquivo específico")
    print("4. Verificar tudo")
    print("0. Sair")
    
    escolha = input("\nEscolha uma opção: ")
    
    if escolha == "1":
        verificar_medicamentos_unicos("../../Scraper/dados_coletados")
    elif escolha == "2":
        verificar_medicamentos_unicos("../")
    elif escolha == "3":
        pasta = input("Digite o caminho da pasta (ou Enter para '../../Scraper/dados_coletados'): ")
        if not pasta:
            pasta = "../../Scraper/dados_coletados"
        
        caminho = Path(pasta)
        arquivos = list(caminho.glob("*.xlsx")) + list(caminho.glob("*.xls"))
        
        if not arquivos:
            print(f"❌ Nenhum arquivo encontrado em {pasta}")
            return
        
        print("\nArquivos disponíveis:")
        for i, arq in enumerate(arquivos, 1):
            print(f"{i}. {arq.name}")
        
        try:
            idx = int(input("\nEscolha o número do arquivo: ")) - 1
            if 0 <= idx < len(arquivos):
                verificar_duplicatas_arquivo(arquivos[idx])
            else:
                print("❌ Número inválido")
        except ValueError:
            print("❌ Digite um número válido")
    
    elif escolha == "4":
        print("\n🔍 VERIFICAÇÃO COMPLETA\n")
        verificar_medicamentos_unicos("../../Scraper/dados_coletados")
        verificar_medicamentos_unicos("../")
    
    elif escolha == "0":
        print("\n👋 Até logo!")
        return False
    
    return True


# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    continuar = True
    while continuar:
        continuar = menu_principal()
        if continuar:
            input("\nPressione Enter para continuar...")