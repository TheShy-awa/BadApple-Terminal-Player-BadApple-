import subprocess
import sys
import os
import time
import msvcrt
import threading
import signal
import json

CONFIG_FILE_PATH = "config.json"
DEFAULT_CONFIG = {
    "play_start_offset": 0.4,
    "pipe_ready_sleep": 0.05,
    "status_refresh_interval": 0.5,
    "min_display_width": 20,
    "min_display_height": 10
}

if sys.platform == 'win32':
    SIGNALS_TO_CATCH = (signal.SIGBREAK, signal.SIGINT)
else:
    SIGNALS_TO_CATCH = (signal.SIGINT,)

g_stop_event = None
g_video_proc = None
g_audio_proc = None


def load_config():
    config = DEFAULT_CONFIG.copy()
    if not os.path.exists(CONFIG_FILE_PATH):
        print(f"提示：未找到配置文件 {CONFIG_FILE_PATH}，使用默认配置")
        return config
    
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
        
        for key in config.keys():
            if key in user_config:
                if isinstance(user_config[key], (int, float)):
                    if key == "play_start_offset":
                        config[key] = max(0.0, min(2.0, user_config[key]))
                    else:
                        config[key] = user_config[key]
                else:
                    print(f"警告：配置项 {key} 类型错误（需为数字），使用默认值 {config[key]}")
        
        print(f"成功加载配置文件 {CONFIG_FILE_PATH}，当前核心偏移量：{config['play_start_offset']}s")
        return config
    
    except json.JSONDecodeError:
        print(f"错误：配置文件 {CONFIG_FILE_PATH} 格式错误（非合法JSON），使用默认配置")
    except Exception as e:
        print(f"错误：读取配置文件失败 - {e}，使用默认配置")
    
    return config


def check_ffmpeg():
    try:
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            startupinfo=startupinfo,  
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return True
    except FileNotFoundError:
        return False


def play_audio_direct(video_path, stop_event, start_offset=0.0):
    global g_audio_proc
    try:
        if start_offset > 0.001:
            time.sleep(start_offset)
        
        cmd = [
            'ffplay',
            '-nodisp',
            '-autoexit',
            '-loglevel', 'quiet',
            '-i', video_path
        ]
        
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        g_audio_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        while g_audio_proc.poll() is None and not stop_event.is_set():
            time.sleep(0.05)
            
        if g_audio_proc.poll() is None:
            g_audio_proc.terminate()
            g_audio_proc.wait(timeout=0.5)
        return True
        
    except Exception as e:
        print(f"音频播放错误: {e}")
        return False
    finally:
        g_audio_proc = None


def get_video_info(video_path):
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate,width,height',
            '-of', 'csv=p=0',
            video_path
        ]
        
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        if result.returncode == 0:
            data = result.stdout.strip().split(',')
            if len(data) >= 3:
                fps_str = data[0]
                width = int(data[1])
                height = int(data[2])
                
                if '/' in fps_str:
                    num, den = map(float, fps_str.split('/'))
                    fps = num / den
                else:
                    fps = float(fps_str)
                return width, height, round(fps, 2)
    except Exception as e:
        print(f"获取视频信息失败: {e}")
    return 640, 480, 30.0


def handle_terminate_signal(signum, frame):
    global g_stop_event, g_video_proc, g_audio_proc
    print("\n\033[K检测到控制台关闭，正在清理进程...\033[K")
    
    if g_stop_event is not None and not g_stop_event.is_set():
        g_stop_event.set()
    
    if g_video_proc is not None and g_video_proc.poll() is None:
        try:
            g_video_proc.terminate()
            g_video_proc.wait(timeout=0.5)
        except:
            pass
        g_video_proc = None
    
    if g_audio_proc is not None and g_audio_proc.poll() is None:
        try:
            g_audio_proc.terminate()
            g_audio_proc.wait(timeout=0.5)
        except:
            pass
        g_audio_proc = None
    
    sys.exit(0)


