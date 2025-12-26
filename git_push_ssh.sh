#!/bin/bash
# GitHub SSH Push Script
# 使用前请确保已配置 SSH key

echo "=========================================="
echo "GitHub SSH 推送脚本"
echo "=========================================="

# 进入项目目录
cd /Users/yixiangtiankai/Documents/UBS_FinAI

# 检查是否已初始化 git
if [ ! -d ".git" ]; then
    echo "正在初始化 Git 仓库..."
    git init
    git branch -M main
else
    echo "Git 仓库已存在"
fi

# 添加所有文件
echo "正在添加文件..."
git add .

# 提交
echo "正在提交..."
git commit -m "Initial commit: Structured Product Extraction & Payoff Calculator System

Features:
- PDF extraction with LLM (100% accuracy on test set)
- Post-processing with deterministic rules
- Payoff calculation for Phoenix products (single & worst-of)
- Complete validation layer
- Comprehensive documentation"

# 提示用户输入仓库信息
echo ""
echo "=========================================="
echo "请在 GitHub 上创建一个新仓库"
echo "=========================================="
echo "1. 访问: https://github.com/new"
echo "2. 创建仓库后，复制 SSH URL"
echo "   格式: git@github.com:USERNAME/REPO_NAME.git"
echo ""
read -p "请输入仓库的 SSH URL: " REPO_URL

# 添加远程仓库
echo "正在添加远程仓库..."
git remote add origin "$REPO_URL"

# 推送到 GitHub
echo "正在推送到 GitHub..."
git push -u origin main

echo ""
echo "=========================================="
echo "✅ 推送完成！"
echo "=========================================="
echo "访问您的仓库: https://github.com/$(echo $REPO_URL | cut -d':' -f2 | cut -d'.' -f1)"



