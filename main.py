import pandas as pd
from datetime import datetime
import time
import random
import re
import os
import json
from typing import Dict, List, Optional
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict

# Imports para método BeautifulSoup (método primário)
import requests
from bs4 import BeautifulSoup, Tag

# Imports para método Selenium (fallback)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler('scraper_medicamentos_hibrido.log', encoding='utf-8')  # Arquivo
    ]
)
logger = logging.getLogger(__name__)

# Variável global para controlar modo de teste
test_mode = False

# ==========================================
# CLASSES DE DADOS
# ==========================================

@dataclass
class InfoMedicamento:
    """
    Informações básicas sobre cada medicamento veterinário
    Usada para categorizar e organizar os dados coletados
    """
    empresa: str         # Fabricante do medicamento
    categoria: str       # Tipo (antipulgas, anti-inflamatório, etc.)
    animal: str          # Para quais animais serve
    porte: str           # Tamanho dos animais
    eficacia: str        # Duração do efeito

@dataclass
class InfoProduto:
    """
    Dados coletados de cada produto encontrado nos sites
    Estrutura unificada para armazenar informações de qualquer site
    """
    categoria: str                          # Categoria do medicamento
    marca: str                              # Nome da marca/medicamento
    produto: str                            # Nome completo do produto
    quantidade: str                         # Tamanho/quantidade (ex: 10mg, 3 comprimidos)
    preco: str                              # Preço atual
    site: str                               # Site onde foi coletado
    data_coleta: str                        # Data da coleta
    preco_antigo: Optional[str] = None      # Preço original (se em promoção)
    desconto: Optional[str] = None          # Percentual de desconto
    disponibilidade: Optional[str] = None   # Status de disponibilidade
    produto_id: Optional[str] = None        # ID interno do produto
    sku_id: Optional[str] = None            # SKU/código da variação
    url: Optional[str] = None               # URL do produto
    metodo: Optional[str] = None            # Método usado (bs4/selenium)

# ==========================================
# MANIPULADOR DE REQUISIÇÕES HTTP
# ==========================================

class ManipuladorRequests:
    """
    Gerencia requisições HTTP com proteções anti-bot
    Método primário para coleta de dados (mais rápido e eficiente)
    """
    
    def __init__(self):
        self.session = requests.Session()
        
        # Lista de User-Agents realistas para rotacionar
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self.configurar_sessao()
    
    def aceitar_cookies(self, site_url: str):
        """
        Acessa a home do site para receber cookies de consentimento
        Importante para evitar pop-ups de cookies que podem interferir
        """
        try:
            response = self.session.get(f"https://{site_url}", timeout=10)
            if response.status_code == 200:
                logger.info(f"Cookies aceitos automaticamente de {site_url}")
        except Exception as e:
            logger.warning(f"Falha ao aceitar cookies de {site_url}: {e}")
    
    def configurar_sessao(self):
        """
        Configura a sessão HTTP com headers realistas
        Simula um navegador real para evitar detecção como bot
        """
        # Cookie padrão para aceitar políticas automaticamente
        self.session.cookies.set('OptanonAlertBoxClosed', '2024-01-01T00:00:00.000Z')
        
        # Headers que simulam navegador real
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',  # Do Not Track
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def rotacionar_user_agent(self):
        """
        Muda o User-Agent para parecer diferentes usuários
        Ajuda a evitar rate limiting e detecção
        """
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    def adicionar_headers_especificos(self, url: str):
        """
        Adiciona headers específicos para cada site
        Cada site pode ter suas próprias expectativas
        """
        if 'petlove.com.br' in url:
            self.session.headers.update({
                'Referer': 'https://www.petlove.com.br/',
                'Origin': 'https://www.petlove.com.br',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            })
        elif 'petz.com.br' in url:
            self.session.headers.update({
                'Referer': 'https://www.petz.com.br/',
                'Origin': 'https://www.petz.com.br',
                'X-Requested-With': 'XMLHttpRequest',
            })
        elif 'cobasi.com.br' in url:
            self.session.headers.update({
                'Referer': 'https://www.cobasi.com.br/',
                'Origin': 'https://www.cobasi.com.br',
            })
    
    def fazer_requisicao(self, url: str, max_tentativas: int = 3) -> Optional[requests.Response]:
        """
        Faz requisição HTTP com retry automático e proteções anti-bot
        
        Args:
            url: URL para fazer requisição
            max_tentativas: Número máximo de tentativas
            
        Returns:
            Response object ou None se falhou
        """
        for tentativa in range(max_tentativas):
            try:
                # Rotacionar User-Agent a cada tentativa (parecer usuários diferentes)
                self.rotacionar_user_agent()
                
                # Adicionar headers específicos do site
                self.adicionar_headers_especificos(url)
                
                # Delay progressivo entre tentativas
                if tentativa > 0:
                    delay = random.uniform(2, 5) + (tentativa * 2)
                    logger.info(f"Aguardando {delay:.2f}s antes da tentativa {tentativa + 1}")
                    time.sleep(delay)
                
                # Headers adicionais para simular navegação real
                self.session.headers.update({
                    "X-Forwarded-For": f"177.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache"
                })

                # Fazer a requisição
                response = self.session.get(url, timeout=15, allow_redirects=True)
                
                logger.info(f"Status {response.status_code} para {url}")
                
                # Verificar se foi bem-sucedida
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    logger.warning(f"403 Forbidden - Site pode estar bloqueando bots (tentativa {tentativa + 1})")
                elif response.status_code == 429:
                    logger.warning(f"429 Too Many Requests - Aguardando mais tempo")
                    time.sleep(random.uniform(10, 20))  # Pausa longa para rate limit
                    continue
                else:
                    logger.warning(f"Status code inesperado {response.status_code}")
                    
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout na requisição para {url}: {e}")
                continue
            except Exception as e:
                logger.error(f"Erro na requisição para {url}: {e}")
                if tentativa < max_tentativas - 1:
                    time.sleep(2 ** tentativa)  # Backoff exponencial
        
        logger.error(f"Todas as tentativas falharam para {url}")
        return None

# ==========================================
# MANIPULADOR DO SELENIUM
# ==========================================

