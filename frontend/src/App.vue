<template>
  <div class="app">
    <el-container>
      <el-main>
        <el-upload
          class="upload-demo"
          drag
          :http-request="handleUpload"
          :on-preview="handlePreview"
          :before-upload="beforeUpload"
          accept=".mp4,.avi,.mov,.wmv"
          name="video"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 mp4/avi/mov/wmv 格式视频，且不超过 500MB
            </div>
          </template>
        </el-upload>

        <!-- 视频列表 -->
        <div class="video-list">
          <h2>已上传视频</h2>
          <el-table :data="videoList" style="width: 100%">
            <el-table-column label="预览" width="180">
              <template #default="scope">
                <div class="video-thumbnail" @click="previewVideo(scope.row)">
                  <video
                    :src="`/uploads/${scope.row.filename}`"
                    class="thumbnail-video"
                    preload="metadata"
                    @loadeddata="handleThumbnailLoaded($event, scope.row)"
                  ></video>
                  <div class="play-icon">
                    <el-icon><video-play /></el-icon>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="filename" label="文件名" />
            <el-table-column prop="uploadTime" label="上传时间" />
            <el-table-column label="操作" width="200">
              <template #default="scope">
                <el-button size="small" @click="previewVideo(scope.row)">预览</el-button>
                <el-button size="small" type="danger" @click="deleteVideo(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 视频预览对话框 -->
        <el-dialog 
          v-model="previewDialogVisible" 
          title="视频预览" 
          width="70%"
          @close="handleDialogClose"
        >
          <video
            v-if="currentVideo"
            ref="videoPlayer"
            :src="`/uploads/${currentVideo.filename}`"
            controls
            style="width: 100%"
          ></video>
        </el-dialog>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { UploadFilled, VideoPlay } from '@element-plus/icons-vue'

// 根据环境设置 API 基础 URL
const API_BASE_URL = process.env.NODE_ENV === 'production' ? 'http://43.156.12.152:5000/api' : '/api'

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL
})

const videoList = ref([])
const previewDialogVisible = ref(false)
const currentVideo = ref(null)
const videoPlayer = ref(null)

// 获取视频列表
const fetchVideoList = async () => {
  try {
    const response = await api.get('/videos')
    videoList.value = response.data
  } catch (error) {
    ElMessage.error('获取视频列表失败：' + error.message)
  }
}

// 处理文件上传
const handleUpload = async (options) => {
  try {
    const formData = new FormData()
    formData.append('video', options.file)
    
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        options.onProgress({ percent: percentCompleted })
      }
    })
    
    options.onSuccess(response.data)
    ElMessage.success(`上传成功！文件名：${response.data.filename}`)
    fetchVideoList() // 刷新视频列表
  } catch (error) {
    options.onError(error)
    ElMessage.error('上传失败：' + (error.message || '未知错误'))
  }
}

// 上传前处理
const handlePreview = (file) => {
  console.log(file)
}

// 上传前验证
const beforeUpload = (file) => {
  const isLt500M = file.size / 1024 / 1024 < 500
  if (!isLt500M) {
    ElMessage.error('文件大小不能超过 500MB!')
    return false
  }
  return true
}

// 预览视频
const previewVideo = (video) => {
  currentVideo.value = video
  previewDialogVisible.value = true
}

// 关闭对话框
const handleDialogClose = () => {
  // 暂停视频播放
  if (videoPlayer.value) {
    videoPlayer.value.pause()
  }
  currentVideo.value = null
}

// 缩略图加载完成
const handleThumbnailLoaded = (event, video) => {
  // 设置视频缩略图的时间点（比如第一帧）
  const videoElement = event.target
  videoElement.currentTime = 0.1
}

// 删除视频
const deleteVideo = async (video) => {
  try {
    await api.delete(`/videos/${video.filename}`)
    ElMessage.success('删除成功')
    fetchVideoList() // 刷新视频列表
  } catch (error) {
    ElMessage.error('删除失败：' + error.message)
  }
}

// 组件挂载时获取视频列表
onMounted(() => {
  fetchVideoList()
})
</script>

<style>
.app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

.el-header {
  background-color: #409EFF;
  color: white;
  line-height: 60px;
}

.el-main {
  padding: 20px;
}

.upload-demo {
  width: 500px;
  margin: 0 auto;
}

.video-list {
  margin-top: 40px;
  width: 80%;
  margin-left: auto;
  margin-right: auto;
}

.video-list h2 {
  text-align: left;
  margin-bottom: 20px;
}

.video-thumbnail {
  position: relative;
  width: 160px;
  height: 90px;
  cursor: pointer;
  overflow: hidden;
  border-radius: 4px;
  background-color: #000;
}

.thumbnail-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.play-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 24px;
  opacity: 0.8;
  transition: opacity 0.3s;
}

.video-thumbnail:hover .play-icon {
  opacity: 1;
}
</style> 