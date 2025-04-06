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
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置上传文件夹
# 使用绝对路径，确保在任何环境下都能找到
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

# FFmpeg 路径配置
# 根据环境选择不同的路径
ffmpeg_installed = False
if os.name == 'nt':  # Windows 环境
    FFMPEG_PATH = r"D:\ffmpeg-2025-03-27-git-114fccc4a5-essentials_build\bin\ffmpeg.exe"
    FFPROBE_PATH = r"D:\ffmpeg-2025-03-27-git-114fccc4a5-essentials_build\bin\ffprobe.exe"
else:  # Linux 环境
    # 尝试多个可能的路径
    possible_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/opt/ffmpeg/bin/ffmpeg',
        'ffmpeg'  # 系统 PATH 中的 ffmpeg
    ]
    
    FFMPEG_PATH = None
    for path in possible_paths:
        try:
            logger.info(f"尝试 FFmpeg 路径: {path}")
            result = subprocess.run([path, '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                FFMPEG_PATH = path
                logger.info(f"找到可用的 FFmpeg: {path}")
                ffmpeg_installed = True
                break
            else:
                logger.warning(f"FFmpeg 路径 {path} 返回非零状态码: {result.returncode}")
        except Exception as e:
            logger.warning(f"检查 FFmpeg 路径 {path} 时出错: {str(e)}")
            continue
    
    if FFMPEG_PATH is None:
        logger.error("找不到 FFmpeg，请确保已安装 FFmpeg")
        FFMPEG_PATH = 'ffmpeg'  # 使用默认值，但会记录错误
    
    # 同样处理 FFprobe
    possible_paths = [
        '/usr/bin/ffprobe',
        '/usr/local/bin/ffprobe',
        '/opt/ffmpeg/bin/ffprobe',
        'ffprobe'  # 系统 PATH 中的 ffprobe
    ]
    
    FFPROBE_PATH = None
    for path in possible_paths:
        try:
            logger.info(f"尝试 FFprobe 路径: {path}")
            result = subprocess.run([path, '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                FFPROBE_PATH = path
                logger.info(f"找到可用的 FFprobe: {path}")
                break
            else:
                logger.warning(f"FFprobe 路径 {path} 返回非零状态码: {result.returncode}")
        except Exception as e:
            logger.warning(f"检查 FFprobe 路径 {path} 时出错: {str(e)}")
            continue
    
    if FFPROBE_PATH is None:
        logger.error("找不到 FFprobe，请确保已安装 FFmpeg")
        FFPROBE_PATH = 'ffprobe'  # 使用默认值，但会记录错误

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"当前工作目录: {os.getcwd()}")
logger.info(f"应用目录: {BASE_DIR}")
logger.info(f"上传文件夹路径: {UPLOAD_FOLDER}")
logger.info(f"FFmpeg 路径: {FFMPEG_PATH}")
logger.info(f"FFprobe 路径: {FFPROBE_PATH}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_video_info(file_path):
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        # 检查 FFprobe 是否可用
        try:
            logger.info(f"检查 FFprobe 可用性: {FFPROBE_PATH}")
            result = subprocess.run([FFPROBE_PATH, '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"FFprobe 命令返回非零状态码: {result.returncode}")
                logger.error(f"FFprobe 错误输出: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"FFprobe 不可用: {str(e)}")
            return None
            
        cmd = [FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path]
        logger.info(f"执行 FFprobe 命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFprobe 命令失败: {result.stderr}")
            return None
            
        data = json.loads(result.stdout)
        
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
        return {
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'duration': float(data['format']['duration'])
        }
    except Exception as e:
        logger.error(f"获取视频信息时出错: {str(e)}", exc_info=True)
        return None

def transcode_video(input_path, output_path, quality):
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            return False
            
        # 检查 FFmpeg 是否可用
        if not ffmpeg_installed:
            logger.error("FFmpeg 未安装，无法进行转码")
            return False
            
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

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # 检查文件权限
        try:
            # 检查输入文件权限
            if not os.access(input_path, os.R_OK):
                logger.error(f"无法读取输入文件: {input_path}")
                return False
                
            # 检查输出目录权限
            if not os.access(output_dir, os.W_OK):
                logger.error(f"无法写入输出目录: {output_dir}")
                return False
        except Exception as e:
            logger.error(f"检查文件权限时出错: {str(e)}")
            return False
        
        cmd = [
            FFMPEG_PATH, '-i', input_path,
            '-c:v', 'libx264', '-crf', '23',
            '-preset', 'medium',
            '-c:a', 'aac', '-b:a', '128k',
            '-vf', f'scale={scale}',
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        logger.info(f"开始转码视频: {input_path} -> {output_path}")
        logger.info(f"转码命令: {' '.join(cmd)}")
        
        # 执行转码命令并捕获输出
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"转码失败，返回码: {result.returncode}")
            logger.error(f"FFmpeg 错误输出: {result.stderr}")
            
            # 检查输入文件信息
            try:
                input_info = subprocess.run([FFPROBE_PATH, '-v', 'error', '-show_format', '-show_streams', input_path], 
                                         capture_output=True, text=True)
                logger.info(f"输入文件信息: {input_info.stdout}")
            except Exception as e:
                logger.error(f"获取输入文件信息失败: {str(e)}")
            
            return False
            
        logger.info(f"转码成功: {output_path}")
        return True
    except Exception as e:
        logger.error(f"转码过程中发生错误: {str(e)}", exc_info=True)
        return False

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
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
            original_path = os.path.join(video_folder, f'original{ext}')
            logger.info(f"保存原始文件: {original_path}")
            file.save(original_path)
            
            # 检查文件权限
            try:
                if not os.access(original_path, os.R_OK):
                    logger.error(f"无法读取上传的文件: {original_path}")
                    return jsonify({'error': '文件权限错误'}), 500
            except Exception as e:
                logger.error(f"检查文件权限时出错: {str(e)}")
                return jsonify({'error': '文件权限错误'}), 500
            
            # 获取视频信息
            video_info = get_video_info(original_path)
            if not video_info:
                logger.error("无法获取视频信息")
                return jsonify({'error': '无法获取视频信息'}), 500
            
            # 转码不同质量的视频
            try:
                # 高清版本 (1080p)
                high_path = os.path.join(video_folder, f'high{ext}')
                if not transcode_video(original_path, high_path, 'high'):
                    logger.error("高清版本转码失败")
                
                # 标清版本 (720p)
                medium_path = os.path.join(video_folder, f'medium{ext}')
                if not transcode_video(original_path, medium_path, 'medium'):
                    logger.error("标清版本转码失败")
                
                # 流畅版本 (480p)
                low_path = os.path.join(video_folder, f'low{ext}')
                if not transcode_video(original_path, low_path, 'low'):
                    logger.error("流畅版本转码失败")
                
            except Exception as e:
                logger.error(f"转码过程中发生错误: {str(e)}", exc_info=True)
                # 如果转码失败，至少保留原始文件
                pass
            
            return jsonify({
                'message': '文件上传成功',
                'filename': folder_name,
                'info': video_info
            })
            
        except Exception as e:
            logger.error(f"上传过程中发生错误: {str(e)}", exc_info=True)
            return jsonify({'error': f'上传失败: {str(e)}'}), 500
    
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

# 全局错误处理
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"发生错误: {str(error)}", exc_info=True)
    return jsonify({'error': '服务器内部错误'}), 500

# 定期检查服务状态的路由
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # 检查上传文件夹是否存在
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            logger.info(f"创建上传文件夹: {UPLOAD_FOLDER}")
        
        # 检查 FFmpeg 是否可用
        try:
            subprocess.run([FFMPEG_PATH, '-version'], capture_output=True, check=True)
            ffmpeg_status = "可用"
        except Exception as e:
            logger.error(f"FFmpeg 检查失败: {str(e)}")
            ffmpeg_status = "不可用"
        
        return jsonify({
            'status': 'ok',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'upload_folder': UPLOAD_FOLDER,
            'ffmpeg_status': ffmpeg_status
        })
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 