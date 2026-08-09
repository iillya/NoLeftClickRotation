# -*- coding: utf-8 -*-
"""NoLeftClickRotation（禁用左键视图旋转）— 纯 Python 版（ZBrush 2026）。

ZBrush 2026 启动时会自动执行 ZStartup\\ZPlugs64 下的 *.py 文件，因此本插件
无需 .zsc、无需 DLL、无需环境变量，安装 = 复制这一个文件。

工作原理（两层）：
1. 窗口子类：Edit 模式画布内的左键按下不转发给 ZBrush；光标进入模型后
   补发一次按下，笔刷从进入点正常起笔；离开模型及时补发抬起。
2. IAT 钩子：ZBrush 的视图旋转由“物理左键状态 + 光标位置”轮询驱动（直接
   调用 GetAsyncKeyState），只拦窗口消息拦不住。插件在本进程内把 ZBrush.exe
   导入表里的 GetAsyncKeyState 指向一个极小的原生存根：光标在空白画布上时
   对 VK_LBUTTON 返回 0（等于告诉 ZBrush“左键没按住”，旋转无从触发）；
   光标在模型上时返回真实状态，雕刻不受影响。钩子随 ZBrush 进程启停。
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes
from typing import Optional, Tuple

# ---------------- Win32 常量与类型 ----------------

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203

MK_LBUTTON = 0x0001
MK_SHIFT = 0x0004
MK_CONTROL = 0x0008

VK_LBUTTON = 0x01
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_SHIFT = 0x10

ST_IDLE = 0
ST_ARMED = 1
ST_STROKING = 2

SUBCLASS_ID = 0x4E525442  # 'NRB'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
IMAGE_ORDINAL_FLAG64 = 0x8000000000000000

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
    ctypes.c_void_p,
    ctypes.c_void_p,
)


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]


user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetCursorInfo.restype = wintypes.BOOL
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.LoadCursorW.restype = ctypes.c_void_p
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProcType,
    ctypes.c_size_t,   # UINT_PTR
    ctypes.c_size_t,   # DWORD_PTR
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetProcAddress.restype = ctypes.c_void_p
kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

# ---------------- 路径与配置 ----------------

PLUGIN_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH: str = os.path.join(PLUGIN_DIR, "config.txt")

_enabled: bool = True

# ---- DIAG (temporary) ----
_DIAG_LOG: str = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_diag.log"


def _diag(text: str) -> None:
    try:
        with open(_DIAG_LOG, "a", encoding="utf-8") as f:
            f.write("%.3f %s\n" % (time.monotonic(), text))
    except Exception:
        pass


def _read_enabled() -> bool:
    """从磁盘读取启用状态（仅启动时调用一次）。"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return f.read(8).strip() != "0"
    except Exception:
        return True


def load_enabled() -> bool:
    """读取内存中的启用状态（按下判定时零开销、无文件竞争）。"""
    return _enabled


def save_enabled(value: bool) -> None:
    """更新内存并原子持久化启用状态，避免写入中断产生半截文件。"""
    global _enabled
    _enabled = bool(value)
    try:
        tmp_path = CONFIG_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("1\n" if _enabled else "0\n")
        os.replace(tmp_path, CONFIG_PATH)
    except Exception:
        pass


# ---------------- 语言与界面 ----------------


def detect_language() -> str:
    """中文 Windows 系统返回 'zh'，其他系统返回 'en'。"""
    try:
        lang_id: int = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if (lang_id & 0x3FF) == 0x04:
            return "zh"
    except Exception:
        pass
    return "en"


LANG: str = detect_language()
if LANG == "zh":
    PLUGIN_NAME: str = "禁用左键视图旋转"
    SWITCH_LABEL: str = "启用"
    SWITCH_INFO: str = "左键按住空白画布不再旋转视图；拖到模型上时笔刷从进入点正常起笔。"
else:
    PLUGIN_NAME = "Disable Left-Button View Rotation"
    SWITCH_LABEL = "Enable"
    SWITCH_INFO = (
        "Left-drag on blank canvas won't rotate the view; "
        "strokes start when the cursor reaches the mesh."
    )

PALETTE: str = "Zplugin:" + PLUGIN_NAME
BODY: str = PALETTE + ":Body"
SWITCH_PATH: str = BODY + ":" + SWITCH_LABEL