class ManipuladorSelenium:
    """
    Gerencia navegador Chrome com Selenium
    Usado como fallback quando o método HTTP falha
    Mais lento mas consegue lidar com JavaScript complexo
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.inicializado = False
        
        # User Agents para o Selenium também
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
    def configurar_driver(self) -> bool:
        """
        Configura o Chrome com webdriver-manager
        Inicialização sob demanda - só cria quando necessário
        
        Returns:
            bool: True se configurou com sucesso
        """
        if self.inicializado:
            return True
            
        try:
            logger.info("Inicializando Selenium como fallback...")
            
            # Opções do Chrome para modo stealth
            chrome_options = Options()
            
            # ---- CONFIGURAÇÕES ANTI-DETECÇÃO ----
            chrome_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--ignore-ssl-errors")
            chrome_options.add_argument("--disable-web-security")
            
            # ---- CONFIGURAÇÕES DE PERFORMANCE ----
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")      # Não carregar imagens (mais rápido)
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-background-timer-throttling")
            
            # ---- CONFIGURAÇÕES DE JANELA ----
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            
            # Remover indicadores de automação
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # ---- INICIALIZAR DRIVER ----
            service = Service(ChromeDriverManager("140.0.7339").install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configurar timeout e scripts anti-detecção
            self.wait = WebDriverWait(self.driver, 10)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.inicializado = True
            logger.info("Selenium inicializado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar Selenium: {e}")
            return False
    
    def navegar_para_url(self, url: str, max_tentativas: int = 3) -> bool:
        """
        Navega para uma URL usando Selenium
        
        Args:
            url: URL de destino
            max_tentativas: Número de tentativas
            
        Returns:
            bool: True se navegou com sucesso
        """
        if not self.inicializado:
            if not self.configurar_driver():
                return False
        
        for tentativa in range(max_tentativas):
            try:
                logger.info(f"Navegando via Selenium para: {url} (Tentativa {tentativa + 1})")
                
                # Delay progressivo entre tentativas
                if tentativa > 0:
                    delay = random.uniform(2, 4) + (tentativa * 2)
                    logger.info(f"Aguardando {delay:.1f}s antes da próxima tentativa...")
                    time.sleep(delay)
                
                # Navegar para a URL
                self.driver.get(url)
                
                # Aguardar página carregar
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                logger.info("Navegação Selenium bem-sucedida!")
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout no Selenium - Tentativa {tentativa + 1}")
            except WebDriverException as e:
                logger.error(f"Erro do WebDriver: {e}")
            except Exception as e:
                logger.error(f"Erro inesperado no Selenium: {e}")
                
        logger.error(f"Selenium falhou para {url} após {max_tentativas} tentativas")
        return False
    
    def aceitar_cookies(self, url: str):
        """
        Tenta aceitar cookies automaticamente se aparecer pop-up
        """
        try:
            if not self.inicializado:
                return
                
            # Seletores comuns para botões de aceitar cookies
            seletores_cookies = [
                "//button[contains(text(), 'Aceitar')]",
                "//button[contains(text(), 'Aceito')]", 
                "//button[contains(text(), 'OK')]",
                "//a[contains(text(), 'Aceitar')]",
                "[data-testid='cookie-accept']",
                ".cookie-banner button",
            ]
            
            # Tentar cada seletor
            for seletor in seletores_cookies:
                try:
                    if seletor.startswith("//"):
                        elemento = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, seletor))
                        )
                    else:
                        elemento = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                        )
                    
                    elemento.click()
                    logger.info("Cookies aceitos via Selenium!")
                    time.sleep(1)
                    break
                    
                except TimeoutException:
                    continue  # Tentar próximo seletor
                    
        except Exception as e:
            logger.warning(f"Não foi possível aceitar cookies via Selenium: {e}")
    
    def obter_html(self) -> Optional[str]:
        """
        Obtém o HTML da página atual
        
        Returns:
            str: HTML da página ou None se erro
        """
        try:
            if self.driver:
                return self.driver.page_source
        except Exception as e:
            logger.error(f"Erro ao obter HTML do Selenium: {e}")
        return None
    
    def fechar_driver(self):
        """
        Fecha o navegador de forma segura
        """
        try:
            if self.driver and self.inicializado:
                # Opcional: pausar para debug
                # input("Pressione Enter para fechar o navegador...")
                self.driver.quit()
                logger.info("Selenium fechado com sucesso")
                self.inicializado = False
        except Exception as e:
            logger.error(f"Erro ao fechar Selenium: {e}")

# ==========================================
# GERENCIADOR DE DADOS DOS MEDICAMENTOS
# ==========================================

class GerenciadorDados:
    """
    Gerencia informações sobre medicamentos veterinários
    Base de conhecimento para categorizar produtos encontrados
    """
    
    def __init__(self):
        # Lista completa de medicamentos para buscar
        self.medicamentos = [
            "Simparic", "Revolution", "NexGard", "NexGard Spectra", "NexGard Combo", 
            "Bravecto", "Frontline", "Advocate", "Drontal", "Milbemax", "Vermivet",
            "Rimadyl", "Onsior", "Maxicam", "Carproflan", "Previcox",
            "Apoquel", "Zenrelia", "Synulox", "Baytril",
        ]
        
        # Base de conhecimento detalhada sobre cada medicamento
        self.info_medicamentos = {
            # ANTIPULGAS E CARRAPATOS
            "Simparic": InfoMedicamento("Zoetis", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "35 dias"),
            "Revolution": InfoMedicamento("Zoetis", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "NexGard": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "30 dias"),
            "NexGard Spectra": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "30 dias"),
            "NexGard Combo": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Gatos", "Todos os portes", "30 dias"),
            "Bravecto": InfoMedicamento("MSD Saúde Animal", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "90 dias"),
            "Frontline": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "Advocate": InfoMedicamento("Elanco", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            
            # VERMÍFUGOS
            "Drontal": InfoMedicamento("Elanco", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Milbemax": InfoMedicamento("Elanco", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Vermivet": InfoMedicamento("Agener União Química", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            
            # ANTI-INFLAMATÓRIOS
            "Rimadyl": InfoMedicamento("Zoetis", "Anti-inflamatório", "Cães", "Todos os portes", "12-24 horas"),
            "Onsior": InfoMedicamento("Elanco", "Anti-inflamatório", "Cães e Gatos", "Todos os portes", "24 horas"),
            "Maxicam": InfoMedicamento("Ourofino Saúde Animal", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Carproflan": InfoMedicamento("Agener União Química", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Previcox": InfoMedicamento("Boehringer Ingelheim", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            
            # DERMATOLÓGICOS/ANTIALÉRGICOS
            "Apoquel": InfoMedicamento("Zoetis", "Dermatológico / Antialérgico", "Cães", "Todos os portes", "12 horas"),
            "Zenrelia": InfoMedicamento("Elanco", "Dermatológico / Antialérgico", "Cães", "Todos os portes", "24 horas"),
            
            # ANTIBIÓTICOS
            "Synulox": InfoMedicamento("Zoetis", "Antibiótico", "Cães e Gatos", "Todos os portes", "12 horas"),
            "Baytril": InfoMedicamento("Elanco", "Antibiótico", "Cães e Gatos", "Todos os portes", "24 horas"),
        }
    
    def obter_info_medicamento(self, medicamento: str) -> InfoMedicamento:
        """
        Retorna informações de um medicamento específico
        """
        return self.info_medicamentos.get(
            medicamento, 
            InfoMedicamento("N/A", "N/A", "N/A", "N/A", "N/A")
        )
    
    def obter_lista_medicamentos(self) -> List[str]:
        """
        Retorna lista completa de medicamentos para buscar
        """
        return self.medicamentos

# ==========================================
# GERENCIADOR DE ARQUIVOS
# ==========================================

class GerenciadorArquivos:
    """
    Responsável por salvar dados coletados em arquivos Excel
    """
    
    @staticmethod
    def salvar_excel(dados: List[Dict], nome_arquivo: str) -> bool:
        """
        Salva dados em arquivo Excel com tratamento de erros
        
        Args:
            dados: Lista de dicionários com dados dos produtos
            nome_arquivo: Nome do arquivo Excel
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            if not dados:
                logger.warning(f"Nenhum dado para salvar em {nome_arquivo}")
                return False
                
            # Converter para DataFrame do pandas
            df = pd.DataFrame(dados)
            
            # Determinar pasta baseado no modo
            global test_mode
            pasta = 'dados_teste' if test_mode else 'dados_coletados'
            
            # Criar pasta se não existir
            os.makedirs(pasta, exist_ok=True)
            
            # Caminho completo
            caminho_completo = os.path.join(pasta, nome_arquivo)
            
            # Salvar Excel
            df.to_excel(caminho_completo, index=False, engine='openpyxl')
            logger.info(f"Dados salvos: {caminho_completo} ({len(dados)} produtos)")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar {nome_arquivo}: {e}")
            return False

