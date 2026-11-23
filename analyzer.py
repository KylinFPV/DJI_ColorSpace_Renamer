# -*- coding: utf-8 -*-
"""画面饱和度参考分析（可选能力，默认不启用）。

把 画面参考.py 的核心逻辑抽成 ASCII 文件名的模块，供 app.py 的 /api/analyze
按需加载，也供 画面参考.py 的 CLI 复用，避免 import 中文模块名。

约束：
  - pillow / imageio-ffmpeg 只在真正分析时才导入，/api/scan 阶段绝不加载；
  - ffmpeg 抽帧走内存管道，全程只读素材，不写文件、不改元数据/时间戳；
  - 结论只是「参考值」，中间地带不给确定性结论。
"""
import io
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

VIDEO_EXTS = {'.mp4', '.mov', '.osv'}

# ffmpeg 兜底路径不写死用户名、盘符或 exe 版本名，运行时按当前用户 / 项目目录推导。
# 显式指定：环境变量 DJI_FFMPEG（单个路径）或 DJI_FFMPEG_EXTRA（os.pathsep 分隔）。
def _scan_ffmpeg_dir(folder):
    """返回目录下所有 ffmpeg*.exe（按名称排序），目录不存在时返回空列表。"""
    if not os.path.isdir(folder):
        return []
    try:
        return [os.path.join(folder, n) for n in sorted(os.listdir(folder))
                if n.lower().startswith('ffmpeg') and n.lower().endswith('.exe')]
    except OSError:
        return []


def _fallback_ffmpeg_paths():
    """跨机通用的兜底候选，避免在模块级绑定某台机器的绝对路径。"""
    here = os.path.dirname(os.path.abspath(__file__))
    out = _scan_ffmpeg_dir(os.path.join(here, 'bin'))
    # 绿色版依赖目录：把 ffmpeg.exe 放到解压目录 depend/ 或 depend/bin/ 即可
    out.extend(_scan_ffmpeg_dir(os.path.join(here, 'depend')))
    out.extend(_scan_ffmpeg_dir(os.path.join(here, 'depend', 'bin')))
    # WorkBuddy 默认 venv 自带的 ffmpeg，按当前用户主目录推导（跨机通用）
    out.extend(_scan_ffmpeg_dir(os.path.join(
        os.path.expanduser('~'), '.workbuddy', 'binaries', 'python', 'envs',
        'default', 'Lib', 'site-packages', 'imageio_ffmpeg', 'binaries')))
    extra = os.environ.get('DJI_FFMPEG_EXTRA')
    if extra:
        out.extend(p for p in extra.split(os.pathsep) if p)
    return out

# 标定阈值（见 画面参考.py）：D-Log M 14~48，Normal 62~63，无重叠。
SAT_LOW = 32.0
SAT_HIGH = 48.0


class AnalyzerUnavailable(Exception):
    """分析能力不可用（缺 pillow / ffmpeg）时抛出。"""


def find_ffmpeg():
    """查找顺序：DJI_FFMPEG → PATH → imageio_ffmpeg → 项目 bin/ → 当前用户 WorkBuddy venv。"""
    env = os.environ.get('DJI_FFMPEG')
    if env and os.path.isfile(env):
        return env
    p = shutil.which('ffmpeg')
    if p:
        return p
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    for p in _fallback_ffmpeg_paths():
        if os.path.isfile(p):
            return p
    return None


def ensure_available():
    """确认分析能力可用并返回 ffmpeg 路径；缺失时抛 AnalyzerUnavailable。"""
    try:
        from PIL import Image, ImageStat  # noqa: F401
    except ImportError as e:
        raise AnalyzerUnavailable(
            '缺少 Pillow，画面分析不可用。请用 启动start.bat 启动（它会选用带依赖的 '
            'Python），或在当前 Python 执行：pip install pillow') from e
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise AnalyzerUnavailable(
            '未找到 ffmpeg，画面分析不可用。请用 启动start.bat 启动，或执行：'
            'pip install imageio-ffmpeg（也可把 ffmpeg 加入 PATH）')
    return ffmpeg


def frame_stats(ffmpeg, path, sec, timeout=600, hwaccel=False):
    """抽一帧，返回 (HSV 的 S 均值, 灰度 stddev, 是否硬件解码成功)。

    hwaccel=True 时先尝试 ffmpeg -hwaccel auto；若当前机器/驱动/编码器不支持，
    自动退回纯 CPU 解码再抽一次。全程只把 PNG 写入内存管道，不写素材文件。
    """
    def decode(use_hw):
        cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error']
        if use_hw:
            cmd.extend(['-hwaccel', 'auto'])
        cmd.extend(['-ss', str(sec), '-i', str(path),
                    '-frames:v', '1', '-vf', 'scale=480:-1',
                    '-f', 'image2pipe', '-vcodec', 'png', '-'])
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except Exception:
            return None
        if not r.stdout:
            return None
        try:
            from PIL import Image, ImageStat
            img = Image.open(io.BytesIO(r.stdout)).convert('RGB')
            gray = img.convert('L')
            return (ImageStat.Stat(img.convert('HSV').split()[1]).mean[0],
                    ImageStat.Stat(gray).stddev[0])
        except Exception:
            return None

    if hwaccel:
        st = decode(True)
        if st is not None:
            return st[0], st[1], True
    st = decode(False)
    if st is None:
        return None, None, False
    return st[0], st[1], False


