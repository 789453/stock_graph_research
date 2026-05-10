#!/bin/bash
# =====================================================================
# git_update_main.sh - 更新到 GitHub main 分支（增量更新）
# =====================================================================
# 使用方法: bash scripts/git_update_main.sh

set -e

REPO_URL="https://github.com/789453/stock_graph_research.git"
PROJECT_ROOT="/home/purple_born/QuantSum/stock_graph_research"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "Git: 增量更新到 main 分支"
echo "============================================================"

# 确保 git 已初始化
if [ ! -d .git ]; then
    echo "[ERROR] Git 仓库未初始化，请先运行 git_push_to_main.sh"
    exit 1
fi

# 检查远程仓库
if ! git remote get-url origin &>/dev/null; then
    echo "[1/5] 添加远程仓库..."
    git remote add origin "$REPO_URL"
else
    echo "[1/5] 远程仓库已配置..."
fi

# 配置 user（如果未配置）
git config user.email "trae@research.local" 2>/dev/null || true
git config user.name "Trae AI" 2>/dev/null || true

# 添加所有变更（遵守 .gitignore）
echo "[2/5] 添加文件到暂存区..."
git add -A

# 查看变更状态
echo "[3/5] 变更文件状态:"
git status --short | head -50

# 检查是否有变更
if git diff --cached --quiet; then
    echo "[WARNING] 没有新的变更需要提交"
    exit 0
fi

# 提交变更
echo "[4/5] 提交变更..."
git commit -m "Update: $(date '+%Y-%m-%d %H:%M:%S')

$(git status --short | head -20)"

# 推送到 main
echo "[5/5] 推送到 origin/main..."
git push origin main

echo "============================================================"
echo "更新完成! 仓库地址: $REPO_URL"
echo "============================================================"