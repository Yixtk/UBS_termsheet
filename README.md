# Structured Product Payoff Extraction & Calculator

🏦 **AI-powered system for extracting structured product information from PDF term sheets and calculating payoffs**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Overview

This system uses Large Language Models to automatically extract payoff information from structured product term sheets and calculates payoffs for various market scenarios.

### Key Features

- ✅ **Automated PDF Extraction**: Parse Phoenix Snowball and Worst-of products
- ✅ **High Accuracy**: Validated against ground truth with deterministic post-processing
- ✅ **Payoff Calculation**: Calculate coupons and payoffs for multiple scenarios
- ✅ **Safety Validation**: Built-in guardrails for production-grade reliability
- ✅ **Extensible**: Easy to add new product types

### Supported Products

- **Single Underlying Phoenix** (e.g., Phoenix Snowball on S&P 500)
- **Worst-of Phoenix** (e.g., Phoenix on AMD/NVDA/INTC basket)

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/Yixtk/UBS_FinAI.git
cd UBS_FinAI
pip install -r requirements.txt
```

### Configuration

Create `LLM_variables.env` with your API key:

```bash
# Choose your LLM provider
LLM_PROVIDER=anthropic  # or "openai" / "deepseek"
ANTHROPIC_API_KEY=your-api-key-here
LLM_MODEL=claude-3-sonnet-20240229
LLM_TEMPERATURE=0.0
```

### Usage

```bash
# 1. Extract from PDF
python -m tests.test

# 2. Calculate payoffs
python -m scripts.calculate_payoff_from_json results/test_results_*.json

# 3. Compare with ground truth
python -m scripts.compare_with_ground_truth results/test_results_*.json
```

---

## 📖 Example

```python
from src.prompts import PayoffExtractor
from src.payoff_single import SinglePhoenixPayoff

# Extract from PDF
extractor = PayoffExtractor()
result = extractor.extract_from_pdf("data/your_termsheet.pdf")

# Calculate payoff
calc = SinglePhoenixPayoff(result)
price_path = [2000, 2100, 2200, 2300, 2400]
coupons, payoff, details = calc.calculate_payoff(price_path)

print(f"Total Value: ${coupons + payoff:.2f}")
```

---

## 📁 Project Structure

```
UBS_FinAI/
├── src/                    # Core source code
│   ├── prompts.py          # Extraction orchestrator
│   ├── llm_client.py       # LLM API client
│   ├── payoff_single.py    # Single underlying payoff engine
│   └── payoff_worst_of.py  # Worst-of payoff engine
├── tests/                  # Test files
├── scripts/                # Utility scripts
├── data/                   # Input PDF files
├── results/                # Output JSON files
└── docs/                   # Documentation

For detailed structure, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
```

---

## 🔧 Architecture

```
PDF → Document Loader → LLM Extraction → Post-Processing → 
Validation → Payoff Calculation → Results
```

### Key Components

- **Hybrid AI + Rules**: LLM intelligence + deterministic post-processing
- **Post-Processing**: Deduplicates underlyings, normalizes structure type
- **Validation Layer**: Schema validation before payoff calculation
- **Payoff Engines**: Separate calculators for single/worst-of products

---

## ✅ Accuracy

Tested on real term sheets from BNP Paribas and Natixis:

| Metric | Score |
|--------|-------|
| Structure Type | 100% (2/2) |
| Underlying Extraction | 100% (4/4) |
| Date Extraction | 100% (49/49) |
| **Overall Payoff-Ready** | **100%** |

---

## 📝 Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation and configuration
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Code organization
- **[Payoff System](docs/README_PAYOFF_READY.md)** - Technical details
- **[GitHub Guide](docs/GITHUB_UPLOAD_GUIDE.md)** - Contribution guide

---

## 🚨 Disclaimer

⚠️ This is a research/prototype system. Always verify extracted data and calculated payoffs against official term sheets before using for trading or client-facing purposes.

---

## 🙏 Acknowledgments

This project builds upon and extends the original work from:

- **[gdgdandsz/UBS_termsheet](https://github.com/gdgdandsz/UBS_termsheet)** - Original term sheet extraction framework  
  Special thanks for the foundational extraction architecture and LLM integration approach.

- **Team Members' Analysis**:
  - BNP Phoenix Snowball analysis documentation
  - Term sheet extraction methodology research
  - Financial product structure analysis

### Enhancements in This Version

- ✨ Organized project structure with `src/`, `tests/`, `scripts/` separation
- ✨ Dedicated payoff calculation engines for single and worst-of products
- ✨ Post-processing layer with deterministic rules for data normalization
- ✨ Payoff validation system with schema checking
- ✨ Ground truth comparison and accuracy evaluation
- ✨ Comprehensive documentation and usage examples
- ✨ Support for multiple LLM providers (OpenAI, Anthropic, DeepSeek)

---

## 📧 Contact

For questions or issues, please open a [GitHub issue](https://github.com/Yixtk/UBS_FinAI/issues).

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Built with Claude Sonnet 4.5** | **Tested on actual structured product term sheets**
