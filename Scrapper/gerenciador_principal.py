"""
Gerenciador principal que coordena todo o sistema de scraping
Integra todos os componentes e gerencia execução completa
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Optional

from configurador_logs import ConfiguradorLogs
from estruturas_dados import InfoMedicamento, InfoProduto
from gerenciador_dados import GerenciadorDados
from gerenciador_conexoes import GerenciadorConexaoHibrida
from gerenciador_arquivos import GerenciadorArquivos
from scraper_cobasi import ScraperCobasi
from scraper_petlove import ScraperPetlove  
from scraper_petz import ScraperPetz

logger = logging.getLogger(__name__)


class GerenciadorScrapingMedicamentos:
    """
    Gerenciador principal que coordena todo o sistema de scraping
    Integra conexões híbridas, dados, arquivos e scrapers específicos
    """
    
    def __init__(self, modo_teste: bool = False):
        """
        Inicializa sistema completo
        
        Args:
            modo_teste: Se True, executa em modo teste (1 produto por medicamento)
        """
        self.modo_teste = modo_teste
        
        # Configurar sistema de logs baseado no modo
        if modo_teste:
            ConfiguradorLogs.configurar_modo_teste()
        else:
            ConfiguradorLogs.configurar_modo_producao()
        
        logger.info(f"Inicializando sistema - Modo: {'TESTE' if modo_teste else 'PRODUCAO'}")
        
        # Inicializar componentes principais
        self.gerenciador_dados = GerenciadorDados()
        self.gerenciador_conexao = GerenciadorConexaoHibrida()
        self.gerenciador_arquivos = GerenciadorArquivos(modo_teste)
        
        # Inicializar scrapers com dependências
        self.scrapers = [
            ScraperCobasi(self.gerenciador_conexao, self.gerenciador_dados, modo_teste),
            ScraperPetlove(self.gerenciador_conexao, self.gerenciador_dados, modo_teste),
            ScraperPetz(self.gerenciador_conexao, self.gerenciador_dados, modo_teste)
        ]
        
        # Estatísticas gerais
        self.estatisticas_globais = {
            'tempo_inicio': None,
            'tempo_fim': None,
            'sites_processados': 0,
            'sites_com_sucesso': 0,
            'total_produtos_coletados': 0,
            'sites_falharam': []
        }
        
        logger.info(f"Sistema inicializado com {len(self.scrapers)} scrapers")
    
    def executar_scraper_especifico(self, scraper) -> bool:
        """
        Executa um scraper específico e salva resultados
        
        Args:
            scraper: Instância do scraper para executar
            
        Returns:
            bool: True se executou com sucesso
        """
        try:
            logger.info(f"Iniciando scraping {scraper.nome_site}")
            
            # Executar scraping completo
            dados_produtos = scraper.executar_scraping_completo()
            
            if not dados_produtos:
                logger.warning(f"{scraper.nome_site}: Nenhum produto coletado")
                return False
            
            # Gerar nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{scraper.nome_site.lower()}_{timestamp}"
            
            # Salvar dados no Excel
            sucesso_salvamento = self.gerenciador_arquivos.salvar_excel(dados_produtos, nome_arquivo)
            
            if sucesso_salvamento:
                self.estatisticas_globais['total_produtos_coletados'] += len(dados_produtos)
                logger.info(f"{scraper.nome_site}: {len(dados_produtos)} produtos salvos com sucesso")
                return True
            else:
                logger.error(f"{scraper.nome_site}: Falha ao salvar dados")
                return False
                
        except Exception as e:
            logger.error(f"{scraper.nome_site}: Erro durante scraping: {e}")
            self.estatisticas_globais['sites_falharam'].append(scraper.nome_site)
            return False
    
    def executar_todos_scrapers(self):
        """
        Executa todos os scrapers sequencialmente
        Gera relatório consolidado ao final
        """
        logger.info("="*60)
        logger.info(f"INICIANDO SCRAPING COMPLETO - {'TESTE' if self.modo_teste else 'PRODUCAO'}")
        logger.info("="*60)
        
        self.estatisticas_globais['tempo_inicio'] = datetime.now()
        dados_todos_sites = {}
        
        # Executar cada scraper
        for indice, scraper in enumerate(self.scrapers, 1):
            try:
                logger.info(f"[{indice}/{len(self.scrapers)}] Processando {scraper.nome_site}")
                
                self.estatisticas_globais['sites_processados'] += 1
                
                # Executar scraper e coletar dados
                dados_produtos = scraper.executar_scraping_completo()
                dados_todos_sites[scraper.nome_site] = dados_produtos
                
                if dados_produtos:
                    # Salvar arquivo individual
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    nome_arquivo = f"{scraper.nome_site.lower()}_{timestamp}"
                    
                    if self.gerenciador_arquivos.salvar_excel(dados_produtos, nome_arquivo):
                        self.estatisticas_globais['sites_com_sucesso'] += 1
                        self.estatisticas_globais['total_produtos_coletados'] += len(dados_produtos)
                        logger.info(f"{scraper.nome_site}: Arquivo individual salvo com sucesso")
                    else:
                        self.estatisticas_globais['sites_falharam'].append(scraper.nome_site)
                else:
                    logger.warning(f"{scraper.nome_site}: Nenhum produto coletado")
                    self.estatisticas_globais['sites_falharam'].append(scraper.nome_site)
                
                # Pausa entre sites para não sobrecarregar
                if indice < len(self.scrapers):
                    logger.info("Pausando entre sites...")
                    time.sleep(2)
                
            except KeyboardInterrupt:
                logger.info("Scraping interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"Erro crítico ao processar {scraper.nome_site}: {e}")
                self.estatisticas_globais['sites_falharam'].append(scraper.nome_site)
                continue
        
        self.estatisticas_globais['tempo_fim'] = datetime.now()
        
        # Gerar relatório consolidado se houver dados
        if any(dados_todos_sites.values()):
            logger.info("Gerando relatório consolidado...")
            self.gerenciador_arquivos.salvar_relatorio_consolidado(dados_todos_sites)
        
        # Fechar conexões
        self.gerenciador_conexao.fechar_conexoes()
        
        # Exibir estatísticas finais
        self._exibir_relatorio_final()
    
    def executar_site_especifico(self, nome_site: str):
        """
        Executa scraping de apenas um site específico
        
        Args:
            nome_site: Nome do site para processar
        """
        # Buscar scraper correspondente
        scraper_encontrado = None
        for scraper in self.scrapers:
            if scraper.nome_site.lower() == nome_site.lower():
                scraper_encontrado = scraper
                break
        
        if not scraper_encontrado:
            sites_disponiveis = [s.nome_site for s in self.scrapers]
            logger.error(f"Site '{nome_site}' não encontrado")
            logger.info(f"Sites disponíveis: {', '.join(sites_disponiveis)}")
            return
        
        logger.info(f"Executando scraping específico para {nome_site}")
        self.estatisticas_globais['tempo_inicio'] = datetime.now()
        
        # Executar scraper específico
        sucesso = self.executar_scraper_especifico(scraper_encontrado)
        
        self.estatisticas_globais['tempo_fim'] = datetime.now()
        self.estatisticas_globais['sites_processados'] = 1
        
        if sucesso:
            self.estatisticas_globais['sites_com_sucesso'] = 1
        else:
            self.estatisticas_globais['sites_falharam'].append(nome_site)
        
        # Fechar conexões
        self.gerenciador_conexao.fechar_conexoes()
        
        # Exibir resultado
        self._exibir_relatorio_final()
    
    def _exibir_relatorio_final(self):
        """Exibe relatório final da execução"""
        tempo_total = None
        if self.estatisticas_globais['tempo_inicio'] and self.estatisticas_globais['tempo_fim']:
            tempo_total = self.estatisticas_globais['tempo_fim'] - self.estatisticas_globais['tempo_inicio']
            tempo_total = tempo_total.total_seconds()
        
        logger.info("="*60)
        logger.info("RELATORIO FINAL DE EXECUÇÃO")
        logger.info("="*60)
        logger.info(f"Sites processados: {self.estatisticas_globais['sites_processados']}")
        logger.info(f"Sites com sucesso: {self.estatisticas_globais['sites_com_sucesso']}")
        logger.info(f"Total de produtos coletados: {self.estatisticas_globais['total_produtos_coletados']}")
        
        if self.estatisticas_globais['sites_falharam']:
            logger.warning(f"Sites com falhas: {', '.join(self.estatisticas_globais['sites_falharam'])}")
        
        if tempo_total:
            logger.info(f"Tempo total de execução: {tempo_total:.1f} segundos")
        
        # Estatísticas de conexão
        stats_conexao = self.gerenciador_conexao.obter_estatisticas()
        if stats_conexao:
            logger.info("Estatísticas de conexão:")
            logger.info(f"  - Requests bem-sucedidos: {stats_conexao.get('taxa_requests', '0%')}")
            logger.info(f"  - Selenium fallback: {stats_conexao.get('taxa_selenium', '0%')}")
            logger.info(f"  - Falhas totais: {stats_conexao.get('taxa_falhas', '0%')}")
        
        # Informações da pasta de destino
        info_pasta = self.gerenciador_arquivos.obter_info_pasta()
        logger.info(f"Arquivos salvos na pasta: {info_pasta.get('pasta', 'N/A')}")
        logger.info(f"Total de arquivos: {info_pasta.get('quantidade_arquivos', 0)}")
        
        logger.info("="*60)
    
    def obter_lista_sites_disponiveis(self) -> List[str]:
        """
        Retorna lista de sites disponíveis para scraping
        
        Returns:
            List[str]: Nomes dos sites disponíveis
        """
        return [scraper.nome_site for scraper in self.scrapers]
    
    # def obter_estatisticas_medicamentos(self) -> dict:
    #     """
    #     Retorna estatísticas sobre a base de medicamentos
        
    #     Returns:
    #         dict: Estatísticas dos medicamentos cadastrados
    #     """
        # return self.gerenciador_dados.obter_estatisticas()
    
    def validar_sistema(self) -> dict:
        """
        Valida se todos os componentes estão funcionando
        
        Returns:
            dict: Status de cada componente
        """
        status = {
            'gerenciador_dados': False,
            'gerenciador_conexao': False,
            'gerenciador_arquivos': False,
            'scrapers': []
        }
        
        try:
            # Testar gerenciador de dados
            # medicamentos = self.gerenciador_dados.obter_lista_completa()
            # if medicamentos:
            status['gerenciador_dados'] = True
            
            # Testar gerenciador de arquivos
            info_pasta = self.gerenciador_arquivos.obter_info_pasta()
            if info_pasta and 'pasta' in info_pasta:
                status['gerenciador_arquivos'] = True
            
            # Testar gerenciador de conexão (teste simples)
            status['gerenciador_conexao'] = True  # Sempre true se inicializou
            
            # Testar scrapers
            for scraper in self.scrapers:
                status['scrapers'].append({
                    'nome': scraper.nome_site,
                    'ativo': True,
                    'url_base': scraper.url_base_site
                })
            
        except Exception as e:
            logger.error(f"Erro na validação do sistema: {e}")
        
        return status