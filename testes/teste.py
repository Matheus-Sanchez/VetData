"""
Script de Teste para Verificação do Web Scraping
Testa a conectividade e estrutura HTML dos sites
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def test_site_connection(url, site_name):
    """Testa a conexão com um site"""
    print(f"\n{'='*50}")
    print(f"Testando {site_name}")
    print('='*50)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✓ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tenta encontrar produtos
            possible_selectors = [
                ('a', 'product'),
                ('li', 'card-product'),
                ('div', 'product'),
            ]
            
            found_products = False
            for tag, class_pattern in possible_selectors:
                # Pega todos os elementos da tag
                elements = soup.find_all(tag)
                products = []
                for elem in elements:
                    if 'class' in elem.attrs:
                        class_list = " ".join(elem['class']).lower()
                        if class_pattern in class_list:
                            products.append(elem)
                
                if products:
                    print(f"✓ Encontrados {len(products)} elementos com padrão '{class_pattern}'")
                    found_products = True

                    # Mostra exemplo do primeiro produto
                    first_product = products[0]
                    print("\nExemplo de estrutura HTML encontrada:")
                    print("-" * 30)

                    # Tenta extrair nome
                    name_tags = ['h1', 'h2', 'h3', 'h4', 'a', 'span', 'p', 'div', 'strong']
                    for tag_name in name_tags:
                        name_elem = first_product.find(tag_name)
                        if name_elem and name_elem.get_text(strip=True):
                            if site_name == 'Petz':
                                # {"price":"136.99","name":"Suplemento Alimentar Petz Articular para Cães 250g","priceForSubs":"123.29","id":"177580","sku":"177580","category":"Suplementos e Vitaminas","brand":"Petz","hideSubscriberDiscountPrice":false} 
                                aux = json.loads(name_elem.get_text(strip=True))
                                nome = aux["name"]
                                print(f"Nome do produto: {nome}")
                                preco = aux["price"]
                                print(f"Preço do produto: R$ {preco}")
                            else:
                                print(f"Possível nome: {name_elem.get_text(strip=True)}")
                            break
                    
                    if url_elem := first_product.find('a', href=True):
                        print(f"Link do produto: {url_elem['href']}")
                    
                    # Tenta extrair preço
                    price_elem = None
                    for text_item in first_product.find_all(string=True):
                        if text_item and 'R$' in text_item:
                            price_elem = text_item
                            break
                    if price_elem:
                        print(f"Possível preço encontrado: {price_elem.strip()[:30]}")
                    
                    break
                

            if not found_products:
                print("⚠ Nenhum produto encontrado com os seletores padrão")
                print("  Pode ser necessário ajustar os seletores CSS")
            
            return True
            
        else:
            print(f"✗ Erro: Status Code {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Erro: Timeout na requisição")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Erro: Não foi possível conectar ao site")
        return False
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
        return False

def test_search_product(site_url, search_term):
    """Testa busca por um produto específico"""
    print(f"\nBuscando por '{search_term}'...")
    
    # URLs de busca comuns
    search_patterns = [
        f"{site_url}/busca?q={search_term}",
        f"{site_url}/search?q={search_term}",
        f"{site_url}/pesquisa?termo={search_term}",
        f"{site_url}/produtos?search={search_term}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for pattern in search_patterns:
        try:
            response = requests.get(pattern, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Verifica se encontrou resultados
                text_content = soup.get_text().lower()
                if search_term.lower() in text_content:
                    print(f"✓ Termo '{search_term}' encontrado na página")
                    
                    # Conta ocorrências
                    count = text_content.count(search_term.lower())
                    print(f"  Encontradas {count} ocorrências do termo")
                    
                    return True
                    
        except:
            continue
    
    print(f"⚠ Não foi possível buscar o termo '{search_term}'")
    return False

def extract_sample_data():
    """Extrai dados de exemplo de uma página específica"""
    print("\n" + "="*50)
    print("TESTE DE EXTRAÇÃO DE DADOS")
    print("="*50)
    
    test_url = "https://www.petlove.com.br/cachorro/antipulgas-e-carrapatos"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Procura por produtos com "Bravecto" no nome
            all_text = []
            for text_item in soup.find_all(text=True):
                if text_item and 'bravecto' in str(text_item).lower():
                    all_text.append(text_item)
            
            if all_text:
                print(f"✓ Encontradas {len(all_text)} referências a 'Bravecto'")
                
                # Exemplo de dados estruturados
                sample_product = {
                    'animal': 'Cachorro',
                    'categoria': 'Antipulgas e Carrapatos',
                    'empresa': 'MSD Saúde Animal',
                    'produto': 'Bravecto (exemplo)',
                    'eficacia': '12 semanas',
                    'preco': 'R$ 150,00 (exemplo)',
                    'site': 'petlove.com.br',
                    'data_coleta': datetime.now().strftime('%Y-%m-%d')
                }
                
                print("\nExemplo de estrutura de dados que será coletada:")
                print(json.dumps(sample_product, indent=2, ensure_ascii=False))
                
            else:
                print("⚠ Produto 'Bravecto' não encontrado na página")
                
    except Exception as e:
        print(f"✗ Erro ao extrair dados: {e}")

def main():
    """Função principal de teste"""
    print("="*50)
    print("TESTE DE CONECTIVIDADE E ESTRUTURA DOS SITES")
    print("="*50)
    
    sites_to_test = [
        {
            'name': 'Petlove',
            'url': 'https://www.petlove.com.br',
            'test_url': 'https://www.petlove.com.br/cachorro/medicamentos'
        },
        {
            'name': 'Cobasi',
            'url': 'https://www.cobasi.com.br',
            'test_url': 'https://www.cobasi.com.br/c/cachorro/medicamentos'
        },
        {
            'name': 'Petz',
            'url': 'https://www.petz.com.br',
            'test_url': 'https://www.petz.com.br/cachorro/farmacia'
        }
    ]
    
    results = {}
    
    # Testa conexão com cada site
    for site in sites_to_test:
        success = test_site_connection(site['test_url'], site['name'])
        results[site['name']] = {
            'conexao': 'OK' if success else 'FALHOU',
            'url_testada': site['test_url']
        }
    
    # Testa busca por produto específico
    print("\n" + "="*50)
    print("TESTE DE BUSCA POR PRODUTO")
    print("="*50)
    
    test_search_product('https://www.petlove.com.br', 'bravecto')
    
    # Extrai dados de exemplo
    extract_sample_data()
    
    # Resumo dos testes
    print("\n" + "="*50)
    print("RESUMO DOS TESTES")
    print("="*50)
    
    for site_name, result in results.items():
        status = "✓" if result['conexao'] == 'OK' else "✗"
        print(f"{status} {site_name}: {result['conexao']}")
    
    print("\n" + "="*50)
    print("PRÓXIMOS PASSOS:")
    print("="*50)
    print("1. Se todos os sites estão OK, execute o script principal")
    print("2. Use: python vet_med_scraper.py --test (para modo teste)")
    print("3. Use: python vet_med_scraper.py (para coleta completa)")
    print("\nNOTA: Os seletores CSS podem precisar de ajustes")
    print("dependendo da estrutura atual de cada site.")
    
    # Salva log de teste
    with open('test_log.json', 'w', encoding='utf-8') as f:
        test_data = {
            'data_teste': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'resultados': results
        }
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print("\nLog de teste salvo em 'test_log.json'")


if __name__ == "__main__":
    main()
