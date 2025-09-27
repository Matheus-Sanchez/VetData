import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import Tag
import pandas as pd
from datetime import datetime
import time
import random
import re
import os
import json
from typing import Dict, List, Optional, Protocol
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict


# Selenium e WebDriver Manager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

# WebDriver Manager - automatiza download do ChromeDriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

test_mode = False  # Variável global para modo de teste

@dataclass
class MedicamentoInfo:
    """Classe de dados para informações do medicamento"""
    empresa: str
    categoria: str
    animal: str
    porte: str
    eficacia: str

@dataclass
class ProdutoInfo:
    """Classe de dados para informações do produto"""
    categoria: str
    marca: str
    produto: str
    quantidade: str
    preco: str
    site: str
    data_coleta: str
    preco_antigo: Optional[str] = None
    desconto: Optional[str] = None
    disponibilidade: Optional[str] = None
    produto_id: Optional[str] = None
    sku_id: Optional[str] = None
    url: Optional[str] = None
    metodo: Optional[str] = None

# ==========================================
# MANIPULADOR DO SELENIUM
# ==========================================

class ManipuladorSelenium:
    """
    Gerencia o navegador Chrome com proteções anti-bot
    e configurações otimizadas para web scraping
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Lista de User Agents para rotacionar e parecer mais humano
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
    def configurar_driver(self) -> bool:
        """
        Configura o Chrome com webdriver-manager e opções anti-detecção
        
        Returns:
            bool: True se configurou com sucesso, False caso contrário
        """
        try:
            logger.info("Configurando Chrome com webdriver-manager...")
            
            # Opções do Chrome para evitar detecção como bot
            chrome_options = Options()
            
            # ---- CONFIGURAÇÕES ANTI-DETECÇÃO ----
            # User Agent aleatório para parecer navegação humana
            chrome_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
            
            # Desabilitar recursos que indicam automação
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--ignore-ssl-errors")
            chrome_options.add_argument("--disable-web-security")

            # Modo estável contra interferência
            chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")

            # Mantém perfil temporário (não pega cookies antigos que o antivírus pode escanear)
            # chrome_options.add_argument("--incognito")
            chrome_options.add_argument("--profile-directory=Default")


            # chrome_options.add_argument("--headless=new")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # ---- CONFIGURAÇÕES DE PERFORMANCE ----
            # Desabilitar recursos desnecessários para acelerar
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")      # Não carregar imagens
            chrome_options.add_argument("--disable-javascript")  # Desabilitar JS quando possível
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            
            # ---- CONFIGURAÇÕES DE JANELA ----
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            

            
            # ---- INICIALIZAR DRIVER COM WEBDRIVER-MANAGER ----
            # O webdriver-manager baixa automaticamente o ChromeDriver correto
            service = Service(ChromeDriverManager("140.0.7339").install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configurar timeout padrão para esperas
            self.wait = WebDriverWait(self.driver, 10)
            
            # Script para esconder que é automação
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome configurado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar Chrome: {e}")
            return False
    
    def navegar_para_url(self, url: str, max_tentativas: int = 3) -> bool:
        for tentativa in range(max_tentativas):
            try:
                logger.info(f"Navegando para: {url} (Tentativa {tentativa + 1})")
                
                # Delay progressivo entre tentativas
                if tentativa > 0:
                    delay = random.uniform(1, 3) + (tentativa * 2)
                    logger.info(f"Aguardando {delay:.1f}s antes da próxima tentativa...")
                    time.sleep(delay)
                
                # Navegar para a URL
                self.driver.get(url)
                
                # Aguardar página carregar completamente
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # Simular comportamento humano com scroll
                # self.scroll_humano()
                
                logger.info("Navegação bem-sucedida!")
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout ao carregar página - Tentativa {tentativa + 1}")
            except WebDriverException as e:
                logger.error(f"Erro do navegador: {e}")
            except Exception as e:
                logger.error(f"Erro inesperado: {e}")
                
        logger.error(f"Falha ao navegar para {url} após {max_tentativas} tentativas")
        return False
    
    # def scroll_humano(self):
    #     """
    #     Simula scroll humano na página para parecer navegação natural
    #     """
    #     try:
    #         # Scroll gradual para baixo
    #         self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
    #         time.sleep(random.uniform(0.5, 1.0))
            
    #         # Scroll para o meio da página
    #         self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    #         time.sleep(random.uniform(0.5, 1.0))
            
    #         # Voltar para o topo
    #         self.driver.execute_script("window.scrollTo(0, 0);")
    #         time.sleep(random.uniform(0.3, 0.8))
            
    #     except Exception as e:
    #         logger.warning(f"Erro no scroll simulado: {e}")
    
    def aceitar_cookies(self, url: str):
        """
        Tenta automaticamente aceitar cookies se aparecer pop-up
        
        Args:
            url: URL do site para tentar aceitar cookies
        """
        try:
            # Ir para página principal primeiro
            self.driver.get(url)
            time.sleep(2)
            
            # Lista de seletores comuns para botões de aceitar cookies
            seletores_cookies = [
                "//button[contains(text(), 'Aceitar')]",
                "//button[contains(text(), 'Aceito')]", 
                "//button[contains(text(), 'OK')]",
                "//button[contains(text(), 'Concordo')]",
                "//a[contains(text(), 'Aceitar')]",
                "[data-testid='cookie-accept']",
                "[id*='cookie'][id*='accept']",
                "[class*='cookie'][class*='accept']",
                ".cookie-banner button",
                "#cookieConsent button"
            ]
            
            # Tentar cada seletor até encontrar o botão de cookies
            for seletor in seletores_cookies:
                try:
                    if seletor.startswith("//"):
                        # XPath
                        elemento = self.wait.until(EC.element_to_be_clickable((By.XPATH, seletor)))
                    else:
                        # CSS Selector
                        elemento = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                    
                    elemento.click()
                    logger.info("Cookies aceitos automaticamente!")
                    time.sleep(1)
                    break
                    
                except TimeoutException:
                    continue  # Tentar próximo seletor
                    
        except Exception as e:
            logger.warning(f"Não foi possível aceitar cookies automaticamente: {e}")
    
    def aguardar_elemento(self, by: By, valor: str, timeout: int = 10):
        """
        Aguarda um elemento aparecer na página
        
        Args:
            by: Tipo de seletor (By.ID, By.CLASS_NAME, etc.)
            valor: Valor do seletor
            timeout: Tempo limite em segundos
            
        Returns:
            WebElement ou None se não encontrou
        """
        try:
            if self.driver is None:
                logger.error("Driver Selenium não inicializado.")
                return None
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, valor))
            )
        except TimeoutException:
            return None
    
    def encontrar_elementos_seguro(self, by: By, valor: str) -> List:
        """
        Busca elementos de forma segura sem gerar exceção
        
        Args:
            by: Tipo de seletor
            valor: Valor do seletor
            
        Returns:
            Lista de elementos (vazia se não encontrou)
        """
        try:
            return self.driver.find_elements(by, valor)
        except NoSuchElementException:
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar elementos: {e}")
            return []
    
    def obter_texto_seguro(self, elemento) -> str:
        """
        Obtém texto de um elemento de forma segura
        
        Args:
            elemento: WebElement
            
        Returns:
            str: Texto do elemento ou "N/A" se erro
        """
        try:
            return elemento.text.strip() if elemento and elemento.text else "N/A"
        except Exception:
            return "N/A"
    
    def obter_atributo_seguro(self, elemento, atributo: str) -> str:
        """
        Obtém atributo de um elemento de forma segura
        
        Args:
            elemento: WebElement
            atributo: Nome do atributo
            
        Returns:
            str: Valor do atributo ou "N/A" se erro
        """
        try:
            return elemento.get_attribute(atributo) if elemento else "N/A"
        except Exception:
            return "N/A"
    
    def fechar_driver(self):
        """
        Fecha o navegador de forma segura
        """
        try:
            if self.driver:
                input("Pressione Enter para fechar o navegador...")
                self.driver.quit()
                logger.info("Navegador fechado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao fechar navegador: {e}")


