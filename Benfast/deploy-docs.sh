 #!/bin/bash

# Benfast文档部署脚本

set -e

echo "🚀 Benfast 总文档站构建脚本"
echo "============================="

# 检查是否安装了UV
if ! command -v uv &> /dev/null; then
    echo "❌ UV 未安装，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
fi

# 安装文档依赖
echo "📦 安装文档依赖..."
uv sync --group docs

# 构建统一文档站
echo "🏗️  构建总文档站..."
PYTHONPATH=src venv/bin/python scripts/build_unified_site.py

# 检查构建结果
if [ -d "site" ]; then
    echo "✅ 文档构建成功！"
    echo "📁 构建文件位于: site/"
else
    echo "❌ 文档构建失败"
    exit 1
fi

echo ""
echo "📖 本地预览:"
echo "   python3 -m http.server 8800 --directory site"
echo "   访问地址: http://127.0.0.1:8800"
echo ""
echo "🎉 总文档站已完成构建。"
