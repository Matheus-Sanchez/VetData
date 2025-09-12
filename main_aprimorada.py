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

class PetloveScraper(BaseSiteScraper):
    """Scraper específico para Petlove"""
    
    @property
    def site_name(self) -> str:
        return "Petlove"
    
    @property
    def site_url(self) -> str:
        return "petlove.com.br"
    
    def scrape_medicamento(self, medicamento: str) -> List[ProdutoInfo]:
        """Scraping de medicamento na Petlove"""
        logger.info(f"Buscando {medicamento} na Petlove...")
        produtos = []
        
        url = f"https://www.petlove.com.br/busca?q={medicamento}"
        self.request_handler.accept_cookies(f"www.petlove.com.br/busca?q={medicamento}")
        response = self.request_handler.make_request(url)
        
        if not response:
            return produtos
            
        soup = BeautifulSoup(response.content, 'html.parser')
        produtos_html = soup.find_all('div', class_='list__item')
        
        if self.test_mode and produtos_html:
            produtos_html = produtos_html[:1]
        
        info_base = self.data_manager.get_medicamento_info(medicamento)
        
        from bs4 import Tag
        for produto_html in produtos_html:
            try:
                # Certifique-se de que produto_html é um Tag antes de acessar .find
                if not isinstance(produto_html, Tag):
                    continue

                nome_elem = produto_html.find('h2', class_='product-card__name')
                nome = nome_elem.text.strip() if nome_elem else "N/A"

                preco_elem = produto_html.find('p', class_='color-neutral-dark font-bold font-body-s') or produto_html.find('p', {'data-testid': 'price'})
                preco = preco_elem.text.strip() if preco_elem else "N/A"
                
                link_elem = produto_html.find('a', {'itemprop': 'url'})
                link_produto = None
                from bs4 import Tag
                if link_elem and isinstance(link_elem, Tag):
                    link_produto = link_elem.get('href')
                if link_produto:
                    # Se link_produto não for string, converte para string
                    if not isinstance(link_produto, str):
                        link_produto = str(link_produto)
                    if not link_produto.startswith('http'):
                        link_produto = f"https://www.petlove.com.br{link_produto}"
                
                # Buscar variações
                variacoes = self._get_variations(str(link_produto)) if link_produto else []
                
                if not variacoes:
                    variacoes = [{"quantidade": "N/A", "preco": preco}]
                
                for variacao in variacoes:
                    produto = ProdutoInfo(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome,
                        quantidade=variacao.get("quantidade", "N/A"),
                        preco=variacao.get("preco", preco),
                        url=str(link_produto) if link_produto else "N/A",
                        site=self.site_url,
                        data_coleta=datetime.now().strftime("%Y-%m-%d"),
                    )
                    produtos.append(produto)
                
            except Exception as e:
                logger.error(f"Erro ao processar produto Petlove: {e}")
        
        return produtos
    
    def _get_variations(self, url: str) -> List[Dict]:
        """Busca variações de quantidade na Petlove"""
        variacoes = []
        try:
            response = self.request_handler.make_request(url)
            if not response:
                return variacoes
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar variações no popup
            variations_popup = soup.find('div', class_='variant-list flex align-items-center full-width')

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
                from bs4 import Tag
                if selected_button and isinstance(selected_button, Tag):
                    quantidade_elem = selected_button.find('b')
                    quantidade = quantidade_elem.text.strip() if quantidade_elem else "Único"

                    price_elem = soup.find('span', class_='price-value') or soup.find('div', class_='price')
                    preco = price_elem.text.strip() if price_elem else "N/A"
                    
                    variacoes.append({"quantidade": quantidade, "preco": preco})
                    
        except Exception as e:
            logger.error(f"Erro ao buscar variações Petlove: {e}")
            
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

    
    def run_scraper(self, scraper: BaseSiteScraper) -> bool:
        """Executa um scraper específico"""
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
            success = self.run_scraper(scraper)
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