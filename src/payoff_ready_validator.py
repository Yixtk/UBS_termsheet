"""
Payoff-Ready Validator
======================
Lightweight schema validation to ensure extracted JSON is safe for payoff calculation.

This is the critical guardrail between extraction and payoff engine.
"""
from typing import Dict, List, Tuple, Optional


# ============================================================
# Required Fields for Payoff Calculation
# ============================================================

REQUIRED_FIELDS = {
    "structure_type": str,
    "underlyings": list,
    "dates": dict,
}

REQUIRED_DATES = [
    "observation_dates",
    "valuation_date"
]

REQUIRED_PAYOFF_COMPONENTS = [
    "conditional_coupons",
    "final_redemption"
]


# ============================================================
# Validation Functions
# ============================================================

def validate_for_payoff(extraction_result: Dict) -> Tuple[bool, List[str], Dict]:
    """
    Validate if extraction result is ready for payoff calculation
    
    Returns:
        (is_valid, error_messages, cleaned_result)
    """
    errors = []
    warnings = []
    
    # Filter out noise fields first
    cleaned = _remove_noise_fields(extraction_result)
    
    # Layer 1: Check top-level required fields
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in cleaned:
            errors.append(f"FATAL: Missing required field '{field}'")
        elif not isinstance(cleaned[field], expected_type):
            errors.append(f"FATAL: Field '{field}' has wrong type (expected {expected_type.__name__})")
    
    if errors:
        return False, errors, cleaned
    
    # Layer 2: Structure type validation
    structure_type = cleaned.get("structure_type", "").lower()
    if structure_type not in ("single", "worst_of"):
        errors.append(f"FATAL: Invalid structure_type '{structure_type}' (must be 'single' or 'worst_of')")
        return False, errors, cleaned
    
    # Layer 3: Underlyings validation
    underlyings = cleaned.get("underlyings", [])
    if len(underlyings) == 0:
        errors.append("FATAL: No underlyings found")
    elif structure_type == "single" and len(underlyings) != 1:
        warnings.append(f"WARNING: structure_type is 'single' but found {len(underlyings)} underlyings")
    elif structure_type == "worst_of" and len(underlyings) < 2:
        warnings.append(f"WARNING: structure_type is 'worst_of' but only {len(underlyings)} underlying(s)")
    
    # Check underlying fields
    for i, u in enumerate(underlyings):
        if not isinstance(u, dict):
            errors.append(f"FATAL: Underlying {i+1} is not a dict")
            continue
        if not u.get("name"):
            warnings.append(f"WARNING: Underlying {i+1} missing name")
    
    if errors:
        return False, errors, cleaned
    
    # Layer 4: Dates validation
    dates = cleaned.get("dates", {})
    for required_date in REQUIRED_DATES:
        if required_date not in dates:
            errors.append(f"FATAL: Missing required date field '{required_date}'")
        elif required_date == "observation_dates":
            obs_dates = dates.get("observation_dates", [])
            if not isinstance(obs_dates, list) or len(obs_dates) == 0:
                errors.append("FATAL: observation_dates is empty or not a list")
    
    if errors:
        return False, errors, cleaned
    
    # Layer 5: Payoff components validation
    missing_components = []
    for component in REQUIRED_PAYOFF_COMPONENTS:
        if component not in cleaned or not cleaned[component]:
            missing_components.append(component)
    
    if missing_components:
        errors.append(f"FATAL: Missing payoff components: {', '.join(missing_components)}")
        return False, errors, cleaned
    
    # Layer 6: Conditional coupons validation
    coupons = cleaned.get("conditional_coupons", [])
    if isinstance(coupons, list) and len(coupons) > 0:
        for i, coupon in enumerate(coupons):
            if not isinstance(coupon, dict):
                continue
            if "trigger_condition" not in coupon:
                warnings.append(f"WARNING: Conditional coupon {i+1} missing trigger_condition")
            if "barrier_level" not in coupon and "barrier_price" not in coupon:
                warnings.append(f"WARNING: Conditional coupon {i+1} missing barrier info")
    
    # Layer 7: Cross-field Logical Consistency
    # 7.1 Barrier level ordering (financial logic validation)
    knock_in = cleaned.get("knock_in", {})
    autocall = cleaned.get("autocall", {})
    coupon_barrier = None
    
    # Extract coupon barrier
    if coupons and len(coupons) > 0:
        for coupon in coupons:
            if "barrier_level" in coupon:
                coupon_barrier = _parse_barrier(coupon["barrier_level"])
                break
            elif "barrier_price" in coupon:
                # For worst-of products with barrier_prices
                barrier_prices = coupon.get("barrier_prices", [])
                if barrier_prices and len(barrier_prices) > 0:
                    first_barrier = barrier_prices[0]
                    if isinstance(first_barrier, dict) and "barrier_level" in first_barrier:
                        coupon_barrier = _parse_barrier(first_barrier["barrier_level"])
                        break
    
    # Extract knock-in and autocall barriers
    ki_barrier = _parse_barrier(knock_in.get("barrier_level", "0%"))
    ac_barrier = _parse_barrier(autocall.get("barrier_level", "100%"))
    
    # Check barrier ordering: knock-in ≤ coupon ≤ autocall
    if ki_barrier is not None and coupon_barrier is not None:
        if ki_barrier > coupon_barrier:
            warnings.append(
                f"WARNING: Knock-in barrier ({ki_barrier:.1%}) should be ≤ coupon barrier ({coupon_barrier:.1%})"
            )
    
    if coupon_barrier is not None and ac_barrier is not None:
        if coupon_barrier > ac_barrier:
            warnings.append(
                f"WARNING: Coupon barrier ({coupon_barrier:.1%}) should be ≤ autocall barrier ({ac_barrier:.1%})"
            )
    
    # 7.2 Numerical sanity checks for underlyings
    for i, u in enumerate(underlyings):
        initial_price = u.get("initial_price")
        if initial_price is not None:
            if not isinstance(initial_price, (int, float)):
                warnings.append(f"WARNING: Underlying {i+1} has non-numeric initial_price: {initial_price}")
            elif initial_price <= 0:
                warnings.append(f"WARNING: Underlying {i+1} has invalid initial_price: {initial_price} (must be > 0)")
    
    # 7.3 Structure-specific validations
    if structure_type == "worst_of":
        # All underlyings should have initial_price for worst-of products
        missing_prices = []
        for i, u in enumerate(underlyings):
            if not u.get("initial_price"):
                missing_prices.append(i + 1)
        
        if missing_prices:
            warnings.append(
                f"WARNING: Worst-of product missing initial_price for underlying(s): {missing_prices}"
            )
    
    # 7.4 Date count consistency (if payment_dates exist)
    payment_dates = dates.get("payment_dates", [])
    obs_dates = dates.get("observation_dates", [])
    
    if payment_dates and obs_dates:
        if len(payment_dates) != len(obs_dates):
            warnings.append(
                f"WARNING: Mismatched date counts - observation_dates: {len(obs_dates)}, "
                f"payment_dates: {len(payment_dates)}"
            )
    
    # All checks passed
    all_messages = errors + warnings
    return True, all_messages, cleaned


