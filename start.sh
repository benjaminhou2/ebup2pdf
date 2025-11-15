#!/bin/bash
# EPUB 转 PDF 转换工具启动脚本

echo "📚 EPUB 转 PDF 转换工具"
echo "========================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.7 或更高版本"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"
echo ""

# 检查 Calibre 是否安装
if ! command -v ebook-convert &> /dev/null; then
    echo "⚠️  警告: 未检测到 Calibre"
    echo ""
    echo "请先安装 Calibre:"
    echo "  macOS: brew install calibre"
    echo "  Linux: sudo apt-get install calibre"
    echo "  或访问: https://calibre-ebook.com/download"
    echo ""
    echo "服务器仍会启动，但转换功能将无法使用。"
    echo ""
else
    echo "✅ Calibre 已安装"
    echo ""
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
pip install -q -r requirements.txt

echo ""
echo "🚀 启动服务器..."
echo "📖 访问 http://localhost:5000 使用转换工具"
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动 Flask 应用
python3 app.py

