# -*- coding: utf-8 -*-
"""smoke: 画面分析硬解开关（默认 CPU、auto 硬解、失败回退）。"""
import os
import subprocess
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import analyzer  # noqa: E402


class _FakeImage:
    def convert(self, mode):
        return self

    def split(self):
        return [self, self, self]


class _FakeStat:
    def __init__(self, img):
        pass

    @property
    def mean(self):
        return [12.5]

    @property
    def stddev(self):
        return [30.0]


def _install_fake_pil():
    keys = ('PIL', 'PIL.Image', 'PIL.ImageStat')
    saved = {k: sys.modules.get(k) for k in keys}
    pil = types.ModuleType('PIL')
    image = types.ModuleType('PIL.Image')
    image.open = lambda data: _FakeImage()
    stat = types.ModuleType('PIL.ImageStat')
    stat.Stat = _FakeStat
    pil.Image = image
    pil.ImageStat = stat
    sys.modules['PIL'] = pil
    sys.modules['PIL.Image'] = image
    sys.modules['PIL.ImageStat'] = stat
    return saved


def _restore_modules(saved):
    for name, mod in saved.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


def _fake_run(calls, outputs):
    def run(cmd, **kwargs):
        calls.append(list(cmd))
        out = outputs.pop(0) if outputs else b'png'
        return subprocess.CompletedProcess(cmd, 0, out, b'')
    return run


def _flag(cmd, name):
    return cmd[cmd.index(name) + 1] if name in cmd else None


class HwaccelSmoke(unittest.TestCase):
    def setUp(self):
        self.saved = _install_fake_pil()
        self.original_run = analyzer.subprocess.run

    def tearDown(self):
        analyzer.subprocess.run = self.original_run
        _restore_modules(self.saved)

    def test_default_is_cpu(self):
        calls = []
        analyzer.subprocess.run = _fake_run(calls, [b'png'])
        result = analyzer.frame_stats('ffmpeg', 'a.mp4', 2)
        self.assertIsNotNone(result[0])
        self.assertFalse(result[2])
        self.assertNotIn('-hwaccel', calls[0])

    def test_hwaccel_uses_auto_before_input(self):
        calls = []
        analyzer.subprocess.run = _fake_run(calls, [b'png'])
        result = analyzer.frame_stats('ffmpeg', 'a.mp4', 2, hwaccel=True)
        self.assertEqual(result, (12.5, 30.0, True))
        self.assertEqual(_flag(calls[0], '-hwaccel'), 'auto')
        self.assertLess(calls[0].index('-hwaccel'), calls[0].index('-i'))

    def test_hwaccel_falls_back_to_cpu(self):
        calls = []
        analyzer.subprocess.run = _fake_run(calls, [b'', b'png'])
        result = analyzer.frame_stats('ffmpeg', 'a.mp4', 2, hwaccel=True)
        self.assertIsNotNone(result[0])
        self.assertFalse(result[2])
        self.assertEqual(len(calls), 2)
        self.assertIn('-hwaccel', calls[0])
        self.assertNotIn('-hwaccel', calls[1])

    def test_analyze_file_reports_decoder(self):
        calls = []
        analyzer.subprocess.run = _fake_run(calls, [b'png'])
        result = analyzer.analyze_file('a.mp4', frames=1, ffmpeg='ffmpeg',
                                       hwaccel=True)
        self.assertEqual(result['decoder'], 'GPU')
        self.assertEqual(result['hardwareFrames'], 1)
        self.assertTrue(result['hwaccel'])

    def test_analyze_file_reports_fallback(self):
        calls = []
        analyzer.subprocess.run = _fake_run(calls, [b'', b'png'])
        result = analyzer.analyze_file('a.mp4', frames=1, ffmpeg='ffmpeg',
                                       hwaccel=True)
        self.assertEqual(result['decoder'], 'CPU（硬解失败已回退）')
        self.assertEqual(result['hardwareFrames'], 0)


if __name__ == '__main__':
    unittest.main()
