#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "comctl32.lib")

/*
 * NoLeftClickRotation.dll - Disable Left-Button View Rotation.
 *
 * Official ZPlugin: the .zsc creates the UI and a canvas-state detection
 * loop (MouseHPos/VPos + PixolPick material index, same logic as the
 * Python build) and pushes the state into this DLL via UpdateState.
 * All input interception lives here:
 *
 * 1. IAT hook: ZBrush.exe's imported GetAsyncKeyState is pointed at a tiny
 *    machine-code stub. On blank canvas it returns 0 for VK_LBUTTON (view
 *    rotation and Alt-pan cannot start); on the mesh it returns the real
 *    state so sculpting is unaffected. Ctrl is preserved for masking.
 * 2. Window subclass: press/release state machine (blank press swallowed,
 *    fresh down injected when the cursor reaches the mesh, mesh press
 *    forwarded natively).
 */

#define SUBCLASS_ID 0x4E525442 /* 'NRB' */

enum {
    ST_IDLE = 0,
    ST_ARMED = 1,    /* blank press swallowed; waiting for the cursor to reach the mesh */
    ST_STROKING = 2  /* stroke active */
};

enum { ZS_OTHER = 0, ZS_BLANK = 1, ZS_MESH = 2 };  /* state pushed by the .zsc */
enum { KIND_OTHER = 0, KIND_BLANK = 1, KIND_MESH = 2 };

static HWND g_hwnd = NULL;
static wchar_t g_configPath[MAX_PATH];

static volatile LONG g_state = ST_IDLE;
static volatile LONG g_armedHits = 0;
static volatile LONG g_enabled = 1;
static volatile LONG g_zsState = ZS_OTHER;
static volatile LONG g_zsTicks = 0;

/* Forward declaration so set_paths() can locate this module. */
__declspec(dllexport) float Install(const char *optional_text,
                                    double optional_number,
                                    char *input_memory,
                                    char *output_memory);

/* ---- TEMP debug log (removed after diagnosis) ---- */
static void dbg_log(const char *text)
{
    HANDLE h = CreateFileW(L"C:\\Users\\liuwenbo\\AppData\\Local\\Temp\\nlr_zsdll.log",
                           GENERIC_WRITE, FILE_SHARE_READ, NULL,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE)
        return;
    SetFilePointer(h, 0, NULL, FILE_END);
    DWORD wr = 0;
    WriteFile(h, text, (DWORD)strlen(text), &wr, NULL);
    CloseHandle(h);
}

/* ---- IAT hook (GetAsyncKeyState) ---- */

static const BYTE IAT_STUB_CODE[24] = {
    0x83, 0xF9, 0x01,                          /* cmp ecx, 1 */
    0x75, 0x0D,                                /* jne +0x0D -> forward */
    0x80, 0x3D, 0x14, 0x00, 0x00, 0x00, 0x00,  /* cmp byte [rip+0x14], 0 */
    0x75, 0x04,                                /* jne +0x04 -> forward */
    0x31, 0xC0,                                /* xor eax, eax */
    0xC3,                                      /* ret */
    0xCC,                                      /* int3 (padding) */
    0xFF, 0x25, 0x00, 0x00, 0x00, 0x00         /* jmp qword [rip+0] */
};

typedef struct {
    ULONGLONG slot;
    ULONGLONG original;
    ULONGLONG stub;
    BYTE *flag;
    int active;
} IatState;

static IatState g_iat;

static WORD rd16(ULONGLONG a)
{
    WORD v = 0;
    memcpy(&v, (const void *)(UINT_PTR)a, sizeof(v));
    return v;
}

static DWORD rd32(ULONGLONG a)
{
    DWORD v = 0;
    memcpy(&v, (const void *)(UINT_PTR)a, sizeof(v));
    return v;
}

static ULONGLONG rd64(ULONGLONG a)
{
    ULONGLONG v = 0;
    memcpy(&v, (const void *)(UINT_PTR)a, sizeof(v));
    return v;
}

static int write_u64(ULONGLONG addr, ULONGLONG value)
{
    DWORD old = 0;
    if (!VirtualProtect((void *)(UINT_PTR)addr, 8, PAGE_READWRITE, &old))
        return 0;
    *(volatile ULONGLONG *)(UINT_PTR)addr = value;
    VirtualProtect((void *)(UINT_PTR)addr, 8, old, &old);
    return 1;
}

