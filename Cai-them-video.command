#!/bin/bash
# Cài thư viện cho video (giọng đọc AI + ffmpeg) rồi khởi động lại bot.
cd "$(dirname "$0")"
.venv/bin/pip install --only-binary=:all: "edge-tts>=6.1.0" "imageio-ffmpeg>=0.5.1" || .venv/bin/pip install "edge-tts>=6.1.0" "imageio-ffmpeg>=0.5.1"
.venv/bin/python -c "import edge_tts, imageio_ffmpeg; print('OK edge-tts', imageio_ffmpeg.get_ffmpeg_exe())" > data/cai_video.txt 2>&1
cat data/cai_video.txt
launchctl unload ~/Library/LaunchAgents/com.agentarmy.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.agentarmy.plist
echo "Xong. Bot đã khởi động lại."
sleep 3
exit 0
