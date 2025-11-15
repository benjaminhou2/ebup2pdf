@echo off
REM EPUB 转 PDF 转换工具启动脚本 (Windows)

echo 📚 EPUB 转 PDF 转换工具
echo ========================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.7 或更高版本
    pause
    exit /b 1
)

echo ✅ Python 已安装
echo.

REM 检查 Calibre 是否安装
ebook-convert --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告: 未检测到 Calibre
    echo.
    echo 请先安装 Calibre:
    echo 访问: https://calibre-ebook.com/download
    echo.
    echo 服务器仍会启动，但转换功能将无法使用。
    echo.
) else (
    echo ✅ Calibre 已安装
    echo.
)

REM 检查虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo 📥 安装依赖包...
pip install -q -r requirements.txt

echo.
echo 🚀 启动服务器...
echo 📖 访问 http://localhost:5000 使用转换工具
echo 按 Ctrl+C 停止服务器
echo.

REM 启动 Flask 应用
python app.py

pause