static int find_get_async_key_state_slot(ULONGLONG *slot_out,
                                         ULONGLONG *orig_out)
{
    ULONGLONG base = (ULONGLONG)(UINT_PTR)GetModuleHandleW(NULL);
    if (base == 0 || rd16(base) != 0x5A4D)
        return 0;
    ULONGLONG pe = base + rd32(base + 0x3C);
    if (rd32(pe) != 0x00004550)
        return 0;
    ULONGLONG opt = pe + 24;
    if (rd16(opt) != 0x20B)
        return 0;
    DWORD image_size = rd32(opt + 56);
    DWORD imp_rva = rd32(opt + 120);
    DWORD imp_size = rd32(opt + 124);
    if (!(imp_rva > 0 && imp_rva < image_size &&
          imp_size > 0 && imp_size < 0x10000))
        return 0;
    ULONGLONG real = (ULONGLONG)(UINT_PTR)
        GetProcAddress(GetModuleHandleW(L"user32.dll"), "GetAsyncKeyState");
    ULONGLONG desc = base + imp_rva;
    for (DWORD idx = 0; idx * 20 < imp_size; ++idx) {
        ULONGLONG d = desc + idx * 20;
        DWORD oft_rva = rd32(d);
        DWORD ft_rva = rd32(d + 16);
        if (ft_rva == 0 || ft_rva >= image_size)
            continue;
        for (int i = 0; i < 2048; ++i) {
            ULONGLONG slot = base + ft_rva + i * 8;
            if (ft_rva + i * 8 >= image_size ||
                ft_rva + i * 8 + 8 > image_size)
                break;
            if (oft_rva && oft_rva + i * 8 + 8 <= image_size) {
                ULONGLONG entry = rd64(base + oft_rva + i * 8);
                if (entry == 0)
                    break;
                if (entry & 0x8000000000000000ULL)
                    continue;
                DWORD byname = (DWORD)(entry & 0x7FFFFFFFFFFFFFFFULL);
                if (byname + 2 < image_size) {
                    const char *p =
                        (const char *)(UINT_PTR)(base + byname + 2);
                    if (strncmp(p, "GetAsyncKeyState", 16) == 0) {
                        *slot_out = slot;
                        *orig_out = rd64(slot);
                        return 1;
                    }
                }
            } else {
                ULONGLONG val = rd64(slot);
                if (val == 0)
                    break;
                if (val == real) {
                    *slot_out = slot;
                    *orig_out = val;
                    return 1;
                }
            }
        }
    }
    return 0;
}

static int iat_install(void)
{
    if (g_iat.active)
        return 1;
    ULONGLONG slot = 0, original = 0;
    if (!find_get_async_key_state_slot(&slot, &original))
        return 0;
    ULONGLONG real = (ULONGLONG)(UINT_PTR)
        GetProcAddress(GetModuleHandleW(L"user32.dll"), "GetAsyncKeyState");
    if (real == 0 || original != real)
        return 0;
    ULONGLONG page = (ULONGLONG)(UINT_PTR)VirtualAlloc(
        NULL, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (page == 0)
        return 0;
    memcpy((void *)(UINT_PTR)page, IAT_STUB_CODE, sizeof(IAT_STUB_CODE));
    memcpy((void *)(UINT_PTR)(page + 0x18), &real, 8);
    *(volatile BYTE *)(UINT_PTR)(page + 0x20) = 1;
    if (!write_u64(slot, page)) {
        VirtualFree((void *)(UINT_PTR)page, 0, MEM_RELEASE);
        return 0;
    }
    g_iat.slot = slot;
    g_iat.original = original;
    g_iat.stub = page;
    g_iat.flag = (BYTE *)(UINT_PTR)(page + 0x20);
    g_iat.active = 1;
    return 1;
}

static void iat_restore(void)
{
    if (!g_iat.active)
        return;
    if (g_iat.slot && rd64(g_iat.slot) == g_iat.stub)
        write_u64(g_iat.slot, g_iat.original);
    g_iat.active = 0;
}

static void iat_set_block(int block)
{
    if (g_iat.active && g_iat.flag != NULL)
        *(volatile BYTE *)g_iat.flag = block ? 0 : 1;
}

/* ---- config ---- */

static void set_paths(void)
{
    HMODULE self = NULL;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                       GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCWSTR)(void *)&Install, &self);
    if (self == NULL)
        return;
    GetModuleFileNameW(self, g_configPath, MAX_PATH);
    wchar_t *slash = wcsrchr(g_configPath, L'\\');
    if (slash == NULL)
        return;
    slash[1] = L'\0';
    wcsncat_s(g_configPath, MAX_PATH, L"config.txt", _TRUNCATE);
}

