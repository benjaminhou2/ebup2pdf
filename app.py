#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB 转 PDF 转换工具 - Flask 后端应用
使用 Calibre 的 ebook-convert 命令进行高质量转换
"""

import os
import subprocess
import shutil
import threading
import time
import json
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from werkzeug.utils import secure_filename
import uuid
import re

# 创建 Flask 应用实例
app = Flask(__name__)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 最大文件大小 100MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# 确保上传和输出目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'epub'}

# 存储转换任务状态
conversion_tasks = {}

# 文件名映射文件（持久化存储原始文件名）
FILENAME_MAPPING_FILE = 'filename_mapping.json'

def load_filename_mapping():
    """加载文件名映射"""
    if os.path.exists(FILENAME_MAPPING_FILE):
        try:
            with open(FILENAME_MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_filename_mapping(mapping):
    """保存文件名映射"""
    try:
        with open(FILENAME_MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
    except:
        pass

def add_filename_mapping(storage_filename, original_filename):
    """添加文件名映射"""
    mapping = load_filename_mapping()
    mapping[storage_filename] = original_filename
    save_filename_mapping(mapping)

def get_original_filename(storage_filename):
    """获取原始文件名"""
    mapping = load_filename_mapping()
    return mapping.get(storage_filename)

# 缓存 Calibre 检查结果（避免每次请求都检查）
_calibre_cache = {'installed': None, 'check_time': 0, 'path': None}
CALIBRE_CACHE_DURATION = 300  # 缓存 5 分钟


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def find_ebook_convert():
    """查找 ebook-convert 命令的路径"""
    # 可能的路径列表
    possible_paths = [
        'ebook-convert',  # 系统 PATH 中
        '/Applications/calibre.app/Contents/MacOS/ebook-convert',  # macOS 应用路径
        '/Applications/Calibre.app/Contents/MacOS/ebook-convert',  # 大写版本
        os.path.expanduser('~/Applications/calibre.app/Contents/MacOS/ebook-convert'),  # 用户应用目录
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run(
                [path, '--version'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    return None


def check_calibre(use_cache=True):
    """检查 Calibre 是否已安装（带缓存）"""
    current_time = time.time()
    
    # 如果使用缓存且缓存未过期，直接返回缓存结果
    if use_cache and _calibre_cache['installed'] is not None:
        if current_time - _calibre_cache['check_time'] < CALIBRE_CACHE_DURATION:
            return _calibre_cache['installed']
    
    # 查找 ebook-convert 命令
    ebook_convert_path = find_ebook_convert()
    installed = ebook_convert_path is not None
    
    # 更新缓存
    _calibre_cache['installed'] = installed
    _calibre_cache['check_time'] = current_time
    _calibre_cache['path'] = ebook_convert_path  # 缓存路径
    
    return installed


def get_ebook_convert_path():
    """获取 ebook-convert 的完整路径"""
    if _calibre_cache.get('path'):
        return _calibre_cache['path']
    
    # 如果缓存中没有，重新查找
    check_calibre(use_cache=False)
    return _calibre_cache.get('path', 'ebook-convert')


def convert_epub_to_pdf(epub_path, pdf_path, task_id):
    """
    使用 Calibre 将 EPUB 转换为 PDF（带进度更新）
    
    参数:
        epub_path: EPUB 文件路径
        pdf_path: 输出 PDF 文件路径
        task_id: 任务 ID，用于更新进度
    
    返回:
        (success: bool, error_message: str)
    """
    try:
        # 初始化任务状态
        conversion_tasks[task_id] = {
            'status': 'running',
            'progress': 0,
            'message': '准备开始转换...',
            'start_time': time.time()
        }
        
        # 获取 ebook-convert 的完整路径
        ebook_convert_path = get_ebook_convert_path()
        
        # 使用 Calibre 的 ebook-convert 命令进行转换
        # 注意：某些选项可能在不同版本的 Calibre 中不支持，已移除不兼容选项
        cmd = [
            ebook_convert_path,
            epub_path,
            pdf_path,
            '--base-font-size', '12',
            '--pdf-page-numbers',
            '--pdf-mark-links',
            '--embed-font-family', 'Times New Roman',
            '--pdf-default-font-size', '12',
            '--pdf-mono-font-size', '12',
            '--pdf-standard-font', 'serif',
            '--preserve-cover-aspect-ratio',
            '--keep-ligatures',
            '--pdf-page-margin-left', '72',
            '--pdf-page-margin-right', '72',
            '--pdf-page-margin-top', '72',
            '--pdf-page-margin-bottom', '72',
        ]
        
        # 更新进度：开始转换
        conversion_tasks[task_id].update({
            'progress': 10,
            'message': '正在解析 EPUB 文件结构...'
        })
        
        # 执行转换命令，实时读取输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 读取输出并更新进度
        last_update_time = time.time()
        output_lines = []
        max_duration = 600  # 最大转换时间 10 分钟
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            
            current_time = time.time()
            elapsed = current_time - conversion_tasks[task_id]['start_time']
            
            # 检查超时
            if elapsed > max_duration:
                process.kill()
                conversion_tasks[task_id].update({
                    'status': 'failed',
                    'message': f'转换超时（超过 {max_duration} 秒），文件可能过大或过于复杂'
                })
                return False, '转换超时'
            
            if output:
                output_lines.append(output.strip())
                
                # 每 0.5 秒更新一次进度，避免过于频繁
                if current_time - last_update_time >= 0.5:
                    # 根据输出内容判断阶段
                    output_lower = output.lower()
                    if 'cover' in output_lower or '封面' in output_lower:
                        progress = 20
                        message = '正在处理封面...'
                    elif 'image' in output_lower or '图片' in output_lower:
                        progress = min(30 + int(elapsed * 0.4), 70)
                        message = f'正在处理图片和内容... ({int(elapsed)}秒)'
                    elif 'pdf' in output_lower or 'generating' in output_lower or 'render' in output_lower:
                        progress = min(70 + int(elapsed * 0.2), 90)
                        message = f'正在生成 PDF 文件... ({int(elapsed)}秒)'
                    else:
                        # 基于时间的进度估算（前 30% 快速，后面慢一些）
                        if elapsed < 10:
                            progress = min(10 + int(elapsed * 2), 30)
                        else:
                            progress = min(30 + int((elapsed - 10) * 0.6), 85)
                        message = f'正在转换中... ({int(elapsed)}秒)'
                    
                    conversion_tasks[task_id].update({
                        'progress': progress,
                        'message': message
                    })
                    last_update_time = current_time
            
            # 即使没有输出，也定期更新进度（防止卡住）
            elif current_time - last_update_time >= 2:
                progress = min(30 + int(elapsed * 0.5), 85)
                message = f'正在处理中... ({int(elapsed)}秒)'
                conversion_tasks[task_id].update({
                    'progress': progress,
                    'message': message
                })
                last_update_time = current_time
        
        # 等待进程完成
        return_code = process.poll()
        
        if return_code == 0:
            conversion_tasks[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': '转换完成！'
            })
            return True, None
        else:
            error_msg = '\n'.join(output_lines[-10:]) or '转换失败，未知错误'
            conversion_tasks[task_id].update({
                'status': 'failed',
                'message': f'转换失败: {error_msg[:100]}'
            })
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        conversion_tasks[task_id].update({
            'status': 'failed',
            'message': '转换超时，文件可能过大或过于复杂'
        })
        return False, '转换超时，文件可能过大或过于复杂'
    except Exception as e:
        conversion_tasks[task_id].update({
            'status': 'failed',
            'message': f'转换过程中发生错误: {str(e)}'
        })
        return False, f'转换过程中发生错误: {str(e)}'


@app.route('/')
def index():
    """主页路由"""
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    """处理文件上传，返回任务 ID"""
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['file']
    
    # 检查文件名
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    # 检查文件格式
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式，请上传 EPUB 文件'}), 400
    
    # 检查 Calibre 是否安装（不使用缓存，确保实时检测）
    if not check_calibre(use_cache=False):
        return jsonify({
            'error': '未检测到 Calibre，请先安装 Calibre。\n'
                     'macOS: brew install calibre\n'
                     '或访问: https://calibre-ebook.com/download\n\n'
                     '安装完成后，请刷新页面或重启服务器。'
        }), 500
    
    # 生成唯一任务 ID
    task_id = str(uuid.uuid4())
    
    # 保存原始文件名（用于最终下载）
    original_filename = file.filename
    # 使用 secure_filename 处理文件名用于存储（避免安全问题）
    safe_filename = secure_filename(original_filename)
    
    # 生成 PDF 文件名（保持原始文件名，只改扩展名）
    if original_filename.lower().endswith('.epub'):
        pdf_original_filename = original_filename[:-5] + '.pdf'
    else:
        pdf_original_filename = original_filename.rsplit('.', 1)[0] + '.pdf'
    
    # 存储路径（使用 UUID 前缀避免文件名冲突）
    epub_path = os.path.join(
        app.config['UPLOAD_FOLDER'],
        f'{task_id}_{safe_filename}'
    )
    
    # 保存上传的文件
    try:
        file.save(epub_path)
    except Exception as e:
        return jsonify({'error': f'保存文件失败: {str(e)}'}), 500
    
    # PDF 存储路径（使用 UUID 前缀）
    pdf_safe_filename = secure_filename(pdf_original_filename)
    pdf_path = os.path.join(
        app.config['OUTPUT_FOLDER'],
        f'{task_id}_{pdf_safe_filename}'
    )
    
    # 在后台线程中执行转换
    def run_conversion():
        try:
            success, error_message = convert_epub_to_pdf(epub_path, pdf_path, task_id)
            
            if success:
                storage_filename = f'{task_id}_{pdf_safe_filename}'
                # 保存文件名映射到持久化文件
                add_filename_mapping(storage_filename, pdf_original_filename)
                
                conversion_tasks[task_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'message': '转换完成！',
                    'filename': storage_filename,  # 存储文件名（带 UUID）
                    'original_filename': pdf_original_filename  # 原始文件名（用于下载，保持与 EPUB 文件名一致）
                })
            else:
                conversion_tasks[task_id].update({
                    'status': 'failed',
                    'message': error_message or '转换失败'
                })
                # 清理失败的输出文件
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except:
                    pass
        finally:
            # 清理上传的 EPUB 文件
            try:
                os.remove(epub_path)
            except:
                pass
    
    # 启动转换线程
    thread = threading.Thread(target=run_conversion)
    thread.daemon = True
    thread.start()
    
    # 返回任务 ID
    return jsonify({
        'task_id': task_id,
        'message': '文件上传成功，开始转换...'
    })


@app.route('/progress/<task_id>')
def progress(task_id):
    """SSE 端点，推送转换进度"""
    def generate():
        """生成 SSE 事件流"""
        last_status = None
        last_progress = -1
        
        while True:
            if task_id not in conversion_tasks:
                yield f"data: {json.dumps({'error': '任务不存在'})}\n\n"
                break
            
            task = conversion_tasks[task_id]
            status = task.get('status')
            progress = task.get('progress', 0)
            message = task.get('message', '')
            
            # 只在状态或进度变化时发送更新
            if status != last_status or progress != last_progress:
                data = {
                    'status': status,
                    'progress': progress,
                    'message': message
                }
                
                # 如果完成或失败，发送最终结果
                if status in ['completed', 'failed']:
                    if status == 'completed':
                        data['filename'] = task.get('filename')
                        data['original_filename'] = task.get('original_filename')
                    data['error'] = message if status == 'failed' else None
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                else:
                    yield f"data: {json.dumps(data)}\n\n"
                
                last_status = status
                last_progress = progress
            
            time.sleep(0.5)  # 每 0.5 秒检查一次
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/download/<filename>')
def download(filename):
    """下载转换后的 PDF 文件"""
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 从转换任务中获取原始文件名（如果存在）
    # filename 格式: {task_id}_{secure_filename}
    original_filename = None
    
    # 优先从持久化映射文件中获取（即使服务器重启也能找到）
    original_filename = get_original_filename(filename)
    
    # 如果映射文件中没有，尝试从内存中的任务记录获取
    if not original_filename:
        for task_id_key, task_info in conversion_tasks.items():
            if task_info.get('filename') == filename:
                original_filename = task_info.get('original_filename')
                break
    
    # 如果还是找不到，从文件名中提取（去掉 UUID 前缀）
    if not original_filename:
        if '_' in filename:
            parts = filename.split('_', 1)
            if len(parts) == 2:
                stored_filename = parts[1]
                # 将 secure_filename 处理过的文件名恢复为 PDF 格式
                # 如果存储的文件名以 .pdf 结尾，直接使用
                if stored_filename.lower().endswith('.pdf'):
                    original_filename = stored_filename
                else:
                    # 否则添加 .pdf 扩展名
                    original_filename = stored_filename.rsplit('.', 1)[0] + '.pdf'
            else:
                original_filename = filename
        else:
            original_filename = filename
    
    # 确保文件名不为空
    if not original_filename:
        original_filename = 'converted.pdf'
    
    # 使用 send_file 下载文件，设置正确的下载文件名
    # Flask 2.0+ 使用 download_name，旧版本使用 attachment_filename
    try:
        # 尝试使用 download_name (Flask 2.0+)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=original_filename,
            mimetype='application/pdf'
        )
    except TypeError:
        # 如果失败，尝试使用 attachment_filename (Flask < 2.0)
        return send_file(
            file_path,
            as_attachment=True,
            attachment_filename=original_filename,
            mimetype='application/pdf'
        )


@app.route('/health')
def health():
    """健康检查接口"""
    # 使用缓存，避免阻塞
    calibre_installed = check_calibre(use_cache=True)
    return jsonify({
        'status': 'ok',
        'calibre_installed': calibre_installed
    })


@app.route('/refresh-calibre')
def refresh_calibre():
    """手动刷新 Calibre 检测（清除缓存）"""
    global _calibre_cache
    _calibre_cache = {'installed': None, 'check_time': 0}
    calibre_installed = check_calibre(use_cache=False)
    return jsonify({
        'status': 'ok',
        'calibre_installed': calibre_installed,
        'message': 'Calibre 检测已刷新'
    })


if __name__ == '__main__':
    # 检查 Calibre 是否安装
    if not check_calibre():
        print('⚠️  警告: 未检测到 Calibre')
        print('请先安装 Calibre:')
        print('  macOS: brew install calibre')
        print('  或访问: https://calibre-ebook.com/download')
        print('\n服务器仍会启动，但转换功能将无法使用。\n')
    
    # 启动 Flask 开发服务器
    print('🚀 服务器启动中...')
    print('📖 访问 http://localhost:8080 使用转换工具')
    print('按 Ctrl+C 停止服务器\n')
    
    app.run(debug=False, host='0.0.0.0', port=8080, threaded=True)

