#!/usr/bin/env python3
"""
Sistema Principal de Scraping de Medicamentos Veterinários
Versão refatorada com conexões híbridas (Requests + Selenium)

Interface de linha de comando para execução do scraper
"""

import sys
import logging
from gerenciador_principal import GerenciadorScrapingMedicamentos

def exibir_cabecalho():
    """Exibe cabeçalho do programa"""
    print("\n" + "="*70)
    print("SCRAPER DE MEDICAMENTOS VETERINÁRIOS - VERSÃO HÍBRIDA")
    print("="*70)
    print("\nEste sistema coleta preços de medicamentos veterinários dos")
    print("principais pet shops online do Brasil usando conexão inteligente:")
    print("• Tenta REQUESTS primeiro (mais rápido)")
    print("• USA SELENIUM como fallback (quando necessário)")
    print("\nSites suportados:")
    print("• Cobasi (cobasi.com.br)")
    print("• Petlove (petlove.com.br)")  
    print("• Petz (petz.com.br)")

def exibir_opcoes_execucao():
    """Exibe opções de execução disponíveis"""
    print("\n" + "-"*50)
    print("MODOS DE EXECUÇÃO DISPONÍVEIS:")
    print("-"*50)
    print("1. MODO TESTE")
    print("   • Coleta apenas 1 produto por medicamento")
    print("   • Execução mais rápida para verificações")
    print("   • Ideal para testar funcionamento")
    print("   • Logs otimizados para terminal")
    
    print("\n2. MODO COMPLETO")
    print("   • Coleta todos os produtos encontrados")
    print("   • Processo completo e detalhado")
    print("   • Recomendado para coleta real de dados")
    print("   • Gera relatório consolidado")
    
    print("\n3. SITE ESPECÍFICO")
    print("   • Executa scraping em apenas um site")
    print("   • Útil para testes direcionados")
    print("   • Permite focar em site problemático")

def obter_escolha_usuario():
    """
    Obtém escolha do usuário com validação
    
    Returns:
        str: Opção escolhida pelo usuário
    """
    while True:
        try:
            escolha = input("\nDigite sua escolha (1, 2 ou 3): ").strip()
            if escolha in ['1', '2', '3']:
                return escolha
            else:
                print("Escolha inválida. Digite 1, 2 ou 3.")
        except KeyboardInterrupt:
            print("\n\nExecução cancelada pelo usuário.")
            sys.exit(0)
        except Exception:
            print("Erro ao ler entrada. Tente novamente.")

def obter_site_especifico(sites_disponiveis):
    """
    Obtém nome do site específico do usuário
    
    Args:
        sites_disponiveis: Lista de sites disponíveis
        
    Returns:
        str: Nome do site escolhido
    """
    print("\n" + "-"*30)
    print("SITES DISPONÍVEIS:")
    print("-"*30)
    for site in sites_disponiveis:
        print(f"• {site}")

    while True:
        try:
            site_escolhido = input("\nDigite o nome do site: ").strip()
            
            # Buscar site (case-insensitive)
            for site in sites_disponiveis:
                if site.lower() == site_escolhido.lower():
                    return site
            
            print(f"Site '{site_escolhido}' não encontrado.")
            print(f"Sites disponíveis: {', '.join(sites_disponiveis)}")
            
        except KeyboardInterrupt:
            print("\n\nExecução cancelada pelo usuário.")
            sys.exit(0)
        except Exception:
            print("Erro ao ler entrada. Tente novamente.")

