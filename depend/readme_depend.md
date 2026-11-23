# depend 文件夹放什么

这个文件夹是给“绿色版/免安装”用法准备的。把依赖放进来后，整个软件目录可以拷到任何电脑，双击 `启动start.bat` 就能用，不需要改系统环境变量。

## 一、目录结构

```text
DJI_Color_Space\
├─ 启动start.bat
├─ app.py
├─ web\
└─ depend\
   ├─ readme_depend.md        ← 本文件
   ├─ python\
   │  └─ python.exe           ← Python 放这里
   └─ ffmpeg.exe              ← ffmpeg 放这里（或放 depend\bin\ffmpeg.exe）
```

## 二、Python 放哪里

### 1. 必需性

- 只做**扫描、识别、改名**：只需要 Python 3，不需要 ffmpeg、不需要 Pillow。
- 要用**画面饱和度/对比度分析**：还需要 Pillow 和 ffmpeg。

### 2. 推荐放法

把 Python 3.12 或更高版本安装到任意位置，然后把安装目录复制到：

```text
depend\python\
```

确保这个文件存在：

```text
depend\python\python.exe
```

`启动start.bat` 会优先查找它。

### 3. 官方下载

Python 官网：<https://www.python.org/downloads/windows/>

下载 **Windows installer (64-bit)**。安装时建议勾选 **Add Python to PATH**；即使不勾选，只要按上面放进 `depend\python\`，启动脚本也能找到。

## 三、Pillow 放哪里（仅画面分析需要）

Pillow 是 Python 库，不是 exe。安装到 `depend\python\` 这份 Python 里：

```bat
depend\python\python.exe -m pip install pillow
```

验证：

```bat
depend\python\python.exe -c "import PIL; print('Pillow OK')"
```

看到 `Pillow OK` 即可。

## 四、ffmpeg 放哪里（仅画面分析需要）

### 1. 官方下载

- 推荐：<https://www.gyan.dev/ffmpeg/builds/>，下载 `ffmpeg-release-essentials.zip`
- 备用：<https://ffmpeg.org/download.html>

### 2. 放置方法

解压下载包，找到里面的 `bin\ffmpeg.exe`，复制到下面任一位置：

```text
depend\ffmpeg.exe
depend\bin\ffmpeg.exe
```

程序会按这个顺序找：`DJI_FFMPEG` 环境变量 → PATH → imageio-ffmpeg → `bin/` → `depend/` → `depend/bin/` → WorkBuddy venv。

验证：

```bat
depend\ffmpeg.exe -version
```

能打印版本号即可。

## 五、启动与检查

双击 `启动start.bat`。控制台第一行会显示实际使用的 Python 路径，例如：

```text
正在使用 Python 解释器：G:\...\DJI_Color_Space\depend\python\python.exe
Python interpreter: G:\...\DJI_Color_Space\depend\python\python.exe
```

如果 Pillow 或 ffmpeg 没装好，会出现提示；此时扫描和改名仍然可用，只是画面分析不可用。

## 六、常见问题

| 问题 | 处理 |
|---|---|
| 双击后闪退 | 用映射盘符打开，例如 `W:\...\启动start.bat`，不要用 UNC 路径 |
| 提示没有 Python | 确认 `depend\python\python.exe` 存在，或安装 Python 3.12+ 并勾选 Add Python to PATH |
| 提示缺 ffmpeg | 把 `ffmpeg.exe` 放到 `depend\` 或 `depend\bin\` |
| 提示缺 Pillow | 执行 `depend\python\python.exe -m pip install pillow` |
| 换电脑 | 整个软件目录连 `depend\` 一起拷过去即可 |
