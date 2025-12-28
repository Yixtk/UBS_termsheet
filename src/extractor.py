"""
Main workflow for extracting payoff information from term sheets
"""
import json
from typing import Dict, Optional
from src.llm_client import LLMClient
from src.document_loader import load_pdf_text, split_text
from src.prompt import (
    get_payoff_extraction_prompt,
    get_section_extraction_prompt,
    get_validation_prompt
)


class PayoffExtractor:
    """Main class for extracting payoff information from term sheets"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        Initialize the payoff extractor
        
        Args:
            provider: LLM provider ("openai", "anthropic", "deepseek")
            model: Model name
            temperature: Temperature setting
        """
        self.llm_client = LLMClient(provider=provider, model=model, temperature=temperature)
    
    def extract_from_pdf(
        self,
        pdf_path: str,
        use_chunking: bool = True,
        chunk_size: int = 4000
    ) -> Dict:
        """
        Extract payoff information from a PDF term sheet
        
        Args:
            pdf_path: Path to the PDF file
            use_chunking: Whether to split document into chunks for processing
            chunk_size: Size of chunks if chunking is used
            
        Returns:
            Dictionary containing extracted payoff information
        """
        # Load document
        print(f"Loading PDF: {pdf_path}")
        document_text = load_pdf_text(pdf_path)
        print(f"Document loaded: {len(document_text)} characters")
        
        if use_chunking and len(document_text) > chunk_size:
            # Split into chunks
            print("Splitting document into chunks...")
            chunks = split_text(document_text, chunk_size=chunk_size, overlap=200)
            print(f"Split into {len(chunks)} chunks")
            
            # Process each chunk and merge results
            all_results = []
            for i, chunk in enumerate(chunks):
                print(f"Processing chunk {i+1}/{len(chunks)}...")
                try:
                    prompt = get_payoff_extraction_prompt(chunk)
                    result = self.llm_client.extract_json(prompt)
                    # Ensure result is a dictionary
                    if isinstance(result, dict):
                        all_results.append(result)
                    else:
                        print(f"Warning: Chunk {i+1} returned non-dict result, skipping")
                except Exception as e:
                    print(f"Error processing chunk {i+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Merge results
            if all_results:
                merged_result = self._merge_results(all_results)
                print("Extraction completed successfully!")
                return merged_result
            else:
                return {"error": "Failed to extract information from any chunk"}
        else:
            # Process entire document
            print("Extracting payoff information...")
            try:
                prompt = get_payoff_extraction_prompt(document_text)
                result = self.llm_client.extract_json(prompt)
                result = self._post_process_result(result)
                print("Extraction completed successfully!")
                return result
            except Exception as e:
                print(f"Error during extraction: {e}")
                return {
                    "error": f"Extraction failed: {str(e)}"
                }
    
    def _merge_results(self, results: list) -> Dict:
        """
        Merge multiple extraction results into one
        
        Args:
            results: List of extraction result dictionaries
            
        Returns:
            Merged result dictionary
        """
        merged = {}
        
        # Merge all results - use the most complete one or merge intelligently
        for result in results:
            if not isinstance(result, dict):
                continue
            
            # For each key in the result, merge into merged dict
            for key, value in result.items():
                if value is None or value == "":
                    continue
                
                if key not in merged:
                    # First time seeing this key, just use it
                    merged[key] = value
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    # Both are dicts, merge them
                    for sub_key, sub_value in value.items():
                        if sub_value and (sub_key not in merged[key] or not merged[key][sub_key]):
                            merged[key][sub_key] = sub_value
                elif isinstance(value, list) and isinstance(merged[key], list):
                    # Both are lists, merge unique items
                    # For conditional_coupons, check for duplicates based on trigger_condition
                    if key == "conditional_coupons":
                        seen_conditions = set()
                        # First, collect conditions from existing merged list
                        for item in merged[key]:
                            if isinstance(item, dict):
                                condition = item.get("trigger_condition", str(item))
                                seen_conditions.add(condition)
                        
                        # Then add new items that aren't duplicates
                        for item in value:
                            if isinstance(item, dict):
                                condition = item.get("trigger_condition", str(item))
                                if condition and condition not in seen_conditions:
                                    merged[key].append(item)
                                    seen_conditions.add(condition)
                            elif item not in merged[key]:
                                merged[key].append(item)
                    else:
                        # For other lists, just append unique items
                        for item in value:
                            if item not in merged[key]:
                                merged[key].append(item)
                else:
                    # If types don't match or value is more complete, use the new value
                    if isinstance(value, str) and len(value) > len(str(merged[key])):
                        merged[key] = value
                    elif not isinstance(merged[key], (dict, list)):
                        merged[key] = value
        
        return self._post_process_result(merged)
    
    def _post_process_result(self, result: Dict) -> Dict:
        """
        Post-process extraction result to fix common issues
        
        Args:
            result: Raw extraction result
            
        Returns:
            Cleaned and normalized result
        """
        # 1. Normalize underlyings (deduplicate and merge)
        result = self._normalize_underlyings(result)
        
        # 2. Fix structure_type based on deterministic rules
        result = self._fix_structure_type(result)
        
        # 3. Remove noise/redundant fields
        result = self._clean_noise_fields(result)
        
        return result
    
    def _normalize_underlyings(self, result: Dict) -> Dict:
        """
        Deduplicate and merge underlyings
        
        Simple strategy: Same name = same asset
        Priority: name > ticker > isin for matching
        """
        if "underlyings" not in result or not isinstance(result["underlyings"], list):
            return result
        
        # Build a map: name -> merged underlying
        underlying_map = {}
        
        for u in result["underlyings"]:
            if not isinstance(u, dict):
                continue
            
            # Extract identifiers (handle None properly)
            name = (u.get("name") or "").strip()
            ticker = (u.get("ticker") or "").strip()
            isin = (u.get("isin") or "").strip()
            
            # Skip if no name at all
            if not name:
                continue
            
            # Skip generic/placeholder names
            if self._is_generic_name(name):
                continue
            
            # Normalize name for consistent matching
            normalized_name = self._normalize_underlying_name(name)
            
            # Use normalized name as key
            if normalized_name not in underlying_map:
                underlying_map[normalized_name] = {
                    "name": name  # Keep original name
                }
            
            # Merge all non-empty fields into the existing entry
            for field, value in u.items():
                if not value or value in ("not specified", "N/A", ""):
                    continue
                
                # Update if field doesn't exist or we have a better value
                if field not in underlying_map[normalized_name]:
                    underlying_map[normalized_name][field] = value
                elif isinstance(value, (int, float)):
                    # Always prefer numeric values (like initial_price)
                    underlying_map[normalized_name][field] = value
                elif field in ("ticker", "isin") and value:
                    # Always take ticker/isin if we have it
                    underlying_map[normalized_name][field] = value
                elif field == "name" and len(value) > len(str(underlying_map[normalized_name].get(field, ""))):
                    # Keep the longer, more complete name
                    underlying_map[normalized_name]["name"] = value
        
        # Convert back to list
        result["underlyings"] = list(underlying_map.values())
        
        return result
    
    def _is_generic_name(self, name: str) -> bool:
        """Check if name is a generic placeholder"""
        if not name:
            return True
        
        generic_patterns = [
            "underlying",
            "underlying index",
            "underlying asset",
            "index",
            "share",
            "stock",
            "asset",
            "instrument"
        ]
        
        normalized = name.lower().strip()
        
        # Exact match with generic patterns
        if normalized in generic_patterns:
            return True
        
        # If it's only "underlying" + something generic
        if normalized.startswith("underlying") and len(normalized.split()) <= 2:
            return True
        
        return False
    
    def _normalize_underlying_name(self, name: str) -> str:
        """
        Normalize underlying name for consistent matching
        
        Examples:
        - "S&P 500" -> "s&p 500"
        - "Advanced Micro Devices Inc" -> "advanced micro devices"
        """
        if not name:
            return ""
        
        # Convert to lowercase and strip
        normalized = name.lower().strip()
        
        # Remove common suffixes (but keep important parts)
        normalized = normalized.replace(" inc", "")
        normalized = normalized.replace(" corp", "")
        normalized = normalized.replace(" ltd", "")
        normalized = normalized.replace(".", "")
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def _fix_structure_type(self, result: Dict) -> Dict:
        """
        Apply deterministic rule for structure_type based on underlyings
        
        Rule:
        - 1 underlying -> "single"
        - 2+ underlyings -> "worst_of"
        """
        underlyings = result.get("underlyings", [])
        num_underlyings = len(underlyings) if isinstance(underlyings, list) else 0
        
        # Only fix if structure_type is missing or unknown
        current_type = result.get("structure_type", "").lower()
        
        if not current_type or current_type == "unknown":
            if num_underlyings == 1:
                result["structure_type"] = "single"
            elif num_underlyings > 1:
                result["structure_type"] = "worst_of"
        
        return result
    
    def _clean_noise_fields(self, result: Dict) -> Dict:
        """
        Remove noise/redundant fields that shouldn't be in final payoff extraction
        """
        # Fields that are noise for payoff analysis
        noise_fields = [
            "distributor", "fees", "commissions", 
            "selling_restrictions", "offering_details",
            "suitability_assessment", "risk_factors",
            "form_of_notes", "governing_law", "listing",
            "business_day", "business_day_convention"
        ]
        
        for field in noise_fields:
            result.pop(field, None)
        
        return result
    
    def extract_section(self, section_text: str, section_name: str) -> Dict:
        """
        Extract information from a specific section
        
        Args:
            section_text: Text content of the section
            section_name: Name of the section
            
        Returns:
            Dictionary containing extracted information
        """
        print(f"Extracting from section: {section_name}")
        try:
            prompt = get_section_extraction_prompt(section_text, section_name)
            result = self.llm_client.extract_json(prompt)
            return result
        except Exception as e:
            return {
                "error": f"Failed to extract section: {str(e)}"
            }
    
    def validate_extraction(self, extracted_data: Dict, original_text: str) -> Dict:
        """
        Validate extracted data against original text
        
        Args:
            extracted_data: Previously extracted data
            original_text: Original document text for validation
            
        Returns:
            Validation results
        """
        print("Validating extraction...")
        try:
            extracted_json = json.dumps(extracted_data, indent=2, ensure_ascii=False)
            # Limit text for validation to avoid token limits
            validation_text = original_text[:2000] if len(original_text) > 2000 else original_text
            
            prompt = get_validation_prompt(extracted_json, validation_text)
            result = self.llm_client.extract_json(prompt)
            return result
        except Exception as e:
            return {
                "error": f"Validation failed: {str(e)}"
            }
    
    def extract_with_validation(self, pdf_path: str) -> Dict:
        """
        Extract and validate payoff information
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted and validated information
        """
        # Extract
        extracted = self.extract_from_pdf(pdf_path)
        
        if "error" in extracted:
            return extracted
        
        # Load original text for validation
        original_text = load_pdf_text(pdf_path)
        
        # Validate
        validation = self.validate_extraction(extracted, original_text)
        
        return {
            "extracted_data": extracted,
            "validation": validation
        }