def _parse_barrier(barrier_value) -> Optional[float]:
    """
    Parse barrier level from various formats
    
    Args:
        barrier_value: Can be string like '50%', '50.00%', or numeric
        
    Returns:
        Float representation (e.g., 0.5 for 50%) or None if invalid
    """
    if barrier_value is None:
        return None
    
    # If already numeric
    if isinstance(barrier_value, (int, float)):
        # Assume it's already in decimal form (0.5) or percentage (50)
        if barrier_value <= 1.0:
            return float(barrier_value)
        else:
            return float(barrier_value) / 100.0
    
    # If string, try to parse
    if isinstance(barrier_value, str):
        try:
            # Remove '%' and whitespace
            cleaned = barrier_value.strip().replace('%', '').replace(' ', '')
            value = float(cleaned)
            # Convert to decimal if it's in percentage form
            if value > 1.0:
                return value / 100.0
            else:
                return value
        except (ValueError, AttributeError):
            return None
    
    return None


def _remove_noise_fields(result: Dict) -> Dict:
    """Remove fields that are not needed for payoff calculation"""
    NOISE_FIELDS = [
        "error", "reason", "note", "extraction_status",
        "distributor", "fees", "commissions",
        "selling_restrictions", "offering_details",
        "suitability_assessment", "risk_factors",
        "secondary_market", "settlement", 
        "form_of_notes", "governing_law", "listing",
        "business_day", "business_day_convention",
        "valuation_time", "share_performance_formula"
    ]
    
    cleaned = {}
    for key, value in result.items():
        if key not in NOISE_FIELDS:
            cleaned[key] = value
    
    return cleaned