static int read_enabled(void)
{
    if (g_configPath[0] == L'\0')
        return 1;
    HANDLE h = CreateFileW(g_configPath, GENERIC_READ, FILE_SHARE_READ,
                           NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE)
        return 1;
    char buf[16] = {0};
    DWORD rd = 0;
    ReadFile(h, buf, sizeof(buf) - 1, &rd, NULL);
    CloseHandle(h);
    return (buf[0] == '0') ? 0 : 1;
}

static void write_enabled(int enabled)
{
    if (g_configPath[0] == L'\0')
        return;
    const char *out = enabled ? "1\n" : "0\n";
    HANDLE hw = CreateFileW(g_configPath, GENERIC_WRITE, 0, NULL,
                            CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hw == INVALID_HANDLE_VALUE)
        return;
    DWORD wr = 0;
    WriteFile(hw, out, (DWORD)strlen(out), &wr, NULL);
    CloseHandle(hw);
}

/* ---- window lookup (multi-instance safe) ---- */

typedef struct {
    HWND hwnd;
    DWORD pid;
} FindCtx;

static BOOL CALLBACK enum_proc(HWND hwnd, LPARAM lp)
{
    FindCtx *ctx = (FindCtx *)lp;
    wchar_t cls[256];
    if (GetClassNameW(hwnd, cls, 256) && wcscmp(cls, L"ZBrush") == 0) {
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);
        if (pid == ctx->pid) {
            ctx->hwnd = hwnd;
            return FALSE;
        }
    }
    return TRUE;
}

static HWND find_zbrush_window(void)
{
    FindCtx ctx = { NULL, GetCurrentProcessId() };
    EnumWindows(enum_proc, (LPARAM)&ctx);
    return ctx.hwnd;
}

/* ---- detection + flag ---- */

static int ctrl_down(void)
{
    return (GetKeyState(VK_CONTROL) & 0x8000) != 0;
}

static int is_standard_ui_cursor(HCURSOR h)
{
    static HCURSOR std[16];
    static int inited = 0;
    if (!inited) {
        inited = 1;
        std[0] = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
        std[1] = LoadCursorW(NULL, (LPCWSTR)IDC_IBEAM);
        std[2] = LoadCursorW(NULL, (LPCWSTR)IDC_WAIT);
        std[3] = LoadCursorW(NULL, (LPCWSTR)IDC_CROSS);
        std[4] = LoadCursorW(NULL, (LPCWSTR)IDC_UPARROW);
        std[5] = LoadCursorW(NULL, (LPCWSTR)IDC_SIZENWSE);
        std[6] = LoadCursorW(NULL, (LPCWSTR)IDC_SIZENESW);
        std[7] = LoadCursorW(NULL, (LPCWSTR)IDC_SIZEWE);
        std[8] = LoadCursorW(NULL, (LPCWSTR)IDC_SIZENS);
        std[9] = LoadCursorW(NULL, (LPCWSTR)IDC_SIZEALL);
        std[10] = LoadCursorW(NULL, (LPCWSTR)IDC_NO);
        std[11] = LoadCursorW(NULL, (LPCWSTR)IDC_HAND);
        std[12] = LoadCursorW(NULL, (LPCWSTR)IDC_APPSTARTING);
        std[13] = LoadCursorW(NULL, (LPCWSTR)IDC_HELP);
        std[14] = LoadCursorW(NULL, (LPCWSTR)MAKEINTRESOURCE(32671));
        std[15] = LoadCursorW(NULL, (LPCWSTR)MAKEINTRESOURCE(32672));
    }
    if (h == NULL)
        return 0;
    for (int i = 0; i < 16; ++i) {
        if (std[i] != NULL && std[i] == h)
            return 1;
    }
    return 0;
}

