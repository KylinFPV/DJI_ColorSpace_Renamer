# -*- coding: utf-8 -*-
r"""
画面参考值（辅助判断色彩模式，非确定性判定）
------------------------------------------------
用途：Osmo Nano / Avata 2 / O4 Pro 等机型的文件里没有记录色彩模式，
      可用画面的"饱和度"作为参考来人工判断是否为 D-Log M。

原理：D-Log M 是 flat 曲线，会明显压低饱和度。本脚本抽若干帧算均值。

标定（用 Avata 360 的 SRT 已知标签实测，同一台机器）：
      D-Log M (dlog_m) ：饱和度 14 ~ 48
      Normal  (default)：饱和度 62 ~ 63
  实测 17 个文件：2 个 Normal 全部正确判为"普通"；
  15 个 D-Log M 中 11 个明确命中、4 个落在"中间地带"。
  → 饱和度偏低时判定可信（未出现把 Normal 误判成 D-Log M 的情况）；
    中间地带必须肉眼确认。饱和度受场景影响大（拍蓝天绿叶自然偏高）。

用法：
    python 画面参考.py "<素材文件夹>"
    python 画面参考.py "<素材文件夹>" --frames 5    # 每文件抽 5 帧（更准但更慢）

需要：ffmpeg（自动查找，或 pip install imageio-ffmpeg）+ pillow

核心逻辑已抽到 analyzer.py（ASCII 模块名），供 Web 端 /api/analyze 复用；
本文件保留原有命令行参数、输出格式与错误提示，CLI 行为不变。
"""
import sys
from pathlib import Path

from analyzer import VIDEO_EXTS, analyze_file, find_ffmpeg


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    nframes = 2
    if '--frames' in sys.argv:
        try:
            nframes = int(sys.argv[sys.argv.index('--frames') + 1])
        except Exception:
            pass
    if not args:
        print(__doc__)
        return 1
    folder = Path(args[0])
    if not folder.is_dir():
        print('文件夹不存在：%s' % folder)
        return 1

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print('未找到 ffmpeg。请先安装：pip install imageio-ffmpeg')
        return 1
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print('缺少 Pillow。请安装：pip install pillow')
        return 1

    files = sorted(f for f in folder.iterdir()
                   if f.is_file() and f.suffix.lower() in VIDEO_EXTS)
    if not files:
        print('文件夹里没有视频文件')
        return 1
    print('ffmpeg: %s' % ffmpeg)
    print('共 %d 个视频，每个抽 %d 帧（大文件较慢，请耐心）\n' % (len(files), nframes))
    print('%-44s %10s %10s   %s' % ('文件', '饱和度', '对比度', '参考'))
    print('-' * 94)
    for f in files:
        r = analyze_file(f, frames=nframes, ffmpeg=ffmpeg)
        if r['sat'] is None:
            print('%-44s %10s %10s   %s' % (f.name[:42], '-', '-', '抽帧失败'))
            continue
        print('%-44s %10.1f %10.1f   %s' %
              (f.name[:42], r['sat'], r['contrast'], r['hint']))
    print('\n提示：数值仅供参考，最终以肉眼为准——D-Log M 画面明显发灰、平淡。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
