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
            "Simparic", "Revolution", "NexGard", "NexGard Spectra", "NexGard Combo", "Bravecto", "Frontline", "Advocate",
            "Drontal", "Milbemax", "Vermivet",
            "Rimadyl", "Onsior", "Maxicam", "Carproflan", "Previcox",
            "Apoquel", "Zenrelia",
            "Synulox", "Baytril",
        ]
        
        # Mapeamento expandido com informações da bula
        self.medicamento_info = {
            "Simparic": {
                "empresa": "Zoetis", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "35 dias"
            },
            "Revolution": {
                "empresa": "Zoetis", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "30 dias"
            },
            "NexGard": {
                "empresa": "Boehringer Ingelheim", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "30 dias"
            },
            "NexGard Spectra": {
                "empresa": "Boehringer Ingelheim", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "30 dias"
            },
            "NexGard Combo": {
                "empresa": "Boehringer Ingelheim", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Gatos",
                "porte": "Todos os portes",
                "eficacia": "30 dias"
            },
            "Bravecto": {
                "empresa": "MSD Saúde Animal", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "90 dias"
            },
            "Frontline": {
                "empresa": "Boehringer Ingelheim", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "30 dias"
            },
            "Advocate": {
                "empresa": "Elanco", 
                "categoria": "Antipulgas e Carrapatos",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "30 dias"
            },

            "Drontal": {
                "empresa": "Elanco", 
                "categoria": "Vermífugo",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "Dose única"
            },
            "Milbemax": {
                "empresa": "Elanco", 
                "categoria": "Vermífugo",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "Dose única"
            },
            "Vermivet": {
                "empresa": "Agener União Química", 
                "categoria": "Vermífugo",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "Dose única"
            },
            
            "Rimadyl": {
                "empresa": "Zoetis", 
                "categoria": "Anti-inflamatório",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "12-24 horas"
            },
            "Onsior": {
                "empresa": "Elanco", 
                "categoria": "Anti-inflamatório",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "24 horas"
            },
            "Maxicam": {
                "empresa": "Ourofino Saúde Animal", 
                "categoria": "Anti-inflamatório",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "24 horas"
            },
            "Carproflan": {
                "empresa": "Agener União Química", 
                "categoria": "Anti-inflamatório",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "24 horas"
            },
            "Previcox": {
                "empresa": "Boehringer Ingelheim", 
                "categoria": "Anti-inflamatório",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "24 horas"
            },
            
            "Apoquel": {
                "empresa": "Zoetis", 
                "categoria": "Dermatológico / Antialergico",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "12 horas"
            },
            "Zenrelia": {
                "empresa": "Elanco", 
                "categoria": "Dermatológico / Antialergico",
                "animal": "Cães",
                "porte": "Todos os portes",
                "eficacia": "24 horas"
            },
        
            "Synulox": {
                "empresa": "Zoetis", 
                "categoria": "Antibiótico",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "12 horas"
            },
            "Baytril": {
                "empresa": "Elanco", 
                "categoria": "Antibiótico",
                "animal": "Cães e Gatos",
                "porte": "Todos os portes",
                "eficacia": "24 horas"
            },
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
        """Scraper otimizado para Cobasi usando dados JSON"""
        logger.info("Iniciando scraping Cobasi...")
        produtos_data = []
        
        for medicamento in self.medicamentos:
            url = f"https://www.cobasi.com.br/pesquisa?terms={medicamento}"
            logger.info(f"Buscando {medicamento} na Cobasi...")
            
            response = self.make_request(url)
            if not response:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')

            # Buscar o script que contém os dados JSON estruturados
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

            if script_tag:
                try:
                    # Converter o conteúdo do script de texto JSON para dicionário Python
                    data = json.loads(script_tag.string)
                    
                    # Navegar até a seção de produtos na estrutura JSON
                    produtos_json = data["props"]["pageProps"]["searchResult"]["products"]
                    logger.info(f"Encontrados {len(produtos_json)} produtos no JSON para {medicamento}")
                    
                    # Limitar produtos em modo teste
                    if self.test_mode and produtos_json:
                        produtos_json = produtos_json[:1]  # Apenas 1 produto em modo teste
                    
                    # Processar cada produto encontrado no JSON
                    for produto_json in produtos_json:
                        try:
                            # Extrair dados básicos do produto
                            nome_produto = produto_json.get('name', 'N/A')
                            produto_id = produto_json.get('id', 'N/A')
                            preco_base = produto_json.get('price', 0)
                            marca = produto_json.get('brand', medicamento)
                            
                            logger.info(f"Processando produto: {nome_produto}")
                            
                            # Buscar as variações de SKU (diferentes quantidades/embalagens)
                            skus = produto_json.get('skus', [])
                            
                            if not skus:
                                # Se não há SKUs específicos, usar dados do produto principal
                                info_base = self.medicamento_info.get(medicamento, {})
                                produto_info = {
                                    "categoria": info_base.get("categoria", "N/A"),
                                    "marca": medicamento,
                                    "produto": nome_produto,
                                    "quantidade": "N/A",
                                    "preco": f"R$ {preco_base:.2f}" if isinstance(preco_base, (int, float)) else str(preco_base),
                                    "site": "cobasi.com.br",
                                    "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                                }
                                produtos_data.append(produto_info)
                                logger.info(f"Produto coletado (sem SKUs): {nome_produto}")
                            else:
                                # Processar cada SKU (variação) do produto
                                for sku in skus:
                                    try:
                                        # Extrair informações específicas de cada variação
                                        quantidade = sku.get('name', 'N/A')  # Ex: "1 tablete", "3 tabletes"
                                        preco_sku = sku.get('price', 0)
                                        preco_antigo = sku.get('oldPrice', 0)
                                        disponibilidade = sku.get('available', 'UNKNOWN')
                                        
                                        # Calcular desconto se houver preço antigo
                                        desconto_percent = sku.get('discountPercent', 0)
                                        
                                        # Verificar se o produto está disponível
                                        if disponibilidade != 'AVAILABLE':
                                            logger.warning(f"Produto indisponível: {nome_produto} - {quantidade}")
                                            continue
                                        
                                        # Formatar preço
                                        preco_formatado = f"R$ {preco_sku:.2f}" if isinstance(preco_sku, (int, float)) else str(preco_sku)
                                        
                                        # Obter informações base do medicamento
                                        info_base = self.medicamento_info.get(medicamento, {})
                                        
                                        # Criar registro do produto com todas as informações
                                        produto_info = {
                                            "categoria": info_base.get("categoria", "N/A"),
                                            "marca": medicamento,
                                            "produto": nome_produto,
                                            "quantidade": quantidade,
                                            "preco": preco_formatado,
                                            "preco_antigo": f"R$ {preco_antigo:.2f}" if preco_antigo and isinstance(preco_antigo, (int, float)) else "N/A",
                                            "desconto": f"{desconto_percent}%" if desconto_percent > 0 else "0%",
                                            "disponibilidade": disponibilidade,
                                            "site": "cobasi.com.br",
                                            "produto_id": produto_id,
                                            "sku_id": sku.get('sku', 'N/A'),
                                            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                                        }
                                        
                                        produtos_data.append(produto_info)
                                        logger.info(f"SKU coletado: {nome_produto} - {quantidade} - {preco_formatado}")
                                        
                                    except Exception as e:
                                        logger.error(f"Erro ao processar SKU: {e}")
                                        continue
                            
                        except Exception as e:
                            logger.error(f"Erro ao processar produto JSON da Cobasi: {e}")
                            continue
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar JSON da Cobasi: {e}")
                    # Fallback para método HTML se JSON falhar
                    produtos_data.extend(self._scrape_cobasi_html_fallback(soup, medicamento))
                    
            else:
                logger.warning(f"Não encontrou script __NEXT_DATA__ para {medicamento}")
                # Fallback para método HTML se não encontrar o script JSON
                produtos_data.extend(self._scrape_cobasi_html_fallback(soup, medicamento))
                
            # Delay entre requisições para evitar sobrecarga do servidor
            time.sleep(1)
            
        logger.info(f"Cobasi: Total de {len(produtos_data)} produtos coletados")
        return produtos_data

    def _scrape_cobasi_html_fallback(self, soup, medicamento) -> List[Dict]:
        """Método de fallback usando HTML caso o JSON não funcione"""
        logger.info(f"Usando método HTML fallback para {medicamento}")
        produtos_data = []
        
        try:
            # Buscar produtos usando seletores HTML (método original)
            produtos = soup.find_all('a', {'data-testid': 'product-item-v4'})
            
            if self.test_mode and produtos:
                produtos = produtos[:1]  # Apenas 1 produto em modo teste
            
            for produto in produtos:
                try:
                    # Extrair nome do produto
                    nome_elem = produto.find('h3', class_='body-text-sm')
                    nome = nome_elem.text.strip() if nome_elem else "N/A"
                    
                    # Extrair preço
                    preco_elem = produto.find('span', class_='card-price')
                    preco = preco_elem.text.strip() if preco_elem else "N/A"
                    
                    # Criar registro básico do produto
                    info_base = self.medicamento_info.get(medicamento, {})
                    produto_info = {
                        "categoria": info_base.get("categoria", "N/A"),
                        "marca": medicamento,
                        "produto": nome,
                        "quantidade": "N/A",
                        "preco": preco,
                        "site": "cobasi.com.br",
                        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                        "metodo": "html_fallback"  # Indicar que foi coletado via fallback
                    }
                    produtos_data.append(produto_info)
                    logger.info(f"Produto coletado via HTML: {nome}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto HTML: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro no método HTML fallback: {e}")
            
        return produtos_data
        
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
                    
                    # Buscar variações de quantidade
                    variacoes = self.get_petlove_variations(link_produto) if link_produto else []
                    
                    # Se não houver variações, criar produto único
                    if not variacoes:
                        variacoes = [{"quantidade": "N/A", "preco": preco}]
                    
                    # Criar um produto para cada variação
                    for variacao in variacoes:
                        info_base = self.medicamento_info.get(medicamento, {})
                        produto_info = {
                            "categoria": info_base.get("categoria", "N/A"),
                            "marca": medicamento,
                            "produto": nome,
                            # "animal": info_base.get("animal", "N/A"),
                            # "porte": info_base.get("porte", "N/A"),
                            # "eficacia": info_base.get("eficacia", "N/A"),
                            "quantidade": variacao.get("quantidade", "N/A"),
                            "preco": variacao.get("preco", preco),
                            # "empresa": info_base.get("empresa", "N/A"),
                            "site": "petlove.com.br",
                            # "url": link_produto or "N/A",
                            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                        }
                        produtos_data.append(produto_info)
                        logger.info(f"Produto coletado: {nome} - {variacao.get('quantidade', 'Único')}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Petlove: {e}")
                    
            time.sleep(1)
            
        return produtos_data
    
    def get_petlove_variations(self, url: str) -> List[Dict]:
        """Busca variações de quantidade na Petlove"""
        variacoes = []
        try:
            response = self.make_request(url)
            if not response:
                return variacoes
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar na div de variações (se existir)
            variations_popup = soup.find('div', class_='variant-list flex align-items-center full-width')
            if variations_popup:
                variation_items = variations_popup.find_all('div', class_='badge__container variant-selector__badge')

                for item in variation_items:
                    try:
                        # Quantidade
                        nome_elem = item.find('span', class_='font-bold mb-2')
                        quantidade = nome_elem.text.strip() if nome_elem else "Único"

                        # Preço
                        preco_elem = item.find('div', class_='font-body-s')
                        preco = preco_elem.text.strip() if preco_elem else "N/A"
                        
                        variacoes.append({
                            "quantidade": quantidade,
                            "preco": preco
                        })
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar item de variação Petlove: {e}")
            
            # Se não encontrou no popup, buscar no botão selecionado
            if not variacoes:
                selected_button = soup.find('button', class_='size-select-button')
                if selected_button:
                    quantidade_elem = selected_button.find('b')
                    quantidade = quantidade_elem.text.strip() if quantidade_elem else "Único"

                    # Preço atual
                    price_elem = soup.find('span', class_='price-value') or soup.find('div', class_='price')
                    preco = price_elem.text.strip() if price_elem else "N/A"
                    
                    variacoes.append({
                        "quantidade": quantidade,
                        "preco": preco
                    })
                    
        except Exception as e:
            logger.error(f"Erro ao buscar variações Petlove: {e}")
            
        return variacoes
    
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
                    # Link do produto
                    aux = produto.find('meta', itemprop="url")
                    link_produto = aux.get('content') if aux else "N/A"
                    
                    # Dados do JSON
                    try:
                        produto_json = json.loads(produto.get_text(strip=True))
                        nome = produto_json.get('name', 'N/A').strip()
                        preco_base = produto_json.get('price', 'N/A')
                    except:
                        nome = "N/A"
                        preco_base = "N/A"
                    
                    # Buscar variações de quantidade
                    variacoes = self.get_petz_variations(link_produto) if link_produto != "N/A" else []
                    
                    # Se não houver variações, criar produto único
                    if not variacoes:
                        variacoes = [{"quantidade": "N/A", "preco": preco_base}]
                    
                    # Criar um produto para cada variação
                    for variacao in variacoes:
                        info_base = self.medicamento_info.get(medicamento, {})
                        produto_info = {
                            "categoria": info_base.get("categoria", "N/A"),
                            "marca": medicamento,
                            "produto": nome,
                            # "animal": info_base.get("animal", "N/A"),
                            # "porte": info_base.get("porte", "N/A"),
                            # "eficacia": info_base.get("eficacia", "N/A"),
                            "quantidade": variacao.get("quantidade", "N/A"),
                            "preco": variacao.get("preco", preco_base),
                            # "empresa": info_base.get("empresa", "N/A"),
                            "site": "petz.com.br",
                            # "url": link_produto,
                            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
                        }
                        produtos_data.append(produto_info)
                        logger.info(f"Produto coletado: {nome} - {variacao.get('quantidade', 'Único')}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto Petz: {e}")
                    
            time.sleep(1)
            
        return produtos_data
    
    def get_petz_variations(self, url: str) -> List[Dict]:
        """Busca variações de quantidade na Petz"""
        variacoes = []
        try:
            response = self.make_request(url)
            if not response:
                return variacoes
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar no popup de variações
            popup_variacoes = soup.find('div', id='popupVariacoes')
            if popup_variacoes:
                variation_items = popup_variacoes.find_all('div', class_='variacao-item')
                
                for item in variation_items:
                    logger.debug(f"Processando variação: {item}")
                    try:

                        # Quantidade
                        nome_elem = item.find('div', class_='item-name')
                        quantidade = nome_elem.get_text(strip=True) if nome_elem else "Único"
                        
                        # Preço
                        preco_elem = item.find('b')
                        preco = preco_elem.get_text(strip=True) if preco_elem else "N/A"
                        
                        variacoes.append({
                            "quantidade": quantidade,
                            "preco": preco
                        })
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar variação Petz: {e}")
            
            # Se não encontrou no popup, buscar na variação atual
            if not variacoes:
                nome_var = soup.find('div', class_='nome-variacao')
                if nome_var:
                    qtd_elem = nome_var.find('b')
                    quantidade = qtd_elem.text.strip() if qtd_elem else "Único"
                    
                    # Preço atual
                    price_elem = soup.find('span', class_='price') or soup.find('div', class_='preco')
                    preco = price_elem.text.strip() if price_elem else "N/A"
                    
                    variacoes.append({
                        "quantidade": quantidade,
                        "preco": preco
                    })
                    
        except Exception as e:
            logger.error(f"Erro ao buscar variações Petz: {e}")
            
        return variacoes
    
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
        try:
            cobasi_data = self.scrape_cobasi()
            self.save_to_excel(cobasi_data, f"cobasi_{datetime.now().strftime('%Y%m%d')}.xlsx")
            logger.info(f"Cobasi: {len(cobasi_data)} produtos coletados")
        except Exception as e:
            logger.error(f"Erro no scraping Cobasi: {e}")
        
        # Scraping Petlove
        try:
            petlove_data = self.scrape_petlove()
            self.save_to_excel(petlove_data, f"petlove_{datetime.now().strftime('%Y%m%d')}.xlsx")
            logger.info(f"Petlove: {len(petlove_data)} produtos coletados")
        except Exception as e:
            logger.error(f"Erro no scraping Petlove: {e}")
        
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