def on_toggle(sender: str, value: bool) -> None:
    """开关回调（官方签名 fn(sender, value)）。"""
    save_enabled(bool(value))
    if value:
        _iat["failed"] = False
        _sync_iat(2)  # 先以真实状态运行，随后由消息驱动更新
    else:
        _iat_restore()


def setup_ui() -> None:
    """创建插件界面：外层显示插件名，内层 Body 隐藏标题栏避免开关被遮挡。"""
    import zbrush.commands as zbc

    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)

    state: bool = load_enabled()
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(
        SWITCH_PATH,
        state,
        SWITCH_INFO,
        on_toggle,
        initially_disabled=False,
        width=1.0,
    )


# ---------------- IAT 钩子（GetAsyncKeyState） ----------------

# 存根机器码（x64）：参数 vKey 在 ECX。
#   vKey != 1（非左键）              -> 跳转真实函数
#   vKey == 1 且 flag == 0           -> 返回 0（左键“未按下”）
#   vKey == 1 且 flag != 0           -> 跳转真实函数
# 布局：代码 0x00..0x17，真实函数指针 0x18..0x1F，flag 字节 0x20。
_IAT_STUB_CODE: bytes = bytes([
    0x83, 0xF9, 0x01,                          # cmp ecx, 1
    0x75, 0x0D,                                # jne +0x0D -> forward
    0x80, 0x3D, 0x14, 0x00, 0x00, 0x00, 0x00,  # cmp byte ptr [rip+0x14], 0
    0x75, 0x04,                                # jne +0x04 -> forward
    0x31, 0xC0,                                # xor eax, eax
    0xC3,                                      # ret
    0xCC,                                      # int3（填充）
    0xFF, 0x25, 0x00, 0x00, 0x00, 0x00,        # jmp qword ptr [rip+0]
])

_iat = {
    "slot": 0,        # IAT 槽地址
    "original": 0,    # 原始函数指针
    "stub": 0,        # 存根可执行内存地址
    "flag": 0,        # flag 字节地址
    "active": False,  # 当前是否已接管
    "failed": False,  # 安装失败后不再反复尝试
}


def _read_u16(addr: int) -> int:
    return ctypes.c_uint16.from_address(addr).value


def _read_u32(addr: int) -> int:
    return ctypes.c_uint32.from_address(addr).value


def _read_u64(addr: int) -> int:
    return ctypes.c_uint64.from_address(addr).value


def _read_name(base: int, image_size: int, rva: int) -> bytes:
    """读取导入函数名（最多 64 字节，限制在镜像范围内）。"""
    if not (0 < rva < image_size):
        return b""
    avail = min(64, image_size - rva)
    if avail <= 0:
        return b""
    raw = ctypes.string_at(base + rva, avail)
    return raw.split(b"\x00", 1)[0]


def _in_image(image_size: int, rva: int, size: int = 8) -> bool:
    return 0 < rva and rva + size <= image_size


def _write_u64(addr: int, value: int) -> bool:
    """以原子 8 字节写入目标地址（临时改为可写并恢复原保护）。"""
    try:
        old = wintypes.DWORD()
        if not kernel32.VirtualProtect(ctypes.c_void_p(addr), 8, PAGE_READWRITE, ctypes.byref(old)):
            return False
        ctypes.c_uint64.from_address(addr).value = value
        kernel32.VirtualProtect(ctypes.c_void_p(addr), 8, old.value, ctypes.byref(old))
        return True
    except Exception:
        return False


def _find_get_async_key_state_slot() -> Tuple[Optional[int], Optional[int]]:
    """在 ZBrush.exe 导入表中定位 GetAsyncKeyState 的 IAT 槽。

    返回 (槽地址, 原始函数指针)；定位失败返回 (None, None)。
    """
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
        if not base or _read_u16(base) != 0x5A4D:  # 'MZ'
            return None, None
        pe = base + _read_u32(base + 0x3C)
        if _read_u32(pe) != 0x00004550:  # 'PE\0\0'
            return None, None
        opt = pe + 24
        if _read_u16(opt) != 0x20B:  # PE32+
            return None, None
        image_size = _read_u32(opt + 56)
        imp_rva = _read_u32(opt + 120)
        imp_size = _read_u32(opt + 124)
        if not (0 < imp_rva < image_size and 0 < imp_size < 0x10000):
            return None, None
        real = int(kernel32.GetProcAddress(user32._handle, b"GetAsyncKeyState") or 0)
        desc = base + imp_rva
        idx = 0
        while idx * 20 < imp_size:
            d = desc + idx * 20
            oft_rva = _read_u32(d)
            ft_rva = _read_u32(d + 16)
            if _in_image(image_size, ft_rva):
                i = 0
                while i < 2048:
                    slot = base + ft_rva + i * 8
                    if not _in_image(image_size, ft_rva + i * 8):
                        break
                    if oft_rva and _in_image(image_size, oft_rva + i * 8):
                        entry = _read_u64(base + oft_rva + i * 8)
                        if entry == 0:
                            break
                        if entry & IMAGE_ORDINAL_FLAG64:
                            i += 1
                            continue
                        byname = entry & ~IMAGE_ORDINAL_FLAG64
                        if _read_name(base, image_size, byname + 2) == b"GetAsyncKeyState":
                            return slot, _read_u64(slot)
                    else:
                        # 无 INT（绑定导入）：按运行时指针识别。
                        val = _read_u64(slot)
                        if val == 0:
                            break
                        if val == real:
                            return slot, val
                    i += 1
            idx += 1
    except Exception:
        return None, None
    return None, None