def get_payoff_ready_summary(extraction_result: Dict) -> Dict:
    """
    Get a compact summary suitable for payoff engine
    
    Returns only essential fields
    """
    return {
        "structure_type": extraction_result.get("structure_type"),
        "underlyings": extraction_result.get("underlyings", []),
        "dates": extraction_result.get("dates", {}),
        "conditional_coupons": extraction_result.get("conditional_coupons", []),
        "autocall": extraction_result.get("autocall"),
        "knock_in": extraction_result.get("knock_in"),
        "final_redemption": extraction_result.get("final_redemption"),
        "fixed_coupon": extraction_result.get("fixed_coupon"),
        "capital_protection": extraction_result.get("capital_protection", False)
    }


# ============================================================
# Main Entry Point
# ============================================================

def validate_and_prepare_for_payoff(extraction_result: Dict, strict: bool = True) -> Dict:
    """
    Main function: Validate extraction result and prepare for payoff calculation
    
    Args:
        extraction_result: Raw extraction result from PayoffExtractor
        strict: If True, raise exception on validation failure
        
    Returns:
        Dict with keys: "is_valid", "errors", "payoff_ready_data"
    """
    is_valid, messages, cleaned = validate_for_payoff(extraction_result)
    
    errors = [m for m in messages if m.startswith("FATAL") or m.startswith("❌")]
    warnings = [m for m in messages if m.startswith("WARNING") or m.startswith("⚠️")]
    
    result = {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "payoff_ready_data": get_payoff_ready_summary(cleaned) if is_valid else None
    }
    
    if strict and not is_valid:
        error_msg = "\n".join(errors)
        raise ValueError(f"Validation failed:\n{error_msg}")
    
    return result


# ============================================================
# CLI Interface
# ============================================================

def main():
    """Command line interface for validation"""
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python payoff_ready_validator.py <test_results.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    with open(results_file, 'r', encoding='utf-8') as f:
        test_results = json.load(f)
    
    print("\n" + "=" * 80)
    print("🔍 Payoff-Ready Validation Report")
    print("=" * 80)
    
    for test_result in test_results:
        print(f"\n📄 {test_result['test_name']}")
        print("-" * 80)
        
        extraction = test_result.get("extraction_result", {})
        validation = validate_and_prepare_for_payoff(extraction, strict=False)
        
        if validation["is_valid"]:
            print("✅ PASS - Ready for payoff calculation")
            
            if validation["warnings"]:
                print("\n⚠️  Warnings:")
                for warning in validation["warnings"]:
                    print(f"   {warning}")
            
            # Show summary
            summary = validation["payoff_ready_data"]
            print(f"\n📊 Payoff Summary:")
            print(f"   Structure: {summary['structure_type']}")
            print(f"   Underlyings: {len(summary['underlyings'])}")
            print(f"   Observation dates: {len(summary['dates'].get('observation_dates', []))}")
            print(f"   Has conditional coupons: {bool(summary['conditional_coupons'])}")
            print(f"   Has autocall: {bool(summary['autocall'])}")
            print(f"   Has knock-in: {bool(summary['knock_in'])}")
        else:
            print("❌ FAIL - Not ready for payoff calculation")
            print("\n🚫 Errors:")
            for error in validation["errors"]:
                print(f"   {error}")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()

