"""
Scraper específico para o site Cobasi
Implementa extração de dados via JSON e HTML como fallback
"""

import json
import logging
from typing import List
from datetime import datetime

from scraper_base import ScraperBase
from estruturas_dados import InfoProduto

logger = logging.getLogger(__name__)

class ScraperCobasi(ScraperBase):
    """
    Scraper especializado para Cobasi
    Prioriza extração JSON do __NEXT_DATA__, usa HTML como fallback
    """
    
    @property
    def nome_site(self) -> str:
        return "Cobasi"
    
    @property
    def url_base_site(self) -> str:
        return "cobasi.com.br"
    
    def construir_url_busca(self, medicamento: str) -> str:
        """Constrói URL de busca na Cobasi"""
        return f"https://www.cobasi.com.br/pesquisa?terms={medicamento}"
    
    def extrair_produtos_pagina(self, soup, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Extrai produtos da página da Cobasi
        
        Args:
            soup: BeautifulSoup da página
            medicamento: Nome do medicamento
            metodo_usado: requests ou selenium
            
        Returns:
            List[InfoProduto]: Produtos encontrados
        """
        produtos = []
        
        # MÉTODO 1: Tentar extrair do JSON (mais confiável)
        script_json = soup.find("script", {"id": "__NEXT_DATA__"})
        
        if script_json and script_json.string:
            try:
                produtos = self._extrair_do_json(script_json.string, medicamento, metodo_usado)
                if produtos:
                    logger.info(f"Cobasi: Dados extraídos via JSON para {medicamento}")
                    return produtos
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Cobasi: Falha na extração JSON para {medicamento}: {e}")
        
        # MÉTODO 2: Fallback para extração HTML
        logger.info(f"Cobasi: Usando método HTML para {medicamento}")
        produtos = self._extrair_do_html(soup, medicamento, metodo_usado)
        
        return produtos
    
    def _extrair_do_json(self, conteudo_json: str, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Extrai produtos do JSON da página Next.js
        
        Args:
            conteudo_json: String JSON do script
            medicamento: Nome do medicamento
            metodo_usado: Método de conexão usado
            
        Returns:
            List[InfoProduto]: Produtos extraídos
        """
        produtos = []
        
        try:
            # Parse do JSON
            dados = json.loads(conteudo_json)
            produtos_json = dados.get("props", {}).get("pageProps", {}).get("searchResult", {}).get("products", [])
            
            if not produtos_json:
                logger.info(f"Cobasi: Nenhum produto encontrado no JSON para {medicamento}")
                return produtos
            
            # Obter informações base do medicamento
            info_base = self.gerenciador_dados.obter_info_medicamento(medicamento)
            
            # Processar cada produto encontrado
            for produto_json in produtos_json:
                try:
                    nome_produto = produto_json.get('name', 'N/A')
                    produto_id = str(produto_json.get('id', 'N/A'))
                    preco_base = produto_json.get('price', 0)
                    skus = produto_json.get('skus', [])
                    
                    # Se não tem SKUs, criar produto único
                    if not skus:
                        produto = InfoProduto(
                            categoria=info_base.categoria,
                            marca=medicamento,
                            produto=nome_produto,
                            quantidade="Tamanho Único",
                            preco=self._formatar_preco(preco_base),
                            site=self.url_base_site,
                            data_coleta=datetime.now().strftime("%Y-%m-%d"),
                            produto_id=produto_id,
                            metodo=f"json_{metodo_usado}"
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
                                    preco=self._formatar_preco(preco_sku),
                                    preco_antigo=self._formatar_preco(preco_antigo) if preco_antigo else None,
                                    desconto=f"{desconto_percent}%" if desconto_percent > 0 else None,
                                    disponibilidade=disponibilidade,
                                    site=self.url_base_site,
                                    produto_id=produto_id,
                                    sku_id=str(sku.get('sku', 'N/A')),
                                    data_coleta=datetime.now().strftime("%Y-%m-%d"),
                                    metodo=f"json_{metodo_usado}"
                                )
                                produtos.append(produto)
                                
                            except Exception as e:
                                logger.warning(f"Cobasi: Erro ao processar SKU: {e}")
                                continue
                                
                except Exception as e:
                    logger.warning(f"Cobasi: Erro ao processar produto JSON: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Cobasi: Erro na extração JSON: {e}")
        
        return produtos
    
    def _extrair_do_html(self, soup, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Método de fallback usando extração HTML
        
        Args:
            soup: BeautifulSoup da página
            medicamento: Nome do medicamento
            metodo_usado: Método de conexão usado
            
        Returns:
            List[InfoProduto]: Produtos extraídos via HTML
        """
        produtos = []
        
        try:
            # Buscar elementos de produto na página
            elementos_produto = soup.find_all('a', {'data-testid': 'product-item-v4'})
            
            if not elementos_produto:
                logger.info(f"Cobasi: Nenhum produto encontrado no HTML para {medicamento}")
                return produtos
            
            info_base = self.gerenciador_dados.obter_info_medicamento(medicamento)
            
            # Processar cada elemento de produto encontrado
            for elemento_produto in elementos_produto:
                try:
                    # Extrair nome do produto
                    elemento_nome = elemento_produto.find('h3', class_='body-text-sm')
                    nome = elemento_nome.get_text(strip=True) if elemento_nome else "N/A"
                    
                    # Extrair preço
                    elemento_preco = elemento_produto.find('span', class_='card-price')
                    preco = elemento_preco.get_text(strip=True) if elemento_preco else "N/A"
                    
                    # Extrair URL do produto
                    url = elemento_produto.get('href', 'N/A')
                    if url != 'N/A' and not url.startswith('http'):
                        url = f"https://www.cobasi.com.br{url}"
                    
                    produto = InfoProduto(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=nome,
                        quantidade="Tamanho Único",
                        preco=preco,
                        site=self.url_base_site,
                        url=url,
                        data_coleta=datetime.now().strftime("%Y-%m-%d"),
                        metodo=f"html_{metodo_usado}"
                    )
                    produtos.append(produto)
                    
                except Exception as e:
                    logger.warning(f"Cobasi: Erro ao processar produto HTML: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Cobasi: Erro no método HTML: {e}")
            
        return produtos
    
    def _formatar_preco(self, preco) -> str:
        """
        Formata preço para padrão brasileiro
        
        Args:
            preco: Valor do preço (float, int ou string)
            
        Returns:
            str: Preço formatado
        """
        try:
            if isinstance(preco, (int, float)) and preco > 0:
                return f"R$ {preco:.2f}"
            elif isinstance(preco, str) and preco.strip():
                return preco.strip()
            else:
                return "Consultar"
        except:
            return "N/A"