def _iat_install() -> bool:
    """安装 IAT 钩子：分配存根并把 IAT 槽指向存根。"""
    if _iat["active"]:
        return True
    slot, original = _find_get_async_key_state_slot()
    if not slot:
        _iat["failed"] = True
        return False
    real = int(kernel32.GetProcAddress(user32._handle, b"GetAsyncKeyState") or 0)
    if not real or original != real:
        _iat["failed"] = True
        return False
    page = kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        _iat["failed"] = True
        return False
    page = int(page)
    ctypes.memmove(page, _IAT_STUB_CODE, len(_IAT_STUB_CODE))
    ctypes.memmove(page + 0x18, struct.pack("<Q", real), 8)
    ctypes.c_ubyte.from_address(page + 0x20).value = 1
    if not _write_u64(slot, page):
        _iat["failed"] = True
        return False
    _iat.update(slot=slot, original=original, stub=page, flag=page + 0x20, active=True)
    return True


def _iat_restore() -> None:
    """恢复 IAT 槽为原始函数指针（存根内存保留，可再次启用）。"""
    if not _iat["active"]:
        return
    slot = _iat["slot"]
    if slot and _read_u64(slot) == _iat["stub"]:
        _write_u64(slot, _iat["original"])
    _iat["active"] = False


def _iat_set_block(block: bool) -> None:
    """切换存根行为：block=True 时对 VK_LBUTTON 返回 0。"""
    if _iat["active"]:
        ctypes.c_ubyte.from_address(_iat["flag"]).value = 0 if block else 1


def _sync_iat(kind: int) -> None:
    """按画布判定同步钩子状态：0=空白画布（屏蔽左键），1/2=真实状态。"""
    if not load_enabled():
        _iat_restore()
        return
    if _iat["failed"]:
        _diag("IAT failed-skip kind=%d" % kind)
        return
    if not _iat["active"]:
        if _iat_install():
            _iat_set_block(kind == 0)
            _diag("IAT installed slot=%#x stub=%#x" % (_iat["slot"], _iat["stub"]))
        return
    block = kind == 0
    newflag = 0 if block else 1
    if _iat.get("lastflag") != newflag:
        _iat["lastflag"] = newflag
        _diag("IAT flag=%d kind=%d" % (newflag, kind))
    _iat_set_block(block)


# ---------------- 画布判定（官方 zbrush.commands API） ----------------


_last_kind: int = 2
_last_kind_time: float = 0.0
_last_kind_pos: Optional[Tuple[float, float]] = None


def _query_kind() -> int:
    """当前画布状态：0=空白画布，1=模型，2=其他/不可判定，3=查询异常。"""
    global _last_kind, _last_kind_time, _last_kind_pos
    try:
        import zbrush.commands as zbc

        if not load_enabled():
            return 2
        if not bool(zbc.get("Transform:Edit")):
            _diag("Q not-edit")
            return 2
        doc_w: float = zbc.get("Document:Width")
        doc_h: float = zbc.get("Document:Height")
        # 官方 API 直接返回画布坐标，无需窗口/屏幕坐标换算，DPI 缩放不影响。
        px, py = zbc.get_mouse_pos(global_coordinates=False)
        if not (0 <= px < doc_w and 0 <= py < doc_h):
            _diag("Q out pos=(%.0f,%.0f) doc=(%.0f,%.0f)" % (px, py, doc_w, doc_h))
            return 2
        # 材质索引 0 = 空白画布；不比较颜色。
        mat: float = float(zbc.pixol_pick(5, px, py))
        nx: float = float(zbc.pixol_pick(6, px, py))
        ny: float = float(zbc.pixol_pick(7, px, py))
        nz: float = float(zbc.pixol_pick(8, px, py))
        # 笔画进行中材质分量可能失效，退化为法线判定。
        kind: int = 1 if (mat != 0.0 or abs(nx) > 0.05 or abs(ny) > 0.05 or abs(nz) > 0.05) else 0
        if kind != _last_kind or _state == ST_STROKING:
            _diag("Q kind=%d mat=%.1f n=(%.2f,%.2f,%.2f) pos=(%.0f,%.0f)" % (
                kind, mat, nx, ny, nz, px, py))
        _last_kind = kind
        _last_kind_time = time.monotonic()
        _last_kind_pos = (px, py)
        return kind
    except Exception as e:
        _diag("Q EXC %r" % (e,))
        return 3


