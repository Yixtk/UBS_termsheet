"""
Ground Truth Comparison Script
Compare AI extraction results with human-verified ground truth
"""
import json
from typing import Dict, List, Tuple
from datetime import datetime


# ============================================================
# Ground Truth Definitions (Human-verified)
# ============================================================

GROUND_TRUTH = {
    "BNP-PhoenixSnowball-SP500-XS1083630027-TS.pdf": {
        "structure_type": "single",
        "num_underlyings": 1,
        "underlyings": [
            {
                "name": "S&P 500",
                "ticker": "SPX Index",
                "initial_price": 1985.54
            }
        ],
        "required_dates": {
            "valuation_date": "2022-09-12",
            "maturity_date": "2022-09-26",
            "num_observation_dates": 15
        },
        "payoff_components": {
            "has_conditional_coupon": True,
            "has_autocall": True,
            "has_knock_in": True,
            "coupon_rate": "2.60%",
            "coupon_memory": True,
            "autocall_barrier": "110%",
            "knock_in_barrier": "70%",
            "knock_in_type": "European"
        }
    },
    "IT0006764473-TS.pdf": {
        "structure_type": "worst_of",
        "num_underlyings": 3,
        "underlyings": [
            {
                "name": "Advanced Micro Devices Inc",
                "ticker": "AMD UW",
                "initial_price": 140.75
            },
            {
                "name": "NVIDIA Corp",
                "ticker": "NVDA UW",
                "initial_price": 118.08
            },
            {
                "name": "Intel Corp",
                "ticker": "INTC UW",
                "initial_price": 19.92
            }
        ],
        "required_dates": {
            "valuation_date": "2027-08-09",
            "maturity_date": "2027-08-16",
            "num_observation_dates": 34
        },
        "payoff_components": {
            "has_conditional_coupon": True,
            "has_autocall": True,
            "has_knock_in": True,
            "has_fixed_coupon": True,
            "fixed_coupon_rate": "19.00%",
            "phoenix_barrier": "50%",
            "autocall_barrier": "100%",
            "knock_in_barrier": "50%"
        }
    }
}


# ============================================================
# Scoring Functions
# ============================================================

def score_structure_type(ai_result: Dict, ground_truth: Dict) -> Tuple[str, str]:
    """Score structure_type - FATAL if wrong"""
    ai_type = ai_result.get("extraction_result", {}).get("structure_type", "unknown").lower()
    gt_type = ground_truth.get("structure_type", "").lower()
    
    if ai_type == gt_type:
        return "PASS", f"✅ structure_type: {ai_type}"
    else:
        return "FAIL", f"❌ structure_type: AI={ai_type}, Expected={gt_type} [FATAL]"


def score_underlyings(ai_result: Dict, ground_truth: Dict) -> Tuple[str, str]:
    """Score underlying count and basic info"""
    ai_underlyings = ai_result.get("extraction_result", {}).get("underlyings", [])
    gt_count = ground_truth.get("num_underlyings", 0)
    ai_count = len(ai_underlyings) if isinstance(ai_underlyings, list) else 0
    
    if ai_count == gt_count:
        # Check if names roughly match
        gt_names = {u["name"] for u in ground_truth.get("underlyings", [])}
        ai_names = {u.get("name", "") for u in ai_underlyings if isinstance(u, dict)}
        
        # Fuzzy match (any overlap is good)
        matched = len(gt_names & ai_names)
        if matched == gt_count:
            return "PASS", f"✅ underlyings: {ai_count} (all matched)"
        elif matched > 0:
            return "WARNING", f"⚠️ underlyings: count OK ({ai_count}), but {gt_count - matched} names mismatch"
        else:
            return "WARNING", f"⚠️ underlyings: count OK ({ai_count}), but names all different"
    else:
        return "FAIL", f"❌ underlyings: AI={ai_count}, Expected={gt_count}"


def score_dates(ai_result: Dict, ground_truth: Dict) -> Tuple[str, str]:
    """Score date extraction"""
    ai_dates = ai_result.get("extraction_result", {}).get("dates", {})
    gt_dates = ground_truth.get("required_dates", {})
    
    issues = []
    
    # Check valuation_date
    if ai_dates.get("valuation_date") == gt_dates.get("valuation_date"):
        issues.append("✅ valuation_date")
    else:
        issues.append(f"❌ valuation_date: {ai_dates.get('valuation_date')} vs {gt_dates.get('valuation_date')}")
    
    # Check maturity_date
    if ai_dates.get("maturity_date") == gt_dates.get("maturity_date"):
        issues.append("✅ maturity_date")
    else:
        issues.append(f"❌ maturity_date: {ai_dates.get('maturity_date')} vs {gt_dates.get('maturity_date')}")
    
    # Check observation dates count
    ai_obs_count = len(ai_dates.get("observation_dates", []))
    gt_obs_count = gt_dates.get("num_observation_dates", 0)
    if ai_obs_count == gt_obs_count:
        issues.append(f"✅ observation_dates: {ai_obs_count}")
    else:
        issues.append(f"⚠️ observation_dates: {ai_obs_count} vs {gt_obs_count}")
    
    # Determine overall status
    if all("✅" in i for i in issues):
        return "PASS", " | ".join(issues)
    elif any("❌" in i for i in issues):
        return "FAIL", " | ".join(issues)
    else:
        return "WARNING", " | ".join(issues)