# ==========================================
# CLASSE BASE PARA SCRAPERS HÍBRIDOS
# ==========================================

class ScraperHibridoBase(ABC):
    """
    Classe abstrata que define scraper híbrido
    Combina BeautifulSoup (primário) + Selenium (fallback)
    """
    
    def __init__(self, request_handler: ManipuladorRequests, selenium_handler: ManipuladorSelenium, 
                 data_manager: GerenciadorDados, test_mode: bool = False):
        self.request_handler = request_handler
        self.selenium_handler = selenium_handler
        self.data_manager = data_manager
        self.test_mode = test_mode
    
    @property
    @abstractmethod
    def nome_site(self) -> str:
        """Nome do site"""
        pass
    
    @property
    @abstractmethod
    def url_site(self) -> str:
        """URL base do site"""
        pass
    
    @abstractmethod
    def extrair_com_beautifulsoup(self, soup: BeautifulSoup, medicamento: str) -> List[InfoProduto]:
        """
        Método de extração usando BeautifulSoup
        Deve ser implementado por cada site
        """
        pass
    
    @abstractmethod
    def extrair_com_selenium(self, html: str, medicamento: str) -> List[InfoProduto]:
        """
        Método de extração usando Selenium
        Deve ser implementado por cada site
        """
        pass
    
    def fazer_scraping_medicamento(self, medicamento: str) -> List[InfoProduto]:
        """
        Método híbrido: tenta BeautifulSoup primeiro, Selenium como fallback
        
        Args:
            medicamento: Nome do medicamento para buscar
            
        Returns:
            List[InfoProduto]: Lista de produtos encontrados
        """
        logger.info(f"Buscando {medicamento} em {self.nome_site} (método híbrido)...")
        produtos = []
        
        # Construir URL de busca
        url_busca = self._construir_url_busca(medicamento)
        
        # MÉTODO 1: Tentar com BeautifulSoup/requests (mais rápido)
        logger.info(f"Tentando método BeautifulSoup para {medicamento}")
        try:
            # Aceitar cookies via requests
            self.request_handler.aceitar_cookies(self.url_site)
            
            # Fazer requisição
            response = self.request_handler.fazer_requisicao(url_busca)
            
            if response and response.status_code == 200:
                # Parse com BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extrair produtos usando método específico do site
                produtos = self.extrair_com_beautifulsoup(soup, medicamento)
                
                if produtos:
                    # Marcar método usado
                    for produto in produtos:
                        produto.metodo = "beautifulsoup"
                    logger.info(f"BeautifulSoup bem-sucedido: {len(produtos)} produtos para {medicamento}")
                    return produtos
                else:
                    logger.warning(f"BeautifulSoup não encontrou produtos para {medicamento}")
            else:
                logger.warning(f"Requisição falhou com status: {response.status_code if response else 'None'}")
                
        except Exception as e:
            logger.error(f"Erro no método BeautifulSoup para {medicamento}: {e}")
        
        # MÉTODO 2: Fallback para Selenium (mais lento mas mais robusto)
        logger.info(f"Usando Selenium como fallback para {medicamento}")
        try:
            # Navegar com Selenium
            if self.selenium_handler.navegar_para_url(url_busca):
                # Aceitar cookies via Selenium
                self.selenium_handler.aceitar_cookies(url_busca)
                
                # Aguardar carregamento
                time.sleep(3)
                
                # Obter HTML renderizado
                html = self.selenium_handler.obter_html()
                
                if html:
                    # Extrair produtos usando método específico do site
                    produtos = self.extrair_com_selenium(html, medicamento)
                    
                    # Marcar método usado
                    for produto in produtos:
                        produto.metodo = "selenium_fallback"
                    
                    logger.info(f"Selenium bem-sucedido: {len(produtos)} produtos para {medicamento}")
                    return produtos
                else:
                    logger.error(f"Selenium não conseguiu obter HTML para {medicamento}")
            else:
                logger.error(f"Selenium não conseguiu navegar para {url_busca}")
                
        except Exception as e:
            logger.error(f"Erro no método Selenium para {medicamento}: {e}")
        
        # Se ambos os métodos falharam
        logger.error(f"Ambos os métodos falharam para {medicamento} em {self.nome_site}")
        return produtos
    
    def _construir_url_busca(self, medicamento: str) -> str:
        """
        Constrói URL de busca específica para cada site
        Deve ser sobrescrita por cada implementação
        """
        return f"https://{self.url_site}/busca?q={medicamento}"
    
    def fazer_scraping_completo(self) -> List[Dict]:
        """
        Executa scraping de todos os medicamentos do site
        
        Returns:
            List[Dict]: Lista com dados de todos os produtos encontrados
        """
        logger.info(f"Iniciando scraping completo híbrido para {self.nome_site}...")
        produtos_coletados = []
        
        medicamentos = self.data_manager.obter_lista_medicamentos()
        total_medicamentos = len(medicamentos)
        
        # Processar cada medicamento
        for indice, medicamento in enumerate(medicamentos):
            try:
                logger.info(f"Processando {medicamento} ({indice + 1}/{total_medicamentos})")
                
                # Fazer scraping híbrido do medicamento
                produtos = self.fazer_scraping_medicamento(medicamento)
                
                # Converter para dicionário e adicionar à lista
                produtos_dict = [asdict(produto) for produto in produtos]
                produtos_coletados.extend(produtos_dict)
                
                logger.info(f"Encontrados {len(produtos)} produtos para {medicamento}")
                
                # Pausa entre medicamentos para não sobrecarregar
                if indice < total_medicamentos - 1:
                    delay = random.uniform(1, 3)
                    logger.info(f"Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Erro ao processar {medicamento} no {self.nome_site}: {e}")
                continue
        
        logger.info(f"{self.nome_site}: {len(produtos_coletados)} produtos coletados no total")
        return produtos_coletados

