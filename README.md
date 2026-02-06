# Bad Apple 终端ASCII播放器 README.md

# Bad Apple 终端 ASCII 播放器

一个在终端里播放 Bad Apple 的 ASCII 动画播放器，自定义分辨率、配置文件微调

## 📦 环境要求

- Python 3.8+（兼容3.8-3.13，推荐3.10+）

- FFmpeg / FFplay（必须添加到系统环境变量PATH）

- 操作系统：Windows（优先适配），Linux/macOS可运行（终端显示未完全优化）

## 🚀 快速开始

### 1. 克隆/下载项目

```bash
git clone https://github.com/ThwShy-awa/bad-apple-terminal.git
cd BadApple-Terminal-player
```

### 2. 依赖说明

本项目无任何第三方Python依赖，无需pip install，直接运行主脚本即可。

### 3. 验证FFmpeg环境

打开终端，输入以下命令，能正常输出版本信息即说明环境配置成功：

```bash
ffmpeg -version
ffplay -version
```

### 4. 准备视频文件

- 将 `BadApple.mp4` 视频文件放入项目根目录（与 `ba_run.py` 同目录）；

- 若视频文件名/路径不同，可通过命令行指定（见下文）。

### 5. 运行播放器

根据需求选择运行命令，直接在终端执行：

#### 默认运行（推荐）

使用默认视频（BadApple.mp4）、默认分辨率（70x35）、默认配置：

```bash
python ba_run.py
```

#### 指定视频路径

播放自定义视频文件（需输入完整/相对路径）：

```bash
python ba_run.py <你的视频路径.mp4>
```

#### 指定视频+自定义分辨率

自定义终端显示宽高（例如宽100、高40，根据终端大小调整）：

```bash
python ba_run_audio.py <你的视频路径.mp4> 100 40
```

## ⚙️ 配置文件详解（config.json）

所有核心参数均通过 `config.json` 配置，无需修改Python代码，调试更便捷。若配置文件不存在，程序会自动使用默认配置并提示。

### 配置文件示例

```json
{
  "play_start_offset": 0.4,
  "pipe_ready_sleep": 0.05,
  "status_refresh_interval": 0.5,
  "min_display_width": 20,
  "min_display_height": 10
}
```

### 各配置项说明

|配置项|类型|默认值|说明|
|---|---|---|---|
|play_start_offset|float|0.4|音画同步核心偏移量（秒）；音频快→增大，画面快→减小；推荐范围0.2~0.6|
|pipe_ready_sleep|float|0.05|视频管道就绪短延时，保证解码稳定，一般无需修改|
|status_refresh_interval|float|0.5|终端底部状态行刷新间隔（秒），0.5秒兼顾流畅与性能|
|min_display_width|int|20|最小显示宽度，避免输入过小分辨率导致终端错乱|
|min_display_height|int|10|最小显示高度，同上|
## 🎮 使用说明

- 程序启动后，按 **任意键** 开始播放；

- 播放过程中，按 **Ctrl+C** 或直接 **关闭控制台窗口**，均可安全退出；

- 退出时程序会自动清理所有子进程（ffmpeg/ffplay），无音频残留；

- 终端底部状态行实时显示：帧数、实际FPS、目标FPS、当前偏移量，便于调试音画同步。

## 📁 项目结构

```bash
BadApple-terminal-player/          # 项目根目录
├── ba_run.py                # 主程序（核心播放逻辑）
├── config.json              # 配置文件（音画偏移、分辨率等）
├── BadApple.mp4             # 视频文件（可替换）
└── README.md                # 项目说明文档（本文档）
```
