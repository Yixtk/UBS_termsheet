# GitHub Upload Guide

## 🚀 Quick Upload Steps

### Option 1: Using GitHub Desktop (Easiest)

1. Download and install [GitHub Desktop](https://desktop.github.com/)
2. Sign in with your GitHub account
3. Click "Add" → "Add Existing Repository"
4. Select this folder: `UBS_FinAI`
5. Click "Publish repository"
6. Choose repository name and visibility (Public/Private)
7. Click "Publish"

### Option 2: Using Command Line

```bash
# Navigate to project directory
cd /Users/yixiangtiankai/Documents/UBS_FinAI

# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Structured Product Extraction & Payoff Calculator"

# Create repository on GitHub.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Option 3: Using GitHub Web UI

1. Create a new repository on [GitHub.com](https://github.com/new)
2. **Don't** initialize with README (we already have one)
3. Use "upload files" button
4. Drag and drop all files from this folder

---

## ⚠️ Before Uploading - Security Checklist

### ✅ What's Already Protected

The `.gitignore` file automatically excludes:
- ✅ `LLM_variables.env` (your API keys)
- ✅ `test_results_*.json` (temporary test outputs)
- ✅ `payoff_results_*.json` (temporary payoff outputs)
- ✅ `__pycache__/` (Python cache)

### 🔒 Manual Check: Remove Sensitive Files

Before uploading, double-check these files are NOT included:

```bash
# Check for API keys
cat LLM_variables.env  # Should NOT be uploaded

# Remove if exists
rm LLM_variables.env
```

### 📄 Optional: Decide on PDF Files

PDFs are currently **included** in the repository. If you want to exclude them:

1. Edit `.gitignore` and uncomment:
   ```
   *.pdf
   *.docx
   ```

2. Remove from git:
   ```bash
   git rm --cached *.pdf
   git rm --cached "*.docx"
   ```

---

## 📝 Recommended Repository Settings

### Repository Name
`structured-product-extraction` or `phoenix-payoff-calculator`

### Description
```
AI-powered extraction of structured product term sheets and payoff calculation for Phoenix Snowball products
```

### Topics (for discoverability)
```
structured-products
financial-engineering
llm
pdf-extraction
payoff-calculation
phoenix-snowball
ai-finance
quantitative-finance
```

### README Badges (optional)
Already included in README.md:
- Python version
- License

---

## 🎯 After Upload

### 1. Verify Upload
- Check all files are present
- Ensure `.gitignore` is working (no `LLM_variables.env`)
- Test clone: `git clone YOUR_REPO_URL`

### 2. Set Up GitHub Actions (optional)
Create `.github/workflows/test.yml` for automated testing:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python -m pytest
```

### 3. Add Releases (optional)
- Create a release tag: `v1.0.0`
- Add release notes describing the system

---

## 📊 What Gets Uploaded (Summary)

### ✅ Core Code
- All `.py` files
- `requirements.txt`
- `README.md`, `SETUP.md`, `LICENSE`

### ✅ Sample Data (optional)
- `BNP-PhoenixSnowball-SP500-XS1083630027-TS.pdf`
- `IT0006764473-TS.pdf`

### ❌ NOT Uploaded (Automatic)
- `LLM_variables.env` (API keys)
- `test_results_*.json` (temporary)
- `__pycache__/` (Python cache)
- `.DS_Store` (Mac system file)

---

## 🎉 You're Ready!

Your project is now GitHub-ready with:
- ✅ Professional README
- ✅ Clear setup instructions  
- ✅ Security (API keys protected)
- ✅ License (MIT)
- ✅ Proper `.gitignore`

Just pick Upload Option 1, 2, or 3 above and go! 🚀

