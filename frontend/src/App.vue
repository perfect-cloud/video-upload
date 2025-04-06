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
          <el-table 
            :data="videoList" 
            style="width: 100%"
            :max-height="tableHeight"
            class="video-table"
          >
            <el-table-column label="预览" width="180" class-name="preview-column">
              <template #default="scope">
                <div class="video-thumbnail" @click="previewVideo(scope.row)">
                  <video
                    :src="getVideoUrl(scope.row.filename)"
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
            <el-table-column prop="filename" label="文件名" class-name="filename-column" />
            <el-table-column prop="uploadTime" label="上传时间" class-name="time-column" />
            <el-table-column label="操作" width="200" class-name="action-column">
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
          width="90%"
          :fullscreen="isMobile"
          @close="handleDialogClose"
          destroy-on-close
        >
          <div class="video-player-container">
            <div class="video-controls">
              <el-select v-model="currentQuality" placeholder="选择清晰度" size="small">
                <el-option
                  v-for="quality in videoQualities"
                  :key="quality.value"
                  :label="quality.label"
                  :value="quality.value"
                />
              </el-select>
              <el-button 
                type="primary" 
                size="small" 
                @click="toggleAutoQuality"
                :class="{ 'is-active': autoQuality }"
              >
                {{ autoQuality ? '自动' : '手动' }}
              </el-button>
            </div>
            <video
              v-if="currentVideo"
              ref="videoPlayer"
              controls
              preload="auto"
              style="width: 100%"
              @loadedmetadata="handleVideoLoaded"
            ></video>
          </div>
        </el-dialog>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
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
const isMobile = ref(false)
const tableHeight = ref('auto')

// 视频质量相关
const currentQuality = ref('auto')
const autoQuality = ref(true)
const videoQualities = ref([
  { label: '自动', value: 'auto' },
  { label: '原始', value: 'original' },
  { label: '高清', value: 'high' },
  { label: '标清', value: 'medium' },
  { label: '流畅', value: 'low' }
])

// 检查是否为移动设备
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
  tableHeight.value = isMobile.value ? '400px' : 'auto'
}

// 监听窗口大小变化
const handleResize = () => {
  checkMobile()
}

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
  // 等待 DOM 更新后再设置视频源
  nextTick(() => {
    if (videoPlayer.value) {
      // 直接设置初始质量，不触发自动切换
      currentQuality.value = 'original'
      const url = getVideoUrl(video.filename, 'original')
      videoPlayer.value.src = url
      videoPlayer.value.load()
    }
  })
}

