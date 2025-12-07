"""
Scraper específico para o site Petlove
Implementa extração de produtos com busca de variações
"""

import logging
from typing import List, Dict
from datetime import datetime
from bs4 import Tag

from scraper_base import ScraperBase
from estruturas_dados import InfoProduto

logger = logging.getLogger(__name__)

class ScraperPetlove(ScraperBase):
    """
    Scraper especializado para Petlove
    Foca na extração de produtos e suas variações de tamanho
    """
    
    @property
    def nome_site(self) -> str:
        return "Petlove"
    
    @property
    def url_base_site(self) -> str:
        return "petlove.com.br"
    
    def construir_url_busca(self, medicamento: str) -> str:
        """Constrói URL de busca na Petlove"""
        return f"https://www.petlove.com.br/busca?q={medicamento}"
    
    def extrair_produtos_pagina(self, soup, medicamento: str, metodo_usado: str) -> List[InfoProduto]:
        """
        Extrai produtos da página da Petlove
        
        Args:
            soup: BeautifulSoup da página
            medicamento: Nome do medicamento
            metodo_usado: requests ou selenium
            
        Returns:
            List[InfoProduto]: Produtos encontrados
        """
        produtos = []
        
        # Buscar elementos de produto na página
        elementos_produto = soup.find_all('div', class_='list__item')
        
        if not elementos_produto:
            logger.info(f"Petlove: Nenhum produto encontrado para {medicamento}")
            return produtos
        
        info_base = self.gerenciador_dados.obter_info_medicamento(medicamento)
        
        # Processar cada produto encontrado
        for elemento_produto in elementos_produto:
            try:
                # Extrair dados básicos do produto
                dados_basicos = self._extrair_dados_basicos(elemento_produto)
                
                if not dados_basicos:
                    continue
                
                # Buscar variações se tiver link do produto
                variacoes = []
                if dados_basicos.get('link_produto'):
                    variacoes = self._buscar_variacoes_produto(dados_basicos['link_produto'])
                
                # Se não encontrou variações, usar dados básicos
                if not variacoes:
                    variacoes = [{
                        'quantidade': dados_basicos.get('quantidade_basica', 'Tamanho Único'),
                        'preco': dados_basicos.get('preco_basico', 'Consultar')
                    }]
                
                # Criar produto para cada variação
                for variacao in variacoes:
                    produto = InfoProduto(
                        categoria=info_base.categoria,
                        marca=medicamento,
                        produto=dados_basicos.get('nome', 'N/A'),
                        quantidade=variacao.get('quantidade', 'Tamanho Único'),
                        preco=variacao.get('preco', 'Consultar'),
                        url=dados_basicos.get('link_produto', 'N/A'),
                        site=self.url_base_site,
                        data_coleta=datetime.now().strftime("%Y-%m-%d"),
                        metodo=f"html_{metodo_usado}"
                    )
                    produtos.append(produto)
                
            except Exception as e:
                logger.warning(f"Petlove: Erro ao processar produto: {e}")
                continue
        
        return produtos
    
    def _extrair_dados_basicos(self, elemento_produto) -> Dict:
        """
        Extrai dados básicos de um elemento de produto
        
        Args:
            elemento_produto: Elemento BeautifulSoup do produto
            
        Returns:
            Dict: Dados básicos extraídos
        """
        try:
            dados = {}
            
            # Extrair nome do produto
            elemento_nome = elemento_produto.find('h2', class_='product-card__name')
            dados['nome'] = elemento_nome.get_text(strip=True) if elemento_nome else "N/A"
            
            # Extrair preço básico
            elemento_preco = (
                elemento_produto.find('p', class_='color-neutral-dark font-bold font-body-s') or
                elemento_produto.find('p', {'data-testid': 'price'})
            )
            dados['preco_basico'] = elemento_preco.get_text(strip=True) if elemento_preco else "Consultar"
            
            # Extrair quantidade básica
            elemento_quantidade = elemento_produto.find('span', class_='button__label')
            dados['quantidade_basica'] = elemento_quantidade.get_text(strip=True) if elemento_quantidade else "Tamanho Único"
            
            # Extrair link do produto
            elemento_link = elemento_produto.find('a', {'itemprop': 'url'})
            if elemento_link:
                link = elemento_link.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://www.petlove.com.br{link}"
                dados['link_produto'] = link
            
            # Verificar se tem botão de mais opções
            botoes = elemento_produto.find_all('button', class_='button')
            dados['tem_variacoes'] = any(
                btn.find('span', class_='button__label', string='+opções') 
                for btn in botoes
            )
            
            return dados
            
        except Exception as e:
            logger.warning(f"Petlove: Erro ao extrair dados básicos: {e}")
            return {}
    
    def _buscar_variacoes_produto(self, url_produto: str) -> List[Dict]:
        """
        Busca variações de quantidade/tamanho na página do produto
        
        Args:
            url_produto: URL do produto para buscar variações
            
        Returns:
            List[Dict]: Lista de variações com quantidade e preço
        """
        variacoes = []
        
        if not url_produto or url_produto == "N/A":
            return variacoes
        
        try:
            # Obter conteúdo da página do produto
            soup_produto, _ = self.gerenciador_conexao.obter_soup_pagina(url_produto)
            
            if not soup_produto:
                return variacoes
            
            # MÉTODO 1: Buscar popup de variações
            popup_variacoes = soup_produto.find('div', class_='variant-list')
            
            if popup_variacoes:
                
                if isinstance(popup_variacoes, Tag):
                    elementos_variacao = popup_variacoes.find_all(
                        'div', class_='badge__container variant-selector__badge'
                    )
                    
                    for elemento in elementos_variacao:
                        try:
                            # Extrair nome da variação
                            if isinstance(elemento, Tag):
                                elemento_nome = elemento.find('span', class_='font-bold mb-2')
                                quantidade = elemento_nome.get_text(strip=True) if elemento_nome else "Tamanho Único"
                                
                                # Extrair preço da variação
                                elemento_preco = elemento.find('div', class_='font-body-s')
                                preco = elemento_preco.get_text(strip=True) if elemento_preco else "Consultar"
                                
                                if preco and preco != "Consultar":
                                    variacoes.append({
                                        "quantidade": quantidade, 
                                        "preco": preco
                                    })
                            else:
                                logger.warning("Petlove: elemento is not a Tag, skipping find.")
                                
                        except Exception as e:
                            logger.warning(f"Petlove: Erro ao processar variação: {e}")
                            continue
                else:
                    logger.warning("Petlove: popup_variacoes is not a Tag, skipping find_all.")
            
            # MÉTODO 2: Fallback para variações na página principal
            if not variacoes:
                botoes_variacao = soup_produto.find_all('button', class_='size-select-button')
                
                for botao in botoes_variacao:
                    try:
                        if isinstance(botao, Tag):
                            quantidade_elem = botao.find('b')
                            quantidade = quantidade_elem.get_text(strip=True) if quantidade_elem else "Tamanho Único"
                        else:
                            quantidade = "Tamanho Único"
                        
                        # Para fallback, pegar preço principal da página
                        preco_elem = soup_produto.find('span', class_='price-value') or soup_produto.find('div', class_='price')
                        preco = preco_elem.get_text(strip=True) if preco_elem else "Consultar"
                        
                        variacoes.append({
                            "quantidade": quantidade,
                            "preco": preco
                        })
                        
                    except Exception as e:
                        logger.warning(f"Petlove: Erro ao processar variação fallback: {e}")
                        continue
                
        except Exception as e:
            logger.warning(f"Petlove: Erro ao buscar variações: {e}")
            
        return variacoes