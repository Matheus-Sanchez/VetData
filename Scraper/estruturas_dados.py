"""
Estruturas de dados para o scraper de medicamentos veterinários
Contém dataclasses para organizar informações de medicamentos e produtos
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class InfoMedicamento:
    """
    Informações básicas sobre medicamentos veterinários
    """
    empresa: str         # Empresa fabricante
    categoria: str       # Categoria do medicamento (antipulgas, vermífugo, etc.)
    animal: str          # Animal alvo (cães, gatos, etc.)
    porte: str           # Porte do animal
    eficacia: str        # Duração da eficácia

@dataclass  
class InfoProduto:
    """
    Dados coletados de cada produto nos sites
    """
    categoria: str                          # Categoria do medicamento
    marca: str                              # Marca/nome do medicamento
    produto: str                            # Nome completo do produto
    quantidade: str                         # Quantidade/tamanho do produto
    preco: str                              # Preço atual
    site: str                               # Site onde foi coletado
    data_coleta: str                        # Data da coleta
    preco_antigo: Optional[str] = None      # Preço original (se em promoção)
    desconto: Optional[str] = None          # Percentual de desconto
    disponibilidade: Optional[str] = None   # Status de disponibilidade
    produto_id: Optional[str] = None        # ID único do produto
    sku_id: Optional[str] = None            # SKU da variação
    url: Optional[str] = None               # URL do produto
    metodo: Optional[str] = None            # Método usado para coleta (requests/selenium)

    def __post_init__(self):
        """Define data_coleta automaticamente se não fornecida"""
        if not self.data_coleta:
            self.data_coleta = datetime.now().strftime("%Y-%m-%d")