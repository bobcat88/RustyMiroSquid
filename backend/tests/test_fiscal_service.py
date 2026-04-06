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

def test_calculate_net_profit_extreme_values():
    """Vérifie le calcul avec des valeurs extrêmes."""
    # Très petit profit
    assert FiscalService.calculate_net_profit(0.01, "France") == pytest.approx(0.01 * (1 - 0.314))
    # Très grand profit
    assert FiscalService.calculate_net_profit(1e9, "France") == 1e9 * (1 - 0.314)
    # Zéro exact
    assert FiscalService.calculate_net_profit(0.0, "France") == 0.0

def test_get_tax_breakdown_negative_and_zero():
    """Vérifie le breakdown pour des pertes ou un profit nul."""
    # Profit nul
    breakdown_zero = FiscalService.get_tax_breakdown(0.0, "France")
    assert breakdown_zero["total_tax"] == 0.0
    assert breakdown_zero["net_profit"] == 0.0
    
    # Perte
    breakdown_loss = FiscalService.get_tax_breakdown(-100.0, "France")
    assert breakdown_loss["total_tax"] == 0.0
    assert breakdown_loss["net_profit"] == -100.0

def test_calculate_net_profit_none_domicile():
    """Vérifie le comportement par défaut si le domicile est None/vide."""
    assert FiscalService.calculate_net_profit(100.0, "") == 100.0
    assert FiscalService.calculate_net_profit(100.0, None) == 100.0
