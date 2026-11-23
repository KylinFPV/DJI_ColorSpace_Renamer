# -*- coding: utf-8 -*-
"""
DJI 素材色彩空间识别 + 文件名标记
---------------------------------
原理：DJI（Osmo Pocket 4P / Pocket 3 / Action 系列等）在 MP4 的 moov 里写入
QuickTime 元数据键 com.dji.camera.ColorGammaSxS，其取值即拍摄时的色彩模式，例如：
    D-Log          -> D-Log 10-bit
    D-Log 2        -> D-Log 2 10-bit
    Rec.2100 HLG   -> HDR / HLG
    Rec.709        -> 普通(Normal)
只读文件、只做重命名，不修改任何文件内容、不写元数据、不改时间戳、不新建旁挂文件。
"""
import re
import struct
from collections import Counter
from pathlib import Path

VIDEO_EXTS = {'.mp4', '.mov', '.osv'}
# 需要一起改名的同名配套文件（低码率代理 / 音频 / 字幕 / 缩略图）
SIDECAR_EXTS = {'.lrf', '.aac', '.srt', '.thm', '.jpg', '.wav', '.ass', '.met'}
# 大写扩展名集合预先算好：原实现在遍历每个文件时都重新构造一次 set。
VIDEO_EXTS_UPPER = {e.upper() for e in VIDEO_EXTS}
SIDECAR_EXTS_UPPER = {e.upper() for e in SIDECAR_EXTS}

COLOR_KEY = 'ColorGammaSxS'

# DJI 飞行设备（Avata 360 / Avata 2 等）把色彩模式写在 .SRT 字幕的 color_md 字段里。
# 这些设备的 MP4/OSV 内没有 ColorGammaSxS，SRT 是唯一可靠来源。
SRT_COLORMD = re.compile(r'color_md\s*[:=]\s*([A-Za-z0-9_\-]+)', re.I)
# bytes 版：SRT 每帧都写 color_md，直接在原始字节上匹配可省掉 2MB 文本解码
SRT_COLORMD_BYTES = re.compile(rb'color_md\s*[:=]\s*([A-Za-z0-9_\-]+)', re.I)
COLOR_MD_MAP = {
    'dlog_m': 'D-Log M', 'dlogm': 'D-Log M', 'd_log_m': 'D-Log M',
    'dlog2': 'D-Log 2', 'dlog_2': 'D-Log 2', 'd-log2': 'D-Log 2', 'd-log_2': 'D-Log 2',
    # DJI 官方论坛确认：Mini/Air/Mavic 等机型的 D-Log M 写作 `d-log`。
    # 若映射成 'D-Log'，normalize 会判成 D1(D-Log) —— 这是错判，必须映射为 D-Log M。
    'd-log': 'D-Log M', 'dlog': 'D-Log M', 'd-log_m': 'D-Log M', 'dlog-m': 'D-Log M',
    'hlg': 'Rec.2100 HLG', 'rec2100hlg': 'Rec.2100 HLG', 'rec2100_hlg': 'Rec.2100 HLG',
    'rec709': 'Rec.709', 'normal': 'Rec.709', 'none': 'Rec.709',
    'default': 'Rec.709',   # 官方论坛确认：Normal 色彩时 color_md 写 default
    # O3 天空端的 SRT 实测写 `[color_md : d_cinelike]`（冒号前有空格）。
    # 不能映射成 'D-Log'：D-Cinelike 是独立色彩模式，与 D-Log M 无关。
    'd_cinelike': 'D-Cinelike', 'd-cinelike': 'D-Cinelike',
    'dcinelike': 'D-Cinelike', 'cinelike': 'D-Cinelike',
}

# 归一化后的取值 -> (分类代码, 展示名)
KNOWN = {
    'D-LOG': ('D1', 'D-Log (10-bit)'),
    'D-LOG 2': ('D2', 'D-Log 2 (10-bit)'),
    'D-LOG2': ('D2', 'D-Log 2 (10-bit)'),
    'D-LOG M': ('DM', 'D-Log M'),
    'REC.2100 HLG': ('DH', 'HLG / HDR'),
    'REC.2100': ('DH', 'HLG / HDR'),
    'HLG': ('DH', 'HLG / HDR'),
    'REC.709': ('DN', 'Rec.709 / Normal'),
    'REC709': ('DN', 'Rec.709 / Normal'),
    'NORMAL': ('DN', 'Rec.709 / Normal'),
    'D-CINELIKE': ('DC', 'D-Cinelike'),
    'DCINELIKE': ('DC', 'D-Cinelike'),
    'CINELIKE': ('DC', 'D-Cinelike'),
}