def play_video_with_audio(video_path, display_width=70, display_height=35, config=None):
    global g_stop_event, g_video_proc
    PLAY_START_OFFSET = config["play_start_offset"]
    PIPE_READY_SLEEP = config["pipe_ready_sleep"]
    STATUS_REFRESH_INTERVAL = config["status_refresh_interval"]
    MIN_WIDTH = config["min_display_width"]
    MIN_HEIGHT = config["min_display_height"]

    display_width = max(MIN_WIDTH, display_width)
    display_height = max(MIN_HEIGHT, display_height)

    if not check_ffmpeg():
        print("错误: 未找到ffmpeg/ffplay，请将其加入系统环境变量！")
        print("提示：需下载ffmpeg并将bin目录添加到系统PATH中")
        return
    if not os.path.exists(video_path):
        print(f"错误: 文件 {video_path} 不存在")
        return

    orig_width, orig_height, fps = get_video_info(video_path)
    print(f"原始视频: {orig_width}x{orig_height}, {fps:.2f} FPS")
    print(f"显示尺寸: {display_width}x{display_height}（最小限制：{MIN_WIDTH}x{MIN_HEIGHT}）")
    
    chars = "@%#*+=-:. "[::-1]
    lut = [chars[(i * len(chars)) // 256] for i in range(256)]
    g_stop_event = threading.Event()
    for sig in SIGNALS_TO_CATCH:
        signal.signal(sig, handle_terminate_signal)

    print("\n按任意键开始播放，按 Ctrl+C/关闭窗口 停止...")
    msvcrt.getch()

    print("正在启动音视频...")
    # 启动音频线程
    audio_thread = threading.Thread(
        target=play_audio_direct,
        args=(video_path, g_stop_event, PLAY_START_OFFSET),
        daemon=True
    )
    audio_thread.start()

    video_cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f'fps={fps:.2f},scale={display_width}:{display_height},format=gray',
        '-f', 'rawvideo',
        '-pix_fmt', 'gray',
        '-loglevel', 'quiet',
        'pipe:1'
    ]
    frame_size = display_width * display_height
    os.system('cls')
    
    try:
        print("正在初始化视频解码...")
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        g_video_proc = subprocess.Popen(
            video_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**7,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        time.sleep(PIPE_READY_SLEEP)
        
        main_start_time = time.time()
        actual_play_start = main_start_time + PLAY_START_OFFSET
        frame_count = 0
        last_status_time = main_start_time
        
        print(f"开始播放 (配置偏移量: {PLAY_START_OFFSET}s)...\033[K")
        
        # 主循环
        while not g_stop_event.is_set():
            frame_data = g_video_proc.stdout.read(frame_size)
            if not frame_data or len(frame_data) < frame_size:
                break
            
            frame_count += 1
            current_time = time.time()
            

            lines = []
            for y in range(display_height):
                row_start = y * display_width
                row = frame_data[row_start:row_start + display_width]
                lines.append(''.join(lut[pixel] for pixel in row))
            

            sys.stdout.write(f'\033[H' + '\n'.join(lines))

            if current_time - last_status_time >= STATUS_REFRESH_INTERVAL:
                elapsed = current_time - actual_play_start if current_time > actual_play_start else 0.0
                current_fps = frame_count / elapsed if elapsed > 0 else 0.0
                status = f"帧: {frame_count:4d} | 实际FPS: {current_fps:.1f} | 目标FPS: {fps:.1f} | 偏移: {PLAY_START_OFFSET}s"
                sys.stdout.write(f'\033[{display_height+1}B\033[K{status}\033[{display_height+1}A')
                last_status_time = current_time
            
            sys.stdout.flush()
            

            target_time = frame_count / fps
            actual_time = current_time - actual_play_start
            sleep_time = target_time - actual_time
            if sleep_time > 0.001:
                time.sleep(sleep_time)
            

            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b'\x03', b'\x1b'):
                    print("\n\033[K用户中断播放\033[K")
                    break
                
    except KeyboardInterrupt:
        print("\n\033[K播放被中断\033[K")
    except Exception as e:
        print(f"\n\033[K播放错误: {e}\033[K")
    finally:
        # 清理逻辑
        if g_stop_event is not None and not g_stop_event.is_set():
            g_stop_event.set()
        if g_video_proc is not None and g_video_proc.poll() is None:
            try:
                g_video_proc.terminate()
                g_video_proc.wait(timeout=1)
            except:
                pass
        g_video_proc = None
        global g_audio_proc
        if g_audio_proc is not None and g_audio_proc.poll() is None:
            try:
                g_audio_proc.terminate()
                g_audio_proc.wait(timeout=1)
            except:
                pass
        g_audio_proc = None
        if audio_thread.is_alive():
            audio_thread.join(timeout=2)

        total_play_time = max(0.0, time.time() - actual_play_start)
        print(f"\n\033[K播放结束 | 总播放时间: {total_play_time:.1f}秒 | 总帧数: {frame_count}\033[K")

        for sig in SIGNALS_TO_CATCH:
            signal.signal(sig, signal.SIG_DFL)


def main():
    print("Bad Apple 终端播放器)")
    print("=" * 70)
    

    config = load_config()
    

    if len(sys.argv) < 2:
        video_path = "BadApple.mp4"      
        print(f"未指定视频路径，使用默认: {video_path}")
    else:
        video_path = sys.argv[1]
    

    if not os.path.exists(video_path):
         print(f"错误：视频文件 {video_path} 不存在！")
         print("用法: python ba_run_audio_fix2.py <视频文件路径> [显示宽度] [显示高度]")
         print(f"配置文件：同目录 {CONFIG_FILE_PATH}（可配置音画偏移量等参数）")
         sys.exit(1)
    

    display_width, display_height = 70, 35
    MIN_WIDTH = config["min_display_width"]
    MIN_HEIGHT = config["min_display_height"]
    
    if len(sys.argv) >= 3:
        try:
            display_width = int(sys.argv[2])
        except:
            print(f"警告：显示宽度参数无效，使用默认70（最小{MIN_WIDTH}）")
    if len(sys.argv) >= 4:
        try:
            display_height = int(sys.argv[3])
        except:
            print(f"警告：显示高度参数无效，使用默认35（最小{MIN_HEIGHT}）")
    

    play_video_with_audio(video_path, display_width, display_height, config)

# 程序入口
if __name__ == "__main__":

    if sys.platform != 'win32':
        print("警告：该程序主要适配Windows系统，其他系统可能存在兼容性问题")
    main()