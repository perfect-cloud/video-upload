from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 限制文件大小为500MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    logger.debug('开始处理文件上传请求...')
    logger.debug(f'请求文件: {request.files}')
    logger.debug(f'请求表单: {request.form}')
    
    if 'video' not in request.files:
        logger.error('没有找到video字段')
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['video']
    logger.debug(f'上传的文件名: {file.filename}')
    
    if file.filename == '':
        logger.error('文件名为空')
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.debug(f'保存文件到: {file_path}')
        try:
            file.save(file_path)
            logger.info(f'文件 {filename} 上传成功')
            return jsonify({
                'message': '文件上传成功',
                'filename': filename,
                'uploadTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 200
        except Exception as e:
            logger.error(f'保存文件时出错: {str(e)}')
            return jsonify({'error': f'保存文件时出错: {str(e)}'}), 500
    
    logger.error(f'不支持的文件类型: {file.filename}')
    return jsonify({'error': '不支持的文件类型'}), 400

@app.route('/api/videos', methods=['GET'])
def get_videos():
    try:
        videos = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if allowed_file(filename):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file_stat = os.stat(file_path)
                videos.append({
                    'filename': filename,
                    'uploadTime': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': file_stat.st_size
                })
        return jsonify(videos)
    except Exception as e:
        logger.error(f'获取视频列表时出错: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos/<filename>', methods=['DELETE'])
def delete_video(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'message': '文件删除成功'})
        return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        logger.error(f'删除文件时出错: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def serve_video(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 