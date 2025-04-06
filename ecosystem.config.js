module.exports = {
  apps: [{
    name: "video-upload-backend",
    script: "backend/app.py",
    interpreter: "python3",
    autorestart: true,
    watch: false,
    max_memory_restart: "1G",
    env: {
      NODE_ENV: "production",
      PYTHONUNBUFFERED: "1"
    },
    error_file: "logs/err.log",
    out_file: "logs/out.log",
    log_file: "logs/combined.log",
    time: true,
    max_restarts: 10,
    restart_delay: 4000
  }]
}; 