# 分类代码 -> 文件名后缀（用户要求的标记）
SUFFIX = {'D1': '_D1', 'D2': '_D2', 'DH': '_DH', 'DN': '_DN',
          'DM': '_DM', 'DC': '_DC', 'DU': '_DU'}

ALREADY_TAGGED = re.compile(r'_D[12UHNMC]$', re.I)
# 文件名末尾的色彩标记 token：裸 "_D"，或已标记的 "_D1/_D2/_DH/_DN/_DU/_DM/_DC"
TAG_AT_END = re.compile(r'_D([12UHNMC])?$', re.I)
TAG_CODE = {'1': 'D1', '2': 'D2', 'H': 'DH', 'N': 'DN',
            'M': 'DM', 'C': 'DC', 'U': 'DU'}

# O3 天空端 / Action 2 的命名：DJI_0006.MP4、DJI_0151.MP4（无 _D 标记）。
# 这些文件需要「追加」后缀而不是「替换」；其它机型都是 DJI_yyyymmdd_nnnn_D.MP4。
APPEND_STEM = re.compile(r'^DJI_\d{4,6}$', re.I)

# udta/meta/ilst 的 ©too (encoder) 里写设备型号，实测样本：
#   DJIAction2 / DJI OsmoPocket4P / DJI OsmoPocket3 / DJI Osmo Nano /
#   DJI Avata2 / DJI O4P / Osmo 360 II
# 这里只做显示美化，不改原始值语义。
DEVICE_ALIASES = {
    'DJIAction2': 'DJI Action 2',
    'DJI OsmoPocket4P': 'DJI Osmo Pocket 4P',
    'DJI OsmoPocket3': 'DJI Osmo Pocket 3',
    'DJI Osmo Nano': 'DJI Osmo Nano',
    'DJI Avata2': 'DJI Avata 2',
    'DJI Avata360': 'DJI Avata 360',
    'DJI O4P': 'DJI O4 Air Unit Pro',
    'Osmo 360 II': 'DJI Osmo 360 II',
}


def _iter_boxes(buf, start, end, skip=0):
    """遍历 MP4 box：yield (type, abs_start, size, payload_start, payload_end)"""
    i = start + skip
    while i + 8 <= end:
        size = struct.unpack('>I', buf[i:i + 4])[0]
        typ = buf[i + 4:i + 8]
        hdr = 8
        if size == 1:
            if i + 16 > end:
                return
            size = struct.unpack('>Q', buf[i + 8:i + 16])[0]
            hdr = 16
        elif size == 0:
            size = end - i
        if size < hdr or i + size > end:
            return
        yield (typ, i, size, i + hdr, i + size)
        if typ in (b'moov', b'trak', b'mdia', b'minf', b'stbl', b'udta'):
            yield from _iter_boxes(buf, i + hdr, i + size)
        elif typ == b'stsd':          # full box + entry_count
            yield from _iter_boxes(buf, i + hdr, i + size, skip=8)
        elif typ == b'meta':          # full box
            yield from _iter_boxes(buf, i + hdr, i + size, skip=4)
        i += size


# 反向分块定位 moov：每块 1 MiB，块尾重叠 3 字节（保证跨块 'moov' 可被检出）。
# 与原实现一致，每级最多检查最靠后的 8 个命中。
_MOOV_CHUNK = 1 << 20
_MOOV_OVERLAP = 3
_MOOV_MAX_HITS = 8


def _try_moov_hits(f, hits, base, n):
    """用当前窗口参数 (base, n) 检查已收集的 moov 命中，返回第一个合法的 box。

    hits 为 'moov' 首字节的绝对偏移（降序）。返回的 4 元组形状与旧实现一致：
    buf[p0:p1] 恰好是 moov box 的 payload（跳过 8 字节 box header）。
    """
    for h in hits:
        if h < base + 4:                     # 对应旧实现里的 h_rel < 4
            continue
        h_rel = h - base
        f.seek(h - 4)
        raw = f.read(4)
        if len(raw) < 4:
            continue
        sz = struct.unpack('>I', raw)[0]
        if not (8 <= sz <= n - h_rel + 4):  # 旧实现：sz <= len(buf) - (h - 4)
            continue
        f.seek(h - 4)
        box = f.read(sz)
        if len(box) == sz:
            return box, 8, sz, base
    return None


