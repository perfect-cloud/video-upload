# 视频上传项目

这是一个使用Vue.js和Flask开发的视频上传项目。

## 项目结构

```
video-upload-1/
├── frontend/          # Vue.js前端项目
├── backend/           # Flask后端项目
└── README.md         # 项目说明文档
```

## 功能特点

- 支持视频文件上传
- 实时上传进度显示
- 文件大小限制
- 支持常见视频格式

## 技术栈

### 前端
- Vue.js 3
- Axios
- Element Plus

### 后端
- Flask
- Flask-CORS
- Werkzeug

## 安装和运行

### 前端
```bash
cd frontend
npm install
npm run serve
```

### 后端
```bash
cd backend
pip install -r requirements.txt
python app.py
```

## 使用说明

1. 启动后端服务器
2. 启动前端开发服务器
3. 访问 http://localhost:8080 使用视频上传功能