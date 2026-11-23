# -*- coding: utf-8 -*-
"""
DJI 素材色彩空间标记工具 —— 本地 Web 界面
启动后自动打开浏览器；所有处理都在本机完成，不联网。
"""
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import core

HERE = Path(__file__).resolve().parent
WEB = HERE / 'web'
HISTORY_DIR = HERE / '_history'
HISTORY_DIR.mkdir(exist_ok=True)

# 大写扩展名集合预先算好：原实现在 /api/scan 里遍历每个文件时都会重新构造。
_VIDEO_EXTS_UPPER = {e.upper() for e in core.VIDEO_EXTS}
_SIDECAR_EXTS_UPPER = {e.upper() for e in core.SIDECAR_EXTS}


def _collect_files(root, recursive=False):
    """一次枚举目录里的普通文件，返回 Path 列表。

    用 os.scandir 的 DirEntry 缓存类型做判断，避免对每个条目再单独 os.stat
    （网络盘 / NAS 上每次 stat 都是一次往返，文件多时开销明显）。
    结果集合与 Path.rglob('*') + is_file() 一致；调用方会排序，故枚举顺序无影响。
    """
    out = []
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                subdirs = []
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if recursive:
                                subdirs.append(e.path)
                        elif e.is_file():       # 默认跟随符号链接，与 Path.is_file 一致
                            out.append(Path(e.path))
                    except OSError:
                        continue
        except OSError:
            continue
        if recursive:
            stack.extend(subdirs)
    return out


# ---------------- 系统原生文件夹选择框（独立进程） ----------------
PICKER_PS1 = HERE / 'picker.ps1'
PICKER_RESULT = HERE / '_picker_result.txt'


def _picker_script_to_run():
    """返回应交给 PowerShell 执行的 .ps1 路径（保证是 UTF-8 with BOM）。

    根因：Windows PowerShell 5.1 读取无 BOM 的 .ps1 时会按系统 ANSI(GBK) 解码，
    脚本里的中文 Title / Filter / FileName 必然乱码。picker.ps1 约定保存为
    UTF-8 with BOM；这里再加一道运行时自愈——万一 BOM 被编辑器去掉，就在
    **同一目录**生成一个带 BOM 的副本执行，保证 $PSScriptRoot 仍指向本项目，
    结果文件与错误文件的位置都不变。
    """
    try:
        data = PICKER_PS1.read_bytes()
    except OSError:
        return str(PICKER_PS1)
    if data.startswith(b'\xef\xbb\xbf'):
        return str(PICKER_PS1)
    tmp = HERE / '_picker_run.ps1'
    try:
        tmp.write_bytes(b'\xef\xbb\xbf' + data)
        return str(tmp)
    except OSError:
        return str(PICKER_PS1)


PICKER_ERROR = HERE / '_picker_error.txt'
PICKER_TIMEOUT = 120            # 秒；超时自动强杀，避免对话框卡死留下僵尸进程
_PICKER_PROC = None
_PICKER_LOCK = threading.Lock()


def _kill_picker(proc):
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def cancel_picker():
    """结束当前选择框进程并清理临时文件（幂等）。"""
    global _PICKER_PROC
    with _PICKER_LOCK:
        proc = _PICKER_PROC
        _PICKER_PROC = None
    _kill_picker(proc)
    for f in (PICKER_RESULT, PICKER_ERROR):
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass


def _picker_watchdog(proc):
    """选择框超过 PICKER_TIMEOUT 秒仍未退出就强杀，并写错误让前端停止轮询。"""
    try:
        proc.wait(timeout=PICKER_TIMEOUT)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        return
    global _PICKER_PROC
    with _PICKER_LOCK:
        if _PICKER_PROC is proc:
            _PICKER_PROC = None
    _kill_picker(proc)
    try:
        PICKER_ERROR.write_text(
            '选择框 %d 秒未响应，已自动关闭。请改用「浏览文件夹…」。' % PICKER_TIMEOUT,
            encoding='utf-8')
    except OSError:
        pass