def _find_moov(path, tail_sizes=(4, 32, 128)):
    """反向分块定位 moov，返回 (box_bytes, 8, box_size, window_base)；找不到返回 None。

    语义与旧实现完全等价，但不再有这些开销：
      - 旧实现按 4/32/128 MiB 三级各读一次窗口，失败文件累计读 164 MiB，
        且每级都要分配 4/32/128 MiB 的大 buffer 并多次 rfind；
      - 新实现一次 open、按 1 MiB 分块从尾部反向读取、复用已读区域，
        命中合法 moov 立即返回，内存峰值从 128 MiB 降到 ~1 MiB + box 本身。
    """
    size = path.stat().st_size
    try:
        f = path.open('rb')
    except OSError:
        return None
    with f:
        hits = []                # 'moov' 首字节绝对偏移，降序，最多 8 个
        next_end = size          # 下一块要读到的绝对终点
        scanned = size           # 已扫描到的绝对偏移
        for mb in tail_sizes:
            n = min(size, mb * 1024 * 1024)
            if n < 1024:
                break
            base = size - n
            # 窗口放宽后，先前不合法的命中可能变合法，先按新参数重检一次
            found = _try_moov_hits(f, hits, base, n)
            if found:
                return found
            while scanned > base and len(hits) < _MOOV_MAX_HITS:
                start = max(base, next_end - _MOOV_CHUNK)
                if start >= next_end:
                    break
                f.seek(start)
                data = f.read(next_end - start)
                if not data:
                    break
                i = data.rfind(b'moov')
                while i >= 0 and len(hits) < _MOOV_MAX_HITS:
                    abs_h = start + i
                    if abs_h not in hits:    # 重叠区小于 'moov' 长度，正常不会重复
                        hits.append(abs_h)
                    i = data.rfind(b'moov', 0, i)
                scanned = start
                next_end = min(size, start + _MOOV_OVERLAP)
                found = _try_moov_hits(f, hits, base, n)
                if found:
                    return found
                if next_end <= start:
                    break
            # 本级没有合法命中：交给下一级更宽的窗口
    return None


def _parse_keys(buf, p):
    """keys atom -> {index: key_string}；p = 'keys' 之后的第一个字节"""
    end = len(buf)
    count = struct.unpack('>I', buf[p + 4:p + 8])[0]
    out = {}
    i = p + 8
    for idx in range(1, count + 1):
        if i + 8 > end:
            break
        esz = struct.unpack('>I', buf[i:i + 4])[0]
        if esz < 8 or i + esz > end:
            break
        out[idx] = buf[i + 8:i + esz].decode('utf-8', 'replace')
        i += esz
    return out


def _parse_ilst(buf, p):
    """ilst atom -> {index: value_bytes}；p = 'ilst' 之后的第一个字节"""
    end = len(buf)
    out = {}
    i = p
    while i + 8 <= end:
        esz = struct.unpack('>I', buf[i:i + 4])[0]
        idx = struct.unpack('>I', buf[i + 4:i + 8])[0]
        if esz < 16 or i + esz > end or idx > 4096:
            break
        payload = buf[i + 8:i + esz]
        if payload[4:8] == b'data' and len(payload) > 16:
            out[idx] = payload[16:]
        i += esz
    return out


# 只保留"明确"的模式串。不能搜裸 HLG / 裸 Normal——
# moov 里 "EIS:OFF;FOV:Normal" 的 Normal 是视场角、压缩数据里的 hlg 是随机字节，都会误判。
_FALLBACK_PAT = [
    (re.compile(rb'D-?Log\s*M', re.I), 'D-Log M'),
    (re.compile(rb'D-?Log\s*2', re.I), 'D-Log 2'),
    (re.compile(rb'D-?Log(?![M2\s])', re.I), 'D-Log'),
    (re.compile(rb'Rec\.2100\s*HLG', re.I), 'Rec.2100 HLG'),
    (re.compile(rb'Rec\.?709', re.I), 'Rec.709'),
    (re.compile(rb'color_md\s*[:=]\s*([A-Za-z0-9_\-]+)', re.I), '@color_md'),
]
# 6 个模式都必然含 log / rec / color_md 之一。先做一次廉价预筛：未命中时
# 直接返回，避免对可能很大的 moov region 白跑 6 次全量扫描。
_FALLBACK_HINT = re.compile(rb'log|rec|color_md', re.I)


