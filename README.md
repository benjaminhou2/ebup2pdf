# EPUB 转 PDF 转换工具

一个简单易用的本地网页工具，可以将 EPUB 格式的电子书转换为 PDF 格式，并保持原有的图片、图形、排版和公式不变。

## 功能特点

- 📚 支持 EPUB 格式电子书上传
- 📄 转换为高质量 PDF 文件
- 🎨 保持原有图片、图形、排版和公式
- 💻 本地运行，无需联网
- 🎯 简单易用的网页界面

## 系统要求

- Python 3.7 或更高版本
- Calibre（电子书管理工具）
  - macOS: `brew install calibre` 或从 [官网下载](https://calibre-ebook.com/download)
  - Windows: 从 [官网下载](https://calibre-ebook.com/download) 安装程序
  - Linux: `sudo apt-get install calibre` 或使用包管理器

## 安装步骤

1. 确保已安装 Python 和 Calibre
2. 安装 Python 依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 启动服务器：
   ```bash
   python app.py
   ```
4. 在浏览器中打开 `http://localhost:5000`

## 使用方法

1. 打开网页后，点击"选择文件"按钮
2. 选择要转换的 EPUB 文件
3. 点击"转换为 PDF"按钮
4. 等待转换完成
5. 下载生成的 PDF 文件

## 项目结构

```
epub2pdf/
├── README.md          # 项目说明文档
├── requirements.txt   # Python 依赖列表
├── app.py            # Flask 后端应用
├── templates/        # HTML 模板目录
│   └── index.html    # 前端页面
└── uploads/          # 上传文件临时目录（自动创建）
└── outputs/          # 输出 PDF 文件目录（自动创建）
```

## 技术栈

- 前端：HTML + CSS + JavaScript
- 后端：Python Flask
- 转换工具：Calibre ebook-convert

## 注意事项

- 转换大文件可能需要一些时间，请耐心等待
- 确保有足够的磁盘空间存储转换后的 PDF 文件
- 转换质量取决于原始 EPUB 文件的质量