# ==========================================
# SCRAPER HÍBRIDO ESPECÍFICO - COBASI
# ==========================================

class ScraperHibridoCobasi(ScraperHibridoBase):
    """
    Scraper híbrido específico para Cobasi
    Usa JSON quando possível, HTML como fallback
    """
    
    @property
    def nome_site(self) -> str:
        return "Cobasi"
    
    @property
    def url_site(self) -> str:
        return "cobasi.com.br"
    
    def _construir_url_busca(self, medicamento: str) -> str:
        """Constrói URL de busca específica da Cobasi"""
        return f"https://www.cobasi.com.br/pesquisa?terms={medicamento}"
    
    def extrair_com_beautifulsoup(self, soup: BeautifulSoup, medicamento: str) -> List[InfoProduto]:
        """
        Extração de produtos da Cobasi usando BeautifulSoup
        Prioriza dados JSON do Next.js quando disponível
        """
        produtos = []
        
        try:
            # MÉTODO 1: Tentar extrair do JSON Next.js (mais confiável)
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            
            if script_tag:
                logger.info(f"Encontrado script JSON para {medicamento} na Cobasi")
                try:
                    produtos = self._extrair_do_json_cobasi(script_tag, medicamento)
                    if produtos:
                        return produtos
                except Exception as e:
                    logger.warning(f"Falha na extração JSON da Cobasi: {e}")
            
            # MÉTODO 2: Fallback para HTML
            logger.info(f"Usando método HTML para {medicamento} na Cobasi")
            produtos = self._extrair_do_html_cobasi(soup, medicamento)
            
        except Exception as e:
            logger.error(f"Erro na extração BeautifulSoup da Cobasi: {e}")
        
        return produtos
    
    def extrair_com_selenium(self, html: str, medicamento: str) -> List[InfoProduto]:
        """
        Extração de produtos da Cobasi usando HTML do Selenium
        """
        produtos = []
        
        try:
            # Parse do HTML obtido pelo Selenium
            soup = BeautifulSoup(html, 'html.parser')
            
            # Usar mesmos métodos de extração
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            
            if script_tag:
                try:
                    produtos = self._extrair_do_json_cobasi(script_tag, medicamento)
                    if produtos:
                        return produtos
                except Exception as e:
                    logger.warning(f"Falha JSON Selenium Cobasi: {e}")
            
            # Fallback HTML
            produtos = self._extrair_do_html_cobasi(soup, medicamento)
            
        except Exception as e:
            logger.error(f"Erro na extração Selenium da Cobasi: {e}")
        
        return produtos
    
    def _extrair_do_json_cobasi(self, script_tag, medicamento: str) -> List[InfoProduto]:
        """
        Extrai dados de produtos do JSON da Cobasi
        """
        produtos = []
        
        try:
            # Parse do JSON
            dados = json.loads(script_tag.string)
            produtos_json = dados.get("props", {}).get("pageProps", {}).get("searchResult", {}).get("products", [])
            
            # Limitar produtos em modo teste
            if self.test_mode and produtos_json:
                produtos_json = produtos_json[:1]
                logger.info("Modo teste Cobasi: limitando a 1 produto")
            
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            # Processar cada produto
            for produto_json in produtos_json:
                try:
                    nome_produto = produto_json.get('name', 'N/A')
                    produto_id = produto_json.get('id', 'N/A')
                    preco_base = produto_json.get('price', 0)
                    skus = produto_json.get('skus', [])
                    
                    # Se não tem SKUs, criar produto único
                    if not skus:
                        produto = InfoProduto(
                            categoria=info_base.categoria,
                            marca=medicamento,
                            produto=nome_produto,
                            quantidade="N/A",
                            preco=f"R$ {preco_base:.2f}" if isinstance(preco_base, (int, float)) else str(preco_base),
                            site=self.url_site,
                            data_coleta=datetime.now().strftime("%Y-%m-%d"),
                            produto_id=str(produto_id)
                        )
                        produtos.append(produto)
                    else:
                        # Processar cada SKU (variação)
                        for sku in skus:
                            try:
                                quantidade = sku.get('name', 'N/A')
                                preco_sku = sku.get('price', 0)
                                preco_antigo = sku.get('oldPrice', 0)
                                disponibilidade = sku.get('available', 'UNKNOWN')
                                desconto_percent = sku.get('discountPercent', 0)
                                
                                # Só incluir produtos disponíveis
                                if disponibilidade != 'AVAILABLE':
                                    continue
                                
                                produto = InfoProduto(
                                    categoria=info_base.categoria,
                                    marca=medicamento,
                                    produto=nome_produto,
                                    quantidade=quantidade,
                                    preco=f"R$ {preco_sku:.2f}" if isinstance(preco_sku, (int, float)) else str(preco_sku),
                                    preco_antigo=f"R$ {preco_antigo:.2f}" if preco_antigo and isinstance(preco_antigo, (int, float)) else "N/A",
                                    desconto=f"{desconto_percent}%" if desconto_percent > 0 else "0%",
                                    disponibilidade=disponibilidade,
                                    site=self.url_site,
                                    produto_id=str(produto_id),
                                    sku_id=sku.get('sku', 'N/A'),
                                    data_coleta=datetime.now().strftime("%Y-%m-%d")
                                )
                                produtos.append(produto)
                                
                            except Exception as e:
                                logger.error(f"Erro ao processar SKU Cobasi: {e}")
                                continue
                                
                except Exception as e:
                    logger.error(f"Erro ao processar produto JSON Cobasi: {e}")
                    continue
        
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da Cobasi: {e}")
        except Exception as e:
            logger.error(f"Erro na extração JSON da Cobasi: {e}")
        
        return produtos
    
    def _extrair_do_html_cobasi(self, soup: BeautifulSoup, medicamento: str) -> List[InfoProduto]:
        """
        Método de fallback usando extração HTML da Cobasi
        """
        produtos = []
        
        try:
            # Buscar elementos de produto
            elementos_produto = soup.find_all('a', {'data-testid': 'product-item-v4'})
            
            # Limitar em modo teste
            if self.test_mode and elementos_produto:
                elementos_produto = elementos_produto[:1]
            
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            for elemento_produto in elementos_produto:
                try:
                    # Extrair nome
                    nome_elem = elemento_produto.find('h3', class_='body-text-sm')
                    nome = nome_elem.text.strip() if nome_elem else "N/A"
                    
                    # Extrair preço
                    preco_elem = elemento_produto.find('span', class_='card-price')
                    preco = preco_elem.text.strip() if preco_elem else "N/A"
                    
                    # Extrair URL
                    url = elemento_produto.get("href", "N/A")
                    
                    produto = InfoProduto(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome,
                        quantidade="N/A",
                        preco=preco,
                        site=self.url_site,
                        url=url,
                        data_coleta=datetime.now().strftime("%Y-%m-%d")
                    )
                    produtos.append(produto)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto HTML Cobasi: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro no método HTML Cobasi: {e}")
            
        return produtos

