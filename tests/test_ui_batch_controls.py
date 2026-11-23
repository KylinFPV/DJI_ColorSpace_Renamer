# -*- coding: utf-8 -*-
"""smoke: 画面分析批量勾选与批量标记控件 + v3.04.03 UI/README/版本一致性。"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'web', 'index.html')
README = os.path.join(ROOT, 'README.md')


def _read_html():
    with open(HTML, encoding='utf-8') as f:
        return f.read()


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class UiBatchControlsSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = _read_html()

    def test_mit_license_in_ui_and_readme(self):
        self.assertIn('class="site-foot"', self.html)
        self.assertIn('MIT 许可证', self.html)
        self.assertIn('MIT License', self.html)
        self.assertIn('⑨ 开源许可证', self.html)
        self.assertIn('以下 9 节', self.html)
        self.assertIn('MIT License', _read('README.md'))
        self.assertIn('MIT License', _read('README-eng.md'))
        self.assertIn('[MIT License（MIT 许可证）](LICENSE)', _read('README.md'))
        self.assertIn('[MIT License](LICENSE)', _read('README-eng.md'))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, 'LICENSE')))
        self.assertIn('MIT License', _read('LICENSE'))

    def test_launcher_warning_is_accurate(self):
        bat = _read('启动start.bat')
        self.assertNotIn('画面分析不可用', bat)
        self.assertNotIn('frame analysis is disabled', bat)
        self.assertIn('已用备选 Python', bat)
        self.assertIn('using a fallback Python', bat)
        self.assertIn('Analysis still works when Pillow is present', bat)
        self.assertIn('python -m pip install imageio-ffmpeg', bat)

    def test_v30401ui_layout_and_bilingual_intro(self):
        self.assertLess(self.html.index('id="anAll"'), self.html.index('id="all"'),
                        '分析列应在改名列左侧')
        self.assertIn('class="an-col"', self.html)
        self.assertIn('class="ren-col"', self.html)
        self.assertIn('class="rename-zone"', self.html)
        self.assertIn('class="zone-divider"', self.html)
        self.assertIn('勾选的文件将会把挂的标记改入文件名中', self.html)
        self.assertIn('Checked files will have their selected tags written into the filenames', self.html)
        self.assertIn('<div class="i18n-pair">自动判定色彩空间并标记文件名。', self.html)
        self.assertIn('Automatically detects the color space and tags the filename.', self.html)
        self.assertNotIn('<div class="sub" data-en=', self.html)

    def test_batch_select_control_exists(self):
        self.assertIn('onclick="anSelectPendingUnknown()"', self.html)
        self.assertIn('选未改名+未识别前100', self.html)
        self.assertIn('const ANALYZE_MAX = 100;', self.html)
        self.assertIn('function anSelectPendingUnknown()', self.html)

    def test_batch_select_clears_then_limits(self):
        m = re.search(r'function anSelectPendingUnknown\(\)\{.*?\n\}', self.html, re.S)
        self.assertIsNotNone(m)
        body = m.group(0)
        self.assertIn('b.checked = false', body)
        self.assertIn('!hasTag(g) && isUnknown(g)', body)
        self.assertIn('slice(0, ANALYZE_MAX)', body)

    def test_mark_control_exists_and_reuses_set_code(self):
        self.assertIn('id="anMarkCode"', self.html)
        self.assertIn('onclick="anMarkSelected()"', self.html)
        m = re.search(r'function anMarkSelected\(\)\{.*?\n\}', self.html, re.S)
        self.assertIsNotNone(m)
        self.assertIn('setCode(p.i, code)', m.group(0))

    def test_mark_select_includes_du_for_reset(self):
        m = re.search(r"\(function initCodeSelects\(\)\{.*?\}\)\(\);", self.html, re.S)
        self.assertIsNotNone(m)
        self.assertIn("opts(CODES, 'DM')", m.group(0))
        self.assertNotIn('bulkCode', self.html)

    def test_console_banner_version_matches_current(self):
        changelog = _read('CHANGELOG.md')
        m = re.search(r'当前版本：\*\*v([\d.]+[A-Za-z]*)\*\*', changelog)
        self.assertIsNotNone(m)
        version = 'v' + m.group(1)
        self.assertIn("工具 %s 已启动" % version, _read('app.py'))
        self.assertIn(version, self.html)

    def test_javascript_syntax(self):
        node = os.environ.get('NODE_BIN') or shutil.which('node')
        if not node:
            self.skipTest('node not available')
        m = re.search(r'<script>(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(m)
        fd, path = tempfile.mkstemp(suffix='.js')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(m.group(1))
            r = subprocess.run([node, '--check', path], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr.strip())
        finally:
            os.unlink(path)

    # ---------- v3.04.00 新增 ----------
    def test_hw_bar_checked_and_css_derived_state(self):
        self.assertIn('<label class="hw-bar">', self.html)
        self.assertIn('<input type="checkbox" id="anHw" checked', self.html)
        self.assertIn('启用硬解（GPU 优先）', self.html)
        self.assertIn('默认开启；显卡或驱动不支持时自动回退 CPU，只影响分析速度，'
                      '不改变判定阈值与素材内容。', self.html)
        self.assertIn('已开启 · GPU 优先', self.html)
        self.assertIn('已关闭 · CPU 解码', self.html)
        self.assertIn('#anHw:checked ~ .hw-state-on', self.html)
        self.assertIn('#anHw:not(:checked) ~ .hw-state-off', self.html)
        self.assertIn("const hwaccel = !!$('anHw').checked;", self.html)
        self.assertIn('frames: 2', self.html)
        # 胶囊只显示当前状态，不再用「默认」，也不用 ::before 生成文字
        self.assertNotIn('默认开启 · 失败自动回退', self.html)
        # 状态文字来自真实 span，而不是伪元素 content（排除 justify-content 等属性）
        css = re.search(r'<style>(.*?)</style>', self.html, re.S).group(1)
        self.assertNotRegex(css, r'(?<!-)\bcontent\s*:')
        # #anHw 与 .hw-state 是同一 label 的直接子元素，input 在前且不隐藏
        bar = re.search(r'<label class="hw-bar">.*?</label>', self.html, re.S).group(0)
        self.assertEqual(bar.count('<label'), 1)
        self.assertRegex(bar, r'<label class="hw-bar">\s*<input[^>]+id="anHw"')
        self.assertRegex(bar, r'<span class="hw-state hw-state-on"[^>]*>')
        self.assertRegex(bar, r'<span class="hw-state hw-state-off"[^>]*>')
        self.assertNotIn('display:none', bar)
        # 全局焦点统一 outline，无 .hw-bar:focus-within 双环
        self.assertIn('outline:2px solid var(--accent);outline-offset:2px', self.html)
        self.assertRegex(self.html, r'#anHw:focus-visible\{outline-color:var\(--hw\);?\}')
        self.assertNotIn('.hw-bar:focus-within', self.html)
        self.assertNotIn('box-shadow:var(--focus)', self.html)
        # 可见文案不再出现历史默认值表述
        self.assertNotIn('默认关闭', self.html)
        self.assertNotIn('默认不开启', self.html)

    def test_backend_hwaccel_defaults_untouched(self):
        analyzer = _read('analyzer.py')
        app = _read('app.py')
        self.assertIn('def frame_stats(ffmpeg, path, sec, timeout=600, hwaccel=False):', analyzer)
        self.assertIn("payload.get('hwaccel', False)", app)

    def test_help_dialog_and_keyboard(self):
        for needle in ('id="helpBtn"', 'onclick="openHelp()"', 'function openHelp()',
                       'id="helpMask"', 'role="dialog"', 'aria-modal="true"',
                       'aria-labelledby="helpTitle"', 'id="helpCloseBtn"',
                       'z-index:101', '知道了', '>使用说明</span>'):
            self.assertIn(needle, self.html)
        for marker in '①②③④⑤⑥⑦⑧':
            self.assertIn(marker, self.html)
        # ESC 优先级：helpMask → verMask → pickerMask
        body = re.search(r"document\.addEventListener\('keydown', e => \{.*?\n\}\);",
                         self.html, re.S).group(0)
        self.assertLess(body.index('helpMask'), body.index('verMask'))
        self.assertLess(body.index('verMask'), body.index('pickerMask'))
        # 文件名键盘可达，保留原 onclick
        self.assertIn('class="fn" tabindex="0" role="button"', self.html)
        self.assertIn("onkeydown=\"if(event.key==='Enter'||event.key===' ')"
                      "{event.preventDefault();openFile(${i})}\"", self.html)
        self.assertIn('onclick="openFile(${i})"', self.html)

    def test_header_intro_and_single_legend(self):
        for needle in ('font-size:22px', 'font-weight:700',
                       'B站 / 抖音 / 小红书 / YouTube：',
                       'href="https://space.bilibili.com/36780014"',
                       '本软件永久免费开源',
                       'href="https://github.com/KylinFPV/DJI_ColorSpace_Renamer"',
                       'target="_blank"', 'rel="noopener noreferrer"',
                       'KylinFPV/DJI_ColorSpace_Renamer ↗'):
            self.assertIn(needle, self.html)
        self.assertEqual(self.html.count('class="legend"'), 1)
        self.assertIn('<b>D-Log M</b> → _DM', self.html)
        self.assertNotIn('!important', self.html)   # 显隐一律 JS inline style

    def test_readme_is_beginner_friendly(self):
        self.assertTrue(os.path.isfile(README))
        readme = _read('README.md')
        for title in ('## 一、这本工具会做什么，不会做什么',
                      '## 二、需要什么软件，放在哪里',
                      '## 三、按顺序使用', '## 四、文件名标记对照',
                      '## 五、画面饱和度 / 对比度分析（参考值，按需抽帧，需要有 FFmpeg）', '## 六、常见问题',
                      '## 七、给开发者', '## 附录：开源信息'):
            self.assertIn(title, readme)
        for claim in ('只会修改文件名', '不上网', '不会改动素材内容',
                      '调用 ffmpeg 只用于画面分析'):
            self.assertIn(claim, readme)
        self.assertIn('把整个解压包交给你的 AI', readme)
        self.assertIn('depend\\python\\python.exe', readme)
        self.assertIn('depend\\ffmpeg.exe', readme)
        self.assertIn('https://www.python.org/downloads/windows/', readme)
        self.assertIn('https://www.gyan.dev/ffmpeg/builds/', readme)
        self.assertNotIn('**源码依据**', readme)
        self.assertIn('v3.04.03', readme)
        self.assertIn('https://github.com/KylinFPV/DJI_ColorSpace_Renamer', readme)

    def test_picker_root_and_last_folder_memory(self):
        self.assertIn("const LAST_FOLDER_KEY = 'djiLastFolder'", self.html)
        self.assertIn("const start = $('folder').value.trim() || lastFolder();", self.html)
        self.assertIn("pkGo(start || '');", self.html)
        self.assertIn('我的电脑（请选择盘符）', self.html)
        self.assertIn('rememberFolder(p);', self.html)
        self.assertIn('rememberFolder(q.path);', self.html)
        self.assertIn('rememberFolder(folder);', self.html)

    def test_layout_removes_hint_module_and_integrates_analysis(self):
        for stale in ('id="bulkBox"', 'id="bulkCode"', 'onclick="bulkSet()"',
                      '对未识别文件应用', '请在 DJI Fly / 飞行眼镜里开启'):
            self.assertNotIn(stale, self.html)
        self.assertIn('<div class="analyze-section" id="analyzeBox"', self.html)
        self.assertIn('.analyze-section{', self.html)
        self.assertIn('.an-mark-row{', self.html)
        self.assertIn('class="row an-mark-row"', self.html)
        self.assertRegex(self.html,
                         r'<button class="primary" onclick="anMarkSelected\(\)"[^>]*>确认标记</button>')

    def test_local_depend_directories_are_supported(self):
        bat = _read('启动start.bat')
        analyzer = _read('analyzer.py')
        self.assertIn('depend\\python\\python.exe', bat)
        self.assertIn('depend\\python\\Scripts\\python.exe', bat)
        self.assertIn("os.path.join(here, 'depend')", analyzer)
        self.assertIn("os.path.join(here, 'depend', 'bin')", analyzer)

    def test_language_toggle_and_bilingual_hooks(self):
        for needle in ('id="langBtn"', 'onclick="toggleLang()"',
                       'function toggleLang()', 'function applyI18n()',
                       'body.lang-both .i18n-en', "localStorage.setItem('djiLangMode'",
                       '语言 / Language：中文'):
            self.assertIn(needle, self.html)
        self.assertGreaterEqual(self.html.count('data-en='), 20)

    def test_kylin_link_devices_flow_and_ffmpeg_title(self):
        self.assertIn('https://space.bilibili.com/36780014', self.html)
        for cls in ('dev-meta', 'dev-srt', 'dev-manual'):
            self.assertIn('class="%s"' % cls, self.html)
        self.assertIn('使用顺序：', self.html)
        self.assertIn('① 选择分析范围', self.html)
        self.assertIn('⑤ 按标记改名', self.html)
        self.assertIn('需要有 FFmpeg', self.html)
        readme = _read('README.md')
        self.assertIn('[KylinFPV](https://space.bilibili.com/36780014)', readme)
        self.assertIn('① 选择分析范围', readme)
        self.assertIn('style="color:#0f766e"', readme)

    def test_mark_section_precedes_rename_section(self):
        mark = self.html.index('class="row an-mark-row"')
        rename = self.html.index("onclick=\"renSelect('tagged')\"")
        self.assertLess(mark, rename)

    def test_depend_folder_and_bilingual_launcher(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, 'depend', 'readme_depend.md')))
        readme = _read('README.md')
        self.assertIn('readme_depend.md', readme)
        self.assertIn('让 AI', readme)
        bat = _read('启动start.bat')
        self.assertIn('正在使用 Python 解释器', bat)
        self.assertIn('Python interpreter:', bat)
        self.assertIn('[错误] 没有找到可用的 Python。', bat)
        self.assertIn('[ERROR] No usable Python found.', bat)

    def test_launcher_bat_is_crlf(self):
        # LF-only .bat makes cmd.exe mis-parse rem lines / goto labels and
        # exit immediately (window flashes). Must stay CRLF, no BOM.
        with open(os.path.join(ROOT, '启动start.bat'), 'rb') as f:
            raw = f.read()
        crlf = raw.count(b'\r\n')
        bare_lf = raw.count(b'\n') - crlf
        self.assertEqual(bare_lf, 0, '启动start.bat contains LF-only line breaks')
        self.assertGreater(crlf, 0)
        self.assertNotEqual(raw[:3], b'\xef\xbb\xbf', 'BOM not allowed in .bat')
        ga = os.path.join(ROOT, '.gitattributes')
        self.assertTrue(os.path.isfile(ga))
        self.assertIn('*.bat text eol=crlf', _read('.gitattributes'))


if __name__ == '__main__':
    unittest.main()
