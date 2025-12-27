"""
Prompt templates for extracting payoff information from structured product term sheets.

This file defines:
- A canonical extraction prompt with strict schema and structure classification
- A section-level extraction prompt for targeted fallback
- A validation prompt for post-extraction consistency checks
"""

# ============================================================
# Main extraction prompt (CANONICAL, STRUCTURE-AWARE)
# ============================================================

PAYOFF_EXTRACTION_PROMPT_TEMPLATE = """
You are extracting structured payoff information from a structured product term sheet.

Your task is to extract ALL payoff-related parameters and organize them into a clean,
machine-readable JSON object that can be used directly to generate payoff code.

==================================================
1. STRUCTURE CLASSIFICATION (MANDATORY, STRICT)
==================================================
First, determine the product structure.

Classify the product as ONE of the following:
- "single": all payoff conditions depend on exactly one underlying
- "worst_of": payoff conditions depend on the lowest / worst / minimum performance
  among multiple underlyings

Indicators of "worst_of" include (but are not limited to):
- Explicit references to "Worst-of"
- "Lowest Performing Share"
- "Lowest Performing Underlying"
- Payoff, coupon, autocall, knock-in, or redemption defined by
  the minimum or worst performance across underlyings

STRICT CLASSIFICATION RULES (DO NOT IGNORE):
- If multiple underlyings are present AND ANY payoff-related condition
  depends on the lowest, worst, or minimum performance,
  you MUST classify the product as "worst_of".
- If multiple underlyings are present and the document does NOT clearly state
  that each underlying is evaluated independently,
  classify the product as "worst_of" by default.
- Classify as "single" ONLY if all payoff conditions depend on exactly one
  underlying or if underlyings are explicitly evaluated independently
  without aggregation.

Return the result explicitly as:
"structure_type": "single" or "worst_of"

==================================================
2. DATE EXTRACTION (CRITICAL, FIRST-CLASS)
==================================================
Extract ALL relevant dates and return them under a single top-level object named "dates".

Include the following fields ONLY if they exist in the document
(do NOT invent or infer dates):

- trade_date
- strike_date
- issue_date
- observation_dates              (coupon and/or autocall observation dates)
- valuation_date                 (final valuation date)
- maturity_date
- payment_dates                  (coupon and/or redemption payment dates)
- knock_in_period:
    - start_date
    - end_date

DATE RULES (STRICT):
- Use ISO format: YYYY-MM-DD
- observation_dates and payment_dates MUST be arrays
- Do NOT embed dates inside descriptive strings or formulas
- All dates MUST appear only inside the "dates" object

==================================================
3. UNDERLYING ASSETS
==================================================
Extract all underlying reference assets.

Return them as an array under the key:
"underlyings"

For each underlying, include ONLY if available:
- name
- ticker
- exchange
- initial_price
- initial_price_date

==================================================
4. PAYOFF COMPONENTS
==================================================
Extract payoff-related terms using structured objects.
Include a component ONLY if it exists in the document.

--- Fixed Coupon ---
"fixed_coupon":
- rate OR amount
- payment_dates
- calculation_formula

--- Conditional Coupons ---
"conditional_coupons": [
  {{
    trigger_condition,
    barrier_level OR barrier_price,
    observation_dates,
    payment_dates,
    rate OR calculation_formula,
    memory_feature (true/false)
  }}
]

--- Automatic Early Redemption (Autocall) ---
"autocall":
- trigger_condition
- barrier_level OR barrier_price
- observation_dates
- redemption_amount OR redemption_formula

--- Knock-in Event ---
"knock_in":
- type ("European" or "American")
- barrier_level OR barrier_price
- determination_period (reference dates or date range)

--- Final Redemption ---
"final_redemption":
- scenarios
- redemption_formula

==================================================
5. STRICT OUTPUT RULES
==================================================
1. Use exact numbers, percentages, dates, and wording from the document
2. Do NOT infer, normalize, or reinterpret financial terms
3. If a field does not exist, omit it entirely
4. Return ONE valid JSON object and NOTHING ELSE
5. Do NOT include explanations, comments, markdown, or extra text

==================================================
DOCUMENT TEXT
==================================================
{document_text}
"""

# ============================================================
# Section-level extraction prompt (fallback / debugging)
# ============================================================

SECTION_EXTRACTION_PROMPT_TEMPLATE = """
You are extracting payoff-related information from a specific section of a term sheet.

Section Name:
{section_name}

Section Content:
{section_text}

Extract all payoff-related numerical values, percentages, dates, formulas,
barriers, conditions, and definitions using exact wording from the document.

Return ONE valid JSON object containing all extracted information.
Do NOT include explanations or extra text.
"""

# ============================================================
# Validation prompt (LLM-as-checker)
# ============================================================

VALIDATION_PROMPT_TEMPLATE = """
Please review the extracted payoff data below and verify its accuracy and completeness
against the original document text.

Extracted Data:
{extracted_data}

Original Text Excerpt:
{original_text}

Check for:
- Incorrect values
- Missing payoff-related fields
- Misclassified structure type
- Missing or incorrect dates

If corrections are needed, return the corrected and complete data
as ONE valid JSON object.
Do NOT include explanations or extra text.
"""

# ============================================================
# Prompt helper functions (interface contract)
# ============================================================

def get_payoff_extraction_prompt(document_text: str) -> str:
    """Generate the main payoff extraction prompt"""
    return PAYOFF_EXTRACTION_PROMPT_TEMPLATE.format(
        document_text=document_text
    )


def get_section_extraction_prompt(section_text: str, section_name: str) -> str:
    """Generate section-level extraction prompt"""
    return SECTION_EXTRACTION_PROMPT_TEMPLATE.format(
        section_text=section_text,
        section_name=section_name
    )


def get_validation_prompt(extracted_data: str, original_text: str) -> str:
    """Generate validation prompt"""
    return VALIDATION_PROMPT_TEMPLATE.format(
        extracted_data=extracted_data,
        original_text=original_text
    )