# ==========================================
# SCRAPER HÍBRIDO ESPECÍFICO - PETLOVE
# ==========================================

class ScraperHibridoPetlove(ScraperHibridoBase):
    """
    Scraper híbrido específico para Petlove
    Coleta dados básicos e busca variações quando possível
    """
    
    @property
    def nome_site(self) -> str:
        return "Petlove"
    
    @property
    def url_site(self) -> str:
        return "petlove.com.br"
    
    def _construir_url_busca(self, medicamento: str) -> str:
        """Constrói URL de busca específica da Petlove"""
        return f"https://www.petlove.com.br/busca?q={medicamento}"
    
    def extrair_com_beautifulsoup(self, soup: BeautifulSoup, medicamento: str) -> List[InfoProduto]:
        """
        Extração de produtos da Petlove usando BeautifulSoup
        """
        produtos = []
        
        try:
            # Buscar elementos de produto
            elementos_produto = soup.find_all('div', class_='list__item')
            
            # Limitar em modo teste
            if self.test_mode and elementos_produto:
                elementos_produto = elementos_produto[:1]
            
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            for elemento_produto in elementos_produto:
                try:
                    # Verificar se é um elemento Tag válido
                    if not isinstance(elemento_produto, Tag):
                        continue
                    
                    # Extrair dados básicos
                    nome_elem = elemento_produto.find('h2', class_='product-card__name')
                    nome = nome_elem.text.strip() if nome_elem else "N/A"
                    
                    preco_elem = (elemento_produto.find('p', class_='color-neutral-dark font-bold font-body-s') or 
                                 elemento_produto.find('p', {'data-testid': 'price'}))
                    preco = preco_elem.text.strip() if preco_elem else "N/A"
                    
                    # Extrair link do produto
                    link_elem = elemento_produto.find('a', {'itemprop': 'url'})
                    link_produto = None
                    if link_elem and isinstance(link_elem, Tag):
                        link_produto = link_elem.get('href')
                        if link_produto and not str(link_produto).startswith('http'):
                            link_produto = f"https://www.petlove.com.br{link_produto}"
                    
                    # Buscar variações (se possível via BeautifulSoup)
                    variacoes = []
                    if link_produto:
                        try:
                            variacoes = self._obter_variacoes_petlove(str(link_produto))
                        except Exception as e:
                            logger.warning(f"Erro ao buscar variações via BS4: {e}")
                    
                    # Se não conseguiu variações, usar dados básicos
                    if not variacoes:
                        variacoes = [{"quantidade": "N/A", "preco": preco}]
                    
                    # Criar produto para cada variação
                    for variacao in variacoes:
                        produto = InfoProduto(
                            categoria=info_base.categoria,
                            marca=medicamento,
                            produto=nome,
                            quantidade=variacao.get("quantidade", "N/A"),
                            preco=variacao.get("preco", preco),
                            url=str(link_produto) if link_produto else "N/A",
                            site=self.url_site,
                            data_coleta=datetime.now().strftime("%Y-%m-%d")
                        )
                        produtos.append(produto)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Petlove BS4: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro na extração BeautifulSoup da Petlove: {e}")
        
        return produtos
    
    def extrair_com_selenium(self, html: str, medicamento: str) -> List[InfoProduto]:
        """
        Extração de produtos da Petlove usando HTML do Selenium
        """
        produtos = []
        
        try:
            # Parse do HTML obtido pelo Selenium
            soup = BeautifulSoup(html, 'html.parser')
            
            # Usar mesmo método de extração
            produtos = self.extrair_com_beautifulsoup(soup, medicamento)
            
        except Exception as e:
            logger.error(f"Erro na extração Selenium da Petlove: {e}")
        
        return produtos
    
    def _obter_variacoes_petlove(self, url: str) -> List[Dict]:
        """
        Busca variações de quantidade na página do produto da Petlove
        """
        variacoes = []
        
        try:
            # Fazer requisição para página do produto
            response = self.request_handler.fazer_requisicao(url)
            if not response:
                return variacoes
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar variações no popup
            variations_popup = soup.find('div', class_='variant-list')
            
            if variations_popup and isinstance(variations_popup, Tag):
                variation_items = variations_popup.find_all('div', class_='badge__container variant-selector__badge')
                
                for item in variation_items:
                    try:
                        if not isinstance(item, Tag):
                            continue
                        
                        nome_elem = item.find('span', class_='font-bold mb-2')
                        quantidade = nome_elem.text.strip() if nome_elem else "Único"
                        
                        preco_elem = item.find('div', class_='font-body-s')
                        preco = preco_elem.text.strip() if preco_elem else "N/A"
                        
                        variacoes.append({"quantidade": quantidade, "preco": preco})
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar variação Petlove: {e}")
            
            # Fallback para botão selecionado
            if not variacoes:
                selected_button = soup.find('button', class_='size-select-button')
                if selected_button and isinstance(selected_button, Tag):
                    quantidade_elem = selected_button.find('b')
                    quantidade = quantidade_elem.text.strip() if quantidade_elem else "Único"
                    
                    price_elem = soup.find('span', class_='price-value') or soup.find('div', class_='price')
                    preco = price_elem.text.strip() if price_elem else "N/A"
                    
                    variacoes.append({"quantidade": quantidade, "preco": preco})
                    
        except Exception as e:
            logger.error(f"Erro ao buscar variações Petlove: {e}")
            
        return variacoes

