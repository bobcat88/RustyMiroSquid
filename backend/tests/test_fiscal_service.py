import pytest
from app.services.fiscal_service import FiscalService

def test_calculate_net_profit_france_positive():
    """Vérifie le calcul du profit net pour la France avec un gain."""
    gross = 1000.0
    # 1000 - (1000 * 0.314) = 1000 - 314 = 686
    net = FiscalService.calculate_net_profit(gross, "France")
    assert net == 686.0

def test_calculate_net_profit_france_negative():
    """Vérifie que les pertes ne sont pas taxées (profit net == profit brut)."""
    gross = -500.0
    net = FiscalService.calculate_net_profit(gross, "France")
    assert net == -500.0

def test_calculate_net_profit_other_domicile():
    """Vérifie qu'un domicile inconnu ne subit pas de taxe (pour le moment)."""
    gross = 1000.0
    net = FiscalService.calculate_net_profit(gross, "USA")
    assert net == 1000.0

def test_get_tax_breakdown_france():
    """Vérifie le détail du breakdown fiscal pour la France."""
    gross = 2000.0
    breakdown = FiscalService.get_tax_breakdown(gross, "France")
    assert breakdown["total_tax"] == 2000.0 * 0.314
    assert breakdown["net_profit"] == 2000.0 * (1 - 0.314)
    assert "PFU 31.4%" in breakdown["notes"]

def test_get_tax_breakdown_unsupported():
    """Vérifie l'erreur pour un domicile non supporté."""
    breakdown = FiscalService.get_tax_breakdown(100.0, "Mars")
    assert "error" in breakdown
