# Setup Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure API Keys

Create a file named `.env` or `LLM_variables.env` in the project root:

```bash
# Choose your LLM provider
LLM_PROVIDER=anthropic  # options: "openai", "anthropic", "deepseek"

# Add your API key
ANTHROPIC_API_KEY=your-anthropic-api-key-here
# OPENAI_API_KEY=your-openai-api-key-here  
# DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Model configuration
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_TEMPERATURE=0.0
```

### Getting API Keys

- **Anthropic (Claude)**: https://console.anthropic.com/
- **OpenAI (GPT-4)**: https://platform.openai.com/api-keys
- **DeepSeek**: https://platform.deepseek.com/

## Step 3: Run Tests

```bash
# Test extraction
python test.py

# Validate accuracy
python compare_with_ground_truth.py test_results_*.json

# Calculate payoffs
python calculate_payoff_from_json.py test_results_*.json
```

## Step 4: Use with Your Own PDFs

```python
from prompts import PayoffExtractor

extractor = PayoffExtractor()
result = extractor.extract_from_pdf("your_termsheet.pdf")

# Result will be saved automatically
print(result)
```

## Troubleshooting

### Issue: "Module not found: pypdf"
```bash
pip install pypdf
```

### Issue: "API key not found"
- Make sure your `.env` or `LLM_variables.env` file exists
- Check the file is in the project root directory
- Verify the API key variable names match

### Issue: "Extraction fails"
- Ensure PDF is readable (not image-based)
- Check API rate limits
- Try with a different LLM provider

