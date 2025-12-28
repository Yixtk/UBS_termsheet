# tests/test_extractor.py

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.extractor import PayoffExtractor
from tests.test_case import TEST_CASES


def check_schema(result):
    errors = []

    if not isinstance(result, dict):
        errors.append("Result is not a dict")
        return errors

    if result.get("structure_type") not in {"single", "worst_of"}:
        errors.append("Invalid or missing structure_type")

    if not isinstance(result.get("underlyings"), list):
        errors.append("Missing or invalid underlyings")

    if not isinstance(result.get("dates"), dict):
        errors.append("Missing or invalid dates")

    return errors


def check_dates(dates, required_keys):
    missing = []
    for key in required_keys:
        if key not in dates or not dates[key]:
            missing.append(key)
    return missing


def run_tests():
    extractor = PayoffExtractor()
    all_results = []

    for case in TEST_CASES:
        print("\n" + "=" * 60)
        print(f"Running test: {case['name']}")
        print("=" * 60)

        result = extractor.extract_from_pdf(case["pdf_path"])
        
        # Save result for later
        test_result = {
            "test_name": case["name"],
            "pdf_path": case["pdf_path"],
            "extraction_result": result,
            "expected": case["expected"]
        }

        if "error" in result:
            print("❌ Extraction failed:", result["error"])
            test_result["status"] = "error"
            all_results.append(test_result)
            continue
        
        test_result["status"] = "success"

        # ---------- Schema check ----------
        schema_errors = check_schema(result)
        if schema_errors:
            print("❌ Schema errors:", schema_errors)
            continue
        print("✅ Schema check passed")

        expected = case["expected"]

        # ---------- structure_type ----------
        if result["structure_type"] != expected["structure_type"]:
            print(
                f"❌ structure_type mismatch: "
                f"expected {expected['structure_type']}, "
                f"got {result['structure_type']}"
            )
        else:
            print("✅ structure_type correct")

        # ---------- underlyings count ----------
        num_underlyings = len(result["underlyings"])
        if num_underlyings < expected["min_underlyings"]:
            print(
                f"❌ underlyings count too small: "
                f"{num_underlyings} < {expected['min_underlyings']}"
            )
        else:
            print(f"✅ underlyings count OK ({num_underlyings})")

        # ---------- dates ----------
        dates = result["dates"]
        missing_dates = check_dates(dates, expected["must_have_dates"])

        if missing_dates:
            print("❌ Missing required dates:", missing_dates)
        else:
            print("✅ Required dates present")

        # ---------- summary ----------
        print("Summary:")
        summary = {
            "structure_type": result["structure_type"],
            "num_underlyings": num_underlyings,
            "observation_dates": len(dates.get("observation_dates", [])),
        }
        print(summary)
        test_result["summary"] = summary
        all_results.append(test_result)
    
    # Save all results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"✅ Results saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