// 关闭预览对话框
const handleDialogClose = () => {
  if (videoPlayer.value) {
    videoPlayer.value.pause()
    videoPlayer.value.removeAttribute('src')
    videoPlayer.value.load()
    // 清除质量设置标记
    delete videoPlayer.value.dataset.qualitySet
  }
  currentVideo.value = null
  currentQuality.value = 'auto'
  autoQuality.value = true
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

// 获取视频URL
const getVideoUrl = (filename, quality = 'original') => {
  const baseUrl = process.env.NODE_ENV === 'production' 
    ? 'http://43.156.12.152:5000' 
    : 'http://localhost:5000'
  
  if (!filename) return ''
  
  // 从文件名中提取扩展名
  const ext = '.mp4'  // 默认使用 mp4 扩展名
  
  if (quality === 'original') {
    return `${baseUrl}/uploads/${filename}/original${ext}`
  }
  
  return `${baseUrl}/uploads/${filename}/${quality}${ext}`
}

// 视频加载完成
const handleVideoLoaded = (event) => {
  const video = event.target
  // 只在初始加载时设置自动质量，并且只在自动模式下执行
  if (autoQuality.value && !video.dataset.qualitySet) {
    video.dataset.qualitySet = 'true'
    // 延迟执行自动质量切换，避免与初始加载冲突
    setTimeout(() => {
      setOptimalQuality(video)
    }, 100)
  }
}

// 设置最佳播放质量
const setOptimalQuality = (video) => {
  if (!video || !currentVideo.value) return
  
  const networkSpeed = navigator.connection ? navigator.connection.downlink : 5 // Mbps
  
  // 根据网络速度选择合适的质量
  let newQuality = 'high'
  if (networkSpeed >= 10) {
    newQuality = 'high'
  } else if (networkSpeed >= 5) {
    newQuality = 'medium'
  } else {
    newQuality = 'low'
  }
  
  // 只有当质量发生变化时才切换
  if (currentQuality.value !== newQuality) {
    currentQuality.value = newQuality
    applyVideoQuality(video)
  }
}

// 应用视频质量设置
const applyVideoQuality = (video) => {
  if (!video || !currentVideo.value) return
  
  const quality = currentQuality.value
  if (quality === 'auto') {
    setOptimalQuality(video)
    return
  }
  
  // 保存当前播放时间和状态
  const currentTime = video.currentTime
  const wasPlaying = !video.paused
  
  // 更新视频源
  const newUrl = getVideoUrl(currentVideo.value.filename, quality)
  console.log('Switching to quality:', quality, 'URL:', newUrl)
  
  // 先暂停视频
  video.pause()
  
  // 使用 Promise 处理视频加载
  const loadVideo = () => {
    return new Promise((resolve) => {
      // 先移除旧的事件监听器
      const oldSrc = video.src
      video.src = newUrl
      video.load()
      
      const handleCanPlay = () => {
        video.removeEventListener('canplay', handleCanPlay)
        resolve()
      }
      
      video.addEventListener('canplay', handleCanPlay)
      
      // 如果加载失败，尝试恢复原始源
      const handleError = () => {
        console.error('Failed to load video with quality:', quality)
        video.removeEventListener('error', handleError)
        if (oldSrc) {
          video.src = oldSrc
          video.load()
        }
      }
      
      video.addEventListener('error', handleError)
    })
  }
  
  // 加载新视频并恢复播放状态
  loadVideo().then(() => {
    video.currentTime = currentTime
    if (wasPlaying) {
      video.play().catch(e => console.error('Error playing video:', e))
    }
  }).catch(error => {
    console.error('Error loading video:', error)
    ElMessage.error('切换视频质量失败，请重试')
  })
}

// 切换自动/手动质量
const toggleAutoQuality = () => {
  autoQuality.value = !autoQuality.value
  if (autoQuality.value) {
    setOptimalQuality(videoPlayer.value)
  } else {
    // 切换到手动模式时，使用当前选择的质量
    applyVideoQuality(videoPlayer.value)
  }
}

// 监听质量变化
watch(currentQuality, (newQuality) => {
  if (videoPlayer.value && currentVideo.value) {
    // 无论是否自动模式，都应用新的质量设置
    applyVideoQuality(videoPlayer.value)
  }
})

// 组件挂载时获取视频列表
onMounted(() => {
  fetchVideoList()
  checkMobile()
  window.addEventListener('resize', handleResize)
})

// 组件卸载时移除事件监听
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
}

.video-list {
  margin-top: 40px;
  width: 100%;
  max-width: 1200px;
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

/* 响应式样式 */
@media screen and (max-width: 768px) {
  .app {
    margin-top: 20px;
  }

  .el-main {
    padding: 10px;
  }

  .upload-demo {
    width: 100%;
  }

  .video-list {
    margin-top: 20px;
    width: 100%;
  }

  .video-thumbnail {
    width: 120px;
    height: 68px;
  }

  .el-table {
    font-size: 14px;
  }

  .el-button {
    padding: 8px 12px;
    font-size: 12px;
  }

  .el-dialog {
    margin: 0 !important;
    width: 100% !important;
  }
}

/* 表格响应式样式 */
.video-table {
  width: 100%;
}

@media screen and (max-width: 768px) {
  .preview-column {
    width: 120px !important;
  }

  .filename-column {
    min-width: 120px;
  }

  .time-column {
    min-width: 100px;
  }

  .action-column {
    width: 120px !important;
  }
}

.video-player-container {
  position: relative;
  background-color: #000;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-player-container video {
  max-height: 80vh;
  object-fit: contain;
}

.video-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1;
  display: flex;
  gap: 10px;
  background: rgba(0, 0, 0, 0.5);
  padding: 5px;
  border-radius: 4px;
}

.video-controls .el-select {
  width: 120px;
}

.video-controls .el-button.is-active {
  background-color: #409EFF;
  color: white;
}

@media screen and (max-width: 768px) {
  .video-controls {
    top: 5px;
    right: 5px;
    gap: 5px;
  }
  
  .video-controls .el-select {
    width: 100px;
  }
}
</style> 