def _fallback_scan(region):
    """在 moov 区域里按优先级搜色彩模式字符串（结果与原实现一致）"""
    if not _FALLBACK_HINT.search(region):
        return None
    best, rank = None, 99
    for i, (rx, name) in enumerate(_FALLBACK_PAT):
        if i >= rank:            # 已拿到最高优先级，更低优先级不可能再覆盖结果
            break
        m = rx.search(region)
        if m:
            if name == '@color_md':
                # 保持原有查表行为（bytes 分组），不改动任何既有语义
                best, rank = COLOR_MD_MAP.get(m.group(1).lower(), m.group(1)), i
            else:
                best, rank = name, i
    return best


def _parse_device(region):
    """从 udta/meta/ilst 的 ©too (encoder) 字段读设备型号。

    实测 O3 天空端该字段只有 'DJI DEFAULT ENCODING'（无型号），其余机型写
    DJIAction2 / DJI OsmoPocket4P / DJI Osmo Nano 等。读不到返回 None。
    """
    try:
        pos = region.find(b'\xa9too')
        if pos < 4:
            return None
        i = pos - 4                       # ©too item 的 size 字段
        sz = struct.unpack('>I', region[i:i + 4])[0]
        if not (24 <= sz <= 4096) or i + sz > len(region):
            return None
        # item: size(4)+type(4) + data box: size(4)+'data'(4)+type(4)+locale(4)+payload
        payload = region[i + 8 + 16:i + sz].rstrip(b'\x00')
        if not payload or not all(32 <= b < 127 for b in payload[:64]):
            return None
        val = payload.decode('ascii', 'replace').strip()
        if not val or len(val) > 64:
            return None
        # O3 天空端实测只写编码信息，没有型号；当成设备名会误导
        if val.upper() == 'DJI DEFAULT ENCODING':
            return None
        return DEVICE_ALIASES.get(val, val)
    except Exception:
        return None


def _read_moov_meta(path):
    """一次读 moov，返回 (raw_color, source, device)。

    设备名与色彩元数据共用同一次读取，避免为每个视频多读 1 MiB。
    """
    try:
        mo = _find_moov(path)
        if mo:
            buf, p0, p1, _base = mo
            region = buf[p0:p1]
            device = _parse_device(region)
            kpos = region.find(b'keys')
            if kpos >= 0:
                keys = _parse_keys(region, kpos + 4)
                ipos = region.find(b'ilst', kpos + 4)
                if ipos >= 0:
                    vals = _parse_ilst(region, ipos + 4)
                    for idx, name in keys.items():
                        if COLOR_KEY in name:
                            v = vals.get(idx)
                            if v is not None:
                                return (v.rstrip(b'\x00').decode('utf-8', 'replace').strip(),
                                        'moov/meta', device)
            # 兜底：直接在 moov 区域按优先级搜字符串
            fb = _fallback_scan(region)
            if fb:
                return fb, 'moov/raw', device
            return None, 'none', device
    except Exception:
        pass
    return None, 'none', None


def read_color_gamma(path):
    """读取 DJI ColorGammaSxS。返回 (raw_str|None, source)"""
    raw, src, _device = _read_moov_meta(path)
    return raw, src


def normalize(raw):
    """原始值 -> (分类代码, 展示名)"""
    if not raw:
        return 'DU', '未知'
    key = re.sub(r'\s+', ' ', raw.strip()).upper()
    if key in KNOWN:
        return KNOWN[key]
    for k, v in KNOWN.items():
        if k in key:
            return v
    if 'LOG' in key:
        return 'DU', raw
    return 'DU', raw