def executar_modo_teste():
    """Executa sistema em modo teste"""
    print("\n" + "="*50)
    print("MODO TESTE SELECIONADO")
    print("="*50)
    print("• Coletando apenas 1 produto por medicamento")
    print("• Processo otimizado para verificação rápida")
    print("• Arquivos salvos na pasta 'dados_testes'")
    
    try:
        gerenciador = GerenciadorScrapingMedicamentos(modo_teste=True)
        
        # Validar sistema antes de executar
        status = gerenciador.validar_sistema()
        print(f"\nSistema validado: {len([s for s in status['scrapers'] if s['ativo']])} scrapers ativos")
        
        print("\nIniciando execução...")
        gerenciador.executar_todos_scrapers()
        
        print("\n✅ MODO TESTE CONCLUÍDO!")
        print("📁 Verifique os arquivos na pasta 'dados_testes/'")
        
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        print("📋 Verifique os logs para mais detalhes")

def executar_modo_completo():
    """Executa sistema em modo completo"""
    print("\n" + "="*50)
    print("MODO COMPLETO SELECIONADO")
    print("="*50)
    print("• Coletando todos os produtos encontrados")
    print("• Processo completo pode demorar vários minutos")
    print("• Arquivos salvos na pasta 'dados_coletados'")
    print("• Relatório consolidado será gerado")
    
    try:
        gerenciador = GerenciadorScrapingMedicamentos(modo_teste=False)
        
        # Mostrar estatísticas dos medicamentos
        # stats_medicamentos = gerenciador.obter_estatisticas_medicamentos()
        # total_medicamentos = sum(info['quantidade'] for info in stats_medicamentos.values())
        # print(f"\n📊 {total_medicamentos} medicamentos cadastrados em {len(stats_medicamentos)} categorias")
        
        print("\nIniciando execução completa...")
        gerenciador.executar_todos_scrapers()
        
        print("\n✅ MODO COMPLETO CONCLUÍDO!")
        print("📁 Verifique os arquivos na pasta 'dados_coletados/'")
        print("📋 Relatório consolidado disponível")
        
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        print("📋 Verifique os logs para mais detalhes")

def executar_site_especifico():
    """Executa scraping de site específico"""
    print("\n" + "="*50)
    print("MODO SITE ESPECÍFICO SELECIONADO")
    print("="*50)
    
    try:
        # Criar gerenciador temporário para obter lista de sites
        gerenciador_temp = GerenciadorScrapingMedicamentos(modo_teste=False)
        sites_disponiveis = gerenciador_temp.obter_lista_sites_disponiveis()
        
        # Obter site escolhido
        site_escolhido = obter_site_especifico(sites_disponiveis)
        
        print(f"\n🎯 Executando scraping específico para {site_escolhido}")
        print("• Todos os medicamentos serão processados")
        print("• Arquivo individual será gerado")
        
        # Executar scraping específico
        gerenciador = GerenciadorScrapingMedicamentos(modo_teste=False)
        gerenciador.executar_site_especifico(site_escolhido)
        
        print(f"\n✅ SCRAPING DE {site_escolhido.upper()} CONCLUÍDO!")
        print("📁 Arquivo salvo na pasta 'dados_coletados/'")
        
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        print("📋 Verifique os logs para mais detalhes")

def main():
    """Função principal do programa"""
    try:
        # Exibir interface
        exibir_cabecalho()
        exibir_opcoes_execucao()
        
        # Obter escolha do usuário
        escolha = obter_escolha_usuario()
        
        # Executar baseado na escolha
        if escolha == "1":
            executar_modo_teste()
        elif escolha == "2":
            executar_modo_completo()
        elif escolha == "3":
            executar_site_especifico()
        
        # Mensagem final
        print("\n" + "="*50)
        print("EXECUÇÃO FINALIZADA")
        print("="*50)
        print("📊 Dados coletados e organizados em planilhas Excel")
        print("🔍 Logs detalhados salvos na pasta 'logs/'")
        print("📈 Use os dados para análise de preços e mercado")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Execução interrompida pelo usuário")
        print("📋 Dados parciais podem ter sido salvos")
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        print("📋 Verifique as dependências e tente novamente")
    
    # Aguardar antes de fechar (opcional)
    # try:
    #     input("\nPressione Enter para sair...")
    # except:
    #     pass

if __name__ == "__main__":
    main()