def launch_picker():
    """启动独立 PowerShell 进程弹出原生文件夹选择框。

    不使用 -WindowStyle Hidden：隐藏宿主控制台窗口会让 WinForms 对话框
    偶发无法激活/无响应（用户实测卡死两次）。BOM 修复后那个空白控制台
    也不再有乱码，保留可见窗口更稳。另有超时守护 + 手动取消兜底。
    """
    global _PICKER_PROC
    cancel_picker()             # 先清掉上一次可能卡住的进程与结果文件
    try:
        proc = subprocess.Popen(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
             '-STA', '-File', _picker_script_to_run()],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )
        with _PICKER_LOCK:
            _PICKER_PROC = proc
        threading.Thread(target=_picker_watchdog, args=(proc,), daemon=True).start()
        return None
    except FileNotFoundError:
        return '未找到 powershell.exe，请手动粘贴路径'
    except Exception as e:
        return str(e)


def read_picker_result():
    if PICKER_RESULT.exists():
        txt = PICKER_RESULT.read_text(encoding='utf-8', errors='replace').strip()
        try:
            PICKER_RESULT.unlink()
        except OSError:
            pass
        # PS5.1 的 Set-Content -Encoding UTF8 会写 BOM；新版 picker.ps1 已改为
        # 无 BOM 写入，这里仍统一清理 BOM / 引号，兼容遗留结果文件，
        # 保证 os.path.isdir 首次判断就能命中（含中文路径）。
        cleaned = txt.lstrip('\ufeff').strip('"').strip()
        if cleaned and os.path.isdir(cleaned):
            return cleaned, None
        if txt and os.path.isdir(txt):
            return txt, None
        return None, '选择的路径无效：%s' % (cleaned or txt)
    err_file = HERE / '_picker_error.txt'
    if err_file.exists():
        msg = err_file.read_text(encoding='utf-8', errors='replace').lstrip('\ufeff').strip()
        try:
            err_file.unlink()
        except OSError:
            pass
        first = msg.splitlines()[0][:200] if msg else '（无详情）'
        return None, '选择框出错：%s' % first
    return None, None


# ---------------- 内置文件夹浏览器（不依赖系统对话框） ----------------
def list_drives():
    drives = []
    if os.name == 'nt':
        import string
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, ch in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                p = '%s:\\' % ch
                try:
                    # 排除光驱/未就绪设备
                    if os.path.exists(p):
                        drives.append(p)
                except OSError:
                    pass
    else:
        drives = ['/']
    return drives


def _norm(p):
    """统一路径分隔符，压掉重复斜杠，避免 'W://'、'W:\\\\a\\\\b' 这类写法。"""
    if not p:
        return ''
    if os.name == 'nt':
        p = p.replace('/', '\\')
        # 保留 UNC 前缀（\\server\share），其余重复分隔符压成一个
        unc = p.startswith('\\\\')
        body = p[2:] if unc else p
        while '\\\\' in body:
            body = body.replace('\\\\', '\\')
        p = ('\\\\' + body) if unc else body
        # 盘符根：'W:' -> 'W:\'；'W:\' 保持不变
        if len(p) == 2 and p.endswith(':'):
            p += '\\'
        while len(p) > 3 and p.endswith('\\'):
            p = p[:-1]
    else:
        while '//' in p:
            p = p.replace('//', '/')
        if len(p) > 1 and p.endswith('/'):
            p = p[:-1]
    return p


