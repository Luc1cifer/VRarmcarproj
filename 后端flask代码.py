from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'users.db'
VIDEO_FOLDER = 'videos'
DEMO_IMAGE = 'demo_image.png'
DEMO_VIDEO = 'demo_video.mp4'

os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            location TEXT DEFAULT '',
            save_type TEXT DEFAULT 'cloud',
            username TEXT DEFAULT 'guest'
        )
    ''')
    conn.commit()
    conn.close()
    print('✅数据库初始化完成')

init_db()

# 注册接口
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({'success': False,'message': '用户名和密码不能为空'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False,'message': '用户名已存在'}), 400

    conn.close()
    return jsonify({'success': True,'message': '注册成功'})

# 登录接口
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({'success': True,'message': '登录成功'})
    else:
        return jsonify({'success': False,'message': '用户名或密码错误'}), 401

# 上传视频（支持 guest）
@app.route('/upload_video', methods=['POST'])
def upload_video():
    username = request.form.get('username', 'guest')
    file = request.files.get('file')
    location = request.form.get('location', '未知')
    save_type = request.form.get('save_type', 'cloud')

    if not file:
        return jsonify({'success': False,'message': '缺少文件'}), 400

    filename = f"{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    save_path = os.path.join(VIDEO_FOLDER, filename)
    file.save(save_path)

    if save_type == 'cloud':
        cloud_path = os.path.join(VIDEO_FOLDER, f"cloud_{filename}")
        os.system(f'cp "{save_path}" "{cloud_path}"')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO videos (filename, location, save_type, username) VALUES (?,?,?,?)",
              (filename, location, save_type, username))
    conn.commit()
    conn.close()

    return jsonify({'success': True,'message': '上传成功', 'filename': filename})

# 列出视频（支持 guest）
@app.route('/list_videos', methods=['GET'])
def list_videos():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT filename, timestamp, location, save_type, username FROM videos")
    videos = [
        {
            'filename': row[0],
            'timestamp': row[1],
            'location': row[2],
           'save_type': row[3],
            'username': row[4]
        } for row in c.fetchall()
    ]
    conn.close()
    return jsonify({'success': True, 'videos': videos})

# 访问视频
@app.route('/video/<filename>', methods=['GET'])
def get_video(filename):
    return send_from_directory(VIDEO_FOLDER, filename)

# 演示页面
@app.route('/demo', methods=['GET'])
def demo():
    demo_html = f"""
    <h2>📹演示页面（跳过登录）</h2>
    <p><b>示例录像文件：</b> {DEMO_VIDEO}</p>
    <p><b>时间戳：</b> 2025-07-10 12:00:00</p>
    <p><b>位置信息：</b> 深圳市南山区</p>
    <p><b>保存方式：</b> 云端</p>
    <p>下面是示例截图（供演示）</p>
    <img src="/static/{DEMO_IMAGE}" alt="演示图片" width="600">
    <p><a href="/frontend">⤴️返回演示登录页面</a></p>
    """
    return render_template_string(demo_html)

# 演示前端页面
@app.route('/frontend', methods=['GET'])
def frontend():
    html_content = """
    <h2>📄登录页面（演示）</h2>
    <form action="/login" method="post">
        <label>用户名:</label><br>
        <input type="text" name="username"><br>
        <label>密码:</label><br>
        <input type="password" name="password"><br><br>
        <input type="submit" value="登录">
    </form>
    <p>或</p>
    <form action="/demo" method="get">
        <button type="submit">✈️跳过登录，进入演示</button>
    </form>
    <p>没有账号？注册接口使用 /register</p>
    """
    return render_template_string(html_content)

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        ssl_context=('/root/certs/fullchain.pem', '/root/certs/vramcar.cloud.key')
    )