def score_payoff_components(ai_result: Dict, ground_truth: Dict) -> Tuple[str, str]:
    """Score payoff component extraction"""
    ai_extract = ai_result.get("extraction_result", {})
    gt_components = ground_truth.get("payoff_components", {})
    
    checks = []
    
    # Check component presence
    if gt_components.get("has_conditional_coupon"):
        has_cc = bool(ai_extract.get("conditional_coupons"))
        checks.append("✅ conditional_coupon" if has_cc else "❌ missing conditional_coupon")
    
    if gt_components.get("has_autocall"):
        has_ac = bool(ai_extract.get("autocall"))
        checks.append("✅ autocall" if has_ac else "❌ missing autocall")
    
    if gt_components.get("has_knock_in"):
        has_ki = bool(ai_extract.get("knock_in"))
        checks.append("✅ knock_in" if has_ki else "❌ missing knock_in")
    
    # Determine overall status
    pass_count = sum(1 for c in checks if "✅" in c)
    total = len(checks)
    
    if pass_count == total:
        return "PASS", " | ".join(checks)
    elif pass_count >= total * 0.6:
        return "WARNING", " | ".join(checks)
    else:
        return "FAIL", " | ".join(checks)


# ============================================================
# Main Comparison Logic
# ============================================================

def compare_result(ai_result: Dict) -> Dict:
    """Compare one AI result against ground truth"""
    pdf_path = ai_result.get("pdf_path", "")
    
    if pdf_path not in GROUND_TRUTH:
        return {
            "pdf_path": pdf_path,
            "status": "SKIP",
            "reason": "No ground truth defined"
        }
    
    gt = GROUND_TRUTH[pdf_path]
    
    # Run all checks
    structure_status, structure_msg = score_structure_type(ai_result, gt)
    underlyings_status, underlyings_msg = score_underlyings(ai_result, gt)
    dates_status, dates_msg = score_dates(ai_result, gt)
    payoff_status, payoff_msg = score_payoff_components(ai_result, gt)
    
    # Compute overall score
    scores = {
        "structure_type": structure_status,
        "underlyings": underlyings_status,
        "dates": dates_status,
        "payoff_components": payoff_status
    }
    
    # Overall status: FAIL if any FAIL, WARNING if any WARNING, else PASS
    if any(s == "FAIL" for s in scores.values()):
        overall = "FAIL"
    elif any(s == "WARNING" for s in scores.values()):
        overall = "WARNING"
    else:
        overall = "PASS"
    
    return {
        "pdf_path": pdf_path,
        "overall_status": overall,
        "scores": scores,
        "details": {
            "structure_type": structure_msg,
            "underlyings": underlyings_msg,
            "dates": dates_msg,
            "payoff_components": payoff_msg
        }
    }


def print_comparison_report(comparison: Dict):
    """Pretty print comparison result"""
    status_emoji = {
        "PASS": "✅",
        "WARNING": "⚠️",
        "FAIL": "❌",
        "SKIP": "⏭️"
    }
    
    print("\n" + "=" * 80)
    print(f"📄 {comparison['pdf_path']}")
    print("=" * 80)
    
    overall = comparison.get("overall_status", "UNKNOWN")
    print(f"\n{status_emoji.get(overall, '❓')} Overall: {overall}\n")
    
    if "details" in comparison:
        for layer, message in comparison["details"].items():
            print(f"  {message}")
    
    print()


def main(results_file: str):
    """Main comparison routine"""
    # Load AI results
    with open(results_file, 'r', encoding='utf-8') as f:
        ai_results = json.load(f)
    
    print("\n" + "=" * 80)
    print("🔍 AI Extraction vs Ground Truth Comparison")
    print("=" * 80)
    
    comparisons = []
    for ai_result in ai_results:
        comp = compare_result(ai_result)
        comparisons.append(comp)
        print_comparison_report(comp)
    
    # Summary statistics
    total = len(comparisons)
    passed = sum(1 for c in comparisons if c.get("overall_status") == "PASS")
    warnings = sum(1 for c in comparisons if c.get("overall_status") == "WARNING")
    failed = sum(1 for c in comparisons if c.get("overall_status") == "FAIL")
    
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"Total: {total}")
    print(f"✅ PASS: {passed}")
    print(f"⚠️ WARNING: {warnings}")
    print(f"❌ FAIL: {failed}")
    print(f"\nSuccess Rate: {passed/total*100:.1f}%")
    print(f"Acceptable Rate (PASS + WARNING): {(passed+warnings)/total*100:.1f}%")
    print("=" * 80 + "\n")
    
    # Save comparison results
    output_file = results_file.replace(".json", "_comparison.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparisons, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Detailed comparison saved to: {output_file}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
    else:
        # Find most recent test_results file
        import glob
        files = glob.glob("test_results_*.json")
        if not files:
            print("❌ No test_results_*.json files found")
            sys.exit(1)
        results_file = max(files)  # Most recent by name
    
    print(f"📂 Loading results from: {results_file}")
    main(results_file)