/* State pushed by the .zsc loop: 0=other, 1=blank, 2=mesh.
 * Standard UI cursor (interface control) is always "other". */
static int state_kind(void)
{
    CURSORINFO ci;
    ci.cbSize = sizeof(ci);
    if (GetCursorInfo(&ci) && ci.hCursor != NULL &&
        is_standard_ui_cursor(ci.hCursor))
        return KIND_OTHER;
    LONG s = g_zsState;
    if (s == ZS_BLANK)
        return KIND_BLANK;
    if (s == ZS_MESH)
        return KIND_MESH;
    return KIND_OTHER;
}

/* Blank canvas + Ctrl not held -> block left button (rotation / Alt-pan). */
static void sync_flag(void)
{
    int block = g_enabled && g_zsState == ZS_BLANK && !ctrl_down();
    static int last_block = -1;
    if (last_block != block) {
        last_block = block;
        char line[128];
        _snprintf_s(line, sizeof(line), _TRUNCATE,
                    "flag=%d state=%ld\n", block, g_zsState);
        dbg_log(line);
    }
    iat_set_block(block);
}

/* ---- idle throttle (like the Python build: >=4px and >=30ms) ---- */

static volatile LONG g_lastX = 0, g_lastY = 0, g_lastTick = 0;

static void idle_sync(LPARAM lParam)
{
    LONG x = (LONG)(short)LOWORD(lParam);
    LONG y = (LONG)(short)HIWORD(lParam);
    DWORD now = GetTickCount();
    if (g_lastTick == 0) {
        g_lastX = x;
        g_lastY = y;
        g_lastTick = (LONG)now;
        sync_flag();
        return;
    }
    if ((DWORD)(now - (DWORD)g_lastTick) >= 30 &&
        (abs(x - g_lastX) >= 4 || abs(y - g_lastY) >= 4)) {
        g_lastX = x;
        g_lastY = y;
        g_lastTick = (LONG)now;
        sync_flag();
    }
}

static WPARAM current_button_flags(void)
{
    WPARAM w = MK_LBUTTON;
    if (GetKeyState(VK_CONTROL) & 0x8000)
        w |= MK_CONTROL;
    if (GetKeyState(VK_SHIFT) & 0x8000)
        w |= MK_SHIFT;
    return w;
}

/* ---- subclass: press/release state machine ---- */