# ==========================================
# SCRAPER HÍBRIDO ESPECÍFICO - PETZ
# ==========================================

class ScraperHibridoPetz(ScraperHibridoBase):
    """
    Scraper híbrido específico para Petz
    Extrai dados JSON quando disponível
    """
    
    @property
    def nome_site(self) -> str:
        return "Petz"
    
    @property
    def url_site(self) -> str:
        return "petz.com.br"
    
    def _construir_url_busca(self, medicamento: str) -> str:
        """Constrói URL de busca específica da Petz"""
        return f"https://www.petz.com.br/busca?q={medicamento}"
    
    def extrair_com_beautifulsoup(self, soup: BeautifulSoup, medicamento: str) -> List[InfoProduto]:
        """
        Extração de produtos da Petz usando BeautifulSoup
        """
        produtos = []
        
        try:
            # Buscar elementos de produto (usando diferentes seletores)
            elementos_produto = (soup.find_all('product-card') or 
                               soup.find_all('li', class_='card-product') or
                               soup.find_all('div', class_='product-card'))
            
            # Limitar em modo teste
            if self.test_mode and elementos_produto:
                elementos_produto = elementos_produto[:1]
            
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            for elemento_produto in elementos_produto:
                try:
                    # Método 1: Tentar extrair do atributo product-details (Web Component)
                    detalhes_produto = elemento_produto.get('product-details')
                    
                    if detalhes_produto:
                        produtos_do_json = self._extrair_do_json_petz(detalhes_produto, medicamento, info_base)
                        produtos.extend(produtos_do_json)
                    else:
                        # Método 2: Fallback para extração HTML tradicional
                        produto_html = self._extrair_do_html_petz(elemento_produto, medicamento, info_base)
                        if produto_html:
                            produtos.append(produto_html)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Petz BS4: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro na extração BeautifulSoup da Petz: {e}")
        
        return produtos
    
    def extrair_com_selenium(self, html: str, medicamento: str) -> List[InfoProduto]:
        """
        Extração de produtos da Petz usando HTML do Selenium
        """
        produtos = []
        
        try:
            # Parse do HTML obtido pelo Selenium
            soup = BeautifulSoup(html, 'html.parser')
            
            # Usar mesmo método de extração
            produtos = self.extrair_com_beautifulsoup(soup, medicamento)
            
        except Exception as e:
            logger.error(f"Erro na extração Selenium da Petz: {e}")
        
        return produtos
    
    def _extrair_do_json_petz(self, detalhes_produto: str, medicamento: str, info_base: InfoMedicamento) -> List[InfoProduto]:
        """
        Extrai dados do JSON product-details da Petz
        """
        produtos = []
        
        try:
            # Corrigir aspas simples se necessário
            elementos_meta = detalhes_produto.strip().replace("'", '"')
            
            # Parse do JSON
            produto_json = json.loads(elementos_meta)
            variacoes = produto_json.get('variations', [])
            
            # Se não tem variações, criar uma padrão
            if not variacoes:
                variacoes = [{
                    "name": produto_json.get('variationAbreviation', 'N/A'),
                    "price": produto_json.get('price', 'N/A'),
                    "promotionalPrice": produto_json.get('promotional_price', produto_json.get('price', 'N/A')),
                    "discountPercentage": produto_json.get('discountPercentage', 0),
                    "sku": produto_json.get('sku', 'N/A'),
                    "availability": produto_json.get('availability', 'UNKNOWN'),
                    "id": produto_json.get('id', 'N/A'),
                }]
            
            # Processar cada variação
            for variacao in variacoes:
                try:
                    quantidade = variacao.get('name', 'N/A')
                    preco = variacao.get('price', 'N/A')
                    promotional_price = variacao.get('promotionalPrice', preco)
                    discount_percentage = variacao.get('discountPercentage', 0)
                    availability = produto_json.get('availability', 'UNKNOWN')
                    produto_id = produto_json.get('id', 'N/A')
                    sku = variacao.get('sku', 'N/A')
                    
                    produto = InfoProduto(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=produto_json.get('name', 'N/A'),
                        quantidade=quantidade,
                        preco=f"R$ {promotional_price}" if promotional_price != 'N/A' else 'N/A',
                        preco_antigo=f"R$ {preco}" if preco != promotional_price and preco != 'N/A' else "N/A",
                        desconto=f"{discount_percentage}%" if discount_percentage else "0%",
                        disponibilidade=availability,
                        site=self.url_site,
                        produto_id=str(produto_id),
                        sku_id=str(sku),
                        url=produto_json.get('url', 'N/A'),
                        data_coleta=datetime.now().strftime("%Y-%m-%d")
                    )
                    produtos.append(produto)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar variação Petz JSON: {e}")
                    continue
                    
        except json.JSONDecodeError as e:
            logger.error(f"Falha ao decodificar JSON da Petz: {e}")
        except Exception as e:
            logger.error(f"Erro na extração JSON da Petz: {e}")
            
        return produtos
    
    def _extrair_do_html_petz(self, elemento_produto, medicamento: str, info_base: InfoMedicamento) -> Optional[InfoProduto]:
        """
        Fallback para extração HTML tradicional da Petz
        """
        try:
            # Extrair URL do produto
            meta_url = elemento_produto.find('meta', itemprop="url")
            link_produto = meta_url.get('content') if meta_url else "N/A"
            
            # Extrair nome (vários seletores possíveis)
            nome_elem = (elemento_produto.find('h3', class_='product-name') or 
                        elemento_produto.find('h2', class_='product-title') or
                        elemento_produto.find('a', class_='product-link'))
            nome = nome_elem.text.strip() if nome_elem else "N/A"
            
            # Extrair preço (vários seletores possíveis)
            preco_elem = (elemento_produto.find('span', class_='price') or
                         elemento_produto.find('div', class_='preco') or
                         elemento_produto.find('span', class_='valor'))
            preco = preco_elem.text.strip() if preco_elem else "N/A"
            
            return InfoProduto(
                categoria=info_base.categoria,
                marca=medicamento,
                produto=nome,
                quantidade="N/A",
                preco=preco,
                site=self.url_site,
                url=str(link_produto) if link_produto != "N/A" else "N/A",
                data_coleta=datetime.now().strftime("%Y-%m-%d")
            )
            
        except Exception as e:
            logger.error(f"Erro na extração HTML Petz: {e}")
            return None

