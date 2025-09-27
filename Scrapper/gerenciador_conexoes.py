"""
Gerenciador híbrido de conexões que tenta requests primeiro e selenium como fallback
Otimiza velocidade tentando método mais rápido antes do mais lento
"""

import requests
import time
import random
import logging
from typing import Optional, List, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ManipuladorRequests:
    """
    Gerencia conexões HTTP usando requests com proteções anti-bot
    Método mais rápido - tentativa primária
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        self._configurar_sessao()
    
    def _configurar_sessao(self):
        """Configura sessão com headers realistas para parecer navegador humano"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Cache-Control': 'max-age=0',
        })
    
    def aceitar_cookies(self, url_site: str):
        """Acessa página inicial para estabelecer sessão e cookies"""
        try:
            resposta = self.session.get(f"https://www.{url_site}", timeout=10)
            if resposta.status_code == 200:
                logger.info(f"Sessao estabelecida com {url_site}")
        except Exception:
            pass  # Falha silenciosa para não poluir logs
    
    def fazer_requisicao(self, url: str, max_tentativas: int = 2) -> Tuple[Optional[requests.Response], str]:
        """
        Tenta fazer requisição HTTP
        
        Args:
            url: URL para acessar
            max_tentativas: Número máximo de tentativas
            
        Returns:
            tuple: (Response ou None, motivo do erro se houver)
        """
        for tentativa in range(max_tentativas):
            try:
                # Rotacionar User-Agent
                self.session.headers['User-Agent'] = random.choice(self.user_agents)
                
                # Adicionar delay progressivo
                if tentativa > 0:
                    time.sleep(1 + tentativa)
                
                resposta = self.session.get(url, timeout=12, allow_redirects=True)
                
                # Verificar se conseguiu acessar
                if resposta.status_code == 200:
                    return resposta, "sucesso"
                elif resposta.status_code == 403:
                    return None, "bloqueado_403"
                elif resposta.status_code == 429:
                    return None, "muitas_requisicoes"
                else:
                    return None, f"status_{resposta.status_code}"
                    
            except requests.exceptions.Timeout:
                if tentativa == max_tentativas - 1:
                    return None, "timeout"
            except requests.exceptions.ConnectionError:
                return None, "conexao_falhou"
            except Exception as e:
                return None, f"erro_geral_{str(e)[:50]}"
                
        return None, "max_tentativas_excedidas"

class ManipuladorSelenium:
    """
    Gerencia navegação com Selenium Chrome otimizado
    Método mais lento - usado como fallback quando requests falha
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def inicializar_driver(self) -> bool:
        """
        Inicializa Chrome com configurações otimizadas para velocidade
        
        Returns:
            bool: True se inicializou com sucesso
        """
        try:
            opcoes_chrome = Options()
            
            # OTIMIZAÇÕES DE VELOCIDADE
            opcoes_chrome.add_argument("--no-sandbox")
            opcoes_chrome.add_argument("--disable-dev-shm-usage")
            opcoes_chrome.add_argument("--disable-extensions")
            opcoes_chrome.add_argument("--disable-plugins")
            opcoes_chrome.add_argument("--disable-images")          # Não carregar imagens
            opcoes_chrome.add_argument("--disable-javascript")      # Desabilitar JS quando possível
            opcoes_chrome.add_argument("--disable-background-timer-throttling")
            opcoes_chrome.add_argument("--disable-backgrounding-occluded-windows")
            opcoes_chrome.add_argument("--disable-renderer-backgrounding")
            
            # CONFIGURAÇÕES ANTI-DETECÇÃO
            opcoes_chrome.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            opcoes_chrome.add_argument("--disable-blink-features=AutomationControlled")
            opcoes_chrome.add_experimental_option("excludeSwitches", ["enable-automation"])
            opcoes_chrome.add_experimental_option('useAutomationExtension', False)
            
            # CONFIGURAÇÕES DE JANELA (menores para velocidade)
            opcoes_chrome.add_argument("--window-size=1024,768")
            opcoes_chrome.add_argument("--headless=new")  # Modo headless para máxima velocidade
            
            # Inicializar driver
            servico = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=servico, options=opcoes_chrome)
            self.wait = WebDriverWait(self.driver, 8)  # Timeout reduzido
            
            # Script anti-detecção
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome inicializado com otimizacoes de velocidade")
            return True
            
        except Exception as e:
            logger.error(f"Falha ao inicializar Chrome: {e}")
            return False
    
    def navegar_para_url(self, url: str, timeout: int = 8) -> Tuple[bool, str]:
        """
        Navega para URL com timeout reduzido
        
        Args:
            url: URL de destino
            timeout: Timeout em segundos
            
        Returns:
            tuple: (sucesso, conteudo_html ou erro)
        """
        try:
            self.driver.get(url)
            
            # Aguardar carregamento básico
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Retornar HTML da página
            return True, self.driver.page_source
            
        except TimeoutException:
            return False, "timeout_carregamento"
        except WebDriverException as e:
            return False, f"erro_webdriver_{str(e)[:50]}"
        except Exception as e:
            return False, f"erro_geral_{str(e)[:50]}"
    
    def fechar_driver(self):
        """Fecha o driver de forma segura"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Chrome fechado")
        except Exception:
            pass  # Falha silenciosa