static LRESULT CALLBACK SubclassProc(HWND hWnd, UINT msg, WPARAM wParam,
                                     LPARAM lParam, UINT_PTR uIdSubclass,
                                     DWORD_PTR dwRefData)
{
    (void)uIdSubclass;
    (void)dwRefData;

    if (g_state != ST_IDLE &&
        msg != WM_LBUTTONUP && msg != WM_LBUTTONDBLCLK &&
        !(GetKeyState(VK_LBUTTON) & 0x8000)) {
        LONG prev = InterlockedExchange(&g_state, ST_IDLE);
        InterlockedExchange(&g_armedHits, 0);
        iat_set_block(0);
        if (prev == ST_STROKING)
            PostMessageW(hWnd, WM_LBUTTONUP, 0, 0);
    }

    if (g_state == ST_ARMED) {
        if (msg == WM_MOUSEMOVE) {
            int kind = state_kind();
            sync_flag();
            if (kind == KIND_MESH) {
                if (InterlockedIncrement(&g_armedHits) >= 2) {
                    InterlockedExchange(&g_armedHits, 0);
                    InterlockedExchange(&g_state, ST_STROKING);
                    SendMessageW(hWnd, WM_LBUTTONDOWN,
                                 current_button_flags(), lParam);
                    return DefSubclassProc(hWnd, msg, wParam, lParam);
                }
                return 0;
            } else if (kind == KIND_OTHER) {
                InterlockedExchange(&g_state, ST_IDLE);
                InterlockedExchange(&g_armedHits, 0);
            } else {
                InterlockedExchange(&g_armedHits, 0);
            }
            return 0;
        }
        if (msg == WM_LBUTTONUP || msg == WM_LBUTTONDBLCLK) {
            InterlockedExchange(&g_state, ST_IDLE);
            InterlockedExchange(&g_armedHits, 0);
            iat_set_block(0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
    } else if (g_state == ST_STROKING) {
        if (msg == WM_MOUSEMOVE) {
            sync_flag();
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        if (msg == WM_LBUTTONUP) {
            LRESULT r = DefSubclassProc(hWnd, msg, wParam, lParam);
            InterlockedExchange(&g_state, ST_IDLE);
            InterlockedExchange(&g_armedHits, 0);
            iat_set_block(0);
            return r;
        }
        if (msg == WM_LBUTTONDBLCLK) {
            InterlockedExchange(&g_state, ST_IDLE);
            InterlockedExchange(&g_armedHits, 0);
        }
    } else if (msg == WM_LBUTTONDOWN || msg == WM_LBUTTONDBLCLK) {
        CURSORINFO ci;
        ci.cbSize = sizeof(ci);
        int ui_cursor = 0;
        if (GetCursorInfo(&ci) && ci.hCursor != NULL)
            ui_cursor = is_standard_ui_cursor(ci.hCursor);
        if (ui_cursor) {
            iat_set_block(0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        if (ctrl_down()) {
            iat_set_block(0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        int kind = state_kind();
        int alt = (GetKeyState(VK_MENU) & 0x8000) != 0;
        int shift = (GetKeyState(VK_SHIFT) & 0x8000) != 0;
        {
            char line[128];
            _snprintf_s(line, sizeof(line), _TRUNCATE,
                        "press kind=%d alt=%d shift=%d ui=%d\n",
                        kind, alt, shift, ui_cursor);
            dbg_log(line);
        }
        if (alt) {
            if (kind == KIND_BLANK) {
                sync_flag();
                return 0; /* Alt+left on blank (pan): disabled */
            }
            if (kind == KIND_MESH) {
                sync_flag();
                InterlockedExchange(&g_state, ST_STROKING);
                InterlockedExchange(&g_armedHits, 0);
                return DefSubclassProc(hWnd, msg, wParam, lParam);
            }
            iat_set_block(0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        if (shift) {
            iat_set_block(0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        if (kind == KIND_OTHER) {
            iat_set_block(0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        if (kind == KIND_MESH) {
            sync_flag();
            InterlockedExchange(&g_state, ST_STROKING);
            InterlockedExchange(&g_armedHits, 0);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        /* blank canvas press: swallow, arm; inject down when reaching mesh */
        sync_flag();
        InterlockedExchange(&g_state, ST_ARMED);
        InterlockedExchange(&g_armedHits, 0);
        return 0;
    } else if (msg == WM_MOUSEMOVE) {
        idle_sync(lParam);
    }

    return DefSubclassProc(hWnd, msg, wParam, lParam);
}

/* ---- exported API (official [FileExecute] signature) ---- */

__declspec(dllexport) float Install(const char *optional_text,
                                    double optional_number,
                                    char *input_memory,
                                    char *output_memory)
{
    (void)optional_text;
    (void)optional_number;
    (void)input_memory;
    (void)output_memory;

    if (g_hwnd != NULL && IsWindow(g_hwnd))
        return 1.0f;

    set_paths();
    InterlockedExchange(&g_enabled, read_enabled());
    InterlockedExchange(&g_state, ST_IDLE);
    InterlockedExchange(&g_armedHits, 0);
    InterlockedExchange(&g_zsState, ZS_OTHER);
    InterlockedExchange(&g_zsTicks, 0);
    g_lastTick = 0;

    HWND h = find_zbrush_window();
    if (h == NULL)
        return 0.0f;
    if (!SetWindowSubclass(h, SubclassProc, SUBCLASS_ID, 0))
        return 0.0f;
    g_hwnd = h;

    if (g_enabled)
        iat_install();
    {
        char line[128];
        _snprintf_s(line, sizeof(line), _TRUNCATE,
                    "install ok iat=%d\n", g_iat.active);
        dbg_log(line);
    }
    sync_flag();
    return 1.0f;
}

__declspec(dllexport) float Uninstall(const char *optional_text,
                                      double optional_number,
                                      char *input_memory,
                                      char *output_memory)
{
    (void)optional_text;
    (void)optional_number;
    (void)input_memory;
    (void)output_memory;
    iat_restore();
    if (g_hwnd != NULL) {
        if (IsWindow(g_hwnd))
            RemoveWindowSubclass(g_hwnd, SubclassProc, SUBCLASS_ID);
        g_hwnd = NULL;
    }
    InterlockedExchange(&g_state, ST_IDLE);
    InterlockedExchange(&g_armedHits, 0);
    return 1.0f;
}

__declspec(dllexport) float IsInstalled(const char *optional_text,
                                        double optional_number,
                                        char *input_memory,
                                        char *output_memory)
{
    (void)optional_text;
    (void)optional_number;
    (void)input_memory;
    (void)output_memory;
    return (g_hwnd != NULL && IsWindow(g_hwnd)) ? 1.0f : 0.0f;
}

__declspec(dllexport) float SetEnabled(const char *optional_text,
                                       double optional_number,
                                       char *input_memory,
                                       char *output_memory)
{
    (void)optional_text;
    (void)input_memory;
    (void)output_memory;
    int enabled = optional_number != 0.0;
    write_enabled(enabled);
    InterlockedExchange(&g_enabled, enabled);
    if (enabled) {
        if (g_hwnd != NULL && IsWindow(g_hwnd))
            iat_install();
        sync_flag();
    } else {
        iat_restore();
        iat_set_block(0);
    }
    return enabled ? 1.0f : 0.0f;
}

__declspec(dllexport) float GetEnabled(const char *optional_text,
                                       double optional_number,
                                       char *input_memory,
                                       char *output_memory)
{
    (void)optional_text;
    (void)optional_number;
    (void)input_memory;
    (void)output_memory;
    return g_enabled ? 1.0f : 0.0f;
}

/* 0 = Chinese system UI, 1 = other (kept for a future localized UI). */
__declspec(dllexport) float Language(const char *optional_text,
                                     double optional_number,
                                     char *input_memory,
                                     char *output_memory)
{
    (void)optional_text;
    (void)optional_number;
    (void)input_memory;
    (void)output_memory;
    LANGID lang = GetUserDefaultUILanguage();
    return ((lang & 0x3FF) == 0x04) ? 0.0f : 1.0f;
}

/* State feed from the .zsc detection loop: 0=other, 1=blank, 2=mesh. */
__declspec(dllexport) float UpdateState(const char *optional_text,
                                        double optional_number,
                                        char *input_memory,
                                        char *output_memory)
{
    (void)optional_text;
    (void)input_memory;
    (void)output_memory;
    LONG s = (LONG)optional_number;
    if (s < ZS_OTHER || s > ZS_MESH)
        s = ZS_OTHER;
    InterlockedExchange(&g_zsState, s);
    InterlockedExchange(&g_zsTicks, (LONG)GetTickCount());
    char line[128];
    _snprintf_s(line, sizeof(line), _TRUNCATE, "state=%ld tick=%lu\n",
                s, GetTickCount());
    dbg_log(line);
    sync_flag();
    return (float)s;
}

/* TEMP: log the loop's mouse coords vs the real cursor (for the offset fix). */
__declspec(dllexport) float DbgCoords(const char *optional_text,
                                      double optional_number,
                                      char *input_memory,
                                      char *output_memory)
{
    (void)optional_text;
    (void)input_memory;
    (void)output_memory;
    long packed = (long)optional_number;
    long mx = packed / 100000;
    long my = packed % 100000;
    POINT pt;
    GetCursorPos(&pt);
    POINT origin = {0, 0};
    if (g_hwnd != NULL)
        ClientToScreen(g_hwnd, &origin);
    char line[256];
    _snprintf_s(line, sizeof(line), _TRUNCATE,
                "coords loop=(%ld,%ld) screen=(%ld,%ld) client=(%ld,%ld)\n",
                mx, my, pt.x, pt.y,
                (long)(pt.x - origin.x),
                (long)(pt.y - origin.y));
    dbg_log(line);
    return 1.0f;
}

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH)
        DisableThreadLibraryCalls(hinst);
    return TRUE;
}