# ==========================================
# GERENCIADOR PRINCIPAL HÍBRIDO
# ==========================================

class GerenciadorScraperHibrido:
    """
    Classe gerenciadora principal que coordena todos os scrapers híbridos
    Combina eficiência do BeautifulSoup com robustez do Selenium
    """
    
    def __init__(self, test_mode: bool = False):
        """
        Inicializa o gerenciador híbrido
        
        Args:
            test_mode: Se True, executa em modo teste (mais rápido, menos dados)
        """
        self.test_mode = test_mode
        
        # Definir variável global
        # global test_mode as global_test_mode
        global_test_mode = self.test_mode
        
        # Inicializar componentes
        self.request_handler = ManipuladorRequests()
        self.selenium_handler = ManipuladorSelenium()  # Inicialização lazy
        self.data_manager = GerenciadorDados()
        self.file_manager = GerenciadorArquivos()
        
        # Inicializar scrapers híbridos
        self.scrapers = [
            ScraperHibridoCobasi(self.request_handler, self.selenium_handler, self.data_manager, test_mode),
            ScraperHibridoPetlove(self.request_handler, self.selenium_handler, self.data_manager, test_mode),
            ScraperHibridoPetz(self.request_handler, self.selenium_handler, self.data_manager, test_mode)
        ]
        
        logger.info(f"Gerenciador híbrido inicializado - Modo: {'TESTE' if test_mode else 'COMPLETO'}")
    
    def executar_scraper(self, scraper: ScraperHibridoBase) -> bool:
        """
        Executa um scraper híbrido específico
        
        Args:
            scraper: Instância do scraper para executar
            
        Returns:
            bool: True se executou e salvou com sucesso
        """
        try:
            logger.info(f"Iniciando scraping híbrido para {scraper.nome_site}...")
            
            # Executar scraping de todos os medicamentos
            dados = scraper.fazer_scraping_completo()
            
            # Gerar nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{scraper.nome_site.lower()}_hibrido_{timestamp}.xlsx"
            
            # Salvar dados no Excel
            sucesso = self.file_manager.salvar_excel(dados, nome_arquivo)
            
            if sucesso:
                logger.info(f"{scraper.nome_site}: {len(dados)} produtos salvos em {nome_arquivo}")
                
                # Estatísticas dos métodos usados
                metodos = {}
                for item in dados:
                    metodo = item.get('metodo', 'unknown')
                    metodos[metodo] = metodos.get(metodo, 0) + 1
                
                logger.info(f"Métodos utilizados no {scraper.nome_site}: {metodos}")
            else:
                logger.error(f"Falha ao salvar dados do {scraper.nome_site}")
                
            return sucesso
            
        except Exception as e:
            logger.error(f"Erro no scraping híbrido {scraper.nome_site}: {e}")
            return False
    
    def executar_todos(self):
        """
        Executa todos os scrapers híbridos disponíveis sequencialmente
        """
        logger.info("=" * 70)
        logger.info(f"INICIANDO SCRAPING HÍBRIDO COMPLETO - Modo: {'TESTE' if self.test_mode else 'COMPLETO'}")
        logger.info("Método: BeautifulSoup (primário) + Selenium (fallback)")
        logger.info("=" * 70)
        
        total_sucesso = 0
        total_scrapers = len(self.scrapers)
        metodos_globais = {"beautifulsoup": 0, "selenium_fallback": 0}
        
        # Executar cada scraper sequencialmente
        for indice, scraper in enumerate(self.scrapers):
            logger.info(f"\n>>> Processando site {indice + 1}/{total_scrapers}: {scraper.nome_site}")
            
            sucesso = self.executar_scraper(scraper)
            if sucesso:
                total_sucesso += 1
                
            # Pausa entre sites para não sobrecarregar
            if indice < total_scrapers - 1:  # Não pausar após o último
                delay = random.uniform(2, 4)
                logger.info(f"Aguardando {delay:.1f}s antes do próximo site...")
                time.sleep(delay)
        
        # Fechar Selenium se foi inicializado
        if self.selenium_handler.inicializado:
            self.selenium_handler.fechar_driver()
        
        # Relatório final
        logger.info("=" * 70)
        logger.info("SCRAPING HÍBRIDO FINALIZADO!")
        logger.info(f"Sites processados com sucesso: {total_sucesso}/{total_scrapers}")
        
        if total_sucesso > 0:
            pasta = 'dados_teste' if self.test_mode else 'dados_coletados'
            logger.info(f"Arquivos Excel salvos na pasta: {pasta}/")
            logger.info("Cada arquivo contém informações sobre qual método foi usado para cada produto")
        
        logger.info("=" * 70)
    
    def executar_site_especifico(self, nome_site: str):
        """
        Executa scraping híbrido de um site específico
        
        Args:
            nome_site: Nome do site para fazer scraping
        """
        # Buscar scraper do site especificado
        scraper = None
        for s in self.scrapers:
            if s.nome_site.lower() == nome_site.lower():
                scraper = s
                break
        
        if scraper:
            logger.info(f"Executando scraping híbrido específico para {nome_site}")
            sucesso = self.executar_scraper(scraper)
            
            if sucesso:
                pasta = 'dados_teste' if self.test_mode else 'dados_coletados'
                logger.info(f"Arquivo salvo na pasta: {pasta}/")
        else:
            sites_disponiveis = [s.nome_site for s in self.scrapers]
            logger.error(f"Site '{nome_site}' não encontrado.")
            logger.info(f"Sites disponíveis: {', '.join(sites_disponiveis)}")
        
        # Fechar Selenium se foi inicializado
        if self.selenium_handler.inicializado:
            self.selenium_handler.fechar_driver()

# ==========================================
# FUNÇÃO PRINCIPAL
# ==========================================