class GerenciadorConexaoHibrida:
    """
    Gerenciador principal que coordena requests e selenium
    Usa requests primeiro por velocidade, selenium como fallback
    """
    
    def __init__(self):
        self.manipulador_requests = ManipuladorRequests()
        self.manipulador_selenium = ManipuladorSelenium()  # Inicializado apenas quando necessário
        self.selenium_inicializado = False
        
        # Estatísticas de uso dos métodos
        self.stats_metodos = {
            'requests_sucesso': 0,
            'selenium_fallback': 0,
            'falhas_totais': 0
        }
    
    def preparar_site(self, url_site: str):
        """Prepara conexão aceitando cookies do site"""
        self.manipulador_requests.aceitar_cookies(url_site)
    
    def obter_conteudo_pagina(self, url: str) -> Tuple[Optional[str], str]:
        """
        Obtém conteúdo da página tentando requests primeiro, selenium depois
        
        Args:
            url: URL para acessar
            
        Returns:
            tuple: (conteudo_html ou None, metodo_usado)
        """
        # MÉTODO 1: Tentar com requests (mais rápido)
        resposta, motivo = self.manipulador_requests.fazer_requisicao(url)
        
        if resposta and resposta.status_code == 200:
            self.stats_metodos['requests_sucesso'] += 1
            return resposta.text, "requests"
        
        # MÉTODO 2: Fallback para Selenium se requests falhou
        # logger.info(f"Requests falhou ({motivo}), usando Selenium...")
        
        # Inicializar Selenium apenas quando necessário
        if not self.selenium_inicializado:
            self.manipulador_selenium = ManipuladorSelenium()
            if not self.manipulador_selenium.inicializar_driver():
                self.stats_metodos['falhas_totais'] += 1
                return None, "selenium_init_falhou"
            self.selenium_inicializado = True
        
        # Tentar com Selenium
        sucesso, conteudo = self.manipulador_selenium.navegar_para_url(url)
        
        if sucesso:
            self.stats_metodos['selenium_fallback'] += 1
            return conteudo, "selenium"
        else:
            self.stats_metodos['falhas_totais'] += 1
            logger.warning(f"Ambos os métodos falharam para {url}")
            return None, f"falha_total_{conteudo}"
    
    def obter_soup_pagina(self, url: str) -> Tuple[Optional[BeautifulSoup], str]:
        """
        Obtém BeautifulSoup da página
        
        Args:
            url: URL para processar
            
        Returns:
            tuple: (BeautifulSoup ou None, metodo_usado)
        """
        conteudo, metodo = self.obter_conteudo_pagina(url)
        
        if conteudo:
            try:
                soup = BeautifulSoup(conteudo, 'html.parser')
                return soup, metodo
            except Exception as e:
                logger.error(f"Erro ao criar BeautifulSoup: {e}")
                return None, f"{metodo}_soup_erro"
        
        return None, metodo
    
    def obter_estatisticas(self) -> dict:
        """Retorna estatísticas de uso dos métodos de conexão"""
        total = sum(self.stats_metodos.values())
        
        if total == 0:
            return self.stats_metodos
        
        return {
            'requests_sucesso': self.stats_metodos['requests_sucesso'],
            'selenium_fallback': self.stats_metodos['selenium_fallback'],
            'falhas_totais': self.stats_metodos['falhas_totais'],
            'taxa_requests': f"{(self.stats_metodos['requests_sucesso'] / total) * 100:.1f}%",
            'taxa_selenium': f"{(self.stats_metodos['selenium_fallback'] / total) * 100:.1f}%",
            'taxa_falhas': f"{(self.stats_metodos['falhas_totais'] / total) * 100:.1f}%"
        }
    
    def fechar_conexoes(self):
        """Fecha todas as conexões abertas"""
        if self.manipulador_selenium:
            self.manipulador_selenium.fechar_driver()
        
        # Estatísticas finais
        stats = self.obter_estatisticas()
        logger.info(f"Métodos utilizados - Requests: {stats.get('taxa_requests', '0%')}, "
                   f"Selenium: {stats.get('taxa_selenium', '0%')}, "
                   f"Falhas: {stats.get('taxa_falhas', '0%')}")
    