def _fallback_kind() -> int:
    """查询失败时的安全兜底：仅当光标基本未移动且最近成功判定仍新鲜时复用。"""
    try:
        import zbrush.commands as zbc

        px, py = zbc.get_mouse_pos(global_coordinates=False)
    except Exception:
        return 2
    if (
        _last_kind in (0, 1)
        and _last_kind_pos is not None
        and time.monotonic() - _last_kind_time <= 0.25
        and abs(px - _last_kind_pos[0]) <= 25
        and abs(py - _last_kind_pos[1]) <= 25
    ):
        return _last_kind
    return 2


def _robust_kind() -> int:
    """带重试与兜底的画布判定：0=空白画布，1=模型，2=其他/不可判定。"""
    kind = _query_kind()
    if kind == 3:
        kind = _query_kind()
    if kind == 3:
        kind = _fallback_kind()
    return kind if kind in (0, 1) else 2


def _point_kind() -> int:
    """0=空白画布，1=模型，2=其他（不处理）。"""
    return _robust_kind()


def _kind_at(px: float, py: float) -> int:
    """查询指定画布坐标的状态：0=空白，1=模型，2/3=其他或异常。"""
    try:
        import zbrush.commands as zbc

        doc_w: float = zbc.get("Document:Width")
        doc_h: float = zbc.get("Document:Height")
        if not (0 <= px < doc_w and 0 <= py < doc_h):
            return 2
        return 0 if float(zbc.pixol_pick(5, px, py)) == 0.0 else 1
    except Exception:
        return 3


def _send_up_clear(hwnd, lparam) -> None:
    """补发抬起，清除 ZBrush 的“按键按下”状态（同步失败退化为异步）。"""
    try:
        user32.SendMessageW(
            hwnd, WM_LBUTTONUP, _button_flags() & ~MK_LBUTTON, lparam)
    except Exception:
        user32.PostMessageW(
            hwnd, WM_LBUTTONUP, _button_flags() & ~MK_LBUTTON, lparam)


def _should_cancel() -> bool:
    """按下点是否为可取消的空白画布。"""
    return _robust_kind() == 0


# ---------------- 光标辅助 ----------------


def _load_standard_cursors() -> list:
    """ZBrush 界面控件使用的标准系统光标句柄集合。"""
    ids = (
        32512, 32513, 32514, 32515, 32516,  # arrow, ibeam, wait, cross, uparrow
        32642, 32643, 32644, 32645, 32646,  # size cursors
        32648, 32649, 32650, 32651,          # no, hand, appstarting, help
        32671, 32672,                        # pin, person
    )
    return [h for h in (user32.LoadCursorW(None, i) for i in ids) if h]


_STD_CURSORS: list = _load_standard_cursors()


def _current_cursor() -> int:
    """返回当前光标句柄（0 表示隐藏/未知）。"""
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if user32.GetCursorInfo(ctypes.byref(ci)):
        return int(ci.hCursor or 0)
    return 0


def _is_standard_ui_cursor(hcursor: int) -> bool:
    if hcursor == 0:
        return False
    return hcursor in _STD_CURSORS


# ---------------- 窗口子类化 ----------------


_state: int = ST_IDLE
_stroke_last_pos: Optional[Tuple[float, float]] = None
_mesh_hits: int = 0
_last_iat_sync_pos: Optional[Tuple[float, float]] = None
_last_iat_sync_time: float = 0.0


