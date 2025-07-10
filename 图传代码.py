import sensor, time, network, usocket

# 设置需要连接的WiFi信息
SSID ='123'  # WiFi名称
KEY  ='123456789'  # WiFi密码

# 服务器设置
HOST =''  # 使用第一个可用的网络接口
PORT = 8080  # 随机选择一个非特权端口

# 初始化并配置图像传感器
sensor.reset()
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.RGB565)

# 初始化无线网络模块并尝试连接到网络
print("正在尝试连接WiFi（可能需要一些时间）...")
wlan = network.WINC()
wlan.connect(SSID, key=KEY, security=wlan.WPA_PSK)

# 输出当前无线网络的相关信息
wlan_inf = wlan.ifconfig()
print('本机IP：', wlan_inf[0])
print('子网掩码：', wlan_inf[1])
print('网关IP：', wlan_inf[3])
print('在浏览器中输入以下地址查看视频流：', wlan_inf[0] + ':8080')

# 创建TCP服务器套接字
s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)

# 绑定地址和端口，并开始监听
s.bind((HOST, PORT))
s.listen(5)

# 设置服务器套接字为阻塞模式
s.setblocking(True)

# 定义开始视频流的函数
def start_streaming(s):
    print ('等待客户端连接...')
    client, addr = s.accept()  # 接受客户端连接
    client.settimeout(2.0)  # 设置客户端超时时间为2秒
    print ('成功连接到：', addr[0] + ':' + str(addr[1]))

    # 读取客户端发送的请求（这里没有进一步处理）
    data = client.recv(1024)

    # 发送HTTP响应头，准备发送多部分数据
    client.send("HTTP/1.1 200 OK\r\n" \
                "Server: OpenMV\r\n" \
                "Content-Type: multipart/x-mixed-replace;boundary=openmv\r\n" \
                "Cache-Control: no-cache\r\n" \
                "Pragma: no-cache\r\n\r\n")

    # 初始化FPS计时器
    clock = time.clock()

    # 主循环：获取并发送图像
    fps = 0  # 初始化FPS值
    while True:
        clock.tick()  # 更新计时器
        frame = sensor.snapshot()  # 拍摄一帧图像

        # 在图像上显示当前FPS
        frame.draw_string(10, 10, 'FPS:' + str(round(fps)), scale=2, color=(255, 0, 0))

        # 压缩图像并准备发送
        cframe = frame.compressed(quality=50)  # 图像压缩
        header = "\r\n--openmv\r\n" \
                 "Content-Type: image/jpeg\r\n" \
                 "Content-Length:" + str(cframe.size()) + "\r\n\r\n"
        client.send(header)  # 发送HTTP分隔符和头信息
        client.send(cframe)  # 发送压缩后的图像

        fps = clock.fps()  # 计算FPS
        print(fps)  # 在终端输出当前FPS

# 持续运行，等待客户端连接
while True:
    try:
        start_streaming(s)
    except OSError as e:  # 捕捉并输出异常
        print("发生套接字错误：", e)
