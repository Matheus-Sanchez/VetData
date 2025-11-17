"""
Script de Validação e Limpeza de Dados
Valida e limpa dados antes do processamento principal
Identifica produtos inválidos e duplicatas
"""

import pandas as pd
from pathlib import Path
import re
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ValidadorDados:
    """
    Valida e limpa dados coletados antes do processamento principal
    """
    
    def __init__(self):
        # Lista de medicamentos válidos (deve coincidir com o processador)
        self.medicamentos_validos = {
            'simparic': ['simparic'],
            'revolution': ['revolution'],
            'nexgard': ['nexgard'],
            'bravecto': ['bravecto'],
            'frontline': ['frontline'],
            'advocate': ['advocate'],
            'drontal': ['drontal'],
            'milbemax': ['milbemax'],
            'vermivet': ['vermivet'],
            'rimadyl': ['rimadyl'],
            'onsior': ['onsior'],
            'maxicam': ['maxicam', 'meloxicam', 'meloxivet'],
            'carproflan': ['carproflan', 'carprofeno', 'carprodyl', 'carproflex'],
            'previcox': ['previcox'],
            'apoquel': ['apoquel'],
            'zenrelia': ['zenrelia'],
            'synulox': ['synulox'],
            'baytril': ['baytril']
        }
        
        # Variações conhecidas
        self.variacoes_conhecidas = {
            'spectra', 'combo', 'plus', 'transdermal', 'topspot', 
            'spray', 'puppy', 'spot', 'spoton', 'flavour', 
            'injetavel', 'composto', 'filhote'
        }

        self.variacoes_invalidas = {
            'casa', 'racao', 'brinquedo', 'acessorio', 'higiene', 'banho',
            'coleira', 'cama', 'petisco', 'alimentacao', 'suplemento',
            'vitamina', 'alca', 'peitoral', 'antipuxao', 'tapete'
        }

    
    def normalizar_texto(self, texto):
        """Remove acentos e normaliza texto"""
        if not texto:
            return ""
        from unicodedata import normalize
        texto = normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('ASCII')
        return texto.lower()
    
    def e_produto_valido(self, produto, marca):
        """
        Verifica se produto pertence à lista de medicamentos válidos,
        não contém palavras proibidas e contém o nome EXATO do medicamento.
        """
        if not produto or not marca:
            return (False, None, None)
        
        texto = self.normalizar_texto(f"{produto} {marca}")

        # ❌ 1. Não pode conter palavras inválidas
        for palavra in self.variacoes_invalidas:
            if palavra in texto:
                return (False, None, None)

        # ✔ 2. Verificar se contém NOME COMPLETO do medicamento (regex)
        import re
        for med_base, variantes in self.medicamentos_validos.items():
            for variante in variantes:
                padrao = r'\b' + re.escape(variante) + r'\b'
                if re.search(padrao, texto):

                    # Encontrou o medicamento certo
                    variacao = None
                    for var in self.variacoes_conhecidas:
                        if var in texto:
                            variacao = var
                            break

                    return (True, med_base, variacao)

        # ❌ 3. Nenhum medicamento válido encontrado
        return (False, None, None)


    
    def analisar_arquivo(self, caminho_arquivo):
        """
        Analisa um arquivo Excel e retorna estatísticas
        
        Args:
            caminho_arquivo: Path para arquivo Excel
            
        Returns:
            dict com estatísticas
        """
        try:
            df = pd.read_excel(caminho_arquivo)
            
            stats = {
                'arquivo': caminho_arquivo.name,
                'total_registros': len(df),
                'validos': 0,
                'invalidos': 0,
                'duplicatas_exatas': 0,
                'medicamentos': defaultdict(int),
                'produtos_invalidos': []
            }
            
            # Validar cada registro
            produtos_vistos = set()
            
            for pos, (idx, row) in enumerate(df.iterrows(), start=2):
                produto = row.get('produto', '')
                marca = row.get('marca', '')

                e_valido, med_base, variacao = self.e_produto_valido(produto, marca)

                if e_valido:
                    stats['validos'] += 1
                    stats['medicamentos'][med_base] += 1

                    # Verificar duplicatas exatas
                    chave = (produto, row.get('quantidade'), row.get('preco'), row.get('site'), row.get('data_coleta'))
                    if chave in produtos_vistos:
                        stats['duplicatas_exatas'] += 1
                    else:
                        produtos_vistos.add(chave)

                else:
                    stats['invalidos'] += 1
                    stats['produtos_invalidos'].append({
                        'produto': produto,
                        'marca': marca,
                        'linha': pos
                    })


            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao analisar {caminho_arquivo.name}: {e}")
            return None
    
    def validar_pasta(self, pasta, extensoes=['.xlsx', '.xls']):
        """
        Valida todos os arquivos de uma pasta
        
        Args:
            pasta: Caminho da pasta
            extensoes: Extensões de arquivo para processar
            
        Returns:
            dict com relatório completo
        """
        caminho = Path(pasta)
        
        if not caminho.exists():
            logger.error(f"Pasta não encontrada: {pasta}")
            return None
        
        arquivos = []
        for ext in extensoes:
            arquivos.extend(list(caminho.glob(f"*{ext}")))
        
        if not arquivos:
            logger.warning(f"Nenhum arquivo encontrado em {pasta}")
            return None
        
        logger.info(f"Validando {len(arquivos)} arquivo(s)...")
        
        relatorio = {
            'total_arquivos': len(arquivos),
            'arquivos': [],
            'totais': {
                'registros': 0,
                'validos': 0,
                'invalidos': 0,
                'duplicatas': 0
            },
            'medicamentos_global': defaultdict(int)
        }
        
        # Analisar cada arquivo
        for arquivo in arquivos:
            stats = self.analisar_arquivo(arquivo)
            if stats:
                relatorio['arquivos'].append(stats)
                relatorio['totais']['registros'] += stats['total_registros']
                relatorio['totais']['validos'] += stats['validos']
                relatorio['totais']['invalidos'] += stats['invalidos']
                relatorio['totais']['duplicatas'] += stats['duplicatas_exatas']
                
                # Acumular medicamentos
                for med, count in stats['medicamentos'].items():
                    relatorio['medicamentos_global'][med] += count
        
        return relatorio
    
    def limpar_arquivo(self, caminho_arquivo, pasta_saida="Dados_Limpos"):
        """
        Limpa um arquivo removendo produtos inválidos
        
        Args:
            caminho_arquivo: Path para arquivo Excel
            pasta_saida: Pasta para salvar arquivo limpo
            
        Returns:
            Path do arquivo limpo
        """
        try:
            df = pd.read_excel(caminho_arquivo)
            
            # Adicionar colunas de validação
            validacoes = []
            for idx, row in df.iterrows():
                e_valido, med_base, variacao = self.e_produto_valido(
                    row.get('produto', ''), 
                    row.get('marca', '')
                )
                validacoes.append({
                    'e_valido': e_valido,
                    'medicamento_base': med_base,
                    'variacao': variacao if variacao else 'Base'
                })
            
            df_validacao = pd.DataFrame(validacoes)
            df = pd.concat([df, df_validacao], axis=1)
            
            # Filtrar apenas válidos
            df_limpo = df[df['e_valido'] == True].copy()
            df_limpo = df_limpo.drop('e_valido', axis=1)
            
            # Remover duplicatas exatas
            antes = len(df_limpo)
            df_limpo = df_limpo.drop_duplicates(
                subset=['produto', 'quantidade', 'preco', 'site', 'data_coleta'],
                keep='first'
            )
            depois = len(df_limpo)
            
            # Salvar
            Path(pasta_saida).mkdir(exist_ok=True)
            arquivo_saida = Path(pasta_saida) / f"limpo_{caminho_arquivo.name}"
            df_limpo.to_excel(arquivo_saida, index=False)
            
            logger.info(f"✓ {caminho_arquivo.name}: {len(df)} → {depois} registros "
                       f"({len(df) - antes} inválidos, {antes - depois} duplicatas)")
            
            return arquivo_saida
            
        except Exception as e:
            logger.error(f"Erro ao limpar {caminho_arquivo.name}: {e}")
            return None
    
    def limpar_pasta(self, pasta, pasta_saida="Dados_Limpos"):
        """
        Limpa todos os arquivos de uma pasta
        
        Args:
            pasta: Pasta com arquivos para limpar
            pasta_saida: Pasta para salvar arquivos limpos
        """
        caminho = Path(pasta)
        arquivos = list(caminho.glob("*.xlsx")) + list(caminho.glob("*.xls"))
        
        logger.info(f"Limpando {len(arquivos)} arquivo(s)...")
        
        for arquivo in arquivos:
            self.limpar_arquivo(arquivo, pasta_saida)
        
        logger.info(f"✓ Arquivos limpos salvos em: {pasta_saida}")
    
    def gerar_relatorio_texto(self, relatorio):
        """
        Gera relatório em formato texto legível
        
        Args:
            relatorio: Dicionário com relatório de validação
            
        Returns:
            String com relatório formatado
        """
        if not relatorio:
            return "Nenhum relatório disponível"
        
        linhas = []
        linhas.append("=" * 80)
        linhas.append("RELATÓRIO DE VALIDAÇÃO DE DADOS")
        linhas.append("=" * 80)
        linhas.append("")
        
        # Totais
        totais = relatorio['totais']
        linhas.append("📊 RESUMO GERAL")
        linhas.append("-" * 80)
        linhas.append(f"Total de arquivos: {relatorio['total_arquivos']}")
        linhas.append(f"Total de registros: {totais['registros']}")
        linhas.append(f"Registros válidos: {totais['validos']} ({totais['validos']/totais['registros']*100:.1f}%)")
        linhas.append(f"Registros inválidos: {totais['invalidos']} ({totais['invalidos']/totais['registros']*100:.1f}%)")
        linhas.append(f"Duplicatas exatas: {totais['duplicatas']}")
        linhas.append("")
        
        # Medicamentos
        linhas.append("💊 DISTRIBUIÇÃO POR MEDICAMENTO")
        linhas.append("-" * 80)
        medicamentos_ordenados = sorted(
            relatorio['medicamentos_global'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for med, count in medicamentos_ordenados:
            linhas.append(f"  {med.capitalize():<20} {count:>6} registros")
        linhas.append("")
        
        # Detalhes por arquivo
        linhas.append("📁 DETALHES POR ARQUIVO")
        linhas.append("-" * 80)
        for arquivo_stats in relatorio['arquivos']:
            linhas.append(f"\n{arquivo_stats['arquivo']}")
            linhas.append(f"  Total: {arquivo_stats['total_registros']}")
            linhas.append(f"  Válidos: {arquivo_stats['validos']}")
            linhas.append(f"  Inválidos: {arquivo_stats['invalidos']}")
            linhas.append(f"  Duplicatas: {arquivo_stats['duplicatas_exatas']}")
            
            if arquivo_stats['produtos_invalidos']:
                linhas.append(f"  ⚠️  Produtos inválidos encontrados:")
                for prod in arquivo_stats['produtos_invalidos'][:5]:  # Mostrar no máximo 5
                    linhas.append(f"     - Linha {prod['linha']}: {prod['produto']} ({prod['marca']})")
                if len(arquivo_stats['produtos_invalidos']) > 5:
                    linhas.append(f"     ... e mais {len(arquivo_stats['produtos_invalidos'])-5}")
        
        linhas.append("")
        linhas.append("=" * 80)
        
        return "\n".join(linhas)


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    validador = ValidadorDados()
    
    print("\n" + "="*80)
    print("VALIDADOR DE DADOS - MEDICAMENTOS VETERINÁRIOS")
    print("="*80)
    
    # 1. Validar dados novos
    print("\n1️⃣  VALIDANDO DADOS NOVOS...")
    relatorio_novos = validador.validar_pasta("../../Scraper/dados_coletados")
    
    if relatorio_novos:
        print(validador.gerar_relatorio_texto(relatorio_novos))
        
        # Salvar relatório
        with open("relatorio_validacao_novos.txt", "w", encoding="utf-8") as f:
            f.write(validador.gerar_relatorio_texto(relatorio_novos))
        print("\n✓ Relatório salvo: relatorio_validacao_novos.txt")
    
    # 2. Validar dados históricos
    print("\n2️⃣  VALIDANDO DADOS HISTÓRICOS...")
    relatorio_historico = validador.validar_pasta("../")
    
    if relatorio_historico:
        print(validador.gerar_relatorio_texto(relatorio_historico))
        
        # Salvar relatório
        with open("relatorio_validacao_historico.txt", "w", encoding="utf-8") as f:
            f.write(validador.gerar_relatorio_texto(relatorio_historico))
        print("\n✓ Relatório salvo: relatorio_validacao_historico.txt")
    
    # 3. Perguntar se deseja limpar
    print("\n3️⃣  LIMPEZA DE DADOS")
    resposta = input("\nDeseja limpar os dados removendo produtos inválidos? (s/n): ")
    
    if resposta.lower() == 's':
        print("\nLimpando dados novos...")
        validador.limpar_pasta("../../Scraper/dados_coletados", "Dados_Limpos/novos")
        
        print("\nLimpando dados históricos...")
        validador.limpar_pasta("../", "Dados_Limpos/historico")
        
        print("\n✓ Dados limpos salvos em: Dados_Limpos/")
        print("\n💡 DICA: Use as pastas 'Dados_Limpos/novos' e 'Dados_Limpos/historico'")
        print("   como entrada no processador principal para melhor qualidade de dados!")
    
    print("\n" + "="*80)
    print("VALIDAÇÃO CONCLUÍDA")
    print("="*80)