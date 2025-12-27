"""
Calculate Payoff from Extracted JSON and Save Results
======================================================
Complete pipeline: JSON → Validation → Payoff Calculation → Results JSON
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.payoff_ready_validator import validate_and_prepare_for_payoff
from src.payoff_single import SinglePhoenixPayoff
from src.payoff_worst_of import WorstOfPhoenixPayoff


def calculate_and_save_payoff(
    json_file: str,
    output_file: str = None,
    scenarios: dict = None
):
    """
    Read extraction JSON, calculate payoff for different scenarios, and save results
    
    Args:
        json_file: Path to extraction results JSON
        output_file: Output file path (auto-generated if None)
        scenarios: Custom price scenarios (uses defaults if None)
    """
    # Load extraction results
    print(f"📂 Loading extraction results from: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        extraction_results = json.load(f)
    
    all_payoff_results = []
    
    # Process each extracted term sheet
    for result in extraction_results:
        product_name = result.get("test_name", "Unknown Product")
        extraction = result.get("extraction_result", {})
        
        print(f"\n{'=' * 80}")
        print(f"💰 Calculating Payoff: {product_name}")
        print('=' * 80)
        
        # Validate extraction
        validation = validate_and_prepare_for_payoff(extraction, strict=False)
        
        if not validation["is_valid"]:
            print(f"❌ Validation failed, skipping payoff calculation")
            all_payoff_results.append({
                "product_name": product_name,
                "status": "validation_failed",
                "errors": validation["errors"]
            })
            continue
        
        payoff_data = validation["payoff_ready_data"]
        structure_type = payoff_data.get("structure_type")
        
        # Initialize appropriate payoff calculator
        try:
            if structure_type == "single":
                calc = SinglePhoenixPayoff(payoff_data)
                payoff_result = _calculate_single_scenarios(calc, scenarios)
            elif structure_type == "worst_of":
                calc = WorstOfPhoenixPayoff(payoff_data)
                payoff_result = _calculate_worst_of_scenarios(calc, scenarios)
            else:
                print(f"❌ Unsupported structure type: {structure_type}")
                continue
            
            # Add metadata
            payoff_result.update({
                "product_name": product_name,
                "structure_type": structure_type,
                "calculation_timestamp": datetime.now().isoformat(),
                "status": "success"
            })
            
            all_payoff_results.append(payoff_result)
            
            # Print summary
            _print_payoff_summary(payoff_result)
            
        except Exception as e:
            print(f"❌ Payoff calculation failed: {e}")
            all_payoff_results.append({
                "product_name": product_name,
                "status": "calculation_failed",
                "error": str(e)
            })
    
    # Save results
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"payoff_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_payoff_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print(f"✅ Payoff results saved to: {output_file}")
    print('=' * 80 + '\n')
    
    return all_payoff_results


def _calculate_single_scenarios(calc: SinglePhoenixPayoff, custom_scenarios=None):
    """Calculate payoff for single underlying across multiple scenarios"""
    initial = calc.initial_price
    num_obs = len(calc.observation_dates)
    
    # Default scenarios
    scenarios = {
        "bullish_autocall": {
            "description": "Strong uptrend - Autocall triggered early",
            "path": [initial * (1 + 0.05 * i) for i in range(1, num_obs + 1)]
        },
        "sideways_coupons": {
            "description": "Sideways market - Coupons paid, principal protected",
            "path": [initial * 0.85 for _ in range(num_obs)]
        },
        "moderate_decline": {
            "description": "Moderate decline - Above knock-in barrier",
            "path": [initial * 0.75 for _ in range(num_obs)]
        },
        "severe_decline": {
            "description": "Severe decline - Knock-in triggered",
            "path": [initial * (1 - 0.05 * i) for i in range(1, num_obs + 1)]
        }
    }
    
    if custom_scenarios:
        scenarios.update(custom_scenarios)
    
    # Calculate payoffs
    scenario_results = {}
    for scenario_name, scenario_data in scenarios.items():
        price_path = scenario_data["path"]
        
        try:
            coupons, payoff, details = calc.calculate_payoff(price_path)
            
            scenario_results[scenario_name] = {
                "description": scenario_data["description"],
                "final_price": price_path[-1],
                "final_performance": price_path[-1] / initial,
                "total_coupons": coupons,
                "final_payoff": payoff,
                "total_value": coupons + payoff,
                "return_pct": ((coupons + payoff) / calc.denomination - 1) * 100,
                "autocall_triggered": details["autocall_triggered"],
                "autocall_date": details.get("autocall_date"),
                "knock_in_event": details["knock_in_event"],
                "num_coupon_payments": len(details["coupon_payments"])
            }
        except Exception as e:
            scenario_results[scenario_name] = {
                "error": str(e)
            }
    
    return {
        "product_parameters": {
            "underlying": calc.underlying["name"],
            "initial_price": initial,
            "denomination": calc.denomination,
            "coupon_rate": calc.coupon_rate,
            "coupon_barrier": calc.coupon_barrier,
            "autocall_barrier": calc.autocall_barrier,
            "knock_in_barrier": calc.knock_in_barrier,
            "num_observations": num_obs
        },
        "scenarios": scenario_results
    }


def _calculate_worst_of_scenarios(calc: WorstOfPhoenixPayoff, custom_scenarios=None):
    """Calculate payoff for worst-of across multiple scenarios"""
    num_obs = len(calc.observation_dates)
    
    # Default scenarios for worst-of
    scenarios = {
        "all_up_autocall": {
            "description": "All assets up - Autocall triggered",
            "paths": [
                [price * (1 + 0.08 * i) for i in range(1, num_obs + 1)]
                for price in calc.initial_prices
            ]
        },
        "mixed_performance": {
            "description": "Mixed - One asset underperforms but above barrier",
            "paths": [
                [calc.initial_prices[0] * 1.1 for _ in range(num_obs)],
                [calc.initial_prices[1] * 1.05 for _ in range(num_obs)],
                [calc.initial_prices[2] * 0.6 for _ in range(num_obs)]
            ]
        },
        "worst_performer_knockin": {
            "description": "Worst performer triggers knock-in",
            "paths": [
                [calc.initial_prices[0] * 0.9 for _ in range(num_obs)],
                [calc.initial_prices[1] * 0.8 for _ in range(num_obs)],
                [calc.initial_prices[2] * 0.4 for _ in range(num_obs)]
            ]
        }
    }
    
    if custom_scenarios:
        scenarios.update(custom_scenarios)
    
    # Calculate payoffs
    scenario_results = {}
    for scenario_name, scenario_data in scenarios.items():
        price_paths = scenario_data["paths"]
        
        try:
            coupons, payoff, details = calc.calculate_payoff(price_paths)
            
            # Calculate worst performance
            final_performances = [
                price_paths[i][-1] / calc.initial_prices[i]
                for i in range(calc.num_underlyings)
            ]
            worst_performance = min(final_performances)
            
            scenario_results[scenario_name] = {
                "description": scenario_data["description"],
                "worst_performance": worst_performance,
                "fixed_coupon": details.get("fixed_coupon", 0),
                "conditional_coupons": details.get("conditional_coupons", 0),
                "total_coupons": coupons,
                "final_payoff": payoff,
                "total_value": coupons + payoff,
                "return_pct": ((coupons + payoff) / calc.denomination - 1) * 100,
                "autocall_triggered": details["autocall_triggered"],
                "autocall_date": details.get("autocall_date"),
                "knock_in_event": details["knock_in_event"],
                "num_conditional_coupon_payments": details.get("num_conditional_coupon_payments", 0)
            }
        except Exception as e:
            scenario_results[scenario_name] = {
                "error": str(e)
            }
    
    return {
        "product_parameters": {
            "underlyings": [
                {"name": u["name"], "initial_price": u["initial_price"]}
                for u in calc.underlyings
            ],
            "denomination": calc.denomination,
            "fixed_coupon_rate": calc.fixed_coupon_rate if calc.has_fixed_coupon else None,
            "monthly_coupon_rate": calc.coupon_rate,
            "phoenix_barrier": calc.coupon_barrier,
            "autocall_barrier": calc.autocall_barrier,
            "knock_in_barrier": calc.knock_in_barrier,
            "num_observations": num_obs
        },
        "scenarios": scenario_results
    }


def _print_payoff_summary(payoff_result):
    """Print a summary of payoff calculations"""
    print(f"\n✅ Calculation completed")
    print(f"   Structure: {payoff_result['structure_type']}")
    
    scenarios = payoff_result.get("scenarios", {})
    print(f"\n📊 Scenarios calculated: {len(scenarios)}")
    
    for scenario_name, scenario_data in scenarios.items():
        if "error" in scenario_data:
            print(f"   ❌ {scenario_name}: {scenario_data['error']}")
        else:
            total_value = scenario_data.get("total_value", 0)
            return_pct = scenario_data.get("return_pct", 0)
            print(f"   • {scenario_name}: ${total_value:.2f} ({return_pct:+.1f}%)")


# ============================================================
# CLI Interface
# ============================================================

def main():
    """Command line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python calculate_payoff_from_json.py <extraction_results.json> [output.json]")
        print("\nExample:")
        print("  python calculate_payoff_from_json.py test_results_20251226_131814.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("\n" + "=" * 80)
    print("💰 PAYOFF CALCULATOR - From Extracted JSON")
    print("=" * 80)
    
    results = calculate_and_save_payoff(input_file, output_file)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r.get("status") == "success")
    failed = len(results) - successful
    
    print(f"Total products: {len(results)}")
    print(f"✅ Successfully calculated: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful > 0:
        print(f"\n💾 Payoff results ready for:")
        for result in results:
            if result.get("status") == "success":
                num_scenarios = len(result.get("scenarios", {}))
                print(f"   • {result['product_name']} ({num_scenarios} scenarios)")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

