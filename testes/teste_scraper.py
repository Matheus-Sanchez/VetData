"""
Script de Teste para verificar o funcionamento do Web Scraping
Testa conexão, estrutura HTML e extração básica de dados
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import json
import os

def testar_conexao(url, nome_site):
    """Testa se consegue conectar ao site"""
    print(f"\n{'='*50}")
    print(f"Testando conexão com {nome_site}")
    print(f"URL: {url}")
    print('-'*50)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✓ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Conexão bem-sucedida!")
            return True, response
        else:
            print(f"✗ Erro HTTP: {response.status_code}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("✗ Timeout - Site demorou muito para responder")
        return False, None
    except requests.exceptions.ConnectionError:
        print("✗ Erro de conexão - Verifique sua internet")
        return False, None
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
        return False, None

def analisar_estrutura_html(response, nome_site):
    """Analisa a estrutura HTML para encontrar produtos"""
    print(f"\nAnalisando estrutura HTML de {nome_site}...")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Possíveis seletores de produtos
    seletores = {
        'cobasi': [
            ('div', {'class': 'product-card'}),
            ('div', {'class': 'product-item'}),
            ('div', {'class': 'shelf-item'}),
            ('article', {'class': 'product'}),
            ('div', {'data-testid': 'product-card'}),
        ],
        'petlove': [
            ('div', {'class': 'product'}),
            ('article', {'class': 'product-item'}),
            ('div', {'class': 'card-product'}),
            ('div', {'class': 'product-card'}),
            ('li', {'class': 'product-item'}),
        ],
        'Petz': [
            ('div', {'data-sqe': 'item'}),
            ('div', {'class': 'shop-search-result-view'}),
            ('div', {'class': 'item-card'}),
            ('a', {'data-sqe': 'link'}),
        ]
    }
    
    produtos_encontrados = []
    
    for tag, attrs in seletores.get(nome_site, []):
        elementos = soup.find_all(tag, attrs)
        if elementos:
            print(f"✓ Encontrados {len(elementos)} elementos com seletor: {tag} {attrs}")
            produtos_encontrados.extend(elementos[:3])  # Pega apenas 3 exemplos
            break
    
    if not produtos_encontrados:
        # Tenta busca genérica
        print("Tentando busca genérica...")
        for palavra in ['product', 'item', 'card']:
            elementos = soup.find_all(attrs={'class': lambda x: x and palavra in x.lower()})
            if elementos:
                print(f"✓ Encontrados {len(elementos)} elementos com classe contendo '{palavra}'")
                produtos_encontrados = elementos[:3]
                break
    
    return produtos_encontrados

def extrair_dados_exemplo(elementos, nome_site):
    """Extrai dados de exemplo dos elementos encontrados"""
    print(f"\nExtraindo dados de exemplo...")
    
    dados_extraidos = []
    
    for i, elemento in enumerate(elementos[:3], 1):
        print(f"\nProduto {i}:")
        dados = {}
        
        # Tenta extrair nome
        for tag in ['h2', 'h3', 'span', 'a', 'div']:
            nome = elemento.find(tag, class_=lambda x: x and any(word in str(x).lower() for word in ['name', 'title', 'produto']))
            if nome:
                dados['nome'] = nome.get_text(strip=True)[:100]
                print(f"  Nome: {dados['nome']}")
                break
        
        # Tenta extrair preço
        for tag in ['span', 'div', 'p']:
            preco = elemento.find(tag, class_=lambda x: x and any(word in str(x).lower() for word in ['price', 'preco', 'valor']))
            if preco:
                dados['preco'] = preco.get_text(strip=True)
                print(f"  Preço: {dados['preco']}")
                break
        
        # Tenta extrair link
        link = elemento.find('a', href=True)
        if link:
            dados['link'] = link['href'][:100]
            print(f"  Link: {dados['link']}")
        
        # Texto completo (para análise)
        texto = elemento.get_text(' ', strip=True)[:200]
        print(f"  Texto preview: {texto}...")
        
        # Verifica se tem palavras-chave de medicamentos
        palavras_medicamento = ['vermífugo', 'vermifugo', 'antiparasitário', 'antipulgas', 
                               'carrapaticida', 'anti-inflamatório', 'antibiótico']
        medicamento_encontrado = any(palavra in texto.lower() for palavra in palavras_medicamento)
        
        if medicamento_encontrado:
            print("  ✓ Parece ser um medicamento veterinário")
        
        dados_extraidos.append(dados)
    
    return dados_extraidos

def testar_site_individual(url, nome_site):
    """Testa um site individual"""
    sucesso, response = testar_conexao(url, nome_site)
    
    if sucesso:
        elementos = analisar_estrutura_html(response, nome_site)
        
        if elementos:
            dados = extrair_dados_exemplo(elementos, nome_site)
            return True, dados
        else:
            print(f"✗ Nenhum produto encontrado em {nome_site}")
            print("  Pode ser necessário ajustar os seletores ou usar Selenium")
            return False, []
    
    return False, []

def salvar_relatorio_teste(resultados):
    """Salva relatório do teste"""
    os.makedirs('test_output', exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    arquivo = f'test_output/teste_scraping_{timestamp}.json'
    
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\nRelatório salvo em: {arquivo}")

def main():
    """Função principal de teste"""
    print("="*60)
    print("TESTE DE WEB SCRAPING - MEDICAMENTOS VETERINÁRIOS")
    print("="*60)
    
    sites_teste = {
        'cobasi': 'https://www.cobasi.com.br/busca?q=vermifugo+cachorro',
        'petlove': 'https://www.petlove.com.br/busca?q=vermifugo%20cachorro',
        'petz': 'https://www.petz.com.br/busca?q=vermifugo+cachorro'
    }
    
    resultados = {}
    sites_funcionando = []
    sites_com_problema = []
    
    for nome_site, url in sites_teste.items():
        sucesso, dados = testar_site_individual(url, nome_site)
        
        resultados[nome_site] = {
            'sucesso': sucesso,
            'dados_exemplo': dados,
            'timestamp': datetime.now().isoformat()
        }
        
        if sucesso:
            sites_funcionando.append(nome_site)
        else:
            sites_com_problema.append(nome_site)
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DO TESTE")
    print("="*60)
    
    print(f"\n✓ Sites funcionando: {', '.join(sites_funcionando) if sites_funcionando else 'Nenhum'}")
    print(f"✗ Sites com problema: {', '.join(sites_com_problema) if sites_com_problema else 'Nenhum'}")
    
    # Salva relatório
    salvar_relatorio_teste(resultados)
    
    # Recomendações
    print("\n" + "="*60)
    print("RECOMENDAÇÕES")
    print("="*60)
    
    if sites_com_problema:
        print("\nPara sites com problema, considere:")
        print("1. Verificar se o site usa carregamento dinâmico (JavaScript)")
        print("2. Usar Selenium para sites com conteúdo dinâmico")
        print("3. Verificar se há proteção anti-bot (Cloudflare, reCAPTCHA)")
        print("4. Ajustar os seletores CSS/HTML específicos do site")
        print("5. Adicionar delays entre requisições")

    if 'MerceariaDoAnimal' in sites_com_problema:
        print("\n⚠ MerceariaDoAnimal geralmente requer Selenium devido ao carregamento dinâmico")

    print("\n" + "="*60)
    print("TESTE CONCLUÍDO")
    print("="*60)

if __name__ == "__main__":
    main()