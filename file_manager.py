"""
文件管理模块
处理拖拽文件的保存和分类
"""

import os
import shutil
from datetime import date
import database

SAVED_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_files")

# 文件类型分类映射
FILE_TYPE_MAP = {
    # 图片
    '.jpg': '图片', '.jpeg': '图片', '.png': '图片', '.gif': '图片',
    '.bmp': '图片', '.webp': '图片', '.svg': '图片', '.ico': '图片',
    '.tiff': '图片', '.tif': '图片', '.heic': '图片', '.raw': '图片',
    # 文档
    '.pdf': '文档', '.doc': '文档', '.docx': '文档', '.txt': '文档',
    '.xls': '文档', '.xlsx': '文档', '.ppt': '文档', '.pptx': '文档',
    '.csv': '文档', '.md': '文档', '.rtf': '文档', '.odt': '文档',
    '.ods': '文档', '.odp': '文档',
    # 音频
    '.mp3': '音频', '.wav': '音频', '.flac': '音频', '.aac': '音频',
    '.ogg': '音频', '.wma': '音频', '.m4a': '音频',
    # 视频
    '.mp4': '视频', '.avi': '视频', '.mkv': '视频', '.mov': '视频',
    '.wmv': '视频', '.flv': '视频', '.webm': '视频', '.m4v': '视频',
    # 压缩包
    '.zip': '压缩包', '.rar': '压缩包', '.7z': '压缩包', '.tar': '压缩包',
    '.gz': '压缩包', '.bz2': '压缩包', '.xz': '压缩包',
    # 代码
    '.py': '代码', '.js': '代码', '.ts': '代码', '.html': '代码',
    '.css': '代码', '.java': '代码', '.c': '代码', '.cpp': '代码',
    '.h': '代码', '.go': '代码', '.rs': '代码', '.rb': '代码',
    '.php': '代码', '.swift': '代码', '.kt': '代码', '.json': '代码',
    '.xml': '代码', '.yaml': '代码', '.yml': '代码', '.sql': '代码',
}


def get_file_type(filename):
    """根据扩展名获取文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    return FILE_TYPE_MAP.get(ext, '其他')


def save_dropped_files(file_paths):
    """
    保存拖拽的文件
    按日期和文件类型分目录保存
    返回保存结果列表
    """
    today_str = date.today().isoformat()
    results = []

    for file_path in file_paths:
        file_path = file_path.strip().strip('{}')  # tkinterdnd2 可能会加花括号
        if not os.path.exists(file_path):
            results.append({'success': False, 'file': file_path, 'error': '文件不存在'})
            continue

        filename = os.path.basename(file_path)
        file_type = get_file_type(filename)

        # 创建目标目录: saved_files/YYYY-MM-DD/类型/
        target_dir = os.path.join(SAVED_FILES_DIR, today_str, file_type)
        os.makedirs(target_dir, exist_ok=True)

        # 处理同名文件
        target_path = os.path.join(target_dir, filename)
        if os.path.exists(target_path):
            name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(target_path):
                target_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                counter += 1

        try:
            shutil.copy2(file_path, target_path)
            # 记录到数据库
            database.add_file_record(filename, target_path, file_type, today_str)
            results.append({
                'success': True,
                'file': filename,
                'type': file_type,
                'saved_to': target_path
            })
        except Exception as e:
            results.append({'success': False, 'file': filename, 'error': str(e)})

    return results


def get_saved_files_tree():
    """
    获取所有保存文件的树形结构
    返回: { 'YYYY-MM-DD': { '类型': [file_records] } }
    """
    from collections import defaultdict
    files = database.get_all_files()
    tree = defaultdict(lambda: defaultdict(list))
    for f in files:
        tree[f['date']][f['file_type']].append(f)
    return dict(tree)