def read_color_from_srt(video):
    """从同名 .SRT 字幕读 color_md（DJI 飞行设备的色彩模式来源）。

    返回 (raw_str|None, 命中次数)。SRT 可能很大，只读前 2MB（每帧都写，足够取众数）。
    优化：直接在 bytes 上惰性匹配并计数，省掉 2MB 文本解码和数万个 str 对象；
    众数、命中次数、并列时的取舍顺序与逐条 findall 完全一致。
    """
    p = Path(video)
    srt = None
    for ext in ('.SRT', '.srt'):
        cand = p.with_suffix(ext)
        if cand.exists():
            srt = cand
            break
    if srt is None:
        return None, 0
    try:
        with srt.open('rb') as f:
            data = f.read(2 * 1024 * 1024)
    except OSError:
        return None, 0
    counts = Counter(m.group(1).lower() for m in SRT_COLORMD_BYTES.finditer(data))
    if not counts:
        return None, 0
    total = sum(counts.values())
    # 捕获组受 [A-Za-z0-9_\-]+ 约束，一定是 ASCII
    val = counts.most_common(1)[0][0].decode('ascii', 'replace')
    if val in COLOR_MD_MAP:
        return COLOR_MD_MAP[val], total
    # 未收录的写法：这些设备的 log 模式就是 D-Log M。
    # 若直接返回原值，normalize 的子串匹配会把它判成 D-Log(D1)，故兜底为 D-Log M。
    if 'log' in val:
        return 'D-Log M', total
    return val, total


def detect(path):
    """识别单个视频：返回 dict

    优先级：
      1) 视频内的 ColorGammaSxS 元数据（Pocket 4 等）——最可靠
      2) 同名 .SRT 的 color_md（Avata 360 / Avata 2 等飞行设备）
      3) 同名 .LRF 代理文件里的元数据
      4) 都没有 -> DU（未知，交给用户在界面上手动指定）
    """
    p = Path(path)
    raw, src, device = _read_moov_meta(p)
    if raw is None:
        raw, _n = read_color_from_srt(p)
        if raw:
            src = 'srt'
    if raw is None:
        lrf = p.with_suffix('.LRF')
        if not lrf.exists():
            lrf = p.with_name(p.stem + '.lrf')
        if lrf.exists():
            raw, src = read_color_gamma(lrf)
            if raw:
                src += '/lrf'
            else:
                raw2, _n2 = read_color_from_srt(lrf)
                if raw2:
                    raw, src = raw2, 'srt/lrf'
    code, label = normalize(raw)
    return {'raw': raw, 'code': code, 'label': label,
            'source': src, 'device': device}


def recover_code_from_tag(stem, code):
    """自动识别为「未知」但文件名已有明确标记时，沿用标记。

    保护用户在无元数据/无字幕素材上手动指定的 _DN/_DC/_DM 等结果：
    否则重扫会把人工标记冲成 _DU。用户仍可在界面下拉里手动改。
    """
    if code != 'DU':
        return code
    m = TAG_AT_END.search(stem)
    if not m or not m.group(1):
        return code
    return TAG_CODE.get(m.group(1).upper(), code)


def plan_new_stem(stem, code):
    """把文件名末尾的 _D 标记替换为对应标记。

    幂等设计（重要）：
      xxx_D    + D-Log -> xxx_D1      已有 _D：替换
      xxx_D1   + D-Log -> xxx_D1      已正确标记，原样返回（不会变成 xxx_D11）
      xxx_D1   + HLG   -> xxx_DH      标记错误时纠正
      DJI_0006 + DN    -> DJI_0006_DN  O3/AC2 无标记命名：追加
      DJI_0006 + DC    -> DJI_0006_DC
      DJI_0006_DN + DN -> DJI_0006_DN  追加后再次扫描也幂等
      xxx             -> None        其余无标记文件不处理
    """
    suffix = SUFFIX.get(code, '_DU')
    m = TAG_AT_END.search(stem)
    if m:
        if m.group(0).upper() == suffix.upper():
            return stem          # 已是正确标记，保持不变（幂等）
        return stem[:m.start()] + suffix
    if APPEND_STEM.match(stem):
        return stem + suffix
    return None