class RequestHandler:
    """Classe responsável por fazer requisições HTTP com proteções anti-bot"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Lista de User-Agents realistas
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
        ]
        
        self.setup_session()
    
    def accept_cookies(self, site_url: str):
        """Acessa a home do site para receber cookies de consentimento"""
        try:
            response = self.session.get(f"https://{site_url}", timeout=10)
            if response.status_code == 200:
                logger.info(f"Cookies aceitos automaticamente de {site_url}")
        except Exception as e:
            logger.warning(f"Falha ao aceitar cookies de {site_url}: {e}")
    
    def setup_session(self):
        """Configura a sessão com headers realistas"""
        self.session.cookies.set('OptanonAlertBoxClosed', '2024-01-01T00:00:00.000Z')
        
        # Headers mais realistas
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def rotate_user_agent(self):
        """Rotaciona o User-Agent"""
        self.session.headers['User-Agent'] = random.choice(self.user_agents)
    
    
    def add_site_specific_headers(self, url: str):
        """Adiciona headers específicos para cada site"""
        if 'petlove.com.br' in url:
            self.session.headers.update({
                'Referer': 'https://www.petlove.com.br/',
                'Origin': 'https://www.petlove.com.br',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
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
    
    def make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Faz requisição com retry e proteções anti-bot"""
        for attempt in range(max_retries):
            try:
                # Rotacionar User-Agent a cada tentativa
                self.rotate_user_agent()
                
                # Adicionar headers específicos do site
                self.add_site_specific_headers(url)
                
                # Delay aleatório entre requisições
                if attempt > 0:
                    delay = random.uniform(2, 5) + (attempt * 2)
                    logger.info(f"Aguardando {delay:.2f}s antes da tentativa {attempt + 1}")
                    time.sleep(delay)
                
                self.session.headers.update({
                    "X-Forwarded-For": f"177.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache"
                })

                # Fazer a requisição
                response = self.session.get(
                    url, 
                    timeout=15,
                    allow_redirects=True
                )
                
                logger.info(f"Status {response.status_code} para {url}")
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    logger.warning(f"403 Forbidden - Tentativa {attempt + 1}/{max_retries}")
                elif response.status_code == 429:
                    logger.warning(f"429 Too Many Requests - Aguardando mais tempo")
                    time.sleep(random.uniform(10, 20))
                    continue
                else:
                    logger.warning(f"Status code {response.status_code} para {url}")
                    
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout na requisição {url}: {e}")
                continue
            except Exception as e:
                logger.error(f"Erro na requisição {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
        
        return None

class DataManager:
    """Classe responsável por gerenciar dados dos medicamentos"""
    
    def __init__(self):
        self.medicamentos = [
            "Simparic", "Revolution", "NexGard", "NexGard Spectra", "NexGard Combo", 
            "Bravecto", "Frontline", "Advocate", "Drontal", "Milbemax", "Vermivet",
            "Rimadyl", "Onsior", "Maxicam", "Carproflan", "Previcox",
            "Apoquel", "Zenrelia", "Synulox", "Baytril",
        ]
        
        self.medicamento_info = {
            "Simparic": MedicamentoInfo("Zoetis", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "35 dias"),
            "Revolution": MedicamentoInfo("Zoetis", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "NexGard": MedicamentoInfo("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "30 dias"),
            "NexGard Spectra": MedicamentoInfo("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "30 dias"),
            "NexGard Combo": MedicamentoInfo("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Gatos", "Todos os portes", "30 dias"),
            "Bravecto": MedicamentoInfo("MSD Saúde Animal", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "90 dias"),
            "Frontline": MedicamentoInfo("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "Advocate": MedicamentoInfo("Elanco", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "Drontal": MedicamentoInfo("Elanco", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Milbemax": MedicamentoInfo("Elanco", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Vermivet": MedicamentoInfo("Agener União Química", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Rimadyl": MedicamentoInfo("Zoetis", "Anti-inflamatório", "Cães", "Todos os portes", "12-24 horas"),
            "Onsior": MedicamentoInfo("Elanco", "Anti-inflamatório", "Cães e Gatos", "Todos os portes", "24 horas"),
            "Maxicam": MedicamentoInfo("Ourofino Saúde Animal", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Carproflan": MedicamentoInfo("Agener União Química", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Previcox": MedicamentoInfo("Boehringer Ingelheim", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Apoquel": MedicamentoInfo("Zoetis", "Dermatológico / Antialergico", "Cães", "Todos os portes", "12 horas"),
            "Zenrelia": MedicamentoInfo("Elanco", "Dermatológico / Antialergico", "Cães", "Todos os portes", "24 horas"),
            "Synulox": MedicamentoInfo("Zoetis", "Antibiótico", "Cães e Gatos", "Todos os portes", "12 horas"),
            "Baytril": MedicamentoInfo("Elanco", "Antibiótico", "Cães e Gatos", "Todos os portes", "24 horas"),
        }
    
    def get_medicamento_info(self, medicamento: str) -> MedicamentoInfo:
        """Retorna informações do medicamento"""
        return self.medicamento_info.get(medicamento, 
                                        MedicamentoInfo("N/A", "N/A", "N/A", "N/A", "N/A"))
    
    def get_medicamentos_list(self) -> List[str]:
        """Retorna lista de medicamentos"""
        return self.medicamentos

class FileManager:
    """Classe responsável por salvar dados em arquivos"""
    global test_mode
    @staticmethod
    def save_to_excel(data: List[Dict], filename: str) -> bool:
        """Salva dados em arquivo Excel"""
        try:
            if not data:
                logger.warning(f"Nenhum dado para salvar em {filename}")
                return False
                
            df = pd.DataFrame(data)

            if test_mode:
                # Criar pasta se não existir
                os.makedirs('dados_testes', exist_ok=True)

                filepath = f"dados_testes/{filename}"
                df.to_excel(filepath, index=False)
                logger.info(f"Dados salvos em {filepath}")
            else:
                # Criar pasta se não existir
                os.makedirs('dados_coletados', exist_ok=True)
                
                filepath = f"dados_coletados/{filename}"
                df.to_excel(filepath, index=False)
                logger.info(f"Dados salvos em {filepath}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo {filename}: {e}")
            return False

class BaseSiteScraper(ABC):
    """Classe abstrata base para scrapers de sites"""
    
    def __init__(self, request_handler: RequestHandler, data_manager: DataManager, test_mode: bool = False):
        self.request_handler = request_handler
        self.data_manager = data_manager
        self.test_mode = test_mode
    
    @property
    @abstractmethod
    def site_name(self) -> str:
        """Nome do site"""
        pass
    
    @property
    @abstractmethod
    def site_url(self) -> str:
        """URL base do site"""
        pass
    
    @abstractmethod
    def scrape_medicamento(self, medicamento: str) -> List[ProdutoInfo]:
        """Scraping de um medicamento específico"""
        pass
    
    def scrape_all(self) -> List[Dict]:
        """Scraping de todos os medicamentos"""
        logger.info(f"Iniciando scraping {self.site_name}...")
        produtos_data = []
        
        for medicamento in self.data_manager.get_medicamentos_list():
            try:
                produtos = self.scrape_medicamento(medicamento)
                produtos_dict = [asdict(produto) for produto in produtos]
                produtos_data.extend(produtos_dict)
                
                # Delay entre requisições
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro ao processar {medicamento} no {self.site_name}: {e}")
                continue
        
        logger.info(f"{self.site_name}: Total de {len(produtos_data)} produtos coletados")
        return produtos_data

class ScraperBase(ABC):
    """
    Classe abstrata que define a interface comum
    para todos os scrapers de sites específicos
    """
    
    def __init__(self, selenium_handler: ManipuladorSelenium, data_manager: GerenciadorDados, test_mode: bool = False):
        self.selenium_handler = selenium_handler
        self.data_manager = data_manager
        self.test_mode = test_mode
    
    @property
    @abstractmethod
    def nome_site(self) -> str:
        """Nome do site para identificação"""
        pass
    
    @property
    @abstractmethod
    def url_site(self) -> str:
        """URL base do site"""
        pass
    
    @abstractmethod
    def fazer_scraping_medicamento(self, medicamento: str) -> List[InfoProduto]:
        """
        Faz scraping de um medicamento específico
        Deve ser implementado por cada site
        """
        pass
    
    def fazer_scraping_completo(self) -> List[Dict]:
        """
        Executa scraping de todos os medicamentos do site
        
        Returns:
            List[Dict]: Lista com dados de todos os produtos encontrados
        """
        logger.info(f"Iniciando scraping completo para {self.nome_site}...")
        produtos_coletados = []
        
        medicamentos = self.data_manager.obter_lista_medicamentos()
        total_medicamentos = len(medicamentos)
        
        # Processar cada medicamento
        for indice, medicamento in enumerate(medicamentos):
            try:
                logger.info(f"Processando {medicamento} ({indice + 1}/{total_medicamentos})")
                
                # Fazer scraping do medicamento
                produtos = self.fazer_scraping_medicamento(medicamento)
                
                # Converter para dicionário e adicionar à lista
                produtos_dict = [asdict(produto) for produto in produtos]
                produtos_coletados.extend(produtos_dict)
                
                logger.info(f"Encontrados {len(produtos)} produtos para {medicamento}")
                
                # Pausa entre medicamentos para não sobrecarregar o site
                if indice < total_medicamentos - 1:  # Não pausar no último
                    delay = random.uniform(1, 3)
                    logger.info(f"Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Erro ao processar {medicamento} no {self.nome_site}: {e}")
                continue
        
        logger.info(f"{self.nome_site}: {len(produtos_coletados)} produtos coletados no total")
        return produtos_coletados

class CobasiScraper(BaseSiteScraper):
    """Scraper específico para Cobasi"""
    
    @property
    def site_name(self) -> str:
        return "Cobasi"
    
    @property
    def site_url(self) -> str:
        return "cobasi.com.br"
    
    def scrape_medicamento(self, medicamento: str) -> List[ProdutoInfo]:
        """Scraping de medicamento na Cobasi"""
        logger.info(f"Buscando {medicamento} na Cobasi...")
        produtos = []
        
        url = f"https://www.cobasi.com.br/pesquisa?terms={medicamento}"
        self.request_handler.accept_cookies(f"www.cobasi.com.br/pesquisa?terms={medicamento}")
        response = self.request_handler.make_request(url)
        
        if not response:
            return produtos
            
        soup = BeautifulSoup(response.content, 'html.parser')
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        
        if script_tag:
            try:
                produtos.extend(self._extract_from_json(script_tag, medicamento))
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON da Cobasi: {e}")
                produtos.extend(self._extract_from_html_fallback(soup, medicamento))
        else:
            logger.warning(f"Não encontrou script __NEXT_DATA__ para {medicamento}")
            produtos.extend(self._extract_from_html_fallback(soup, medicamento))
        
        return produtos
    
    def _extract_from_json(self, script_tag, medicamento: str) -> List[ProdutoInfo]:
        """Extrai produtos do JSON"""
        produtos = []
        data = json.loads(script_tag.string)
        produtos_json = data["props"]["pageProps"]["searchResult"]["products"]
        
        if self.test_mode and produtos_json:
            produtos_json = produtos_json[:1]
        
        for produto_json in produtos_json:
            try:
                nome_produto = produto_json.get('name', 'N/A')
                produto_id = produto_json.get('id', 'N/A')
                preco_base = produto_json.get('price', 0)
                
                skus = produto_json.get('skus', [])
                info_base = self.data_manager.get_medicamento_info(medicamento)
                
                if not skus:
                    produto = ProdutoInfo(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome_produto,
                        quantidade="N/A",
                        preco=f"R$ {preco_base:.2f}" if isinstance(preco_base, (int, float)) else str(preco_base),
                        site=self.site_url,
                        data_coleta=datetime.now().strftime("%Y-%m-%d"),
                        produto_id=produto_id
                    )
                    produtos.append(produto)
                else:
                    for sku in skus:
                        try:
                            quantidade = sku.get('name', 'N/A')
                            preco_sku = sku.get('price', 0)
                            preco_antigo = sku.get('oldPrice', 0)
                            disponibilidade = sku.get('available', 'UNKNOWN')
                            desconto_percent = sku.get('discountPercent', 0)
                            
                            if disponibilidade != 'AVAILABLE':
                                continue
                            
                            produto = ProdutoInfo(
                                categoria=info_base.categoria,
                                marca=medicamento,
                                produto=nome_produto,
                                quantidade=quantidade,
                                preco=f"R$ {preco_sku:.2f}" if isinstance(preco_sku, (int, float)) else str(preco_sku),
                                preco_antigo=f"R$ {preco_antigo:.2f}" if preco_antigo and isinstance(preco_antigo, (int, float)) else "N/A",
                                desconto=f"{desconto_percent}%" if desconto_percent > 0 else "0%",
                                disponibilidade=disponibilidade,
                                site=self.site_url,
                                produto_id=produto_id,
                                sku_id=sku.get('sku', 'N/A'),
                                data_coleta=datetime.now().strftime("%Y-%m-%d")
                            )
                            produtos.append(produto)
                            
                        except Exception as e:
                            logger.error(f"Erro ao processar SKU: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"Erro ao processar produto JSON da Cobasi: {e}")
                continue
        
        return produtos
    
    def _extract_from_html_fallback(self, soup, medicamento: str) -> List[ProdutoInfo]:
        """Método de fallback usando HTML"""
        logger.info(f"Usando método HTML fallback para {medicamento}")
        produtos = []
        
        try:
            produtos_html = soup.find_all('a', {'data-testid': 'product-item-v4'})
            
            if self.test_mode and produtos_html:
                produtos_html = produtos_html[:1]
            
            info_base = self.data_manager.get_medicamento_info(medicamento)
            
            for produto_html in produtos_html:
                try:
                    nome_elem = produto_html.find('h3', class_='body-text-sm')
                    nome = nome_elem.text.strip() if nome_elem else "N/A"
                    
                    preco_elem = produto_html.find('span', class_='card-price')
                    preco = preco_elem.text.strip() if preco_elem else "N/A"
                    
                    produto = ProdutoInfo(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome,
                        quantidade="N/A",
                        preco=preco,
                        site=self.site_url,
                        data_coleta=datetime.now().strftime("%Y-%m-%d"),
                        # metodo="html_fallback"
                    )
                    produtos.append(produto)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto HTML: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro no método HTML fallback: {e}")
            
        return produtos

# ==========================================
# SCRAPER ESPECÍFICO - PETLOVE
# ==========================================

class ScraperPetlove(ScraperBase):
    """
    Scraper específico para o site Petlove
    Foca na extração de produtos e suas variações
    """
    
    @property
    def nome_site(self) -> str:
        return "Petlove"
    
    @property
    def url_site(self) -> str:
        return "petlove.com.br"
    
    def fazer_scraping_medicamento(self, medicamento: str) -> List[ProdutoInfo]:
        """
        Faz scraping de um medicamento específico na Petlove
        
        Args:
            medicamento: Nome do medicamento para buscar
            
        Returns:
            List[ProdutoInfo]: Lista de produtos encontrados
        """
        logger.info(f"Buscando {medicamento} na Petlove...")
        produtos = []
        
        # URL de busca na Petlove
        url_busca = f"https://www.petlove.com.br/busca?q={medicamento}"
        
        # Aceitar cookies primeiro
        self.selenium_handler.aceitar_cookies("https://www.petlove.com.br")
        
        # Navegar para página de busca
        if not self.selenium_handler.navegar_para_url(url_busca):
            logger.error(f"Não conseguiu navegar para {url_busca}")
            return produtos
        
        try:
            # Aguardar carregamento
            self.selenium_handler.aguardar_elemento(By.CSS_SELECTOR, 'div.list__item', timeout=10)

            # Coletar URLs e dados básicos primeiro (antes de navegar para outras páginas)
            produtos_info = []
            elementos_produto = self.selenium_handler.encontrar_elementos_seguro(
                By.CSS_SELECTOR, 
                'div.list__item'
            )
            
            logger.info(f"Elementos de produto carregados: {'Sim' if elementos_produto else 'Não'}")
            logger.info(f"Número de produtos encontrados na página: {len(elementos_produto)}")

            # Limitar em modo teste
            if self.test_mode and elementos_produto:
                elementos_produto = elementos_produto[:1]
                logger.info("Modo teste: limitando a 1 produto")
            
            # PRIMEIRA PASSADA: Coletar todos os dados básicos sem navegar
            for i, elemento_produto in enumerate(elementos_produto):
                try:
                    logger.info(f"Coletando dados básicos do produto {i + 1}/{len(elementos_produto)}")
                    
                    # Extrair nome do produto
                    elementos_nome = elemento_produto.find_elements(By.CSS_SELECTOR, 'h2.product-card__name')
                    nome = self.selenium_handler.obter_texto_seguro(
                        elementos_nome[0] if elementos_nome else None
                    )
                    
                    # Extrair preço
                    elementos_preco = elemento_produto.find_elements(
                        By.CSS_SELECTOR, 
                        'p.color-neutral-dark.font-bold.font-body-s, p[data-testid="price"]'
                    )
                    preco = self.selenium_handler.obter_texto_seguro(
                        elementos_preco[0] if elementos_preco else None
                    )

                    # Extrair quantidade básica
                    elementos_quantidade = elemento_produto.find_elements(By.CSS_SELECTOR, 'span.button__label')
                    quantidade_basica = self.selenium_handler.obter_texto_seguro(
                        elementos_quantidade[0] if elementos_quantidade else None
                    )

                    # Verificar se tem botão "+opções" para variações
                    tem_variacoes = False
                    link_produto = None
                    
                    elementos_quantidade_mais = elemento_produto.find_elements(
                        By.CSS_SELECTOR, 
                        'button.button'
                    )
                    
                    for btn in elementos_quantidade_mais:
                        quantidade_btn = btn.find_elements(By.CSS_SELECTOR, 'span.button__label')
                        btn_text = self.selenium_handler.obter_texto_seguro( 
                            quantidade_btn[0] if quantidade_btn else None
                        )
                        if btn_text and btn_text == "+opções":
                            tem_variacoes = True
                            # Extrair URL do produto
                            elementos_link = elemento_produto.find_elements(By.CSS_SELECTOR, 'a[itemprop="url"]')
                            if elementos_link:
                                link_produto = self.selenium_handler.obter_atributo_seguro(
                                    elementos_link[0], "href"
                                )
                                # Corrigir URL se necessário
                                if link_produto and link_produto != "N/A" and not link_produto.startswith('http'):
                                    link_produto = f"https://www.petlove.com.br{link_produto}"
                            break

                    # Armazenar informações para processamento posterior
                    produto_info = {
                        'nome': nome,
                        'preco_basico': preco,
                        'quantidade_basica': quantidade_basica,
                        'tem_variacoes': tem_variacoes,
                        'link_produto': link_produto
                    }
                    produtos_info.append(produto_info)
                    
                    logger.info(f"Produto coletado: {nome} | Preço: {preco} | Tem variações: {tem_variacoes}")
                    
                except Exception as e:
                    logger.error(f"Erro ao coletar dados básicos do produto {i + 1}: {e}")
                    continue

            # SEGUNDA PASSADA: Processar variações navegando para cada produto
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            for i, produto_info in enumerate(produtos_info):
                try:
                    logger.info(f"Processando variações do produto {i + 1}/{len(produtos_info)}")
                    
                    variacoes = []
                    
                    if produto_info['tem_variacoes'] and produto_info['link_produto']:
                        # Buscar variações navegando para a página do produto
                        variacoes = self._obter_variacoes(produto_info['link_produto'])
                    
                    # Se não conseguiu obter variações, usar dados básicos
                    if not variacoes:
                        variacoes = [{
                            "quantidade": produto_info['quantidade_basica'], 
                            "preco": produto_info['preco_basico']
                        }]
                    
                    # Criar produto para cada variação
                    for variacao in variacoes:
                        logger.info(f"Criando produto: {produto_info['nome']} | Quantidade: {variacao.get('quantidade')} | Preço: {variacao.get('preco')}")
                        
                        produto = ProdutoInfo(
                            categoria=info_base.categoria,
                            marca=medicamento,
                            produto=produto_info['nome'],
                            quantidade=variacao.get("quantidade", produto_info['quantidade_basica']),
                            preco=variacao.get("preco", produto_info['preco_basico']),
                            url=produto_info['link_produto'] if produto_info['link_produto'] else "N/A",
                            site=self.url_site,
                            data_coleta=datetime.now().strftime("%Y-%m-%d"),
                            metodo="selenium_fixed"
                        )
                        produtos.append(produto)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar variações do produto {i + 1}: {e}")
                    # Em caso de erro, criar produto com dados básicos
                    try:
                        produto = ProdutoInfo(
                            categoria=info_base.categoria,
                            marca=medicamento,
                            produto=produto_info['nome'],
                            quantidade=produto_info['quantidade_basica'],
                            preco=produto_info['preco_basico'],
                            url=produto_info['link_produto'] if produto_info['link_produto'] else "N/A",
                            site=self.url_site,
                            data_coleta=datetime.now().strftime("%Y-%m-%d"),
                            metodo="selenium_fallback"
                        )
                        produtos.append(produto)
                    except Exception as e2:
                        logger.error(f"Erro crítico no produto {i + 1}: {e2}")
                        continue
                    
        except Exception as e:
            logger.error(f"Erro geral no scraping Petlove para {medicamento}: {e}")
        
        return produtos

    def _obter_variacoes(self, url: str) -> List[Dict]:
        """
        Busca variações de quantidade/tamanho na página do produto
        
        Args:
            url: URL do produto para buscar variações
            
        Returns:
            List[Dict]: Lista de variações com quantidade e preço
        """
        variacoes = []
        
        if not url or url == "N/A":
            return variacoes
        
        try:
            # Navegar para página do produto
            if not self.selenium_handler.navegar_para_url(url):
                logger.warning(f"Não foi possível navegar para {url}")
                return variacoes
            
            # Aguardar carregamento com timeout maior
            time.sleep(2)
            
            # MÉTODO 1: Buscar popup de variações
            elementos_popup = self.selenium_handler.encontrar_elementos_seguro(
                By.CSS_SELECTOR, 
                'div.variant-list'
            )
            
            if elementos_popup:
                logger.info("Popup de variações encontrado")
                # Buscar itens de variação dentro do popup
                elementos_variacao = elementos_popup[0].find_elements(
                    By.CSS_SELECTOR, 
                    'div.badge__container.variant-selector__badge'
                )
                
                logger.info(f"Encontradas {len(elementos_variacao)} variações")
                
                for j, item in enumerate(elementos_variacao):
                    try:
                        # Extrair nome da variação
                        elementos_nome = item.find_elements(By.CSS_SELECTOR, 'span.font-bold.mb-2')
                        quantidade = self.selenium_handler.obter_texto_seguro(
                            elementos_nome[0] if elementos_nome else None
                        )
                        if quantidade == "N/A":
                            quantidade = f"Variação {j + 1}"
                        
                        # Extrair preço da variação
                        elementos_preco = item.find_elements(By.CSS_SELECTOR, 'div.font-body-s')
                        preco = self.selenium_handler.obter_texto_seguro(
                            elementos_preco[0] if elementos_preco else None
                        )
                        
                        if preco and preco != "N/A":
                            logger.info(f"Variação encontrada: {quantidade} | Preço: {preco}")
                            variacoes.append({"quantidade": quantidade, "preco": preco})
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar variação {j + 1}: {e}")
                        continue
            else:
                logger.info("Popup de variações não encontrado, tentando método alternativo")
                
                # MÉTODO 2: Buscar variações na página principal
                elementos_variacao_alt = self.selenium_handler.encontrar_elementos_seguro(
                    By.CSS_SELECTOR, 
                    'button[data-testid*="variant"], .variant-selector button, .size-selector button'
                )
                
                if elementos_variacao_alt:
                    logger.info(f"Encontradas {len(elementos_variacao_alt)} variações alternativas")
                    
                    for j, btn in enumerate(elementos_variacao_alt):
                        try:
                            quantidade = self.selenium_handler.obter_texto_seguro(btn)
                            if quantidade and quantidade != "N/A":
                                # Para método alternativo, não temos preço específico
                                logger.info(f"Variação alternativa encontrada: {quantidade}")
                                variacoes.append({"quantidade": quantidade, "preco": "N/A"})
                        except Exception as e:
                            logger.error(f"Erro ao processar variação alternativa {j + 1}: {e}")
                            continue
                
        except Exception as e:
            logger.error(f"Erro ao buscar variações em {url}: {e}")
            
        return variacoes


class PetzScraper(BaseSiteScraper):
    """Scraper específico para Petz"""
    
    @property
    def site_name(self) -> str:
        return "Petz"
    
    @property
    def site_url(self) -> str:
        return "petz.com.br"
    
    def scrape_medicamento(self, medicamento: str) -> List[ProdutoInfo]:
        """Scraping de medicamento na Petz"""
        logger.info(f"Buscando {medicamento} na Petz...")
        produtos = []
        
        url = f"https://www.petz.com.br/busca?q={medicamento}"
        self.request_handler.accept_cookies(f"www.petz.com.br/busca?q={medicamento}")
        response = self.request_handler.make_request(url)
        
        if not response:
            return produtos
            
        soup = BeautifulSoup(response.content, 'html.parser')
        produtos_html = soup.find_all('li', class_='card-product')
        
        if self.test_mode and produtos_html:
            produtos_html = produtos_html[:1]
        
        info_base = self.data_manager.get_medicamento_info(medicamento)
        
        for produto_html in produtos_html:
            try:
                aux = produto_html.find('meta', itemprop="url")
                link_produto = aux.get('content') if aux else "N/A"
                
                # Dados do JSON
                try:
                    produto_json = json.loads(produto_html.get_text(strip=True))
                    nome = produto_json.get('name', 'N/A').strip()
                    preco_base = produto_json.get('price', 'N/A')
                except:
                    nome = "N/A"
                    preco_base = "N/A"
                
                # Buscar variações
                variacoes = self._get_variations(str(link_produto)) if link_produto != "N/A" else []
                
                if not variacoes:
                    variacoes = [{"quantidade": "N/A", "preco": preco_base}]
                
                for variacao in variacoes:
                    produto = ProdutoInfo(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome,
                        quantidade=variacao.get("quantidade", "N/A"),
                        preco=variacao.get("preco", preco_base),
                        site=self.site_url,
                        url=str(link_produto) if link_produto != "N/A" else "N/A",
                        data_coleta=datetime.now().strftime("%Y-%m-%d")
                    )
                    produtos.append(produto)
                
            except Exception as e:
                logger.error(f"Erro ao processar produto Petz: {e}")
        
        return produtos
    
    def _get_variations(self, url: str) -> List[Dict]:
        """Busca variações de quantidade na Petz"""
        variacoes = []
        try:
            response = self.request_handler.make_request(url)
            if not response:
                return variacoes
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar no popup de variações
            popup_variacoes = soup.find('div', id='popupVariacoes')
            if popup_variacoes:
                variation_items = popup_variacoes.find_all('div', class_='variacao-item')
                
                for item in variation_items:
                    try:
                        nome_elem = item.find('div', class_='item-name')
                        quantidade = nome_elem.get_text(strip=True) if nome_elem else "Único"
                        
                        preco_elem = item.find('b')
                        preco = preco_elem.get_text(strip=True) if preco_elem else "N/A"
                        
                        variacoes.append({"quantidade": quantidade, "preco": preco})
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar variação Petz: {e}")
            
            # Fallback para variação atual
            if not variacoes:
                nome_var = soup.find('div', class_='nome-variacao')
                if nome_var:
                    qtd_elem = nome_var.find('b')
                    quantidade = qtd_elem.text.strip() if qtd_elem else "Único"
                    
                    price_elem = soup.find('span', class_='price') or soup.find('div', class_='preco')
                    preco = price_elem.text.strip() if price_elem else "N/A"
                    
                    variacoes.append({"quantidade": quantidade, "preco": preco})
                    
        except Exception as e:
            logger.error(f"Erro ao buscar variações Petz: {e}")
            
        return variacoes

class VetMedicineScraperManager:
    """Classe gerenciadora principal do scraping"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.request_handler = RequestHandler()
        self.data_manager = DataManager()
        self.file_manager = FileManager()
        
        # Aceitar cookies antes de rodar os scrapers
        for site in ["www.cobasi.com.br", "www.petlove.com.br", "www.petz.com.br"]:
            self.request_handler.accept_cookies(site)

        # Inicializar scrapers
        self.scrapers = [
            CobasiScraper(self.request_handler, self.data_manager, test_mode),
            PetloveScraper(self.request_handler, self.data_manager, test_mode),
            PetzScraper(self.request_handler, self.data_manager, test_mode)
        ]


    def run_scraper(self, scraper: BaseSiteScraper, ePetlove: bool, scraperSelenium: ScraperBase) -> bool:
        """Executa um scraper específico"""

        if ePetlove:
            data = scraperSelenium.fazer_scraping_completo()
            filename = f"{scraperSelenium.nome_site.lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            success = self.file_manager.save_to_excel(data, filename)
        else:
            try: 
                data = scraper.scrape_all()
                filename = f"{scraper.site_name.lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                success = self.file_manager.save_to_excel(data, filename)

                if success:
                    logger.info(f"{scraper.site_name}: {len(data)} produtos salvos com sucesso")
                return success

            except Exception as e:
                logger.error(f"Erro no scraping {scraper.site_name}: {e}")
                return False
        
        try:
            data = scraper.scrape_all()
            filename = f"{scraper.site_name.lower()}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            success = self.file_manager.save_to_excel(data, filename)
            
            if success:
                logger.info(f"{scraper.site_name}: {len(data)} produtos salvos com sucesso")
            return success
            
        except Exception as e:
            logger.error(f"Erro no scraping {scraper.site_name}: {e}")
            return False
    
    def run_all(self):
        """Executa todos os scrapers"""
        logger.info("=" * 50)
        logger.info(f"Iniciando scraping - Modo: {'TESTE' if self.test_mode else 'COMPLETO'}")
        logger.info("=" * 50)
        
        total_success = 0
        total_scrapers = len(self.scrapers)
        
        for scraper in self.scrapers:
            success = self.run_scraper(scraper, ePetlove=(scraper.site_name == "Petlove"), scraperSelenium=ScraperPetlove(self.request_handler, self.data_manager, self.test_mode) if scraper.site_name == "Petlove" else None)
            if success:
                total_success += 1
        
        logger.info("=" * 50)
        logger.info(f"Scraping finalizado! {total_success}/{total_scrapers} sites processados com sucesso")
        logger.info("=" * 50)
    
    def run_specific_site(self, site_name: str):
        """Executa scraping de um site específico"""
        scraper = None
        for s in self.scrapers:
            if s.site_name.lower() == site_name.lower():
                scraper = s
                break
        
        if scraper:
            logger.info(f"Executando scraping específico para {site_name}")
            self.run_scraper(scraper)
        else:
            logger.error(f"Site '{site_name}' não encontrado. Sites disponíveis: {[s.site_name for s in self.scrapers]}")

def main():
    """Função principal"""
    print("\n" + "=" * 50)
    print("SCRAPER DE MEDICAMENTOS VETERINÁRIOS - OOP")
    print("=" * 50)
    print("\nEscolha o modo de execução:")
    print("1 - Modo TESTE (coleta apenas 1 produto por medicamento)")
    print("2 - Modo COMPLETO (coleta todos os produtos)")
    print("3 - Site específico")
    
    escolha = input("\nDigite sua escolha (1, 2 ou 3): ").strip()
    
    if escolha == "3":
        print("\nSites disponíveis:")
        print("- Cobasi")
        print("- Petlove") 
        print("- Petz")
        site_escolhido = input("\nDigite o nome do site: ").strip()
        
        print(f"\n>>> Executando scraping para {site_escolhido}...")
        manager = VetMedicineScraperManager(test_mode=False)
        manager.run_specific_site(site_escolhido)
        
    else:
        test_mode = escolha == "1"
        
        if test_mode:
            print("\n>>> Executando em modo TESTE...")
            print(">>> Será coletado apenas 1 produto por medicamento para verificação")
            test_mode = True
        else:
            print("\n>>> Executando em modo COMPLETO...")
            print(">>> Todos os produtos serão coletados (pode demorar)")
        
        manager = VetMedicineScraperManager(test_mode=test_mode)
        manager.run_all()
    
    print("\n>>> Processo finalizado!")
    print(f">>> Verifique os arquivos Excel na na pasta 'dados_coletados'")

if __name__ == "__main__":
    main()