def hint(sat):
    """饱和度 -> 参考提示（保留原 CLI 文案，UI 与 CLI 展示一致）。"""
    if sat < SAT_LOW:
        return '偏低 → 较可能是 D-Log M'
    if sat > SAT_HIGH:
        return '偏高 → 较可能是普通 Rec.709'
    return '中间地带，需肉眼确认'


def suggest_code(sat):
    """饱和度 -> 建议标记代码；中间地带返回 None（不强行给结论）。"""
    if sat < SAT_LOW:
        return 'DM'
    if sat > SAT_HIGH:
        return 'DN'
    return None


def analyze_file(path, frames=2, ffmpeg=None, timeout=600, hwaccel=False):
    """分析单个视频，返回 {abs, path, sat, contrast, hint, suggestCode, frames,
    hwaccel, hardwareFrames, decoder, error}。

    ffmpeg 为 None 时自动查找；抽帧时间点与原 CLI 一致（2s 起、每帧间隔 3s），
    多帧取均值；hint/suggestCode 用未取整的均值计算，避免边界值取整后跨档。
    hwaccel=True 仅影响解码方式，不改变只读约束和判定阈值。
    """
    hwaccel = bool(hwaccel)
    if ffmpeg is None:
        ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return {'abs': str(path), 'path': str(path), 'sat': None, 'contrast': None,
                'hint': '未找到 ffmpeg', 'suggestCode': None, 'frames': 0,
                'hwaccel': hwaccel, 'hardwareFrames': 0, 'decoder': None,
                'error': '未找到 ffmpeg'}
    n = max(1, min(8, int(frames)))
    sats, cons = [], []
    hardware_frames = 0
    for i in range(n):
        st = frame_stats(ffmpeg, path, 2.0 + i * 3.0, timeout=timeout,
                         hwaccel=hwaccel)
        if st and st[0] is not None:
            sats.append(st[0])
            cons.append(st[1])
            hardware_frames += 1 if st[2] else 0
    if not sats:
        return {'abs': str(path), 'path': str(path), 'sat': None, 'contrast': None,
                'hint': '抽帧失败（文件可能损坏或非视频）',
                'suggestCode': None, 'frames': 0,
                'hwaccel': hwaccel, 'hardwareFrames': 0, 'decoder': None,
                'error': '抽帧失败'}
    if not hwaccel:
        decoder = 'CPU'
    elif hardware_frames == len(sats):
        decoder = 'GPU'
    elif hardware_frames:
        decoder = 'GPU+CPU（部分回退）'
    else:
        decoder = 'CPU（硬解失败已回退）'
    sat = sum(sats) / len(sats)
    con = sum(cons) / len(cons)
    return {'abs': str(path), 'path': str(path),
            'sat': round(sat, 1), 'contrast': round(con, 1),
            'hint': hint(sat), 'suggestCode': suggest_code(sat),
            'frames': len(sats), 'hwaccel': hwaccel,
            'hardwareFrames': hardware_frames, 'decoder': decoder,
            'error': None}


def analyze_many(paths, workers=3, frames=2, timeout=120, hwaccel=False):
    """批量分析：线程池限并发，返回与 paths 顺序一致的结果列表。

    缺 pillow / ffmpeg 时抛 AnalyzerUnavailable，由调用方转成友好 JSON 错误。
    hwaccel=True 时逐文件尝试硬件解码，失败自动回退 CPU。
    """
    ffmpeg = ensure_available()
    items = list(paths)
    n = max(1, min(8, int(workers)))
    results = [None] * len(items)

    def one(i_p):
        i, p = i_p
        try:
            return i, analyze_file(p, frames=frames, ffmpeg=ffmpeg, timeout=timeout,
                                   hwaccel=hwaccel)
        except Exception as e:
            return i, {'abs': str(p), 'path': str(p), 'sat': None, 'contrast': None,
                       'hint': '分析失败', 'suggestCode': None, 'frames': 0,
                       'hwaccel': bool(hwaccel), 'hardwareFrames': 0,
                       'decoder': None, 'error': str(e)}

    with ThreadPoolExecutor(max_workers=n) as ex:
        for i, r in ex.map(one, enumerate(items)):
            results[i] = r
    return results