def main():
    """
    Função principal do programa - interface híbrida com o usuário
    """
    print("\n" + "=" * 80)
    print("SCRAPER HÍBRIDO DE MEDICAMENTOS VETERINÁRIOS")
    print("BeautifulSoup (Rápido) + Selenium (Robusto)")
    print("=" * 80)
    print("\nEste programa coleta preços de medicamentos veterinários")
    print("dos principais pet shops online do Brasil usando método híbrido:")
    print("\n• MÉTODO PRIMÁRIO: BeautifulSoup/Requests (mais rápido)")
    print("• MÉTODO FALLBACK: Selenium (quando BeautifulSoup falha)")
    print("\nSites suportados:")
    print("• Cobasi (cobasi.com.br)")
    print("• Petlove (petlove.com.br)")
    print("• Petz (petz.com.br)")
    
    print("\n" + "-" * 50)
    print("MODOS DE EXECUÇÃO:")
    print("-" * 50)
    print("1 - MODO TESTE")
    print("    • Coleta apenas 1 produto por medicamento")
    print("    • Mais rápido para verificar funcionamento")
    print("    • Ideal para testes e desenvolvimento")
    print("    • Mostra qual método foi usado para cada produto")
    
    print("\n2 - MODO COMPLETO")
    print("    • Coleta todos os produtos encontrados")
    print("    • Processo mais demorado e completo")
    print("    • Recomendado para coleta de dados real")
    print("    • Relatório detalhado dos métodos utilizados")
    
    print("\n3 - SITE ESPECÍFICO")
    print("    • Executa scraping híbrido em apenas um site")
    print("    • Útil para testes ou coleta direcionada")
    print("    • Permite análise detalhada de um site específico")
    
    # Obter escolha do usuário
    while True:
        try:
            escolha = input("\nDigite sua escolha (1, 2 ou 3): ").strip()
            if escolha in ['1', '2', '3']:
                break
            else:
                print("❌ Escolha inválida. Digite 1, 2 ou 3.")
        except KeyboardInterrupt:
            print("\n\n>>> Execução cancelada pelo usuário.")
            return
    
    try:
        if escolha == "3":
            # Modo site específico
            print("\n" + "-" * 30)
            print("SITES DISPONÍVEIS:")
            print("-" * 30)
            print("• Cobasi")
            print("• Petlove") 
            print("• Petz")

            while True:
                site_escolhido = input("\nDigite o nome do site: ").strip()
                if site_escolhido.lower() in ['cobasi', 'petlove', 'petz']:
                    break
                else:
                    print("❌ Site inválido. Digite: Cobasi, Petlove ou Petz")
            
            print(f"\n>>> Executando scraping híbrido para {site_escolhido.title()}...")
            print(">>> Tentará BeautifulSoup primeiro, Selenium se necessário...")
            print(">>> Aguarde o processamento...")
            
            # Executar scraping híbrido específico
            manager = GerenciadorScraperHibrido(test_mode=False)
            manager.executar_site_especifico(site_escolhido)

        else:
            # Modo teste ou completo
            test_mode = (escolha == "1")
            
            if test_mode:
                print("\n>>> MODO TESTE SELECIONADO")
                print(">>> Será coletado apenas 1 produto por medicamento")
                print(">>> Processo mais rápido para verificação")
                print(">>> Você verá qual método foi usado para cada produto")
            else:
                print("\n>>> MODO COMPLETO SELECIONADO")
                print(">>> Todos os produtos serão coletados")
                print(">>> Processo pode demorar vários minutos")
                print(">>> Relatório completo dos métodos utilizados")
            
            print("\n>>> Inicializando sistema híbrido...")
            print(">>> BeautifulSoup será tentado primeiro (mais rápido)")
            print(">>> Selenium será usado automaticamente se necessário")
            print(">>> Aguarde o processamento...")
            
            # Executar scraping híbrido completo
            manager = GerenciadorScraperHibrido(test_mode=test_mode)
            manager.executar_todos()
        
        print(f"\n{'='*60}")
        print("✅ PROCESSO HÍBRIDO FINALIZADO COM SUCESSO!")
        print(f"{'='*60}")
        
        # Mostrar localização dos arquivos
        folder = 'dados_teste' if (escolha == "1") else 'dados_coletados'
        print(f"\n📁 Arquivos Excel salvos em: ./{folder}/")
        print("📊 Cada arquivo contém uma coluna 'metodo' mostrando:")
        print("    • 'beautifulsoup' = dados coletados via HTTP/BS4")
        print("    • 'selenium_fallback' = dados coletados via Selenium")
        print("📈 Você pode analisar a eficiência de cada método")
        
    except KeyboardInterrupt:
        print("\n\n>>> Execução cancelada pelo usuário.")
    except Exception as e:
        logger.error(f"Erro durante execução: {e}")
        print(f"\n❌ Erro durante execução: {e}")
        print("📋 Verifique os logs para mais detalhes.")
    
    # Aguardar antes de fechar
    input("\nPressione Enter para sair...")

# ==========================================
# UTILITÁRIOS EXTRAS
# ==========================================

def analisar_eficiencia_metodos(pasta_dados: str = "dados_coletados"):
    """
    Função utilitária para analisar a eficiência dos métodos híbridos
    Pode ser chamada separadamente para analisar dados já coletados
    """
    try:
        arquivos_excel = [f for f in os.listdir(pasta_dados) if f.endswith('.xlsx')]
        
        if not arquivos_excel:
            print("Nenhum arquivo Excel encontrado para análise")
            return
        
        print("\n" + "=" * 60)
        print("ANÁLISE DE EFICIÊNCIA DOS MÉTODOS HÍBRIDOS")
        print("=" * 60)
        
        for arquivo in arquivos_excel:
            try:
                caminho = os.path.join(pasta_dados, arquivo)
                df = pd.read_excel(caminho)
                
                if 'metodo' in df.columns:
                    site = arquivo.split('_')[0].title()
                    metodos = df['metodo'].value_counts()
                    total = len(df)
                    
                    print(f"\n📊 {site}:")
                    print(f"   Total de produtos: {total}")
                    
                    for metodo, count in metodos.items():
                        porcentagem = (count / total) * 100
                        print(f"   {metodo}: {count} ({porcentagem:.1f}%)")
                        
                else:
                    print(f"⚠️  Arquivo {arquivo} não contém coluna 'metodo'")
                    
            except Exception as e:
                print(f"❌ Erro ao analisar {arquivo}: {e}")
                
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")

# Verificação se o arquivo está sendo executado diretamente
if __name__ == "__main__":
    # Verificar dependências antes de executar
    main()