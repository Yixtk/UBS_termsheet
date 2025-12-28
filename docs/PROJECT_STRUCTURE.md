# Project Structure

This document describes the organized structure of the UBS_FinAI project.

## Directory Layout

```
UBS_FinAI/
│
├── README.md                     # Main project documentation
├── requirements.txt              # Python dependencies
├── LICENSE                       # MIT License
├── .gitignore                   # Git ignore rules
├── LLM_variables.env            # API keys configuration (not in git)
├── git_push_ssh.sh              # Git push helper script
│
├── src/                         # Core source code
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── llm_client.py            # LLM API client (OpenAI/Anthropic/DeepSeek)
│   ├── document_loader.py       # PDF text extraction utilities
│   ├── prompt.py                # LLM prompt templates
│   ├── extractor.py             # PayoffExtractor main class
│   ├── payoff_ready_validator.py  # Data validation for payoff calculation
│   ├── payoff_single.py         # Single underlying Phoenix payoff engine
│   └── payoff_worst_of.py       # Worst-of Phoenix payoff engine
│
├── tests/                       # Test files
│   ├── __init__.py
│   ├── test.py                  # Main extraction tests
│   ├── test_case.py             # Test case definitions
│   └── test_payoff_engines.py   # Payoff calculation tests
│
├── scripts/                     # Utility scripts
│   ├── calculate_payoff_from_json.py  # Calculate payoffs from extraction JSON
│   └── compare_with_ground_truth.py   # Compare AI extraction with ground truth
│
├── data/                        # Input data files
│   ├── BNP-PhoenixSnowball-SP500-XS1083630027-TS.pdf
│   └── IT0006764473-TS.pdf
│
├── results/                     # Output files (not in git)
│   ├── test_results_*.json      # Extraction results
│   ├── payoff_results_*.json    # Payoff calculation results
│   └── *_comparison.json        # Ground truth comparison results
│
└── docs/                        # Documentation
    ├── README_PAYOFF_READY.md   # Payoff system documentation
    ├── PROJECT_STRUCTURE.md     # This file
    ├── SETUP.md                 # Setup instructions
    ├── GITHUB_UPLOAD_GUIDE.md   # GitHub upload guide
    ├── BNP Phoenix Snowball analysis.pdf
    ├── term_sheet_extraction.pdf
    └── termsheet search keywords.docx
```

## Module Descriptions

### Core Modules (`src/`)

#### `config.py`
- Manages API keys and LLM configuration
- Loads settings from `LLM_variables.env`
- Supports OpenAI, Anthropic Claude, DeepSeek, and Azure OpenAI

#### `llm_client.py`
- Unified LLM API client
- Handles requests to different providers
- Automatic retry logic and error handling

#### `document_loader.py`
- PDF text extraction using `pypdf`
- Text chunking for LLM processing
- Page-by-page loading support

#### `prompt.py`
- LLM prompt templates for extraction tasks
- Includes payoff extraction, section extraction, and validation prompts

#### `extractor.py`
- `PayoffExtractor` class - main extraction orchestrator
- Multi-stage extraction pipeline
- Post-processing and validation logic

#### `payoff_ready_validator.py`
- Schema validation for extracted data
- Ensures data is suitable for payoff calculation
- Type checking and required field verification

#### `payoff_single.py`
- Payoff calculation engine for single-underlying Phoenix products
- Handles auto-call, coupon payments, and knock-in scenarios

#### `payoff_worst_of.py`
- Payoff calculation engine for worst-of Phoenix products
- Supports multiple underlyings with barrier monitoring
- Memory coupon and early redemption logic

### Test Modules (`tests/`)

#### `test.py`
- Runs extraction tests on PDF term sheets
- Validates schema and required fields
- Saves results to JSON files

#### `test_case.py`
- Defines test cases with expected outcomes
- Maps PDF files to their expected structure types

#### `test_payoff_engines.py`
- Integration tests for payoff engines
- Simulates different market scenarios (bullish, bearish, sideways)

### Utility Scripts (`scripts/`)

#### `calculate_payoff_from_json.py`
- Reads extraction JSON files
- Calculates payoffs for multiple scenarios
- Saves results with detailed breakdown

#### `compare_with_ground_truth.py`
- Compares AI extraction results with human-verified ground truth
- Generates detailed comparison reports
- Identifies discrepancies and calculates accuracy metrics

## Import Structure

All modules use absolute imports from the project root:

```python
# Example imports in tests/
from src.extractor import PayoffExtractor
from src.payoff_single import SinglePhoenixPayoff

# Example imports in src/
from src.config import LLM_PROVIDER, LLM_MODEL
from src.llm_client import LLMClient
```

## Running the Project

### From Project Root

All scripts should be run from the project root directory:

```bash
# Run extraction tests
python -m tests.test

# Run payoff engine tests
python -m tests.test_payoff_engines

# Calculate payoffs from JSON
python -m scripts.calculate_payoff_from_json

# Compare with ground truth
python -m scripts.compare_with_ground_truth results/test_results_*.json
```

### Import Path Setup

Each script includes path setup code to ensure proper imports:

```python
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
```

## Data Flow

```
PDF Term Sheet (data/)
    ↓
[document_loader.py] → Extract text
    ↓
[extractor.py + llm_client.py] → LLM extraction
    ↓
[payoff_ready_validator.py] → Validate structure
    ↓
[payoff_single.py / payoff_worst_of.py] → Calculate payoffs
    ↓
Results JSON (results/)
    ↓
[compare_with_ground_truth.py] → Evaluate accuracy
```

## Configuration

### Environment Variables (`LLM_variables.env`)

```bash
# Required for each provider
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
LLM_TEMPERATURE=0.0
```

### Supported Providers

- **OpenAI**: `gpt-4`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-sonnet-20240229`, `claude-3-opus-20240229`
- **DeepSeek**: `deepseek-chat`
- **Azure OpenAI**: Custom deployment names

## Output Files

### Extraction Results (`results/test_results_*.json`)
- Contains extracted payoff structure from PDF
- Includes validation status and error messages

### Payoff Results (`results/payoff_results_*.json`)
- Calculated payoffs for different scenarios
- Detailed breakdown of coupons, auto-call events, knock-in status

### Comparison Reports (`results/*_comparison.json`)
- Field-by-field comparison with ground truth
- Overall accuracy metrics
- Identified discrepancies

## Best Practices

1. **Always run from project root**: Ensures correct import paths
2. **Keep API keys in LLM_variables.env**: Never commit to git
3. **Use absolute imports**: From `src.*` and `tests.*`
4. **Validate before calculation**: Use `payoff_ready_validator.py`
5. **Save results with timestamps**: Avoid overwriting previous runs

## Maintenance

- **Adding new extractors**: Place in `src/` and update `extractor.py`
- **Adding new tests**: Place in `tests/` with proper imports
- **Adding new scripts**: Place in `scripts/` with path setup
- **Updating documentation**: Keep `docs/` files synchronized

---

**Last Updated**: December 26, 2025