def _button_flags() -> int:
    flags: int = MK_LBUTTON
    if user32.GetKeyState(VK_CONTROL) & 0x8000:
        flags |= MK_CONTROL
    if user32.GetKeyState(VK_SHIFT) & 0x8000:
        flags |= MK_SHIFT
    return flags


def _sync_iat_on_move(lparam: int) -> None:
    """IDLE 状态下低频同步 IAT：光标移动明显时提前切换屏蔽状态。"""
    global _last_iat_sync_pos, _last_iat_sync_time
    try:
        px: float = float(lparam & 0xFFFF)
        py: float = float((lparam >> 16) & 0xFFFF)
        now: float = time.monotonic()
        pos = _last_iat_sync_pos
        if pos is None:
            _last_iat_sync_pos = (px, py)
            _last_iat_sync_time = now
            _sync_iat(_point_kind())
            return
        if now - _last_iat_sync_time >= 0.03 and (
            abs(px - pos[0]) >= 4.0 or abs(py - pos[1]) >= 4.0
        ):
            _last_iat_sync_pos = (px, py)
            _last_iat_sync_time = now
            _sync_iat(_point_kind())
    except Exception:
        pass


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    """子类消息处理：仅在空白画布按下时取消旋转，其余原样放行。"""
    global _state, _stroke_last_pos, _mesh_hits

    # 按钮已松开但状态未复位时，清理状态机。
    if (
        _state != ST_IDLE
        and msg not in (WM_LBUTTONUP, WM_LBUTTONDBLCLK)
        and not (user32.GetKeyState(VK_LBUTTON) & 0x8000)
    ):
        prev = _state
        _state = ST_IDLE
        _mesh_hits = 0
        _sync_iat(2)
        _diag("GUARD %d->IDLE msg=0x%04x" % (prev, msg))
        if prev == ST_STROKING:
            user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, 0)

    if _state == ST_ARMED:
        if msg == WM_MOUSEMOVE:
            kind = _point_kind()
            _sync_iat(kind)
            _diag("M armed kind=%d hits=%d pos=(%d,%d)" % (
                kind, _mesh_hits, lparam & 0xFFFF, (lparam >> 16) & 0xFFFF))
            if kind == 1:
                # 连续两次确认光标在模型上才补发按下，避免在边界帧误起笔
                # （ZBrush 一旦有按下状态、光标落在空白，就会自己旋转）。
                _mesh_hits += 1
                if _mesh_hits >= 2:
                    _mesh_hits = 0
                    _state = ST_STROKING
                    _stroke_last_pos = _last_kind_pos
                    _diag("INJECT DOWN w=0x%x pos=(%d,%d)" % (
                        _button_flags(), lparam & 0xFFFF, (lparam >> 16) & 0xFFFF))
                    user32.SendMessageW(hwnd, WM_LBUTTONDOWN, _button_flags(), lparam)
                    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
                return 0
            elif kind == 2:
                # 进入界面控件/未知区域：放弃本次拖拽。
                _state = ST_IDLE
                _mesh_hits = 0
            else:
                # kind == 0（仍为空白）：重置确认计数。
                _mesh_hits = 0
            # 吞掉移动，ZBrush 收不到移动就不会旋转。
            return 0
        if msg in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            _state = ST_IDLE
            _mesh_hits = 0
            _sync_iat(2)
            _diag("ARMED %s -> IDLE" % ("UP" if msg == WM_LBUTTONUP else "DBLCLK"))
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    elif _state == ST_STROKING:
        if msg == WM_MOUSEMOVE:
            kind = _point_kind()
            _sync_iat(kind)
            _diag("M stroke kind=%d pos=(%d,%d)" % (
                kind, lparam & 0xFFFF, (lparam >> 16) & 0xFFFF))
            if kind == 0:
                # 已到空白：立即补发抬起清除按下状态，回到接管。
                _diag("stroke->blank send UP")
                _send_up_clear(hwnd, lparam)
                _stroke_last_pos = None
                _mesh_hits = 0
                _state = ST_ARMED
                return 0
            if kind == 2:
                # 进入界面控件/未知区域：结束本次笔刷。
                _diag("stroke abort kind2")
                _stroke_last_pos = None
                _mesh_hits = 0
                _state = ST_IDLE
                return 0
            # kind == 1：仍在模型上。沿移动方向提前探测，若即将离开模型，
            # 先完成本段笔刷再补发抬起，让 ZBrush 永远不带“按下状态”出现在空白。
            near_edge = False
            cur = _last_kind_pos
            last = _stroke_last_pos
            if cur is not None and last is not None:
                dx = cur[0] - last[0]
                dy = cur[1] - last[1]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > 1.0:
                    ux = dx / dist
                    uy = dy / dist
                    probe_kind = _kind_at(cur[0] + ux * 20.0, cur[1] + uy * 20.0)
                    if probe_kind != 1:
                        near_edge = True
            _stroke_last_pos = cur
            if near_edge:
                _diag("stroke near-edge UP+ARMED")
                r = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
                _send_up_clear(hwnd, lparam)
                _stroke_last_pos = None
                _mesh_hits = 0
                _state = ST_ARMED
                return r
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        if msg == WM_LBUTTONUP:
            r = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            _stroke_last_pos = None
            _mesh_hits = 0
            _state = ST_IDLE
            _sync_iat(2)
            _diag("STROKING UP -> IDLE")
            return r
        if msg == WM_LBUTTONDBLCLK:
            _diag("STROKING DBLCLK -> IDLE")
            _stroke_last_pos = None
            _mesh_hits = 0
            _state = ST_IDLE
    elif msg == WM_MOUSEMOVE:
        # IDLE：低频预同步，保证按下时钩子状态已经就位。
        _sync_iat_on_move(lparam)
    elif msg in (WM_LBUTTONDOWN, WM_LBUTTONDBLCLK):
        # 修饰键操作（Ctrl/Shift/Alt + 左键）原样交给 ZBrush。
        if (wparam & (MK_CONTROL | MK_SHIFT)) or (user32.GetKeyState(VK_MENU) & 0x8000):
            _sync_iat(2)
            _diag("PRESS modifier forward")
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        cursor = _current_cursor()
        std = _is_standard_ui_cursor(cursor)
        if std:
            # 标准光标 = 界面控件，原样放行。
            _sync_iat(2)
            _diag("PRESS ui-cursor forward")
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        kind = _robust_kind()
        _diag("PRESS msg=0x%04x w=0x%x cursor=%d std=%d kind=%d phys=%d" % (
            msg, wparam, cursor, int(std), kind,
            int(bool(user32.GetKeyState(VK_LBUTTON) & 0x8000))))
        if kind == 2:
            # 画布外 / 非 Edit / 不可判定：原样放行，保持 ZBrush 原生行为。
            _sync_iat(2)
            _diag("PRESS kind2 forward")
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        # Edit 模式画布内的按下（空白或模型）一律吞掉，由本插件接管：
        # - 空白：进入 ARMED，进入模型时补发按下；
        # - 模型：立即在原位置补发按下起笔（避免 ZBrush 原生拖到空白时旋转）。
        _sync_iat(kind)
        _state = ST_ARMED
        _stroke_last_pos = None
        _mesh_hits = 1 if kind == 1 else 0
        _diag("PRESS swallow kind=%d -> ARMED" % kind)
        return 0

    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProcType
