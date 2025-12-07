"""
Scraper específico para o site Petz
Implementa extração via JSON do atributo product-details
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from scraper_base import ScraperBase
from estruturas_dados import InfoProduto

logger = logging.getLogger(__name__)

class ScraperPetz(ScraperBase):
    """
    Scraper especializado para Petz
    Extrai dados do atributo JSON 'product-details'
    """
    
    @property
    def nome_site(self) -> str:
        return "Petz"
    
    @property
    def url_base_site(self) -> str:
        return "petz.com.br"
    
    def construir_url_busca(self, medicamento: str) -> str:
        """Constrói URL de busca na Petz"""
        return f"https://www.petz.com.br/busca?q={medicamento}"
    
    def extrair_produtos_pagina(self, soup, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Extrai produtos da página da Petz
        
        Args:
            soup: BeautifulSoup da página
            medicamento: Nome do medicamento
            metodo_usado: requests ou selenium
            
        Returns:
            List[InfoProduto]: Produtos encontrados
        """
        produtos = []
        
        # Buscar elementos product-card na página
        elementos_produto = soup.find_all('product-card')
        
        if not elementos_produto:
            logger.info(f"Petz: Nenhum product-card encontrado para {medicamento}")
            return produtos
        
        info_base = self.gerenciador_dados.obter_info_medicamento(medicamento)
        
        # Processar cada elemento de produto
        for elemento_produto in elementos_produto:
            try:
                # Obter dados do atributo product-details
                detalhes_produto = elemento_produto.get('product-details')
                
                if not detalhes_produto:
                    continue
                
                # Processar JSON do produto
                produto_dados = self._processar_json_produto(detalhes_produto, info_base, medicamento, metodo_usado)
                produtos.extend(produto_dados)
                
            except Exception as e:
                logger.warning(f"Petz: Erro ao processar elemento produto: {e}")
                continue
        
        return produtos
    
    def _processar_json_produto(self, detalhes_json: str, info_base, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Processa JSON do atributo product-details
        
        Args:
            detalhes_json: String JSON do produto
            info_base: Informações base do medicamento
            medicamento: Nome do medicamento
            metodo_usado: Método de conexão
            
        Returns:
            List[InfoProduto]: Lista de produtos/variações
        """
        produtos = []
        
        try:
            # Corrigir aspas simples para aspas duplas se necessário
            detalhes_json = detalhes_json.strip().replace("'", '"')
            
            # Parse do JSON
            produto_json = json.loads(detalhes_json)
            
            # Obter variações do produto
            variacoes = produto_json.get('variations', [])
            
            # Se não tem variações, criar uma variação padrão
            if not variacoes:
                variacoes = [{
                    "name": produto_json.get('variationAbreviation', 'Tamanho Único'),
                    "price": produto_json.get('price', 0),
                    "promotionalPrice": produto_json.get('promotional_price', produto_json.get('price', 0)),
                    "discountPercentage": produto_json.get('discountPercentage', 0),
                    "sku": produto_json.get('sku', 'N/A'),
                    "availability": produto_json.get('availability', 'UNKNOWN'),
                    "id": produto_json.get('id', 'N/A'),
                }]
            
            # Processar cada variação
            for variacao in variacoes:
                try:
                    produto = self._criar_produto_da_variacao(
                        produto_json, variacao, info_base, medicamento, metodo_usado
                    )
                    
                    if produto:
                        produtos.append(produto)
                        
                except Exception as e:
                    logger.warning(f"Petz: Erro ao processar variação: {e}")
                    continue
            
        except json.JSONDecodeError as e:
            logger.warning(f"Petz: Erro ao decodificar JSON: {e}")
        except Exception as e:
            logger.warning(f"Petz: Erro ao processar JSON do produto: {e}")
        
        return produtos
    
    def _criar_produto_da_variacao(self, produto_json: dict, variacao: dict, info_base, medicamento: str, metodo_usado: str) -> Optional[InfoProduto]:
        """
        Cria objeto InfoProduto a partir de uma variação
        
        Args:
            produto_json: JSON completo do produto
            variacao: JSON da variação específica
            info_base: Informações base do medicamento
            medicamento: Nome do medicamento
            metodo_usado: Método de conexão
            
        Returns:
            InfoProduto: Produto criado
        """
        try:
            # Extrair dados da variação
            quantidade = variacao.get('name', 'Tamanho Único')
            preco_original = variacao.get('price', 0)
            preco_promocional = variacao.get('promotionalPrice', preco_original)
            desconto_percentual = variacao.get('discountPercentage', 0)
            disponibilidade = variacao.get('availability', 'UNKNOWN')
            sku = variacao.get('sku', 'N/A')
            
            # Dados gerais do produto
            nome_produto = produto_json.get('name', 'N/A')
            produto_id = str(produto_json.get('id', 'N/A'))
            url_produto = produto_json.get('url', 'N/A')
            
            # Formatar preços
            preco_final = self._formatar_preco(preco_promocional)
            preco_antigo = self._formatar_preco(preco_original) if preco_original != preco_promocional else None
            desconto = f"{desconto_percentual}%" if desconto_percentual > 0 else None
            
            return InfoProduto(
                categoria=info_base.categoria,
                marca=medicamento,
                produto=nome_produto,
                quantidade=quantidade,
                preco=preco_final,
                preco_antigo=preco_antigo,
                desconto=desconto,
                disponibilidade=disponibilidade,
                site=self.url_base_site,
                produto_id=produto_id,
                sku_id=str(sku),
                url=url_produto,
                data_coleta=datetime.now().strftime("%Y-%m-%d"),
                metodo=f"json_{metodo_usado}"
            )
            
        except Exception as e:
            logger.warning(f"Petz: Erro ao criar produto: {e}")
            return None
    
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
                # Se já é string, limpar e retornar
                return preco.strip()
            else:
                return "Consultar"
        except:
            return "N/A"