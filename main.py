# Arrumar html de Petz
# Arrumar eficacia de Petlove

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import os
import json
from typing import Dict, List, Optional
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VetMedicineScraper:
    """Scraper para coletar dados de medicamentos veterinários de e-commerces"""
    
    def __init__(self, test_mode=False):
        """
        Inicializa o scraper
        
        Args:
            test_mode (bool): Se True, coleta apenas 1 produto por medicamento
        """
        self.test_mode = test_mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Lista de medicamentos para buscar
        self.medicamentos = [
            "Simparic", "Revolution", "NexGard", "NextGard Spectra", "Bravecto", "Frontline", "Advocate",
            "Drontal", "Milbemax", "Vermivet",
            "Rimadyl", "Onsior", "Maxicam", "Carproflan", "Previcox",
            "Apoquel", "Zenrelia",
            "Synulox", "Baytril",
        ]
        
        # Mapeamento de medicamentos para empresas e categorias
        self.medicamento_info = {
            "Simparic": {"empresa": "Zoetis", "categoria": "Antipulgas e Carrapatos"},
            "Revolution": {"empresa": "Zoetis", "categoria": "Antipulgas e Carrapatos"},
            "NexGard": {"empresa": "Boehringer Ingelheim", "categoria": "Antipulgas e Carrapatos"},
            "NexGard Spectra": {"empresa": "Boehringer Ingelheim", "categoria": "Antipulgas e Carrapatos"},
            "Bravecto": {"empresa": "MSD Saúde Animal", "categoria": "Antipulgas e Carrapatos"},
            "Frontline": {"empresa": "Boehringer Ingelheim", "categoria": "Antipulgas e Carrapatos"},
            "Advocate": {"empresa": "Elanco", "categoria": "Antipulgas e Carrapatos"},

            "Drontal": {"empresa": "Elanco", "categoria": "Vermífugo"},
            "Milbemax": {"empresa": "Elanco", "categoria": "Vermífugo"},
            "Vermivet": {"empresa": "Agener União Química", "categoria": "Vermífugo"},
            
            "Rimadyl": {"empresa": "Zoetis", "categoria": "Anti-inflamatório"},
            "Onsior": {"empresa": "Elanco", "categoria": "Anti-inflamatório"},
            "Maxicam": {"empresa": "Ourofino Saúde Animal", "categoria": "Anti-inflamatório"},
            "Carproflan": {"empresa": "Agener União Química", "categoria": "Anti-inflamatório"},
            "Previcox": {"empresa": "Boehringer Ingelheim", "categoria": "Anti-inflamatório"},
            
            "Apoquel": {"empresa": "Zoetis", "categoria": "Dermatológico / Antialergico"},
            "Zenrelia": {"empresa": "Elanco", "categoria": "Dermatológico / Antialergico"},
        
            "Synulox": {"empresa": "Zoetis", "categoria": "Antibiótico"},
            "Baytril": {"empresa": "Elanco", "categoria": "Antibiótico"},

        }
        
    def make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Faz requisição com retry"""
        for i in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return response
                logger.warning(f"Status code {response.status_code} para {url}")
            except Exception as e:
                logger.error(f"Erro na requisição {url}: {e}")
                if i < max_retries - 1:
                    time.sleep(2 ** i)  # Backoff exponencial
        return None
    
    def scrape_cobasi(self) -> List[Dict]:
        """Scraper para Cobasi"""
        logger.info("Iniciando scraping Cobasi...")
        produtos_data = []
        
        for medicamento in self.medicamentos:
            url = f"https://www.cobasi.com.br/pesquisa?terms={medicamento}"
            logger.info(f"Buscando {medicamento} na Cobasi...")
            
            response = self.make_request(url)
            if not response:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            produtos = soup.find_all('a', {'data-testid': 'product-item-v4'})
            
            if self.test_mode and produtos:
                produtos = produtos[:1]  # Apenas 1 produto em modo teste
            
            for produto in produtos:
                try:
                    # Dados básicos
                    nome_elem = produto.find('h3', class_='body-text-sm')
                    nome = nome_elem.text.strip() if nome_elem else "N/A"
                    
                    preco_elem = produto.find('span', class_='card-price')
                    preco = preco_elem.text.strip() if preco_elem else "N/A"
                    
                    # Link para detalhes
                    link_produto = produto.get('href')
                    if link_produto and not link_produto.startswith('http'):
                        link_produto = f"https://www.cobasi.com.br{link_produto}"
                    
                    # Buscar ficha técnica
                    ficha_tecnica = self.get_cobasi_details(link_produto) if link_produto else {}
                    
                    # Montar dados do produto
                    info_base = self.medicamento_info.get(medicamento, {})
                    produto_info = {
                        "categoria": info_base.get("categoria", "N/A"),
                        "marca": medicamento,
                        "produto": nome,
                        "animal": ficha_tecnica.get("animal", info_base.get("animal", "N/A")),
                        "porte": ficha_tecnica.get("porte", "N/A"),
                        "eficacia": ficha_tecnica.get("eficacia", "N/A"),
                        "quantidade": ficha_tecnica.get("quantidade", "N/A"),
                        "preco": preco,
                        "empresa": info_base.get("empresa", "N/A"),
                        "site": "cobasi.com.br",
                        "url": link_produto or "N/A",
                        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                    }
                    produtos_data.append(produto_info)
                    logger.info(f"Produto coletado: {nome}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Cobasi: {e}")
                    
            time.sleep(1)  # Delay entre requisições
            
        return produtos_data
    
    def get_cobasi_details(self, url: str) -> Dict:
        """Busca detalhes da ficha técnica na Cobasi"""
        details = {}
        try:
            response = self.make_request(url)
            if not response:
                return details
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar detalhes
            # Para pegar os outros itens com variação de unidade, se tiver, fazer busca em url, fazendo uma copia do remedio so mudando quantidade e preço
            accordion = soup.find('div', {'data-testid': 'accordion-details'})
            if accordion:
                tables = accordion.find_all('thead')
                if len(tables) >= 11:
                    # Animal (11° thead, 2° th)
                    animal_row = tables[10].find_all('th')
                    if len(animal_row) >= 2:
                        details['animal'] = animal_row[1].text.strip()
                    
                    # Porte (1° thead, 2° th)
                    porte_row = tables[0].find_all('th')
                    if len(porte_row) >= 2:
                        details['porte'] = porte_row[1].text.strip()
                    
                    # Eficácia (8° thead, 2° th)
                    if len(tables) >= 8:
                        eficacia_row = tables[7].find_all('th')
                        if len(eficacia_row) >= 2:
                            details['eficacia'] = eficacia_row[1].text.strip()
            
            # Quantidade
            selected_div = soup.find('div', class_='selected')
            if selected_div:
                details['quantidade'] = selected_div.text.strip()
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes Cobasi: {e}")
            
        return details
    
    def scrape_petlove(self) -> List[Dict]:
        """Scraper para Petlove"""
        logger.info("Iniciando scraping Petlove...")
        produtos_data = []
        
        for medicamento in self.medicamentos:
            url = f"https://www.petlove.com.br/busca?q={medicamento}"
            logger.info(f"Buscando {medicamento} na Petlove...")
            
            response = self.make_request(url)
            if not response:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            produtos = soup.find_all('div', class_='list__item')
            
            if self.test_mode and produtos:
                produtos = produtos[:1]
            
            for produto in produtos:
                try:
                    # Dados básicos
                    nome_elem = produto.find('h2', class_='product-card__name')
                    nome = nome_elem.text.strip() if nome_elem else "N/A"

                    preco_elem = produto.find('p', class_='color-neutral-dark font-bold font-body-s') or produto.find('p', {'data-testid': 'price'})
                    preco = preco_elem.text.strip() if preco_elem else "N/A"
                    
                    # Link para detalhes
                    link_elem = produto.find('a', {'itemprop': 'url'})
                    link_produto = link_elem.get('href') if link_elem else None
                    if link_produto and not link_produto.startswith('http'):
                        link_produto = f"https://www.petlove.com.br{link_produto}"
                    
                    # Buscar ficha técnica
                    ficha_tecnica = self.get_petlove_details(link_produto) if link_produto else {}
                    
                    # Montar dados do produto
                    info_base = self.medicamento_info.get(medicamento, {})
                    produto_info = {
                        "animal": ficha_tecnica.get("animal", info_base.get("animal", "N/A")),
                        "categoria": info_base.get("categoria", "N/A"),
                        "empresa": info_base.get("empresa", "N/A"),
                        "produto": nome,
                        "eficacia": ficha_tecnica.get("eficacia", "N/A"),
                        "porte": ficha_tecnica.get("porte", "N/A"),
                        "quantidade": ficha_tecnica.get("quantidade", "N/A"),
                        "preco": preco,
                        "site": "petlove.com.br",
                        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                        "url": link_produto or "N/A"
                    }
                    produtos_data.append(produto_info)
                    logger.info(f"Produto coletado: {nome}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Petlove: {e}")
                    
            time.sleep(1)
            
        return produtos_data
    
    def get_petlove_details(self, url: str) -> Dict:
        """Busca detalhes da ficha técnica na Petlove"""
        details = {}
        try:
            response = self.make_request(url)
            if not response:
                return details
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar properties lists
            properties = soup.find_all('div', class_='properties__list')
            
            # if len(properties) >= 5:
                # Animal (1° div, 2° div interno)
                # animal_divs = properties[0].find_all('div')
                # if len(animal_divs) >= 2:
                #     details['animal'] = animal_divs[1].text.strip()
                
                # Porte (2° div, 2° div interno)
                # porte_divs = properties[1].find_all('div')
                # if len(porte_divs) >= 2:
                #     details['porte'] = porte_divs[1].text.strip()
                
                # Eficácia (5° div, 2° div interno)
                # eficacia_divs = properties[4].find_all('div')
                # if len(eficacia_divs) >= 2:
                #     details['eficacia'] = eficacia_divs[1].text.strip()
            
            # Quantidade
            # Para pegar as outras unidades usar div class="variant-list", tem preço e unidade (fazer copia)
            variant_selected_button = soup.find('button', class_='size-select-button')
            variant_selected = variant_selected_button.find('b')
            variants = soup.find('div', class_='produto-popup-variacoes hidden').find_all('div', class_="variacao-item")
            for var in variants:
                unidade_var = var.find('div', class_='item-name')
                if unidade_var:
                    details['quantidade'] = unidade_var.text.strip()
            # if variant_selected:
            #     qtd_elem = variant_selected.find('span')
            #     if qtd_elem:
            #         details['quantidade'] = qtd_elem.text.strip()
                    
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes Petlove: {e}")
            
        return details
    
    def scrape_petz(self) -> List[Dict]:
        """Scraper para Petz"""
        logger.info("Iniciando scraping Petz...")
        produtos_data = []
        
        for medicamento in self.medicamentos:
            url = f"https://www.petz.com.br/busca?q={medicamento}"
            logger.info(f"Buscando {medicamento} na Petz...")
            
            response = self.make_request(url)
            if not response:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            produtos = soup.find_all('li', class_='card-product')
            
            if self.test_mode and produtos:
                produtos = produtos[:1]
            
            for produto in produtos:
                try:
                    # {"price":"103.99","name":"Revolution Zoetis 6% 0.75ml para Gatos 2,6Kg a 7,5Kg","promotional_price":"72.79","priceForSubs":"72.79","id":"74618","sku":"74618","category":"Antipulgas e Carrapatos","brand":"Zoetis","hideSubscriberDiscountPrice":false}
                    # Em manutenção
                    aux = produto.find('meta', itemprop="url")
                    link_produto = aux.get('content') if aux else "N/A"
                    # aux = produto.find('a', class_="card-link-product")
                    # logger.info(f"Aux: {aux.get_text(strip=True)}")
                    # json_prod = json.loads(aux.get_text(strip=True))
                    # preco = json_prod['price']
                    # nome = json_prod['name']
                    # link_produto = json_prod['url']
                    # variacao = json_prod['variationDescription']
                    # logger.info(json_prod)
                    
                    # Dados básicos
                    aux = json.loads(produto.get_text(strip=True))
                    nome = aux['name'].strip() if aux else "N/A"
                    preco = aux['price'].strip() if aux else "N/A"

                    
                    # Link para detalhes
                    # link_elem = produto.find('a', class_='card-link-product')
                    # link_produto = link_elem.get('href') if link_elem else None
                    # if link_produto and not link_produto.startswith('http'):
                    #     link_produto = f"https://www.petz.com.br{link_produto}"
                    
                    # Buscar ficha técnica
                    ficha_tecnica = self.get_petz_details(link_produto) if link_produto else {}
                    
                    # Montar dados do produto
                    info_base = self.medicamento_info.get(medicamento, {})
                    produto_info = {
                        "categoria": info_base.get("categoria", "N/A"),
                        "marca": medicamento,
                        "produto": nome,
                        "animal": ficha_tecnica.get("animal", info_base.get("animal", "N/A")),
                        "porte": ficha_tecnica.get("porte", "N/A"),
                        "eficacia": ficha_tecnica.get("eficacia", "N/A"),
                        "quantidade": ficha_tecnica.get("quantidade", "N/A"),
                        "preco": preco,
                        "empresa": info_base.get("empresa", "N/A"),
                        "site": "petz.com.br",
                        "url": link_produto or "N/A",
                        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                    }
                    produtos_data.append(produto_info)
                    logger.info(f"Produto coletado: {nome}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Petz: {e}")
                    
            time.sleep(1)
            
        return produtos_data
    
    def get_petz_details(self, url: str) -> Dict:
        """Busca detalhes da ficha técnica na Petz"""
        details = {}
        try:
            response = self.make_request(url)
            if not response:
                return details
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar specifications
            specs_section = soup.find('section', id='specifications')
            if specs_section:
                spec_items = specs_section.find_all('li', class_='specifications')
                
                # Animal (2° li, 2° span)
                if len(spec_items) >= 2:
                    animal_spans = spec_items[1].find_all('span')
                    if len(animal_spans) >= 2:
                        details['animal'] = animal_spans[1].text.strip()
                
                # Porte (3° li, 2° span)
                if len(spec_items) >= 3:
                    porte_spans = spec_items[2].find_all('span')
                    if len(porte_spans) >= 2:
                        details['porte'] = porte_spans[1].text.strip()
            
            # Eficácia (buscar no texto com regex)
            spec_content = soup.find('div', class_='spec-content')
            if spec_content:
                texto = spec_content.text
                match = re.search(r'protege por (\d+ dias)', texto, re.IGNORECASE)
                if match:
                    details['eficacia'] = match.group(1)
            
            # Quantidade
            # Para pegar as outras unidades, pegar pela div id="popupVariacoes", tem o preço lá tambem (fazer cópia)
            nome_var = soup.find('div', class_='nome-variacao')
            if nome_var:
                qtd_elem = nome_var.find('b')
                if qtd_elem:
                    details['quantidade'] = qtd_elem.text.strip()
                    
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes Petz: {e}")
            
        return details
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """Salva dados em arquivo Excel"""
        if not data:
            logger.warning(f"Nenhum dado para salvar em {filename}")
            return
            
        df = pd.DataFrame(data)
        
        # Criar pasta se não existir
        os.makedirs('dados_coletados', exist_ok=True)
        
        filepath = f"dados_coletados/{filename}"
        df.to_excel(filepath, index=False)
        logger.info(f"Dados salvos em {filepath}")
        
    def run(self):
        """Executa o scraping completo"""
        logger.info("=" * 50)
        logger.info(f"Iniciando scraping - Modo: {'TESTE' if self.test_mode else 'COMPLETO'}")
        logger.info("=" * 50)
        
        # Scraping Cobasi
        # try:
        #     cobasi_data = self.scrape_cobasi()
        #     self.save_to_excel(cobasi_data, f"cobasi_{datetime.now().strftime('%Y%m%d')}.xlsx")
        #     logger.info(f"Cobasi: {len(cobasi_data)} produtos coletados")
        # except Exception as e:
        #     logger.error(f"Erro no scraping Cobasi: {e}")
        
        # # Scraping Petlove
        # try:
        #     petlove_data = self.scrape_petlove()
        #     self.save_to_excel(petlove_data, f"petlove_{datetime.now().strftime('%Y%m%d')}.xlsx")
        #     logger.info(f"Petlove: {len(petlove_data)} produtos coletados")
        # except Exception as e:
        #     logger.error(f"Erro no scraping Petlove: {e}")
        
        # Scraping Petz
        try:
            petz_data = self.scrape_petz()
            self.save_to_excel(petz_data, f"petz_{datetime.now().strftime('%Y%m%d')}.xlsx")
            logger.info(f"Petz: {len(petz_data)} produtos coletados")
        except Exception as e:
            logger.error(f"Erro no scraping Petz: {e}")
        
        logger.info("=" * 50)
        logger.info("Scraping finalizado!")
        logger.info("=" * 50)

def main():
    """Função principal"""
    print("\n" + "=" * 50)
    print("SCRAPER DE MEDICAMENTOS VETERINÁRIOS")
    print("=" * 50)
    print("\nEscolha o modo de execução:")
    print("1 - Modo TESTE (coleta apenas 1 produto por medicamento)")
    print("2 - Modo COMPLETO (coleta todos os produtos)")
    
    escolha = input("\nDigite sua escolha (1 ou 2): ").strip()
    
    test_mode = escolha == "1"
    
    if test_mode:
        print("\n>>> Executando em modo TESTE...")
        print(">>> Será coletado apenas 1 produto por medicamento para verificação")
    else:
        print("\n>>> Executando em modo COMPLETO...")
        print(">>> Todos os produtos serão coletados (pode demorar)")
    
    scraper = VetMedicineScraper(test_mode=test_mode)
    scraper.run()
    
    print("\n>>> Processo finalizado!")
    print(f">>> Verifique os arquivos Excel na pasta 'dados_coletados'")

if __name__ == "__main__":
    main()