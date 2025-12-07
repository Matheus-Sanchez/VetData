"""
Classe base abstrata para todos os scrapers de sites
Define interface comum e funcionalidades compartilhadas
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Dict
from dataclasses import asdict
from datetime import datetime

from estruturas_dados import InfoProduto
from gerenciador_dados import GerenciadorDados
from gerenciador_conexoes import GerenciadorConexaoHibrida

logger = logging.getLogger(__name__)

class ScraperBase(ABC):
    """
    Classe abstrata que define interface comum para todos os scrapers
    Implementa funcionalidades básicas compartilhadas entre sites
    """
    
    def __init__(self, 
                 gerenciador_conexao: GerenciadorConexaoHibrida, 
                 gerenciador_dados: GerenciadorDados,
                 modo_teste: bool = False):
        """
        Inicializa scraper base
        
        Args:
            gerenciador_conexao: Gerenciador híbrido de conexões
            gerenciador_dados: Gerenciador de dados dos medicamentos
            modo_teste: Se True, coleta apenas 1 produto por medicamento
        """
        self.gerenciador_conexao = gerenciador_conexao
        self.gerenciador_dados = gerenciador_dados
        self.modo_teste = modo_teste
        
        # Estatísticas do scraper
        self.estatisticas = {
            'medicamentos_processados': 0,
            'produtos_encontrados': 0,
            'medicamentos_sem_resultado': 0,
            'tempo_inicio': None,
            'tempo_fim': None
        }
    
    @property
    @abstractmethod
    def nome_site(self) -> str:
        """Nome do site para identificação"""
        pass
    
    @property
    @abstractmethod
    def url_base_site(self) -> str:
        """URL base do site (sem https://)"""
        pass
    
    @abstractmethod
    def construir_url_busca(self, medicamento: str) -> str:
        """
        Constrói URL de busca específica para o medicamento
        
        Args:
            medicamento: Nome do medicamento
            
        Returns:
            str: URL completa de busca
        """
        pass
    
    @abstractmethod
    def extrair_produtos_pagina(self, soup, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Extrai produtos da página usando BeautifulSoup
        Deve ser implementado por cada site específico
        
        Args:
            soup: BeautifulSoup da página
            medicamento: Nome do medicamento buscado
            metodo_usado: Método usado para obter a página (requests/selenium)
            
        Returns:
            List[InfoProduto]: Lista de produtos encontrados
        """
        pass
    
    def buscar_medicamento(self, medicamento: str) -> List[InfoProduto]:
        """
        Busca um medicamento específico no site
        
        Args:
            medicamento: Nome do medicamento
            
        Returns:
            List[InfoProduto]: Produtos encontrados
        """
        logger.info(f"🔍 {self.nome_site}: Buscando {medicamento}")
        produtos = []
        
        try:
            # Construir URL de busca
            url_busca = self.construir_url_busca(medicamento)
            
            # Obter conteúdo da página
            soup, metodo = self.gerenciador_conexao.obter_soup_pagina(url_busca)
            
            if not soup:
                logger.warning(f"❌ {self.nome_site}: Falha ao acessar página para {medicamento}")
                self.estatisticas['medicamentos_sem_resultado'] += 1
                return produtos
            
            # Extrair produtos da página
            produtos = self.extrair_produtos_pagina(soup, medicamento, metodo)
            
            # Limitar produtos se modo teste
            if self.modo_teste and produtos:
                produtos = produtos[:1]
                logger.info(f"⚡ Modo teste: limitando a 1 produto para {medicamento}")
            
            # Atualizar estatísticas
            self.estatisticas['medicamentos_processados'] += 1
            self.estatisticas['produtos_encontrados'] += len(produtos)
            
            if not produtos:
                self.estatisticas['medicamentos_sem_resultado'] += 1
                logger.info(f"⚪ {self.nome_site}: Nenhum produto encontrado para {medicamento}")
            else:
                logger.info(f"✅ {self.nome_site}: {len(produtos)} produto(s) encontrado(s) para {medicamento}")
            
            # Pausa entre buscas para não sobrecarregar o servidor
            self._pausa_entre_buscas()
            
        except Exception as e:
            logger.error(f"❌ {self.nome_site}: Erro ao buscar {medicamento}: {e}")
            self.estatisticas['medicamentos_sem_resultado'] += 1
        
        return produtos
    
    def executar_scraping_completo(self) -> List[Dict]:
        """
        Executa scraping de todos os medicamentos cadastrados
        
        Returns:
            List[Dict]: Dados de todos os produtos encontrados
        """
        logger.info(f"🚀 Iniciando scraping completo - {self.nome_site}")
        self.estatisticas['tempo_inicio'] = datetime.now()
        
        # Preparar site (cookies, etc.)
        self.gerenciador_conexao.preparar_site(self.url_base_site)
        
        produtos_coletados = []
        medicamentos = self.gerenciador_dados.obter_lista_medicamentos()
        
        logger.info(f"📋 {len(medicamentos)} medicamentos para processar")
        
        # Processar cada medicamento
        for indice, medicamento in enumerate(medicamentos, 1):
            try:
                logger.info(f"📦 [{indice}/{len(medicamentos)}] Processando {medicamento}")
                
                # Buscar produtos do medicamento
                produtos = self.buscar_medicamento(medicamento)
                
                # Converter para dicionários e adicionar à lista
                produtos_dict = [asdict(produto) for produto in produtos]
                produtos_coletados.extend(produtos_dict)
                
            except KeyboardInterrupt:
                logger.info("⚠️ Scraping interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"❌ Erro crítico ao processar {medicamento}: {e}")
                continue
        
        self.estatisticas['tempo_fim'] = datetime.now()
        self._log_estatisticas_finais(len(produtos_coletados))
        
        return produtos_coletados
    
    def _pausa_entre_buscas(self):
        """Pausa aleatória entre buscas para simular comportamento humano"""
        if self.modo_teste:
            # Pausa menor em modo teste
            delay = random.uniform(0.5, 1.5)
        else:
            # Pausa normal em modo produção
            delay = random.uniform(1.0, 3.0)
        
        time.sleep(delay)
    
    def _log_estatisticas_finais(self, total_produtos: int):
        """
        Registra estatísticas finais do scraping
        
        Args:
            total_produtos: Total de produtos coletados
        """
        tempo_total = None
        if self.estatisticas['tempo_inicio'] and self.estatisticas['tempo_fim']:
            tempo_total = self.estatisticas['tempo_fim'] - self.estatisticas['tempo_inicio']
            tempo_total = tempo_total.total_seconds()
        
        logger.info(f"📊 {self.nome_site} - Estatísticas finais:")
        logger.info(f"   • Medicamentos processados: {self.estatisticas['medicamentos_processados']}")
        logger.info(f"   • Produtos encontrados: {total_produtos}")
        logger.info(f"   • Medicamentos sem resultado: {self.estatisticas['medicamentos_sem_resultado']}")
        
        if tempo_total:
            logger.info(f"   • Tempo total: {tempo_total:.1f}s")
            if self.estatisticas['medicamentos_processados'] > 0:
                tempo_medio = tempo_total / self.estatisticas['medicamentos_processados']
                logger.info(f"   • Tempo médio por medicamento: {tempo_medio:.1f}s")
    
    def obter_estatisticas(self) -> dict:
        """
        Retorna estatísticas detalhadas do scraper
        
        Returns:
            dict: Estatísticas completas
        """
        stats = self.estatisticas.copy()
        stats['nome_site'] = self.nome_site
        stats['modo_teste'] = self.modo_teste
        
        return stats