def list_dirs(path, sort='name'):
    """列出 path 下的子目录；path 为空时列出盘符。

    sort: name | name_desc | time（最近修改在前） | time_desc（最早在前）
    """
    path = _norm(path)
    if not path:
        return {'path': '', 'parent': None, 'sort': sort,
                'dirs': [{'name': d, 'path': d, 'mtime': None} for d in list_drives()]}
    if not os.path.isdir(path):
        return {'error': '目录不存在：%s' % path}
    parent = os.path.dirname(path.rstrip('\\/')) or None
    if path.rstrip('\\/').endswith(':'):
        parent = None  # 盘符根的上层是"我的电脑"
    dirs = []
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        try:
                            mtime = e.stat().st_mtime
                        except OSError:
                            mtime = 0
                        dirs.append({'name': e.name,
                                     'path': os.path.join(path, e.name),
                                     'mtime': mtime})
                except OSError:
                    continue
    except PermissionError:
        return {'error': '没有权限读取：%s' % path, 'path': path, 'parent': parent, 'dirs': [], 'sort': sort}
    except OSError as e:
        return {'error': '读取失败：%s' % e, 'path': path, 'parent': parent, 'dirs': [], 'sort': sort}
    name_key = lambda x: x['name'].lower()
    if sort == 'name_desc':
        dirs.sort(key=name_key, reverse=True)
    elif sort == 'time':          # 最近修改在前
        dirs.sort(key=lambda x: (-x['mtime'], x['name'].lower()))
    elif sort == 'time_desc':     # 最早修改在前
        dirs.sort(key=lambda x: (x['mtime'], x['name'].lower()))
    else:
        dirs.sort(key=name_key)
    return {'path': path, 'parent': parent, 'dirs': dirs, 'sort': sort}


