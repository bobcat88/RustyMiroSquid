from typing import Dict, Any

class FiscalService:
    """
    Service centralisant les règles fiscales par pays pour le calcul du profit NET.
    Initialement configuré pour la France (PFU 2026).
    """
    
    # Taux en vigueur en France (PFU - Flat Tax)
    # 12.8% Impôt sur le Revenu + 17.2% Prélèvements Sociaux (Note: User mentionne 18.6% PS, total 31.4%)
    # Nous utilisons les chiffres fournis par l'utilisateur pour la simulation 2026.
    FRANCE_FLAT_TAX = 0.314 

    @staticmethod
    def calculate_net_profit(gross_profit: float, domicile: str = "France") -> float:
        """
        Calcule le profit net après taxes selon le domicile.
        """
        if gross_profit <= 0:
            return gross_profit # Les pertes ne sont pas taxées (mais peuvent être déductibles, hors scope simple)
            
        if domicile == "France":
            tax = gross_profit * FiscalService.FRANCE_FLAT_TAX
            return gross_profit - tax
        
        # Default: No tax simulation for other countries yet
        return gross_profit

    @staticmethod
    def get_tax_breakdown(gross_profit: float, domicile: str = "France") -> Dict[str, Any]:
        """
        Retourne le détail des taxes pour un profit donné.
        """
        if domicile == "France":
            total_tax = gross_profit * FiscalService.FRANCE_FLAT_TAX if gross_profit > 0 else 0
            return {
                "domicile": "France",
                "gross_profit": gross_profit,
                "total_tax": total_tax,
                "net_profit": gross_profit - total_tax,
                "tax_rate_total": FiscalService.FRANCE_FLAT_TAX,
                "notes": "Calcul basé sur le PFU 31.4% (IR + PS)"
            }
        
        return {"error": f"Domicile {domicile} non supporté."}
