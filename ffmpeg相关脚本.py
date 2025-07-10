import cv2
import subprocess
import requests
import time
from datetime import datetime
import os

# ⚡ 配置
mjpeg_url = "http://192.168.66.153:8080"
rtmp_url = "rtmp://你的服务器IP/live/stream"
status_url = "http://你的服务器IP:5000/record_status"
upload_url = "http://你的服务器IP:5000/upload_video"
username = "test_user"  # 改成你的用户名

save_folder = "local_recordings"
os.makedirs(save_folder, exist_ok=True)

# ============= 初始化 ==============
cap = cv2.VideoCapture(mjpeg_url)
if not cap.isOpened():
    print("❌ 无法连接 MJPEG 流")
    exit()

ret, frame = cap.read()
if not ret:
    print("❌ 无法读取帧")
    cap.release()
    exit()

height, width, _ = frame.shape
print(f"✅ 成功连接，分辨率: {width}x{height}")

# 配置 RTMP ffmpeg
ffmpeg_cmd = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f"{width}x{height}",
    '-r', '20',
    '-i', '-',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-preset', 'ultrafast',
    '-f', 'flv',
    rtmp_url
]

rtmp_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
print("🚀 正在推送 RTMP...")

local_process = None
is_recording = False
current_filename = None

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ 丢失帧，跳过...")
            continue

        # 推送到 RTMP
        rtmp_process.stdin.write(frame.tobytes())

        # 查询后端录制状态（每秒一次）
        if int(time.time()) % 1 == 0:
            try:
                res = requests.get(status_url, params={"username": username}, timeout=1)
                status = res.json()["status"]["is_recording"]
            except Exception as e:
                print(f"❗ 后端状态请求失败: {e}")
                status = False

            if status and not is_recording:
                # 开始本地录制
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                current_filename = f"record_{username}_{timestamp}.mp4"
                save_path = os.path.join(save_folder, current_filename)

                local_cmd = [
                    'ffmpeg',
                    '-y',
                    '-f', 'rawvideo',
                    '-vcodec', 'rawvideo',
                    '-pix_fmt', 'bgr24',
                    '-s', f"{width}x{height}",
                    '-r', '20',
                    '-i', '-',
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-preset', 'ultrafast',
                    save_path
                ]

                local_process = subprocess.Popen(local_cmd, stdin=subprocess.PIPE)
                is_recording = True
                print(f"💾 本地开始录制: {save_path}")

            elif not status and is_recording:
                # 停止本地录制
                local_process.stdin.close()
                local_process.wait()
                is_recording = False
                print(f"✅ 本地录制停止: {current_filename}")

                # 自动上传
                try:
                    upload_path = os.path.join(save_folder, current_filename)
                    files = {'file': open(upload_path, 'rb')}
                    data = {
                        'username': username,
                        'location': '未知',  # 可选，或可从 GPS 写入
                        'save_type': 'cloud'
                    }
                    response = requests.post(upload_url, files=files, data=data, timeout=60)
                    if response.ok:
                        print(f"📤 上传成功: {current_filename}")
                        # 上传成功后可选择删除本地文件
                        # os.remove(upload_path)
                    else:
                        print(f"❌ 上传失败: {response.text}")

                except Exception as e:
                    print(f"❗ 上传出错: {e}")

        # 若在本地录制，也写到本地
        if is_recording and local_process is not None:
            local_process.stdin.write(frame.tobytes())

except KeyboardInterrupt:
    print("\n🛑 用户中断")

finally:
    cap.release()
    rtmp_process.stdin.close()
    rtmp_process.wait()
    if is_recording and local_process is not None:
        local_process.stdin.close()
        local_process.wait()
    print("🚪 推流结束，程序退出")
