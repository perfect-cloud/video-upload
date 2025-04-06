import os
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging
import subprocess
import json
import shutil

app = Flask(__name__)
# 配置CORS，允许所有来源和请求方法
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

# FFmpeg 路径配置
FFMPEG_PATH = r"D:\ffmpeg-2025-03-27-git-114fccc4a5-essentials_build\bin\ffmpeg.exe"  # 请根据实际安装路径修改
FFPROBE_PATH = r"D:\ffmpeg-2025-03-27-git-114fccc4a5-essentials_build\bin\ffprobe.exe"  # 请根据实际安装路径修改

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"上传文件夹路径: {UPLOAD_FOLDER}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_info(file_path):
    try:
        cmd = [FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
        return {
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'duration': float(data['format']['duration'])
        }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def transcode_video(input_path, output_path, quality):
    try:
        # 根据质量设置转码参数
        if quality == 'high':
            scale = '1920:1080'
            bitrate = '5000k'
        elif quality == 'medium':
            scale = '1280:720'
            bitrate = '2500k'
        else:  # low
            scale = '854:480'
            bitrate = '1000k'

        cmd = [
            FFMPEG_PATH, '-i', input_path,
            '-vf', f'scale={scale}',
            '-b:v', bitrate,
            '-b:a', '128k',
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"Error transcoding video: {e}")
        return False

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        base_name = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1]
        
        # 创建唯一的文件夹名
        timestamp = int(time.time())
        folder_name = f"{base_name}_{timestamp}"
        video_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        os.makedirs(video_folder, exist_ok=True)
        
        # 保存原始文件
        original_path = os.path.join(video_folder, f'original{ext}')  # 保持原始扩展名格式
        file.save(original_path)
        
        # 获取视频信息
        video_info = get_video_info(original_path)
        if not video_info:
            return jsonify({'error': '无法获取视频信息'}), 500
        
        # 转码不同质量的视频
        try:
            # 高清版本 (1080p)
            high_path = os.path.join(video_folder, f'high{ext}')  # 保持原始扩展名格式
            subprocess.run([
                FFMPEG_PATH, '-i', original_path,
                '-c:v', 'libx264', '-crf', '23',
                '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k',
                '-vf', 'scale=1920:1080',
                high_path
            ], check=True)
            
            # 标清版本 (720p)
            medium_path = os.path.join(video_folder, f'medium{ext}')  # 保持原始扩展名格式
            subprocess.run([
                FFMPEG_PATH, '-i', original_path,
                '-c:v', 'libx264', '-crf', '23',
                '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k',
                '-vf', 'scale=1280:720',
                medium_path
            ], check=True)
            
            # 流畅版本 (480p)
            low_path = os.path.join(video_folder, f'low{ext}')  # 保持原始扩展名格式
            subprocess.run([
                FFMPEG_PATH, '-i', original_path,
                '-c:v', 'libx264', '-crf', '23',
                '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k',
                '-vf', 'scale=854:480',
                low_path
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"转码错误: {str(e)}")
            # 如果转码失败，至少保留原始文件
            pass
        
        return jsonify({
            'message': '文件上传成功',
            'filename': folder_name,
            'info': video_info
        })
    
    return jsonify({'error': '不支持的文件类型'}), 400

@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos = []
    print("开始获取视频列表...")
    # 遍历上传文件夹中的所有文件夹
    for folder_name in os.listdir(app.config['UPLOAD_FOLDER']):
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        print(f"检查文件夹: {folder_path}")
        if os.path.isdir(folder_path):
            # 直接检查文件夹中的文件
            for file_name in os.listdir(folder_path):
                if file_name.startswith('original'):
                    original_path = os.path.join(folder_path, file_name)
                    print(f"找到原始视频文件: {original_path}")
                    video_info = get_video_info(original_path)
                    if video_info:
                        print(f"获取到视频信息: {video_info}")
                        videos.append({
                            'filename': folder_name,
                            'uploadTime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getctime(original_path)))
                        })
                    break  # 找到原始文件后就跳出循环
    print(f"找到 {len(videos)} 个视频")
    return jsonify(videos)

@app.route('/api/videos/<filename>', methods=['DELETE'])
def delete_video(filename):
    try:
        # 获取视频文件夹路径
        base_name = os.path.splitext(filename)[0]
        video_folder = os.path.join(app.config['UPLOAD_FOLDER'], base_name)
        
        # 删除整个视频文件夹
        if os.path.exists(video_folder):
            shutil.rmtree(video_folder)
            return jsonify({'message': '视频删除成功'})
        else:
            return jsonify({'error': '视频不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<path:filename>')
def serve_video(filename):
    # 从路径中提取文件夹名和文件名
    parts = filename.split('/')
    if len(parts) == 2:
        folder_name, file_name = parts
        return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder_name), file_name)
    return jsonify({'error': '无效的文件路径'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 