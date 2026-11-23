# DJI 素材色彩空间标记工具

给 DJI 视频文件名末尾加上色彩标记（`_D1` / `_D2` / `_DH` / `_DN` / `_DM` / `_DC` / `_DU`），后期调色时一眼就能看出是哪一种色彩模式。

当前版本 **v3.04.03**　·　永久免费开源　·　GitHub：<https://github.com/KylinFPV/DJI_ColorSpace_Renamer>  
B站 / 抖音 / 小红书 / YouTube：[KylinFPV](https://space.bilibili.com/36780014)

目前可识别设备：<span style="color:#0f766e"><b>Osmo Pocket 4P</b></span>（机身元数据）；<span style="color:#1f6feb"><b>Avata 360 / Avata 2 / O4 Air Unit Pro / O3 天空端</b></span>（SRT 字幕）；<span style="color:#b45309"><b>Osmo Pocket 3 / Action 2 / Osmo Nano / Osmo 360 II</b></span>（无色彩元数据，需手动指定或画面参考）。

**使用顺序（流程图）：**

```text
① 选择分析范围  →  ② 分析  →  ③ 标记  →  ④ 选择改名范围  →  ⑤ 按标记改名
```

---

## 一、这本工具会做什么，不会做什么

请先看这四条，最重要的信息都在这里：

1. **只会修改文件名，不影响辨认度。**  
   只在文件名末尾加或改色彩标记，例如 `DJI_0151.MP4` → `DJI_0151_DM.MP4`；原主名保持不变，也不会出现 `_D11` 这种重复标记。

2. **不上网。**  
   软件只在你的电脑本机运行，不上传文件、不联网请求、不偷偷上报。界面上的 GitHub 链接只有你自己点击时才会打开浏览器访问外部网站。

3. **不会改动素材内容。**  
   不修改视频画面、不修改元数据、不修改文件修改时间。扫描和识别只是“读文件”，改名只是“改文件名”。

4. **调用 ffmpeg 只用于画面分析。**  
   只有你主动点「分析选中画面」时，才会用本机 ffmpeg 抽几帧出来计算饱和度/对比度；不会转码、不裁剪、不合并、不导出视频。抽帧结果只在内存里算完就丢，不生成中间文件，也不写回素材。

> **还不放心？** 可以把整个解压包交给你的 AI，让它读源码后回答：  
> “这个工具是否真的不上网？是否不改源文件内容？是否只修改文件名？ffmpeg 是否只用于画面分析？”

---

## 二、需要什么软件，放在哪里

### 1. 基本要求

| 用途 | 需要什么 | 是否必须 |
|---|---|---|
| 扫描、识别、改名 | **Python 3** | 必须 |
| 画面分析（可选） | **Pillow** + **ffmpeg** | 只在用画面分析时需要 |

也就是说：**只改名不需要 ffmpeg；要用画面分析才需要 Pillow 和 ffmpeg。**

### 2. 推荐的绿色版放法

更简单的一个做法：解压到你喜欢的地方后，让 AI **读 README.md，确认源码符合那四条重要信息，并把该做的都做完**，然后你只要双击 `启动start.bat` 就能使用。

软件已经默认带一个 `depend` 文件夹，里面放了 `readme_depend.md`，详细说明每个文件该放在哪里、怎么验证。把软件解压后，按下面结构放置：

```text
DJI_Color_Space\
├─ 启动start.bat
├─ app.py
├─ web\
└─ depend\
   ├─ readme_depend.md       ← 依赖放置详细说明
   ├─ python\
   │  └─ python.exe          ← Python 放这里
   └─ ffmpeg.exe             ← ffmpeg 放这里（也可放 depend\bin\）
```

`启动start.bat` 会优先找 `depend\python\python.exe`；`画面分析` 会优先找 `depend\ffmpeg.exe` 或 `depend\bin\ffmpeg.exe`。

### 3. 官方下载方式

| 软件 | 下载地址 | 怎么放 |
|---|---|---|
| Python | <https://www.python.org/downloads/windows/> | 下载 Windows 64-bit installer。安装时勾选 **Add Python to PATH**；或把安装好的 Python 目录复制到 `depend\python\`。 |
| Pillow | 安装好 Python 后执行：`python -m pip install pillow` | 如果 Python 放在 `depend\python\`，执行：`depend\python\python.exe -m pip install pillow` |
| ffmpeg | <https://www.gyan.dev/ffmpeg/builds/> 下载 `ffmpeg-release-essentials.zip`；或 <https://ffmpeg.org/download.html> | 解压后把 `bin\ffmpeg.exe` 复制到 `depend\ffmpeg.exe` 或 `depend\bin\ffmpeg.exe`。 |

没有画面分析需求时，可以完全不装 Pillow 和 ffmpeg，扫描/改名照常可用。

### 4. 启动

双击 `启动start.bat`。如果双击后闪退或找不到文件，请确认是用**映射盘符**打开（例如 `W:\...\启动start.bat`），不要直接用 `\\服务器\共享\...` 这种 UNC 路径。

服务只监听 `127.0.0.1`，只有你这台电脑能访问。

---

## 三、按顺序使用

推荐顺序：**选择分析范围 → 分析 → 标记 → 选择改名范围 → 按标记改名**。

1. **选择分析范围**：在结果表勾选「分析」列，或用「全选未识别」「选未改名+未识别前100」等按钮快速勾选。
2. **分析**：点「分析选中画面」。需要先扫描；画面分析需要 FFmpeg，结果只作建议，不会自动改名。
3. **标记**：在「已勾选分析文件标记为」选好代码，点「确认标记」；也可以直接改每行「标记为」下拉。标记只更新预览。
4. **选择改名范围**：用表头「改名」全选，或「所有已改名 / 未改名 / 未识别 / 已自定义」按钮。
5. **按标记改名**：点「执行重命名」。改错了可以用「撤销重命名」按勾选范围撤回最近一次改名。

选目录与扫描：在路径框粘贴素材文件夹，或点「浏览文件夹…」。第一次打开会显示盘符根目录；之后会自动记住上次位置。扫描选项：是否带上同名配套文件、是否包含子文件夹、是否跳过已标记文件。

---

## 四、文件名标记对照

| 色彩模式 | 后缀 | 色彩模式 | 后缀 |
|---|---|---|---|
| D-Log | `_D1` | D-Log M | `_DM` |
| D-Log 2 | `_D2` | D-Cinelike | `_DC` |
| HLG | `_DH` | 未知 | `_DU` |
| 普通 Rec.709 / Normal | `_DN` | | |

识别来源主要有三类：机身元数据、同名 `.SRT` 字幕里的色彩信息、已有文件名标记。都没有时会标 `_DU`（未知），可以手动指定，或用画面分析作参考。

O3 天空端 / Action 2 的 `DJI_xxxx.MP4` 没有 `_D` 标记时，会**追加**后缀，例如 `DJI_0006.MP4` → `DJI_0006_DN.MP4`，同名配套文件同步改名。

---

## 五、画面饱和度 / 对比度分析（参考值，按需抽帧，需要有 FFmpeg）

- 需要主动勾选「分析」列并点「分析选中画面」才会抽帧，结果只作建议，不会自动改名。
- 饱和度 `<32` 较可能是 D-Log M；`>48` 较可能是普通 Rec.709；`32~48` 需要肉眼确认。
- 单次最多分析 **100 个**文件；可用「选未改名+未识别前100」快速批量勾选。
- 硬解默认开启：优先用显卡加速抽帧，显卡/驱动不支持时自动回退 CPU；只影响速度，不改变判定结果。
- 重要限制：判据只对 D-Log M / Normal 做过标定。实测 O3 的 D-Cinelike 会被误判成 D-Log M，请以 SRT 里的 `color_md : d_cinelike` 或人工指定为准。

---

## 六、常见问题

| 问题 | 处理 |
|---|---|
| 识别结果是“未知” | 有些机型不写色彩信息；录制前需在 DJI Fly / 飞行眼镜开启「视频字幕」，事后补不了。已有素材可手动指定或按画面分析参考。 |
| 浏览文件夹第一次是空白 | 现在第一次打开会列出盘符；之后自动进入上次使用过的目录。 |
| 画面分析提示缺 ffmpeg / Pillow | 按第二章把 `ffmpeg.exe` 放进 `depend\`，并用 `depend\python\python.exe -m pip install pillow` 安装 Pillow。 |
| 系统对话框卡住 | 点「取消系统对话框」，或改用「浏览文件夹…」内置浏览器。 |
| 改错了怎么办 | 用「撤销重命名」，按当前勾选范围撤回最近一次改名。 |
| 换电脑怎么用 | 整个目录拷过去即可；依赖也可一起放在 `depend\`。 |

---

## 七、给开发者

- 版本记录见 `CHANGELOG.md`。
- 冒烟测试：`python -m unittest discover -s tests -q`（JS 语法检查可设置 `NODE_BIN` 指向 `node.exe`）。
- 版本规则：末位为小更新；中间两位为明显功能差异，升级前先确认；首位为主版本。

---

## 附录：开源信息

本项目永久免费开源。源码地址：<https://github.com/KylinFPV/DJI_ColorSpace_Renamer>  
作者：KylinFPV（B站 / 抖音 / 小红书 / YouTube）。

**许可证**：本项目采用 [MIT License（MIT 许可证）](LICENSE)。允许自由使用、复制、修改、合并、发布、分发及再许可，再分发时须保留版权声明与许可声明；软件按「原样」提供，不提供任何担保。
