"""
Gerenciador de arquivos para salvar dados coletados em Excel
Organiza dados por pastas e fornece relatórios de salvamento
"""

import os
import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class GerenciadorArquivos:
    """
    Responsável por salvar dados coletados em arquivos Excel organizados
    """
    
    def __init__(self, modo_teste: bool = False):
        """
        Inicializa gerenciador de arquivos
        
        Args:
            modo_teste: Se True, salva em pasta de testes
        """
        self.modo_teste = modo_teste
        self.pasta_destino = 'dados_testes' if modo_teste else 'dados_coletados'
        self.criar_pasta_se_necessario()
    
    def criar_pasta_se_necessario(self):
        """Cria pasta de destino se ela não existir"""
        try:
            os.makedirs(self.pasta_destino, exist_ok=True)
            logger.info(f"Pasta {self.pasta_destino} preparada")
        except Exception as e:
            logger.error(f"Erro ao criar pasta {self.pasta_destino}: {e}")
    
    def salvar_excel(self, dados: List[Dict], nome_arquivo: str) -> bool:
        """
        Salva lista de dados em arquivo Excel
        
        Args:
            dados: Lista de dicionários com dados dos produtos
            nome_arquivo: Nome do arquivo Excel (sem extensão)
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            if not dados:
                logger.warning(f"Nenhum dado fornecido para {nome_arquivo}")
                return False
            
            # Criar DataFrame
            df = pd.DataFrame(dados)
            
            # Garantir que nome tenha extensão .xlsx
            if not nome_arquivo.endswith('.xlsx'):
                nome_arquivo += '.xlsx'
            
            # Caminho completo do arquivo
            caminho_arquivo = os.path.join(self.pasta_destino, nome_arquivo)
            
            # Salvar Excel com formatação
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as escritor:
                df.to_excel(escritor, index=False, sheet_name='Produtos')
                
                # Obter worksheet para ajustes
                worksheet = escritor.sheets['Produtos']
                
                # Auto-ajustar largura das colunas
                for coluna in worksheet.columns:
                    largura_maxima = 0
                    nome_coluna = coluna[0].column_letter
                    
                    for celula in coluna:
                        try:
                            if len(str(celula.value)) > largura_maxima:
                                largura_maxima = len(str(celula.value))
                        except:
                            pass
                    
                    # Definir largura ajustada (máximo de 50 caracteres)
                    largura_ajustada = min(largura_maxima + 2, 50)
                    worksheet.column_dimensions[nome_coluna].width = largura_ajustada
            
            logger.info(f"Excel salvo: {caminho_arquivo} ({len(dados)} produtos)")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar {nome_arquivo}: {e}")
            return False
    
    def salvar_relatorio_consolidado(self, dados_sites: Dict[str, List[Dict]]) -> bool:
        """
        Salva relatório consolidado com dados de todos os sites
        
        Args:
            dados_sites: Dicionário {nome_site: lista_produtos}
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Criar pasta se não existir
            os.makedirs('dados_relatorios', exist_ok=True)

            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"relatorio_consolidado_{timestamp}.xlsx"
            caminho_arquivo = os.path.join('dados_relatorios', nome_arquivo)
            
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as escritor:
                
                # Aba com dados consolidados de todos os sites
                todos_dados = []
                for site, produtos in dados_sites.items():
                    todos_dados.extend(produtos)
                
                if todos_dados:
                    df_consolidado = pd.DataFrame(todos_dados)
                    df_consolidado.to_excel(escritor, index=False, sheet_name='Todos_Sites')
                
                # Aba separada para cada site
                for nome_site, produtos in dados_sites.items():
                    if produtos:
                        df_site = pd.DataFrame(produtos)
                        # Nome da aba limitado a 31 caracteres (limite Excel)
                        nome_aba = nome_site[:31]
                        df_site.to_excel(escritor, index=False, sheet_name=nome_aba)
                
                # Aba com estatísticas resumidas
                stats = self._gerar_estatisticas(dados_sites)
                if stats:
                    df_stats = pd.DataFrame(stats)
                    df_stats.to_excel(escritor, index=False, sheet_name='Estatisticas')
            
            logger.info(f"Relatório consolidado salvo: {caminho_arquivo}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar relatório consolidado: {e}")
            return False
    
    def _gerar_estatisticas(self, dados_sites: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Gera estatísticas resumidas dos dados coletados
        
        Args:
            dados_sites: Dados organizados por site
            
        Returns:
            List[Dict]: Estatísticas para cada site
        """
        estatisticas = []
        
        for nome_site, produtos in dados_sites.items():
            if not produtos:
                continue
                
            # Contar produtos por categoria
            categorias = {}
            precos = []
            
            for produto in produtos:
                categoria = produto.get('categoria', 'N/A')
                categorias[categoria] = categorias.get(categoria, 0) + 1
                
                # Extrair valores numéricos dos preços
                preco_str = produto.get('preco', '0')
                try:
                    # Remover R$ e converter para float
                    preco_num = float((preco_str.replace('R$', '').replace(' ', '').replace(',', '.')))
                    precos.append(preco_num)
                except:
                    pass
            
            # Calcular estatísticas de preço
            preco_medio = sum(precos) / len(precos) if precos else 0
            preco_min = min(precos) if precos else 0
            preco_max = max(precos) if precos else 0
            
            # Categoria mais comum
            categoria_top = max(categorias.items(), key=lambda x: x[1])[0] if categorias else "N/A"
            
            estatisticas.append({
                'Site': nome_site,
                'Total_Produtos': len(produtos),
                'Categorias_Diferentes': len(categorias),
                'Categoria_Principal': categoria_top,
                'Preco_Medio': f"R$ {preco_medio:.2f}",
                'Preco_Minimo': f"R$ {preco_min:.2f}",
                'Preco_Maximo': f"R$ {preco_max:.2f}",
                'Data_Coleta': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return estatisticas
    
    def listar_arquivos_salvos(self) -> List[str]:
        """
        Lista todos os arquivos Excel salvos na pasta de destino
        
        Returns:
            List[str]: Lista com nomes dos arquivos Excel
        """
        try:
            if not os.path.exists(self.pasta_destino):
                return []
            
            arquivos = [
                arquivo for arquivo in os.listdir(self.pasta_destino)
                if arquivo.endswith('.xlsx')
            ]
            
            return sorted(arquivos, reverse=True)  # Mais recentes primeiro
            
        except Exception as e:
            logger.error(f"Erro ao listar arquivos: {e}")
            return []
    
    def obter_info_pasta(self) -> dict:
        """
        Retorna informações sobre a pasta de destino
        
        Returns:
            dict: Informações da pasta e arquivos
        """
        try:
            arquivos = self.listar_arquivos_salvos()
            
            # Calcular tamanho total
            tamanho_total = 0
            if os.path.exists(self.pasta_destino):
                for arquivo in arquivos:
                    caminho = os.path.join(self.pasta_destino, arquivo)
                    tamanho_total += os.path.getsize(caminho)
            
            return {
                'pasta': self.pasta_destino,
                'quantidade_arquivos': len(arquivos),
                'tamanho_total_mb': f"{tamanho_total / (1024 * 1024):.2f}",
                'arquivos_recentes': arquivos[:5],  # 5 mais recentes
                'modo': 'TESTE' if self.modo_teste else 'PRODUCAO'
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter info da pasta: {e}")
            return {'erro': str(e)}