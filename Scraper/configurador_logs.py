"""
Configurador de logs otimizado para terminal limpo
Reduz poluição visual mantendo informações essenciais
"""

import logging
import sys
from datetime import datetime

class FiltroLogLimpo(logging.Filter):
    """
    Filtro personalizado para manter logs limpos no terminal
    Remove logs verbosos de bibliotecas externas
    """
    
    def __init__(self):
        super().__init__()
        
        # Loggers que devem ser silenciados ou reduzidos
        self.loggers_silenciados = [
            'selenium',
            'urllib3',
            'requests',
            'webdriver_manager',
            'WDM',
            'charset_normalizer'
        ]
        
        # Palavras-chave que indicam logs verbosos
        self.palavras_filtradas = [
            'DEBUG',
            'Created TempFile',
            'Selenium Manager',
            'chrome driver',
            'Starting new HTTPS connection'
        ]
    
    def filter(self, record):
        """
        Filtra registros de log baseado em critérios
        
        Args:
            record: Registro de log
            
        Returns:
            bool: True se deve mostrar o log
        """
        # Silenciar loggers específicos
        for logger in self.loggers_silenciados:
            if record.name.startswith(logger):
                return False
        
        # Filtrar mensagens verbosas
        mensagem = record.getMessage().lower()
        for palavra in self.palavras_filtradas:
            if palavra.lower() in mensagem:
                return False
        
        return True

class FormaterPersonalizado(logging.Formatter):
    """
    Formatador personalizado para logs mais legíveis
    Usa emojis e cores para facilitar leitura
    """
    
    def __init__(self):
        super().__init__()
        
        # Mapeamento de níveis para emojis
        self.emojis_nivel = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨',
            'DEBUG': '🔍'
        }
    
    def format(self, record):
        """
        Formata registro de log com estilo personalizado
        
        Args:
            record: Registro a ser formatado
            
        Returns:
            str: Log formatado
        """
        # Obter emoji do nível
        emoji = self.emojis_nivel.get(record.levelname, '📝')
        
        # Timestamp simples (apenas hora:minuto)
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Formatar mensagem baseado no nível
        if record.levelname == 'ERROR':
            return f"{emoji} [{timestamp}] ERRO: {record.getMessage()}"
        elif record.levelname == 'WARNING':
            return f"{emoji} [{timestamp}] AVISO: {record.getMessage()}"
        elif record.levelname == 'INFO':
            return f"{emoji} [{timestamp}] {record.getMessage()}"
        else:
            return f"{emoji} [{timestamp}] {record.levelname}: {record.getMessage()}"

class ConfiguradorLogs:
    """
    Configurador principal para sistema de logs limpo e eficiente
    """
    
    @staticmethod
    def configurar_logs_limpos(nivel_arquivo: str = 'INFO', nivel_console: str = 'INFO', salvar_arquivo: bool = True):
        """
        Configura sistema de logs otimizado
        
        Args:
            nivel_arquivo: Nível de log para arquivo
            nivel_console: Nível de log para console
            salvar_arquivo: Se deve salvar logs em arquivo
        """
        # Logger raiz
        logger_raiz = logging.getLogger()
        logger_raiz.setLevel(logging.DEBUG)  # Capturar tudo, filtrar depois
        
        # Remover handlers existentes
        for handler in logger_raiz.handlers[:]:
            logger_raiz.removeHandler(handler)
        
        # HANDLER PARA CONSOLE (terminal)
        handler_console = logging.StreamHandler(sys.stdout)
        handler_console.setLevel(getattr(logging, nivel_console.upper()))
        
        # Aplicar filtro e formatador personalizado
        filtro_limpo = FiltroLogLimpo()
        formatador_personalizado = FormaterPersonalizado()
        
        handler_console.addFilter(filtro_limpo)
        handler_console.setFormatter(formatador_personalizado)
        logger_raiz.addHandler(handler_console)
        
        # HANDLER PARA ARQUIVO (opcional)
        if salvar_arquivo:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nome_arquivo = f'logs/scraper_medicamentos_{timestamp}.log'
                
                # Criar pasta de logs se não existir
                import os
                os.makedirs('logs', exist_ok=True)
                
                handler_arquivo = logging.FileHandler(nome_arquivo, encoding='utf-8')
                handler_arquivo.setLevel(getattr(logging, nivel_arquivo.upper()))
                
                # Formatador mais detalhado para arquivo
                formatador_arquivo = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler_arquivo.setFormatter(formatador_arquivo)
                logger_raiz.addHandler(handler_arquivo)
                
            except Exception as e:
                print(f"Aviso: Não foi possível criar arquivo de log: {e}")
        
        # Configurar níveis específicos para bibliotecas externas
        ConfiguradorLogs._configurar_bibliotecas_externas()
        
        # Log inicial
        logger = logging.getLogger(__name__)
        logger.info("Sistema de logs configurado com sucesso")
    
    @staticmethod
    def _configurar_bibliotecas_externas():
        """Configura níveis de log para bibliotecas externas"""
        
        # Silenciar ou reduzir logs verbosos
        bibliotecas_config = {
            'selenium': logging.WARNING,
            'urllib3': logging.WARNING,
            'requests': logging.WARNING,
            'webdriver_manager': logging.ERROR,
            'WDM': logging.ERROR,
            'charset_normalizer': logging.WARNING,
            'connectionpool': logging.WARNING,
        }
        
        for biblioteca, nivel in bibliotecas_config.items():
            logger_lib = logging.getLogger(biblioteca)
            logger_lib.setLevel(nivel)
            
            # Desabilitar propagação para reduzir ainda mais ruído
            logger_lib.propagate = False
    
    @staticmethod
    def configurar_modo_teste():
        """Configuração de logs específica para modo teste"""
        ConfiguradorLogs.configurar_logs_limpos(
            nivel_arquivo='DEBUG',
            nivel_console='INFO',
            salvar_arquivo=False  # Não salvar arquivo em modo teste
        )
        
        logger = logging.getLogger(__name__)
        logger.info("🧪 Logs configurados para MODO TESTE")
    
    @staticmethod
    def configurar_modo_producao():
        """Configuração de logs específica para modo produção"""
        ConfiguradorLogs.configurar_logs_limpos(
            nivel_arquivo='INFO',
            nivel_console='INFO',
            salvar_arquivo=True
        )
        
        logger = logging.getLogger(__name__)
        logger.info("🚀 Logs configurados para MODO PRODUÇÃO")
    
    @staticmethod
    def configurar_modo_debug():
        """Configuração de logs para debug com máximo detalhe"""
        ConfiguradorLogs.configurar_logs_limpos(
            nivel_arquivo='DEBUG',
            nivel_console='DEBUG',
            salvar_arquivo=True
        )
        
        # Para debug, mostrar mais logs de bibliotecas
        logging.getLogger('selenium').setLevel(logging.INFO)
        logging.getLogger('requests').setLevel(logging.INFO)
        
        logger = logging.getLogger(__name__)
        logger.info("🔍 Logs configurados para MODO DEBUG")