def _subclass_proc(hwnd, msg, wparam, lparam, u_id, ref_data) -> int:
    try:
        return _handle_message(hwnd, msg, wparam, lparam)
    except Exception as e:
        _diag("EXC msg=0x%04x err=%r" % (msg, e))
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


# 保持回调引用，防止被垃圾回收。
_subclass_callback = _subclass_proc


def _install_subclass() -> bool:
    """查找本进程的 ZBrush 主窗口并安装子类（多实例安全）。"""
    hwnd = user32.FindWindowW("ZBrush", None)
    if hwnd:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != os.getpid():
            hwnd = None
    if not hwnd:
        return False
    return bool(comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0))


# ---------------- 入口 ----------------


def main() -> None:
    """ZBrush 启动时执行插件入口。"""
    try:
        with open(_DIAG_LOG, "w", encoding="utf-8") as f:
            f.write("=== plugin loaded ===\n")
    except Exception:
        pass
    global _enabled
    if not os.path.isfile(CONFIG_PATH):
        save_enabled(True)
    else:
        _enabled = _read_enabled()
    _diag("enabled=%s lang=%s" % (load_enabled(), LANG))
    try:
        setup_ui()
    except Exception:
        pass

    # 主窗口在 Python 启动脚本执行时可能尚未就绪，做短暂重试。
    installed = _install_subclass()
    for _ in range(20):
        if installed:
            break
        time.sleep(0.5)
        installed = _install_subclass()

    # 启用状态下安装 IAT 钩子（先以真实状态运行，由消息驱动切换）。
    if load_enabled():
        _sync_iat(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
