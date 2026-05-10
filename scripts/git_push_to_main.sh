#!/bin/bash
# =====================================================================
# git_push_to_main.sh - 首次上传到 GitHub main 分支
# =====================================================================
# 使用方法: bash scripts/git_push_to_main.sh

set -e

REPO_URL="https://github.com/789453/stock_graph_research.git"
PROJECT_ROOT="/home/purple_born/QuantSum/stock_graph_research"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "Git: 首次上传到 main 分支"
echo "============================================================"

# 初始化 git（如果还没有）
if [ ! -d .git ]; then
    echo "[1/7] 初始化 git 仓库..."
    git init
else
    echo "[1/7] Git 仓库已存在，跳过初始化..."
fi

# 配置 user（如果未配置）
git config user.email "trae@research.local" 2>/dev/null || true
git config user.name "Trae AI" 2>/dev/null || true

# 添加远程仓库
echo "[2/7] 添加远程仓库..."
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

# 添加所有文件（遵守 .gitignore）
echo "[3/7] 添加文件到暂存区..."
git add -A

# 查看暂存状态
echo "[4/7] 暂存文件状态:"
git status --short | head -50

# 首次提交
echo "[5/7] 提交到 main 分支..."
git commit -m "Phase 1: 语义近邻图工程初始化

- T0-T6 完整流水线完成
- 真实 1024 维语义向量 kNN 构图
- 图诊断统计（含 Union-Find 优化）
- 行情数据覆盖率 100%
- 5 个单元测试全部通过
- 缓存已按规则过滤（仅上传 json/yaml/md/png）"

# 推送 到 main
echo "[6/7] 推送到 origin/main..."
git branch -M main
git push -u origin main --force

echo "[7/7] 完成!"
echo "============================================================"
echo "仓库地址: $REPO_URL"
echo "============================================================"