# ---------------- HTTP 服务 ----------------
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def end_headers(self):
        # 禁止浏览器缓存 HTML/JS，避免改了代码还在跑旧页面
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        route = urlparse(self.path).path
        try:
            n = int(self.headers.get('Content-Length') or 0)
            payload = json.loads(self.rfile.read(n) or b'{}') if n else {}
        except Exception:
            payload = {}

        if route == '/api/browse':
            err = launch_picker()
            self._json({'pending': err is None, 'error': err})

        elif route == '/api/browse-result':
            path, err = read_picker_result()
            self._json({'path': path, 'error': err})

        elif route == '/api/browse-cancel':
            cancel_picker()
            self._json({'ok': True})

        elif route == '/api/ls':
            self._json(list_dirs((payload.get('path') or '').strip(),
                                 (payload.get('sort') or 'name')))

        elif route == '/api/scan':
            folder = payload.get('folder', '')
            if not folder or not os.path.isdir(folder):
                return self._json({'error': '文件夹不存在：%s' % folder}, 400)
            recursive = bool(payload.get('recursive'))
            sidecars = bool(payload.get('sidecars'))
            skip_tagged = bool(payload.get('skipTagged'))
            root = Path(folder)
            # 一次枚举全部文件（scandir 缓存类型，省掉逐条目 stat），并预建
            # (父目录, 主干) 索引。原实现每个视频都要 sorted(f.parent.glob('*'))
            # 重新枚举一遍整个目录，是 O(N²) 的最大热点。
            all_files = _collect_files(root, recursive)
            videos = sorted(f for f in all_files
                            if f.suffix.upper() in _VIDEO_EXTS_UPPER)
            by_key = {}
            for f in all_files:
                by_key.setdefault((str(f.parent), f.stem), []).append(f)
            for lst in by_key.values():
                lst.sort(key=lambda p: str(p))   # 复现 sorted(f.parent.glob('*')) 的顺序
            results = [None] * len(videos)

            def work(i_f):
                i, f = i_f
                info = core.detect(f)
                stem = f.stem
                code = core.recover_code_from_tag(stem, info['code'])
                info = dict(info, code=code)
                tagged = bool(core.ALREADY_TAGGED.search(stem))
                new_stem = core.plan_new_stem(stem, code)
                if tagged and skip_tagged:
                    status = 'skip_tagged'
                elif new_stem is None:
                    status = 'no_D'
                elif new_stem == stem:
                    status = 'unchanged'
                else:
                    status = 'ok'
                members = [{
                    'abs': str(f), 'old': f.name,
                    'new': (new_stem + f.suffix) if new_stem else None,
                }]
                if sidecars:
                    for s in by_key.get((str(f.parent), stem), ()):
                        if s.name == f.name:
                            continue
                        if s.suffix.upper() in _SIDECAR_EXTS_UPPER:
                            ns = core.plan_new_stem(s.stem, info['code'])
                            members.append({'abs': str(s), 'old': s.name,
                                            'new': (ns + s.suffix) if ns else None})
                # 相对所选目录的子文件夹路径（主目录由用户自己选，不重复显示）
                try:
                    rel = str(f.parent.relative_to(root))
                    if rel == '.':
                        rel = ''
                except ValueError:
                    rel = str(f.parent)
                results[i] = {
                    'key': str(f), 'video': f.name, 'raw': info['raw'],
                    'code': info['code'], 'label': info['label'],
                    'source': info['source'], 'status': status, 'tagged': tagged,
                    'device': info.get('device'), 'rel': rel, 'members': members,
                }

            # I/O 密集型任务：并发数可配置（默认 12），不再写死 8。
            try:
                workers = int(os.environ.get('SCAN_WORKERS', '12'))
            except ValueError:
                workers = 12
            workers = max(2, min(32, workers))
            with ThreadPoolExecutor(max_workers=workers) as ex:
                list(ex.map(work, enumerate(videos)))
            groups = [r for r in results if r]
            counts = {}
            for g in groups:
                counts[g['code']] = counts.get(g['code'], 0) + 1
            self._json({'folder': str(root), 'groups': groups, 'counts': counts})

        elif route == '/api/analyze':
            # 画面饱和度分析：完全按需。/api/scan 不加载本分支的任何依赖；
            # 本分支也不改识别码、不改名，只返回「建议」供用户确认。
            paths = payload.get('paths')
            if paths is None:
                paths = payload.get('files') or []      # 兼容旧别名
            if not isinstance(paths, list) or not paths:
                return self._json({'error': '请先勾选要分析的文件', 'results': []}, 400)
            if len(paths) > 100:
                return self._json({'error': '一次最多分析 100 个文件，请分批勾选', 'results': []}, 400)
            try:
                frames = int(payload.get('frames') or 2)
            except (TypeError, ValueError):
                frames = 2
            frames = max(1, min(8, frames))
            # 画面硬解开关：默认关闭；前端勾选后尝试 -hwaccel auto，失败自动回退 CPU。
            raw_hw = payload.get('hwaccel', False)
            if isinstance(raw_hw, str):
                hwaccel = raw_hw.strip().lower() in ('1', 'true', 'yes', 'on', 'auto')
            else:
                hwaccel = bool(raw_hw)
            # 只接受存在的视频文件绝对路径，避免把任意路径喂给 ffmpeg
            checked, skipped = [], []
            for item in paths:
                if not isinstance(item, str) or not item:
                    skipped.append(str(item))
                    continue
                p = Path(item)
                if (not p.is_absolute() or not p.is_file()
                        or p.suffix.upper() not in _VIDEO_EXTS_UPPER):
                    skipped.append(item)
                    continue
                checked.append(item)
            if not checked:
                return self._json({'error': '没有可分析的视频文件（%d 个路径无效）' % len(skipped),
                                   'results': []}, 400)
            # 按需加载：pillow / imageio-ffmpeg 只有走到这里才会被 import
            try:
                if str(HERE) not in sys.path:
                    sys.path.insert(0, str(HERE))
                import analyzer
                ffmpeg = analyzer.ensure_available()
            except ImportError as e:
                return self._json({'error': '画面分析模块不可用：%s' % e, 'results': []})
            except Exception as e:
                return self._json({'error': '画面分析不可用：%s' % e, 'results': []})
            try:
                an_workers = int(os.environ.get('ANALYZE_WORKERS', '3'))
            except ValueError:
                an_workers = 3
            an_workers = max(1, min(8, an_workers))   # ffmpeg 抽帧很慢，限制并发
            try:
                an_results = analyzer.analyze_many(checked, workers=an_workers,
                                                   frames=frames, timeout=120,
                                                   hwaccel=hwaccel)
            except Exception as e:
                return self._json({'error': '画面分析失败：%s' % e, 'results': []})
            self._json({'results': an_results, 'ffmpeg': ffmpeg,
                        'frames': frames, 'hwaccel': hwaccel, 'skipped': skipped})

        elif route == '/api/open':
            # 用系统默认程序打开素材：只读、只打开，不改文件内容/元数据/时间戳。
            target = payload.get('path')
            if not isinstance(target, str) or not target.strip():
                return self._json({'error': '缺少文件路径'}, 400)
            target = target.strip()
            if not os.path.isabs(target):
                return self._json({'error': '非法路径（需为绝对路径）'}, 400)
            if not os.path.isfile(target):
                return self._json({'error': '文件不存在：%s' % target}, 400)
            if Path(target).suffix.upper() not in _VIDEO_EXTS_UPPER:
                return self._json({'error': '不是视频文件：%s' % Path(target).suffix}, 400)
            if os.name != 'nt':
                return self._json({'error': '仅支持 Windows'})
            try:
                os.startfile(target)      # 仅 Windows 提供；调用系统默认关联程序
            except Exception as e:        # OSError（无关联程序 / 权限）等一律兜住，不抛栈
                return self._json({'error': '打开失败：%s' % e}, 500)
            self._json({'ok': True})

        elif route == '/api/apply':
            plans = payload.get('items') or []
            done, failed = core.apply_plans(plans)
            if done:
                ts = time.strftime('%Y%m%d_%H%M%S')
                rec = {'time': ts, 'done': done, 'failed': failed}
                (HISTORY_DIR / ('rename_%s.json' % ts)).write_text(
                    json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
            self._json({'done': done, 'failed': failed})

        elif route == '/api/undo':
            files = sorted(HISTORY_DIR.glob('rename_*.json'))
            if not files:
                return self._json({'error': '没有可撤销的记录'})
            rec = json.loads(files[-1].read_text(encoding='utf-8'))
            all_done = rec.get('done', [])
            names = payload.get('names')
            # names 为非空数组时按勾选范围撤销；缺省（None / 空 / 非数组）保持整批行为。
            # done 项里的 'new' 就是文件当前的名字，正好与前端勾选行的 members[].old 对应。
            if isinstance(names, list) and names:
                name_set = {str(n) for n in names}
                target = [d for d in all_done if d.get('new') in name_set]
                if not target:
                    return self._json({'error': '勾选的文件不在最近一次改名记录中',
                                       'ok': [], 'failed': []})
            else:
                target = all_done
            ok, failed = core.undo_batch(target)
            if ok and not failed:
                # 部分撤销：把未撤销的项写回记录（不删文件）；只有整批全部撤销才删除。
                # 用对象身份匹配，避免依赖文件名唯一性。
                undone_ids = {id(x) for x in ok}
                remain = [d for d in all_done if id(d) not in undone_ids]
                if remain:
                    rec['done'] = remain
                    files[-1].write_text(
                        json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
                else:
                    files[-1].unlink(missing_ok=True)
            self._json({'ok': ok, 'failed': failed, 'time': rec.get('time')})

        else:
            self._json({'error': 'unknown route'}, 404)


def kill_stale_servers(port):
    """启动前清掉上一位占用该端口的旧服务进程，避免"新旧混跑"加载到旧路由。"""
    if os.name != 'nt':
        return
    try:
        r = subprocess.run(
            ['netstat', '-ano', '-p', 'TCP'],
            capture_output=True,       # 不解码：netstat 输出是 GBK，交给下面 latin1 处理
            creationflags=0x08000000,
        )
    except Exception:
        return
    me = os.getpid()
    pids = set()
    text = (r.stdout or b'').decode('latin1', 'replace')   # GBK 中文按 latin1 读不会抛异常
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0].upper().startswith('TCP'):
            local, state, pid = parts[1], parts[3], parts[4] if len(parts) > 4 else ''
            if state.upper() == 'LISTENING' and local.endswith(':%d' % port) and pid.isdigit():
                if int(pid) != me:
                    pids.add(pid)
    for pid in pids:
        subprocess.run(['taskkill', '/F', '/PID', pid],
                       capture_output=True, creationflags=0x08000000)


def main():
    port = int(os.environ.get('PORT', '8733'))
    kill_stale_servers(port)
    for attempt in range(20):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', port + attempt), Handler)
            break
        except OSError:
            continue
    else:
        print('端口占用，无法启动')
        return 1
    url = 'http://127.0.0.1:%d/' % srv.server_address[1]
    print('DJI 色彩空间标记工具 v3.04.03 已启动：%s' % url)
    print('关闭此窗口即退出程序。')
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
