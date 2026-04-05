import sys
import os

# Add backend/app/services to sys.path to import directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "services")))

try:
    from fiscal_service import FiscalService
except ImportError as e:
    # Try alternate if we are running from a different root
    try:
        from app.services.fiscal_service import FiscalService
    except ImportError:
        print(f"FAILED IMPORT: {e}")
        sys.exit(1)

def test_logic():
    print("--- STARTING FISCAL VERIFICATION ---")
    
    # 1. France Positive
    gross = 1000.0
    net = FiscalService.calculate_net_profit(gross, "France")
    expected = 686.0
    if abs(net - expected) < 0.001:
        print("[OK] France Positive: 1000 -> 686")
    else:
        print(f"[FAIL] France Positive: 1000 -> {net} (expected {expected})")
        
    # 2. France Negative
    gross = -500.0
    net = FiscalService.calculate_net_profit(gross, "France")
    if net == -500.0:
        print("[OK] France Negative: -500 -> -500")
    else:
        print(f"[FAIL] France Negative: -500 -> {net}")

    # 3. Breakdown
    gross = 2000.0
    breakdown = FiscalService.get_tax_breakdown(gross, "France")
    if breakdown.get("total_tax") == 2000.0 * 0.314:
        print(f"[OK] France Breakdown: {breakdown['notes']}")
    else:
        print(f"[FAIL] France Breakdown: {breakdown}")

    print("--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    test_logic()