def scan_folder(folder, recursive=False, skip_tagged=True, include_sidecars=True):
    """扫描目录，返回计划列表。只识别 .MP4，改名时带同名配套文件"""
    root = Path(folder)
    it = root.rglob('*') if recursive else root.glob('*')
    files = [f for f in it if f.is_file()]
    videos = [f for f in files if f.suffix.upper() in VIDEO_EXTS_UPPER]
    # 一次建立 (父目录, 主干) 索引：原实现对每个视频都全表扫一遍 files（O(N²)）。
    # 列表保持原始枚举顺序，members 顺序与旧实现完全一致。
    by_key = {}
    for f in files:
        by_key.setdefault((f.parent, f.stem), []).append(f)
    groups = []
    for v in sorted(videos):
        info = detect(v)
        stem = v.stem
        code = recover_code_from_tag(stem, info['code'])
        info = dict(info, code=code)
        tagged = bool(ALREADY_TAGGED.search(stem))
        new_stem = plan_new_stem(stem, code)
        members = [v]
        if include_sidecars:
            for f in by_key.get((v.parent, stem), ()):
                if f is v:
                    continue
                if f.suffix.upper() in SIDECAR_EXTS_UPPER:
                    members.append(f)
        status = 'ok'
        if tagged and skip_tagged:
            status = 'skip_tagged'
        elif new_stem is None:
            status = 'no_D'
        elif new_stem == stem:
            status = 'unchanged'
        plans = []
        for m in members:
            ns = plan_new_stem(m.stem, info['code']) if new_stem else None
            plans.append({'old': m.name, 'new': (ns + m.suffix) if ns else None,
                          'abs': str(m), 'ext': m.suffix})
        try:
            rel = str(v.parent.relative_to(root))
            if rel == '.':
                rel = ''
        except ValueError:
            rel = str(v.parent)
        groups.append({
            'video': v.name, 'abs': str(v), 'raw': info['raw'], 'code': info['code'],
            'label': info['label'], 'source': info['source'], 'status': status,
            'device': info.get('device'), 'rel': rel, 'tagged': tagged, 'members': plans,
        })
    return groups


def apply_plans(plans):
    """执行重命名，返回 (成功列表, 失败列表)。只调用 os.rename，不碰内容/时间"""
    done, failed = [], []
    for item in plans:
        old, new = item['old'], item['new']
        if not new or old == new:
            continue
        # 安全网：绝不允许产生重复标记（如 _D11、_D1H）——只应有单个标记 token
        if not TAG_AT_END.search(Path(new).stem):
            failed.append({'old': old, 'new': new, 'abs': item['abs'],
                           'err': '拒绝：新文件名标记格式异常（可能重复标记）'})
            continue
        src = Path(item['abs'])
        dst = src.with_name(new)
        try:
            if dst.exists():
                failed.append({'old': old, 'new': new, 'abs': item['abs'], 'err': '目标文件已存在'})
                continue
            src.rename(dst)
            done.append({'old': old, 'new': new, 'abs': item['abs'],
                         'abs_new': str(dst)})
        except Exception as e:
            failed.append({'old': old, 'new': new, 'abs': item['abs'], 'err': str(e)})
    return done, failed


def undo_batch(done):
    """按 done 列表反向改回原名"""
    ok, failed = [], []
    for item in reversed(done):
        src = Path(item['abs_new'])
        dst = src.with_name(item['old'])
        try:
            if not src.exists():
                failed.append({'old': item['new'], 'new': item['old'], 'err': '文件不存在'})
                continue
            src.rename(dst)
            ok.append(item)
        except Exception as e:
            failed.append({'old': item['new'], 'new': item['old'], 'err': str(e)})
    return ok, failed


if __name__ == '__main__':
    import sys, time
    from pathlib import Path as _P
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    flags = {a for a in sys.argv[1:] if a.startswith('-')}
    folder = args[0] if args else '.'
    groups = scan_folder(folder, recursive='-r' in flags,
                         skip_tagged='-f' not in flags,
                         include_sidecars='-n' not in flags)
    for g in groups:
        print(f"{g['video']:<40} {str(g['raw']):<16} {g['code']:<3} {g['status']}")
        for m in g['members']:
            if m['new']:
                print(f"    {m['old']}  ->  {m['new']}")
    if '--apply' in flags:
        items = [m for g in groups if g['status'] == 'ok' for m in g['members'] if m['new']]
        done, failed = apply_plans(items)
        print(f"\n已改名 {len(done)} 个文件，失败 {len(failed)} 个")
        for f in failed:
            print('  失败：%s -> %s（%s）' % (f['old'], f['new'], f['err']))
        if done:
            hist = _P(__file__).resolve().parent / '_history'
            hist.mkdir(exist_ok=True)
            rec = {'time': time.strftime('%Y%m%d_%H%M%S'), 'done': done, 'failed': failed}
            (hist / ('rename_%s.json' % rec['time'])).write_text(
                __import__('json').dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
            print('撤销记录：%s' % (hist / ('rename_%s.json' % rec['time'])))
