from estruturas_dados import InfoMedicamento, InfoProduto
from typing import List, Dict, Optional

# ==========================================
# GERENCIADOR DE DADOS DOS MEDICAMENTOS
# ==========================================

class GerenciadorDados:
    """
    Gerencia informações sobre medicamentos veterinários
    e fornece dados estruturados para o scraping
    """
    
    def __init__(self):
        # Lista completa de medicamentos para buscar
        self.medicamentos = [
            "Simparic", "Revolution", "NexGard", "NexGard Spectra", "NexGard Combo", 
            "Bravecto", "Frontline", "Advocate", "Drontal", "Milbemax", "Vermivet",
            "Rimadyl", "Onsior", "Maxicam", "Carproflan", "Previcox",
            "Apoquel", "Zenrelia", "Synulox", "Baytril",
        ]
        
        # Base de conhecimento sobre cada medicamento
        self.info_medicamentos = {
            # ANTIPULGAS E CARRAPATOS
            "Simparic": InfoMedicamento("Zoetis", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "35 dias"),
            "Revolution": InfoMedicamento("Zoetis", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "NexGard": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "30 dias"),
            "NexGard Spectra": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães", "Todos os portes", "30 dias"),
            "NexGard Combo": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Gatos", "Todos os portes", "30 dias"),
            "Bravecto": InfoMedicamento("MSD Saúde Animal", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "90 dias"),
            "Frontline": InfoMedicamento("Boehringer Ingelheim", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            "Advocate": InfoMedicamento("Elanco", "Antipulgas e Carrapatos", "Cães e Gatos", "Todos os portes", "30 dias"),
            
            # VERMÍFUGOS
            "Drontal": InfoMedicamento("Elanco", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Milbemax": InfoMedicamento("Elanco", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            "Vermivet": InfoMedicamento("Agener União Química", "Vermífugo", "Cães e Gatos", "Todos os portes", "Dose única"),
            
            # ANTI-INFLAMATÓRIOS
            "Rimadyl": InfoMedicamento("Zoetis", "Anti-inflamatório", "Cães", "Todos os portes", "12-24 horas"),
            "Onsior": InfoMedicamento("Elanco", "Anti-inflamatório", "Cães e Gatos", "Todos os portes", "24 horas"),
            "Maxicam": InfoMedicamento("Ourofino Saúde Animal", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Carproflan": InfoMedicamento("Agener União Química", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            "Previcox": InfoMedicamento("Boehringer Ingelheim", "Anti-inflamatório", "Cães", "Todos os portes", "24 horas"),
            
            # DERMATOLÓGICOS/ANTIALÉRGICOS
            "Apoquel": InfoMedicamento("Zoetis", "Dermatológico / Antialérgico", "Cães", "Todos os portes", "12 horas"),
            "Zenrelia": InfoMedicamento("Elanco", "Dermatológico / Antialérgico", "Cães", "Todos os portes", "24 horas"),
            
            # ANTIBIÓTICOS
            "Synulox": InfoMedicamento("Zoetis", "Antibiótico", "Cães e Gatos", "Todos os portes", "12 horas"),
            "Baytril": InfoMedicamento("Elanco", "Antibiótico", "Cães e Gatos", "Todos os portes", "24 horas"),
        }
    
    def obter_info_medicamento(self, medicamento: str) -> InfoMedicamento:
        """
        Retorna informações de um medicamento específico
        
        Args:
            medicamento: Nome do medicamento
            
        Returns:
            InfoMedicamento: Dados do medicamento ou padrão se não encontrado
        """
        return self.info_medicamentos.get(
            medicamento, 
            InfoMedicamento("N/A", "N/A", "N/A", "N/A", "N/A")
        )
    
    def obter_lista_medicamentos(self) -> List[str]:
        """
        Retorna lista completa de medicamentos para buscar
        
        Returns:
            List[str]: Lista de nomes de medicamentos
        """
        return self.medicamentos
