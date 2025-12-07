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

# ==========================================
# CONFIGURAÇÃO DE LOGS
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler('scraper_medicamentos.log', encoding='utf-8')  # Arquivo
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
    """
    empresa: str         
    categoria: str       
    animal: str          
    porte: str           
    eficacia: str        

@dataclass
class InfoProduto:
    """
    Dados coletados de cada produto encontrado nos sites
    """
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
            
            # MINIMIZAR LOGS DO CHROMEDRIVER
            chrome_options.add_argument("--log-level=3")  # Minimizar logs
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # remove handshake/usb warnings

            
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

# ==========================================
# GERENCIADOR DE DADOS DOS MEDICAMENTOS
# ==========================================

class GerenciadorDados:
    """
    Gerencia informações sobre medicamentos veterinários
    e fornece dados estruturados para o scraping
    """
    
    def __init__(self):
        # Lista completa de medicamentos para buscar
        self.medicamentos = [
            "Simparic", "Revolution", "NexGard", "NexGard Spectra", "NexGard Combo", 
            "Bravecto", "Frontline", "Advocate", "Drontal", "Milbemax", "Vermivet",
            "Rimadyl", "Onsior", "Maxicam", "Carproflan", "Previcox",
            "Apoquel", "Zenrelia", "Synulox", "Baytril",
        ]
        
        # Base de conhecimento sobre cada medicamento
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
        
        Args:
            medicamento: Nome do medicamento
            
        Returns:
            InfoMedicamento: Dados do medicamento ou padrão se não encontrado
        """
        return self.info_medicamentos.get(
            medicamento, 
            InfoMedicamento("N/A", "N/A", "N/A", "N/A", "N/A")
        )
    
    def obter_lista_medicamentos(self) -> List[str]:
        """
        Retorna lista completa de medicamentos para buscar
        
        Returns:
            List[str]: Lista de nomes de medicamentos
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
# CLASSE BASE PARA SCRAPERS
# ==========================================

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

# ==========================================
# SCRAPER ESPECÍFICO - COBASI
# ==========================================

class ScraperCobasi(ScraperBase):
    """
    Scraper específico para o site Cobasi
    Implementa estratégias de extração JSON e HTML
    """
    
    @property
    def nome_site(self) -> str:
        return "Cobasi"
    
    @property
    def url_site(self) -> str:
        return "cobasi.com.br"
    
    def fazer_scraping_medicamento(self, medicamento: str) -> List[InfoProduto]:
        """
        Faz scraping de um medicamento específico na Cobasi
        
        Args:
            medicamento: Nome do medicamento para buscar
            
        Returns:
            List[InfoProduto]: Lista de produtos encontrados
        """
        logger.info(f"Buscando {medicamento} na Cobasi...")
        produtos = []
        
        # URL de busca na Cobasi
        url_busca = f"https://www.cobasi.com.br/pesquisa?terms={medicamento}"
        
        # Tentar aceitar cookies primeiro
        self.selenium_handler.aceitar_cookies("https://www.cobasi.com.br")
        
        # Navegar para página de busca
        if not self.selenium_handler.navegar_para_url(url_busca):
            logger.error(f"Não conseguiu navegar para {url_busca}")
            return produtos
        
        try:
            # Aguardar página carregar
            time.sleep(3)
            
            # MÉTODO 1: Tentar extrair dados do JSON (mais confiável)
            elementos_script = self.selenium_handler.encontrar_elementos_seguro(By.ID, "__NEXT_DATA__")
            
            if elementos_script:
                try:
                    produtos = self._extrair_do_json(elementos_script[0], medicamento)
                    if produtos:
                        logger.info(f"Dados extraídos via JSON para {medicamento}")
                        return produtos
                except Exception as e:
                    logger.warning(f"Falha na extração JSON: {e}")
            
            # MÉTODO 2: Fallback para extração HTML
            logger.info(f"Usando método HTML para {medicamento}")
            produtos = self._extrair_do_html(medicamento)
            
        except Exception as e:
            logger.error(f"Erro geral no scraping Cobasi para {medicamento}: {e}")
        
        return produtos
    
    def _extrair_do_json(self, elemento_script, medicamento: str) -> List[InfoProduto]:
        """
        Extrai dados de produtos do JSON da página Next.js
        
        Args:
            elemento_script: Elemento script contendo JSON
            medicamento: Nome do medicamento
            
        Returns:
            List[InfoProduto]: Produtos extraídos
        """
        produtos = []
        
        try:
            # Obter conteúdo JSON
            conteudo_json = self.selenium_handler.obter_atributo_seguro(elemento_script, "innerHTML")
            
            if not conteudo_json or conteudo_json == "N/A":
                return produtos
            
            # Parse do JSON
            dados = json.loads(conteudo_json)
            produtos_json = dados.get("props", {}).get("pageProps", {}).get("searchResult", {}).get("products", [])
            
            # Limitar produtos em modo teste (só 1 produto)
            if self.test_mode and produtos_json:
                produtos_json = produtos_json[:1]
                logger.info("Modo teste: limitando a 1 produto")
            
            # Obter informações base do medicamento
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            # Processar cada produto encontrado
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
                            produto_id=str(produto_id),
                            metodo="json"
                        )
                        produtos.append(produto)
                    else:
                        # Processar cada SKU (variação do produto)
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
                                    data_coleta=datetime.now().strftime("%Y-%m-%d"),
                                    metodo="json"
                                )
                                produtos.append(produto)
                                
                            except Exception as e:
                                logger.error(f"Erro ao processar SKU: {e}")
                                continue
                                
                except Exception as e:
                    logger.error(f"Erro ao processar produto JSON: {e}")
                    continue
        
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            logger.error(f"Erro na extração JSON: {e}")
        
        return produtos
    
    def _extrair_do_html(self, medicamento: str) -> List[InfoProduto]:
        """
        Método de fallback usando extração HTML quando JSON falha
        
        Args:
            medicamento: Nome do medicamento
            
        Returns:
            List[InfoProduto]: Produtos extraídos via HTML
        """
        produtos = []
        
        try:
            # Buscar elementos de produto na página
            elementos_produto = self.selenium_handler.encontrar_elementos_seguro(
                By.CSS_SELECTOR, 
                'a[data-testid="product-item-v4"]'
            )
            
            # Limitar em modo teste
            if self.test_mode and elementos_produto:
                elementos_produto = elementos_produto[:1]
                logger.info("Modo teste: limitando a 1 produto")
            
            info_base = self.data_manager.obter_info_medicamento(medicamento)
            
            # Processar cada elemento de produto encontrado
            for elemento_produto in elementos_produto:
                try:
                    # Extrair nome do produto
                    elementos_nome = elemento_produto.find_elements(By.CSS_SELECTOR, 'h3.body-text-sm')
                    nome = self.selenium_handler.obter_texto_seguro(
                        elementos_nome[0] if elementos_nome else None
                    )
                    
                    # Extrair preço
                    elementos_preco = elemento_produto.find_elements(By.CSS_SELECTOR, 'span.card-price')
                    preco = self.selenium_handler.obter_texto_seguro(
                        elementos_preco[0] if elementos_preco else None
                    )
                    
                    # Extrair URL do produto
                    url = self.selenium_handler.obter_atributo_seguro(elemento_produto, "href")
                    
                    produto = InfoProduto(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome,
                        quantidade="N/A",
                        preco=preco,
                        site=self.url_site,
                        url=url,
                        data_coleta=datetime.now().strftime("%Y-%m-%d"),
                        metodo="html_fallback"
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
    
    def fazer_scraping_medicamento(self, medicamento: str) -> List[InfoProduto]:
        """
        Faz scraping de um medicamento específico na Petlove
        
        Args:
            medicamento: Nome do medicamento para buscar
            
        Returns:
            List[InfoProduto]: Lista de produtos encontrados
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
                        
                        produto = InfoProduto(
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
                        produto = InfoProduto(
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

# ==========================================
# SCRAPER ESPECÍFICO - PETZ
# ==========================================

class ScraperPetz(ScraperBase):
    """
    Scraper específico para o site Petz
    Implementa estratégias de extração HTML
    """
    
    @property
    def nome_site(self) -> str:
        return "Petz"
    
    @property
    def url_site(self) -> str:
        return "petz.com.br"
    
    def fazer_scraping_medicamento(self, medicamento: str) -> List[InfoProduto]:
        """
        Faz scraping de um medicamento específico na Petz
        
        Args:
            medicamento: Nome do medicamento para buscar
            
        Returns:
            List[InfoProduto]: Lista de produtos encontrados
        """
        logger.info(f"Buscando {medicamento} na Petz...")
        produtos = []
        
        # URL de busca na Petz
        url_busca = f"https://www.petz.com.br/busca?q={medicamento}"
        
        # Aceitar cookies primeiro
        self.selenium_handler.aceitar_cookies("https://www.petz.com.br")
        
        # Navegar para página de busca
        if not self.selenium_handler.navegar_para_url(url_busca):
            logger.error(f"Não conseguiu navegar para {url_busca}")
            return produtos
        
        try:
            # Aguardar carregamento
            time.sleep(3)
            
            # Buscar elementos de produto na página
            elementos_produto = self.selenium_handler.encontrar_elementos_seguro(
                By.TAG_NAME, 
                'product-card'
            )
            
            # Limitar em modo teste
            if self.test_mode and elementos_produto:
                elementos_produto = elementos_produto[:1]
                logger.info("Modo teste: limitando a 1 produto")
            
            info_base = self.data_manager.obter_info_medicamento(medicamento)

            # logger.info(f"Elementos de produto carregados: {elementos_produto}")
            logger.info(f"Número de produtos encontrados na página: {len(elementos_produto)}")

            for elemento_produto in elementos_produto:
                try:
                    detalhes_produto = elemento_produto.get_attribute('product-details')

                    if not detalhes_produto:
                        logger.warning("Atributo 'product-details' vazio ou None")
                        continue

                    # Corrigir aspas simples se necessário
                    elementos_meta = detalhes_produto.strip().replace("'", '"')

                    # logger.debug(f"elementos_meta len: {len(elementos_meta)} | type: {type(elementos_meta)}")

                    try:
                        produto_json = json.loads(elementos_meta)
                        variacoes = produto_json.get('variations', [])
                        logger.info(f"Variações de {produto_json.get('name', 'N/A')} encontradas Count: {len(variacoes)}")
                        
                        if len(variacoes) == 0:
                            # Se não tem variações, criar uma variação padrão
                            variacoes = [{
                                "name": produto_json.get('variationAbreviation', 'N/A'),
                                "price": produto_json.get('price', 'N/A'),
                                "promotionalPrice": produto_json.get('promotional_price', produto_json.get('price', 'N/A')),
                                "discountPercentage": produto_json.get('discountPercentage', 0),
                                "sku": produto_json.get('sku', 'N/A'),
                                "availability": produto_json.get('availability', 'UNKNOWN'),
                                "id": produto_json.get('id', 'N/A'),
                            }]
                            

                        for variacao in variacoes:
                            try:
                                quantidade = variacao.get('name', 'N/A')
                                preco = variacao.get('price', 'N/A')
                                promotionalPrice = variacao.get('promotionalPrice', preco)
                                discountPercentage = variacao.get('discountPercentage', 0)
                                availability=produto_json.get('availability', 'UNKNOWN')
                                produto_id = produto_json.get('id', 'N/A')
                                sku = variacao.get('sku', 'N/A')
                                
                                produto = InfoProduto(
                                    categoria=info_base.categoria,
                                    marca=medicamento,
                                    produto=produto_json.get('name', 'N/A'),
                                    quantidade=quantidade,
                                    preco=f"R$ {promotionalPrice}",
                                    preco_antigo=f"R$ {preco}",
                                    desconto=f"{discountPercentage}%" if discountPercentage else "0%",
                                    disponibilidade=availability,
                                    site=self.url_site,
                                    produto_id=produto_id,
                                    sku_id=sku,
                                    url=produto_json.get('url', 'N/A'),
                                    data_coleta=datetime.now().strftime("%Y-%m-%d"),
                                    metodo="selenium_petz"
                                )
                                produtos.append(produto)
                            except Exception as e:
                                logger.error(f"Erro ao processar variação Petz: {e}")
                                continue
                        # logger.info(f"Produto JSON carregado: {produto_json.get('name', 'N/A')} | Preço: {produto_json.get('price', 'N/A')}")
                    except json.JSONDecodeError as je:
                        logger.error(f"Falha ao decodificar JSON: {je}")
                        continue

                except Exception as e:
                    logger.error(f"Erro inesperado no processamento de produto: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro geral no scraping Petz para {medicamento}: {e}")
        
        return produtos

# ==========================================
# GERENCIADOR PRINCIPAL
# ==========================================

class GerenciadorScraperMedicamentos:
    """
    Classe gerenciadora principal que coordena todos os scrapers
    e controla o fluxo de execução do sistema
    """
    global test_mode
    
    def __init__(self, test_mode: bool = False):
        """
        Inicializa o gerenciador
        
        Args:
            test_mode: Se True, executa em modo teste (mais rápido, menos dados)
        """
        self.test_mode = test_mode
        
        # Definir variável global para outros componentes
        test_mode = self.test_mode
        
        # Inicializar componentes principais
        self.selenium_handler = ManipuladorSelenium()
        self.data_manager = GerenciadorDados()
        self.file_manager = GerenciadorArquivos()
        
        # Lista de scrapers será inicializada após o driver estar pronto
        self.scrapers = []
        
        logger.info(f"Gerenciador inicializado - Modo: {'TESTE' if test_mode else 'COMPLETO'}")
    
    def inicializar_driver(self) -> bool:
        """
        Inicializa o driver do Selenium e os scrapers
        
        Returns:
            bool: True se inicializou com sucesso
        """
        logger.info("Inicializando driver Selenium com webdriver-manager...")
        sucesso = self.selenium_handler.configurar_driver()
        
        if sucesso:
            # Inicializar scrapers após driver estar pronto
            self.scrapers = [
                ScraperCobasi(self.selenium_handler, self.data_manager, self.test_mode),
                ScraperPetlove(self.selenium_handler, self.data_manager, self.test_mode),
                ScraperPetz(self.selenium_handler, self.data_manager, self.test_mode)
            ]
            logger.info("Driver e scrapers inicializados com sucesso!")
        else:
            logger.error("Falha ao inicializar driver")
            
        return sucesso
    
    def executar_scraper(self, scraper: ScraperBase) -> bool:
        """
        Executa um scraper específico e salva os dados coletados
        
        Args:
            scraper: Instância do scraper para executar
            
        Returns:
            bool: True se executou e salvou com sucesso
        """
        try:
            logger.info(f"Iniciando scraping para {scraper.nome_site}...")
            
            # Executar scraping de todos os medicamentos
            dados = scraper.fazer_scraping_completo()
            
            # Gerar nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{scraper.nome_site.lower()}_{timestamp}.xlsx"
            
            # Salvar dados no Excel
            sucesso = self.file_manager.salvar_excel(dados, nome_arquivo)
            
            if sucesso:
                logger.info(f"{scraper.nome_site}: {len(dados)} produtos salvos em {nome_arquivo}")
            else:
                logger.error(f"Falha ao salvar dados do {scraper.nome_site}")
                
            return sucesso
            
        except Exception as e:
            logger.error(f"Erro no scraping {scraper.nome_site}: {e}")
            return False
    
    def executar_todos(self):
        """
        Executa todos os scrapers disponíveis sequencialmente
        """
        # Verificar se driver foi inicializado
        if not self.selenium_handler.driver:
            if not self.inicializar_driver():
                logger.error("Não é possível continuar sem o driver")
                return
        
        logger.info("=" * 60)
        logger.info(f"INICIANDO SCRAPING COMPLETO - Modo: {'TESTE' if self.test_mode else 'COMPLETO'}")
        logger.info("=" * 60)
        
        total_sucesso = 0
        total_scrapers = len(self.scrapers)
        
        # Executar cada scraper sequencialmente
        for indice, scraper in enumerate(self.scrapers):
            logger.info(f"\n>>> Processando site {indice + 1}/{total_scrapers}: {scraper.nome_site}")
            
            sucesso = self.executar_scraper(scraper)
            if sucesso:
                total_sucesso += 1
                
            # Pausa entre sites para não sobrecarregar
            if indice < total_scrapers - 1:  # Não pausar após o último
                delay = random.uniform(1,3)
                logger.info(f"Aguardando {delay:.1f}s antes do próximo site...")
                time.sleep(delay)
        
        # Fechar driver
        self.selenium_handler.fechar_driver()
        
        # Relatório final
        logger.info("=" * 60)
        logger.info("SCRAPING FINALIZADO!")
        logger.info(f"Sites processados com sucesso: {total_sucesso}/{total_scrapers}")
        
        if total_sucesso > 0:
            pasta = 'dados_testes' if self.test_mode else 'dados_coletados'
            logger.info(f"Arquivos salvos na pasta: {pasta}/")
        
        logger.info("=" * 60)
    
    def executar_site_especifico(self, nome_site: str):
        """
        Executa scraping de um site específico
        
        Args:
            nome_site: Nome do site para fazer scraping
        """
        # Verificar se driver foi inicializado
        if not self.selenium_handler.driver:
            if not self.inicializar_driver():
                logger.error("Não é possível continuar sem o driver")
                return
        
        # Buscar scraper do site especificado
        scraper = None
        for s in self.scrapers:
            if s.nome_site.lower() == nome_site.lower():
                scraper = s
                break
        
        if scraper:
            logger.info(f"Executando scraping específico para {nome_site}")
            sucesso = self.executar_scraper(scraper)
            
            if sucesso:
                pasta = 'dados_teste' if self.test_mode else 'dados_coletados'
                logger.info(f"Arquivo salvo na pasta: {pasta}/")
        else:
            sites_disponiveis = [s.nome_site for s in self.scrapers]
            logger.error(f"Site '{nome_site}' não encontrado.")
            logger.info(f"Sites disponíveis: {', '.join(sites_disponiveis)}")
        
        # Fechar driver
        self.selenium_handler.fechar_driver()

# ==========================================
# FUNÇÃO PRINCIPAL
# ==========================================

def main():
    """
    Função principal do programa - interface com o usuário
    """
    print("\n" + "=" * 60)
    print("SCRAPER DE MEDICAMENTOS VETERINÁRIOS - VERSÃO MELHORADA")
    print("=" * 60)
    print("\nEste programa coleta preços de medicamentos veterinários")
    print("dos principais pet shops online do Brasil.")
    print("\nSites suportados:")
    print("• Cobasi (cobasi.com.br)")
    print("• Petlove (petlove.com.br)")
    print("• Petz (petz.com.br)")
    
    print("\n" + "-" * 40)
    print("MODOS DE EXECUÇÃO:")
    print("-" * 40)
    print("1 - MODO TESTE")
    print("    • Coleta apenas 1 produto por medicamento")
    print("    • Mais rápido para verificar funcionamento")
    print("    • Ideal para testes e desenvolvimento")
    
    print("\n2 - MODO COMPLETO")
    print("    • Coleta todos os produtos encontrados")
    print("    • Processo mais demorado e completo")
    print("    • Recomendado para coleta de dados real")
    
    print("\n3 - SITE ESPECÍFICO")
    print("    • Executa scraping em apenas um site")
    print("    • Útil para testes ou coleta direcionada")
    
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
            
            print(f"\n>>> Executando scraping para {site_escolhido.title()}...")
            print(">>> Aguarde o processamento...")
            
            # Executar scraping específico
            manager = GerenciadorScraperMedicamentos(test_mode=False)
            manager.executar_site_especifico(site_escolhido)

        else:
            # Modo teste ou completo
            test_mode = (escolha == "1")
            
            if test_mode:
                print("\n>>> MODO TESTE SELECIONADO")
                print(">>> Será coletado apenas 1 produto por medicamento")
                print(">>> Processo mais rápido para verificação")
            else:
                print("\n>>> MODO COMPLETO SELECIONADO")
                print(">>> Todos os produtos serão coletados")
                print(">>> Processo pode demorar vários minutos")
            
            print("\n>>> Inicializando sistema...")
            print(">>> Aguarde o processamento...")
            
            # Executar scraping completo
            manager = GerenciadorScraperMedicamentos(test_mode=test_mode)
            manager.executar_todos()
        
        print(f"\n{'='*50}")
        print("✅ PROCESSO FINALIZADO COM SUCESSO!")
        print(f"{'='*50}")
        
        # Mostrar localização dos arquivos
        folder = 'dados_testes' if (escolha == "1") else 'dados_coletados'
        print(f"\n📁 Arquivos Excel salvos em: ./{folder}/")
        print("📊 Você pode abrir os arquivos para analisar os dados coletados.")
        
    except KeyboardInterrupt:
        print("\n\n>>> Execução cancelada pelo usuário.")
    except Exception as e:
        logger.error(f"Erro durante execução: {e}")
        print(f"\n❌ Erro durante execução: {e}")
        print("📋 Verifique os logs para mais detalhes.")
    
    # Aguardar antes de fechar
    # input("\nPressione Enter para sair...")

# Verificação se o arquivo está sendo executado diretamente
if __name__ == "__main__":
    main()