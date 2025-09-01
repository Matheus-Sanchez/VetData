
def debug_page_structure(self, site_name, url):
        """Função de debug para ver a estrutura da página"""
        print(f"\n🔧 DEBUG - Analisando estrutura do {site_name}")
        print(f"URL: {url}")
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Mostrar tags que podem conter produtos
            print("\n📋 Tags encontradas que podem ser produtos:")
            
            possible_selectors = [
                ("div[data-testid*='product']", "Divs com data-testid produto"),
                ("div[class*='product']", "Divs com class produto"),
                ("article", "Tags article"),
                ("div[class*='card']", "Divs com class card"),
                ("li[data-product]", "Li com data-product"),
                ("a[href*='/produto/']", "Links para produtos")
            ]
            
            for selector, description in possible_selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"   • {description}: {len(elements)} encontrados")
                    if len(elements) > 0:
                        # Mostrar exemplo do primeiro elemento
                        first_elem = elements[0]
                        text_content = first_elem.get_text(strip=True)[:100]
                        print(f"     Exemplo: {text_content}...")
            
        except Exception as e:
            print(f"❌ Erro no debug: {e}")

# ==============================================================
# MODO DE TESTE E DEBUG
# ==============================================================

def teste_rapido():
    """Teste rápido para verificar se funciona"""
    tester = TestVetScraper()
    produtos = tester.executar_teste_completo()
    
    if produtos:
        tester.salvar_excel_teste()
    
    return produtos

def debug_sites():
    """Modo debug para analisar estrutura dos sites"""
    print("🔧 MODO DEBUG - Analisando estrutura dos sites")
    print("=" * 60)
    
    tester = TestVetScraper()
    
    urls_debug = [
        ("Petlove", "https://www.petlove.com.br/busca?q=revolution"),
        ("Cobasi", "https://www.cobasi.com.br/busca?q=revolution"),
        ("Petz", "https://www.petz.com.br/busca?q=revolution")
    ]
    
    for site_name, url in urls_debug:
        tester.debug_page_structure(site_name, url)
        time.sleep(2)  # Pausa entre sites#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTE RÁPIDO - Scraper Veterinário
Execução única para testar e ver os dados coletados
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import time
import random
from urllib.parse import urljoin

print("🧪 INICIANDO TESTE DO SCRAPER VETERINÁRIO")
print("=" * 60)

class TestVetScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self.produtos_encontrados = []

    def delay_request(self):
        """Delay pequeno entre requisições"""
        time.sleep(random.uniform(0.5, 1.5))

    def classificar_produto(self, nome_produto):
        """Classificação básica do produto"""
        nome_lower = nome_produto.lower()
        
        # Categoria - mais específica
        if any(word in nome_lower for word in ["vermífugo", "verme", "revolution", "advocate", "drontal", "canex"]):
            categoria = "Vermífugo"
        elif any(word in nome_lower for word in ["pulga", "carrapato", "frontline", "nexgard", "bravecto", "seresto", "antipulgas"]):
            categoria = "Antiparasitário"
        elif any(word in nome_lower for word in ["meloxicam", "anti-inflamatório", "rimadyl", "carprofeno", "maxicam"]):
            categoria = "Anti-inflamatório"
        elif any(word in nome_lower for word in ["alergia", "apoquel", "cytopoint", "coceira", "dermatite"]):
            categoria = "Antialérgico"
        elif any(word in nome_lower for word in ["antibiótico", "amoxicilina", "cefalexina", "doxiciclina"]):
            categoria = "Antibiótico"
        elif any(word in nome_lower for word in ["vitamina", "suplemento", "probiótico", "ômega"]):
            categoria = "Suplemento"
        else:
            categoria = "Outros"
        
        # Animal - mais específico
        if any(word in nome_lower for word in ["cão", "cachorro", "dog", "canino", "cães"]):
            animal = "Cachorro"
        elif any(word in nome_lower for word in ["gato", "felino", "cat", "gatos"]):
            animal = "Gato"
        elif any(word in nome_lower for word in ["cães e gatos", "pets"]):
            animal = "Ambos"
        else:
            animal = "Não identificado"
        
        # Empresa - mais completa
        empresa = "Outros"
        empresas_keywords = {
            "Zoetis": ["zoetis", "revolution", "apoquel", "cytopoint"],
            "Boehringer Ingelheim": ["boehringer", "frontline", "nexgard"],
            "MDS Saúde Animal": ["msd", "mds", "bravecto"],
            "OuroFino Saúde Animal": ["ourofino", "ouro fino"],
            "Virbac": ["virbac", "adapt"],
            "Ceva": ["ceva"],
            "Elanco": ["elanco", "seresto"],
            "Vetnil": ["vetnil"],
            "Agener União Química": ["agener", "união química"]
        }
        
        for emp, keywords in empresas_keywords.items():
            if any(keyword in nome_lower for keyword in keywords):
                empresa = emp
                break
        
        return categoria, animal, empresa

    def extrair_preco(self, texto_preco):
        """Extrai preço do texto"""
        if not texto_preco:
            return "", 0.0
        
        # Busca padrão R$ XX,XX
        match = re.search(r'R\$\s*(\d+(?:\.\d{3})*(?:,\d{2})?)', str(texto_preco))
        if match:
            preco_str = match.group(1)
            try:
                # Converte para float
                preco_num = float(preco_str.replace('.', '').replace(',', '.'))
                return f"R$ {preco_str}", preco_num
            except:
                return str(texto_preco), 0.0
        
        return str(texto_preco), 0.0

    def testar_petlove(self):
        """Teste rápido da Petlove"""
        print("\n🔍 Testando Petlove...")
        
        try:
            url = "https://www.petlove.com.br/busca?q=revolution+vermifugo"
            
            self.delay_request()
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Erro HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            products = []
            
            # Seletores mais específicos para produtos
            items = (soup.find_all("div", {"data-testid": "product-card"}) or 
                    soup.find_all("article", class_=re.compile(r"product")) or
                    soup.find_all("div", class_=re.compile(r"product-item|product-card")) or
                    soup.find_all("li", class_=re.compile(r"product")))
            
            # Se não encontrar, tentar seletores genéricos mas filtrar melhor
            if not items:
                all_divs = soup.find_all("div")
                items = [div for div in all_divs if div.find("h2") or div.find("h3")]
            
            print(f"🔍 Encontrados {len(items)} elementos na página")
            
            for item in items[:10]:  # Pegar mais elementos para filtrar
                try:
                    # Nome do produto - buscar em tags específicas
                    name_elem = (item.find("h3", class_=re.compile(r"product|title")) or 
                                item.find("h2", class_=re.compile(r"product|title")) or
                                item.find("a", {"data-testid": "product-name"}) or
                                item.find("span", class_=re.compile(r"product|name")))
                    
                    if not name_elem:
                        continue
                    
                    nome = name_elem.get_text(strip=True)
                    
                    # Filtrar elementos que não são produtos reais
                    if (len(nome) < 5 or 
                        nome.lower() in ['todos', 'cachorros', 'gatos', 'identificamos', 'localização'] or
                        'você está' in nome.lower() or
                        'localização' in nome.lower()):
                        continue
                    
                    # Buscar preço em elementos específicos
                    price_elem = (item.find("span", {"data-testid": "price"}) or
                                 item.find("div", class_=re.compile(r"price")) or
                                 item.find("span", class_=re.compile(r"price")) or
                                 item.find(text=re.compile(r"R\$\s*\d")))
                    
                    preco_texto = ""
                    if price_elem:
                        if hasattr(price_elem, 'get_text'):
                            preco_texto = price_elem.get_text(strip=True)
                        else:
                            preco_texto = str(price_elem).strip()
                    
                    preco_formatado, preco_numerico = self.extrair_preco(preco_texto)
                    
                    # Classificar
                    categoria, animal, empresa = self.classificar_produto(nome)
                    
                    # Link do produto
                    link_elem = item.find("a", href=True)
                    link = ""
                    if link_elem and link_elem.get("href"):
                        href = link_elem.get("href")
                        if href.startswith('/'):
                            link = f"https://www.petlove.com.br{href}"
                        elif href.startswith('http'):
                            link = href
                    
                    produto = {
                        'site': 'Petlove',
                        'produto': nome,
                        'categoria': categoria,
                        'animal': animal,
                        'empresa': empresa,
                        'preco_texto': preco_formatado or "Não encontrado",
                        'preco_numerico': preco_numerico,
                        'link': link,
                        'data_coleta': datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    
                    products.append(produto)
                    
                except Exception as e:
                    print(f"⚠️  Erro ao processar item: {e}")
                    continue
            
            print(f"✅ Petlove: {len(products)} produtos válidos encontrados")
            return products
            
        except Exception as e:
            print(f"❌ Erro ao acessar Petlove: {e}")
            return []

    def testar_cobasi(self):
        """Teste rápido da Cobasi"""
        print("\n🔍 Testando Cobasi...")
        
        try:
            url = "https://www.cobasi.com.br/busca?q=revolution+vermifugo"
            
            self.delay_request()
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Erro HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            products = []
            
            # Seletores mais específicos para Cobasi
            items = (soup.find_all("div", {"data-product-id": True}) or
                    soup.find_all("article", class_=re.compile(r"product")) or
                    soup.find_all("div", class_=re.compile(r"produto|product-card")) or
                    soup.find_all("li", class_=re.compile(r"product")))
            
            if not items:
                # Fallback: buscar divs com links de produtos
                all_links = soup.find_all("a", href=re.compile(r"/produto/|/p/"))
                items = [link.find_parent() for link in all_links if link.find_parent()]
                items = [item for item in items if item]  # Remove None values
            
            print(f"🔍 Encontrados {len(items)} elementos na página")
            
            for item in items[:10]:
                try:
                    # Nome mais específico
                    name_elem = (item.find("h3", class_=re.compile(r"produto|product|nome")) or
                                item.find("h2", class_=re.compile(r"produto|product|nome")) or
                                item.find("a", class_=re.compile(r"produto|product|nome")) or
                                item.find("span", class_=re.compile(r"produto|product|nome")))
                    
                    if not name_elem:
                        # Tentar pelo link
                        link_elem = item.find("a", href=re.compile(r"/produto/|/p/"))
                        if link_elem:
                            name_elem = link_elem
                    
                    if not name_elem:
                        continue
                    
                    nome = name_elem.get_text(strip=True)
                    
                    # Filtrar nomes inválidos
                    if (len(nome) < 8 or 
                        nome.lower() in ['todos', 'cachorros', 'gatos', 'medicamentos', 'veterinários'] or
                        any(word in nome.lower() for word in ['menu', 'categoria', 'filtro', 'ordenar'])):
                        continue
                    
                    # Buscar preço
                    price_elem = (item.find("span", class_=re.compile(r"preco|price")) or
                                 item.find("div", class_=re.compile(r"preco|price")) or
                                 item.find("strong", class_=re.compile(r"preco|price")))
                    
                    preco_texto = ""
                    if price_elem:
                        preco_texto = price_elem.get_text(strip=True)
                    
                    preco_formatado, preco_numerico = self.extrair_preco(preco_texto)
                    
                    categoria, animal, empresa = self.classificar_produto(nome)
                    
                    # Link
                    link = ""
                    link_elem = item.find("a", href=True)
                    if link_elem and "/produto/" in str(link_elem.get("href", "")):
                        href = link_elem.get("href")
                        if href.startswith('/'):
                            link = f"https://www.cobasi.com.br{href}"
                        elif href.startswith('http'):
                            link = href
                    
                    # Só adicionar se o nome parecer um produto real
                    if len(nome) > 10:  # Nome razoável para um produto
                        produto = {
                            'site': 'Cobasi',
                            'produto': nome,
                            'categoria': categoria,
                            'animal': animal,
                            'empresa': empresa,
                            'preco_texto': preco_formatado or "Não encontrado",
                            'preco_numerico': preco_numerico,
                            'link': link,
                            'data_coleta': datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        
                        products.append(produto)
                    
                except Exception as e:
                    print(f"⚠️  Erro ao processar item: {e}")
                    continue
            
            print(f"✅ Cobasi: {len(products)} produtos válidos encontrados")
            return products
            
        except Exception as e:
            print(f"❌ Erro ao acessar Cobasi: {e}")
            return []

    def testar_petz(self):
        """Teste rápido da Petz"""
        print("\n🔍 Testando Petz...")
        
        try:
            url = "https://www.petz.com.br/busca?q=revolution+vermifugo+cachorro"
            
            self.delay_request()
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Erro HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            products = []
            
            # Seletores específicos para Petz
            items = (soup.find_all("div", {"data-testid": "product-card"}) or
                    soup.find_all("article", class_=re.compile(r"product")) or
                    soup.find_all("div", class_=re.compile(r"product-tile|product-item")) or
                    soup.find_all("li", {"data-product": True}))
            
            if not items:
                # Buscar por links de produtos e pegar os containers pai
                product_links = soup.find_all("a", href=re.compile(r"/produto/|/p/"))
                items = [link.find_parent("div") or link.find_parent("article") for link in product_links]
                items = [item for item in items if item]
            
            print(f"🔍 Encontrados {len(items)} elementos na página")
            
            for item in items[:10]:
                try:
                    # Buscar nome do produto
                    name_elem = (item.find("h3") or
                                item.find("h2") or
                                item.find("span", class_=re.compile(r"product.*name|nome")) or
                                item.find("a", {"title": True}))
                    
                    if not name_elem:
                        continue
                    
                    # Extrair nome
                    if name_elem.has_attr('title'):
                        nome = name_elem.get('title').strip()
                    else:
                        nome = name_elem.get_text(strip=True)
                    
                    # Filtrar elementos inválidos
                    if (len(nome) < 8 or 
                        any(word in nome.lower() for word in ['menu', 'categoria', 'filtrar', 'ordenar', 'busca', 'todos os']) or
                        nome.lower() in ['todos', 'cachorros', 'gatos']):
                        continue
                    
                    # Buscar preço
                    price_elem = (item.find("span", class_=re.compile(r"price|preco")) or
                                 item.find("div", class_=re.compile(r"price|preco")) or
                                 item.find("strong", string=re.compile(r"R\$")))
                    
                    preco_texto = ""
                    if price_elem:
                        preco_texto = price_elem.get_text(strip=True)
                    
                    preco_formatado, preco_numerico = self.extrair_preco(preco_texto)
                    
                    categoria, animal, empresa = self.classificar_produto(nome)
                    
                    # Link
                    link = ""
                    link_elem = item.find("a", href=re.compile(r"/produto/|/p/"))
                    if link_elem:
                        href = link_elem.get("href", "")
                        if href.startswith('/'):
                            link = f"https://www.petz.com.br{href}"
                        elif href.startswith('http'):
                            link = href
                    
                    # Validar se é um produto real (deve ter características de medicamento)
                    if any(word in nome.lower() for word in ['revolution', 'nexgard', 'frontline', 'bravecto', 'vermífugo', 'antipulgas']):
                        produto = {
                            'site': 'Petz',
                            'produto': nome,
                            'categoria': categoria,
                            'animal': animal,
                            'empresa': empresa,
                            'preco_texto': preco_formatado or "Não encontrado",
                            'preco_numerico': preco_numerico,
                            'link': link,
                            'data_coleta': datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        
                        products.append(produto)
                    
                except Exception as e:
                    print(f"⚠️  Erro ao processar item: {e}")
                    continue
            
            print(f"✅ Petz: {len(products)} produtos válidos encontrados")
            return products
            
        except Exception as e:
            print(f"❌ Erro ao acessar Petz: {e}")
            return []

    def executar_teste_completo(self):
        """Executa teste em todos os sites"""
        
        print("🚀 Iniciando coleta de teste...")
        todos_produtos = []
        
        # Testar cada site
        sites_testadores = [
            self.testar_petlove,
            self.testar_cobasi,
            self.testar_petz
        ]
        
        for testador in sites_testadores:
            try:
                produtos_site = testador()
                todos_produtos.extend(produtos_site)
            except Exception as e:
                print(f"❌ Erro no testador: {e}")
        
        self.produtos_encontrados = todos_produtos
        
        # Mostrar resultados
        print(f"\n{'='*60}")
        print(f"📊 RESULTADOS DO TESTE")
        print(f"{'='*60}")
        print(f"Total de produtos encontrados: {len(todos_produtos)}")
        
        if todos_produtos:
            # Agrupar por site
            sites_count = {}
            for produto in todos_produtos:
                site = produto['site']
                sites_count[site] = sites_count.get(site, 0) + 1
            
            print("\n📈 Por site:")
            for site, count in sites_count.items():
                print(f"   • {site}: {count} produtos")
            
            # Mostrar alguns exemplos
            print(f"\n🔍 EXEMPLOS DE PRODUTOS ENCONTRADOS:")
            print("-" * 60)
            
            for i, produto in enumerate(todos_produtos[:5]):  # Mostrar os 5 primeiros
                print(f"\n{i+1}. {produto['produto']}")
                print(f"   Site: {produto['site']}")
                print(f"   Categoria: {produto['categoria']}")
                print(f"   Animal: {produto['animal']}")
                print(f"   Empresa: {produto['empresa']}")
                print(f"   Preço: {produto['preco_texto']}")
                if produto['link']:
                    print(f"   Link: {produto['link'][:80]}...")
        
        return todos_produtos

    def salvar_excel_teste(self):
        """Salva dados do teste em Excel"""
        if not self.produtos_encontrados:
            print("❌ Nenhum produto para salvar")
            return
        
        filename = f"teste_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        df = pd.DataFrame(self.produtos_encontrados)
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Dados_Teste', index=False)
        
        print(f"\n💾 Dados salvos em: {filename}")
        return filename

# Executar teste
if __name__ == "__main__":
    try:
        print("📋 Verificando dependências...")
        
        import sys
        
        # Menu de opções
        print("\n🎯 ESCOLHA O MODO DE TESTE:")
        print("1. Teste rápido (execução normal)")
        print("2. Modo debug (analisar estrutura dos sites)")
        print("3. Teste específico de um site")
        
        if len(sys.argv) > 1:
            opcao = sys.argv[1]
        else:
            opcao = input("\nDigite 1, 2 ou 3: ").strip()
        
        if opcao == "2":
            debug_sites()
        elif opcao == "3":
            print("\nEscolha o site:")
            print("a. Petlove")
            print("b. Cobasi") 
            print("c. Petz")
            
            site_choice = input("Digite a, b ou c: ").strip().lower()
            
            tester = TestVetScraper()
            if site_choice == "a":
                produtos = tester.testar_petlove()
            elif site_choice == "b":
                produtos = tester.testar_cobasi()
            elif site_choice == "c":
                produtos = tester.testar_petz()
            else:
                print("❌ Opção inválida")
                sys.exit(1)
            
            if produtos:
                tester.produtos_encontrados = produtos
                tester.salvar_excel_teste()
        
        else:  # opcao == "1" ou padrão
            produtos = teste_rapido()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        print("\n💡 DICAS:")
        print("   • Verifique se as dependências estão instaladas:")
        print("     pip install requests beautifulsoup4 pandas openpyxl")
        print("   • Verifique sua conexão com a internet")
        print("   • Alguns sites podem bloquear scraping")

print(f"\n{'='*60}")
print("🏁 FIM DO TESTE")

# ==============================================================
# INSTRUÇÕES DE USO:
# ==============================================================
#
# EXECUÇÃO SIMPLES:
# python test_scraper.py
#
# MODO DEBUG (ver estrutura dos sites):
# python test_scraper.py 2
#
# TESTAR SITE ESPECÍFICO:
# python test_scraper.py 3
#
# ==============================================================