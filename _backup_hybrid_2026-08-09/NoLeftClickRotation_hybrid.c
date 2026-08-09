#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "comctl32.lib")

/*
 * NoLeftClickRotation.dll - in-process ZBrush mouse hook.
 *
 * Official .zsc plugin (NoLeftClickRotation.zsc) loads this DLL through
 * [FileExecute] at ZBrush startup. The DLL subclasses the ZBrush main
 * window and, on every plain left-button press, decides whether the press
 * is on blank canvas:
 *
 * - ZBrush 2026+ (embedded CPython): the embedded Python VM (init.py and
 *   the official zbrush.commands API) is queried synchronously - exact
 *   Edit-mode + PixolPick(material index 0) check.
 * - ZBrush 2022-2025 (no Python API): a legacy fallback uses the ZBrush
 *   blank-canvas cursor. The user calibrates it once per machine/version
 *   with F2 while the cursor is over blank canvas; the cursor bitmap
 *   signature is stored in config.txt. Only presses whose cursor matches
 *   the calibrated blank-canvas signature are cancelled.
 *
 * In both modes the click is passed through and immediately followed by a
 * matching button-up, so the view rotation drag is cancelled before it can
 * start. If the cursor later reaches the mesh, a fresh button-down is
 * injected so the brush stroke starts at the entry point. UI controls
 * (standard system cursors) and modifier gestures (Ctrl/Shift/Alt) are
 * never touched.
 *
 * There is no ZScript polling and no Sleep loop: the canvas state is
 * queried synchronously at the moment of the mouse event, so the plugin is
 * active from the first launch. It lives and dies with the ZBrush process.
 */

#define SUBCLASS_ID 0x4E525442 /* 'NRB' */
#define PYTHON_TIMER_ID 0x4E525441 /* 'NRA' */

enum {
    ST_IDLE = 0,
    ST_ARMED = 1,    /* blank press cancelled with an immediate up; waiting for the cursor to reach the mesh */
    ST_STROKING = 2  /* we injected WM_LBUTTONDOWN on the mesh; let ZBrush sculpt */
};

static HWND g_hwnd = NULL;
static wchar_t g_scriptPath[MAX_PATH];
static wchar_t g_configPath[MAX_PATH];
static volatile LONG g_state = ST_IDLE;
static volatile LONG g_scriptRun = 0;
static volatile LONG g_pyTimerTicks = 0;

/* ---- legacy (pre-2026, no Python API) support ---- */
typedef struct {
    int w;
    int h;
    unsigned __int64 hash;
} CursorSig;

static CursorSig g_blankSig;               /* F2-calibrated blank-canvas cursor */
static volatile LONG g_legacyNoticeShown = 0;
static volatile LONG g_pyMissingTicks = 0;
static HHOOK g_keyHook = NULL;

/* ZScript state feed (2022-2025): the .zsc runs a documented [Sleep] loop
 * that wakes on mouse move / left-button down and pushes 0=other,
 * 1=blank canvas, 2=mesh into the DLL via UpdateState. */
static volatile LONG g_zsState = 0;
static volatile LONG g_zsTicks = 0;

static int zs_fresh(void);

/* ---- minimal CPython bridge ---- */
typedef struct {
    HMODULE mod;
    int (*py_is_initialized)(void);
    void *(*py_gil_ensure)(void);
    void (*py_gil_release)(void *);
    void *(*py_import_module)(const char *);
    void *(*py_get_attr_string)(void *, const char *);
    void *(*py_call_object)(void *, void *);
    void *(*py_build_value)(const char *, ...);
    int (*py_object_istrue)(void *);
    long (*py_long_as_long)(void *);
    void (*py_err_print)(void);
    void (*py_err_clear)(void);
    void (*py_dec_ref)(void *);
    int (*py_run_simple_string)(const char *);
    void *g_query_fn;
    void *g_point_kind_fn;
} PyBridge;

static PyBridge g_py;

/* Forward declaration so set_paths() can locate this module. */
__declspec(dllexport) float Install(const char *optional_text,
                                    double optional_number,
                                    char *input_memory,
                                    char *output_memory);

/* ---- paths and persisted switch state ---- */

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
    wcscpy_s(g_scriptPath, MAX_PATH, g_configPath);
    wcsncat_s(g_scriptPath, MAX_PATH, L"init.py", _TRUNCATE);
    wcsncat_s(g_configPath, MAX_PATH, L"config.txt", _TRUNCATE);
}

static void parse_blank_line(const char *s)
{
    /* Format: "32x32;1a2b3c4d5e6f7080" (width x height ; 64-bit hex hash). */
    int w = 0, h = 0;
    const char *p = s;
    while (*p >= '0' && *p <= '9') { w = w * 10 + (*p - '0'); ++p; }
    if (*p != 'x') return;
    ++p;
    while (*p >= '0' && *p <= '9') { h = h * 10 + (*p - '0'); ++p; }
    if (*p != ';') return;
    ++p;
    unsigned __int64 hash = 0;
    for (; *p; ++p) {
        int c = -1;
        if (*p >= '0' && *p <= '9') c = *p - '0';
        else if (*p >= 'a' && *p <= 'f') c = *p - 'a' + 10;
        else if (*p >= 'A' && *p <= 'F') c = *p - 'A' + 10;
        else break;
        hash = (hash << 4) | (unsigned)c;
    }
    if (w > 0 && h > 0) {
        g_blankSig.w = w;
        g_blankSig.h = h;
        g_blankSig.hash = hash;
    }
}

static void read_config(void)
{
    g_blankSig.w = 0;
    g_blankSig.h = 0;
    g_blankSig.hash = 0;
    if (g_configPath[0] == L'\0')
        return;
    HANDLE h = CreateFileW(g_configPath, GENERIC_READ, FILE_SHARE_READ,
                           NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE)
        return;
    char buf[1024] = {0};
    DWORD rd = 0;
    ReadFile(h, buf, sizeof(buf) - 1, &rd, NULL);
    CloseHandle(h);
    char *line = buf;
    while (line != NULL && *line != '\0') {
        char *nl = strchr(line, '\n');
        if (nl != NULL)
            *nl = '\0';
        if (strncmp(line, "blank=", 6) == 0)
            parse_blank_line(line + 6);
        line = (nl != NULL) ? nl + 1 : NULL;
    }
}

static void save_config(int enabled)
{
    if (g_configPath[0] == L'\0')
        return;
    /* Keep an existing calibration line when the UI switch changes. */
    char old[1024] = {0};
    HANDLE hr = CreateFileW(g_configPath, GENERIC_READ, FILE_SHARE_READ,
                            NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hr != INVALID_HANDLE_VALUE) {
        DWORD rd = 0;
        ReadFile(hr, old, sizeof(old) - 1, &rd, NULL);
        CloseHandle(hr);
    }
    char blank[96] = "";
    {
        char *line = old;
        while (line != NULL && *line != '\0') {
            char *nl = strchr(line, '\n');
            if (nl != NULL)
                *nl = '\0';
            if (strncmp(line, "blank=", 6) == 0) {
                strncpy_s(blank, sizeof(blank), line, _TRUNCATE);
                break;
            }
            line = (nl != NULL) ? nl + 1 : NULL;
        }
    }
    char out[1200] = {0};
    _snprintf_s(out, sizeof(out), _TRUNCATE, "%s%s%s",
                enabled ? "1\n" : "0\n", blank, blank[0] ? "\n" : "");
    HANDLE hw = CreateFileW(g_configPath, GENERIC_WRITE, 0, NULL,
                            CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hw == INVALID_HANDLE_VALUE)
        return;
    DWORD wr = 0;
    WriteFile(hw, out, (DWORD)strlen(out), &wr, NULL);
    CloseHandle(hw);
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
    save_config(enabled);
}

static void save_blank_sig(void)
{
    if (g_blankSig.w <= 0 || g_configPath[0] == L'\0')
        return;
    char line[96];
    _snprintf_s(line, sizeof(line), _TRUNCATE, "blank=%dx%d;%016I64x",
                g_blankSig.w, g_blankSig.h, g_blankSig.hash);
    /* Preserve the current enabled state (default 1). */
    char old[1024] = {0};
    HANDLE hr = CreateFileW(g_configPath, GENERIC_READ, FILE_SHARE_READ,
                            NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hr != INVALID_HANDLE_VALUE) {
        DWORD rd = 0;
        ReadFile(hr, old, sizeof(old) - 1, &rd, NULL);
        CloseHandle(hr);
    }
    int enabled = (old[0] == '0') ? 0 : 1;
    char out[1200] = {0};
    _snprintf_s(out, sizeof(out), _TRUNCATE, "%s%s\n",
                enabled ? "1\n" : "0\n", line);
    HANDLE hw = CreateFileW(g_configPath, GENERIC_WRITE, 0, NULL,
                            CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hw == INVALID_HANDLE_VALUE)
        return;
    DWORD wr = 0;
    WriteFile(hw, out, (DWORD)strlen(out), &wr, NULL);
    CloseHandle(hw);
}

/* ---- window lookup ---- */

typedef struct {
    DWORD pid;
    HWND hwnd;
} FindZBrushCtx;

static BOOL CALLBACK FindZBrushEnumProc(HWND hwnd, LPARAM lParam)
{
    FindZBrushCtx *ctx = (FindZBrushCtx *)lParam;
    wchar_t cls[64];
    if (GetClassNameW(hwnd, cls, 64) == 0 || wcscmp(cls, L"ZBrush") != 0)
        return TRUE;
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == ctx->pid) {
        ctx->hwnd = hwnd;
        return FALSE;
    }
    return TRUE;
}

/* Finds the ZBrush main window owned by THIS process (multi-instance safe). */
static HWND find_zbrush_window(void)
{
    HWND h = FindWindowW(L"ZBrush", NULL);
    DWORD winPid = 0;
    if (h != NULL) {
        GetWindowThreadProcessId(h, &winPid);
        if (winPid == GetCurrentProcessId())
            return h;
    }
    FindZBrushCtx ctx;
    ctx.pid = GetCurrentProcessId();
    ctx.hwnd = NULL;
    EnumWindows(FindZBrushEnumProc, (LPARAM)&ctx);
    return ctx.hwnd;
}

/* ---- CPython bridge ---- */

static int resolve_python(void)
{
    if (g_py.mod != NULL)
        return 1;

    /* ZBrush 2026 embeds CPython; accept the common 3.x names so a future
     * ZBrush update does not silently break the bridge. */
    static const wchar_t *python_names[] = {
        L"python311.dll",
        L"python313.dll",
        L"python312.dll",
        L"python310.dll",
    };
    HMODULE m = NULL;
    for (int i = 0; i < (int)(sizeof(python_names) / sizeof(python_names[0])); ++i) {
        m = GetModuleHandleW(python_names[i]);
        if (m == NULL)
            m = LoadLibraryW(python_names[i]);
        if (m != NULL)
            break;
    }
    if (m == NULL)
        return 0;

    g_py.mod = m;
    g_py.py_is_initialized = (int (*)(void))GetProcAddress(m, "Py_IsInitialized");
    g_py.py_gil_ensure = (void *(*)(void))GetProcAddress(m, "PyGILState_Ensure");
    g_py.py_gil_release = (void (*)(void *))GetProcAddress(m, "PyGILState_Release");
    g_py.py_import_module = (void *(*)(const char *))GetProcAddress(m, "PyImport_ImportModule");
    g_py.py_get_attr_string = (void *(*)(void *, const char *))GetProcAddress(m, "PyObject_GetAttrString");
    g_py.py_call_object = (void *(*)(void *, void *))GetProcAddress(m, "PyObject_CallObject");
    g_py.py_build_value = (void *(*)(const char *, ...))GetProcAddress(m, "Py_BuildValue");
    g_py.py_object_istrue = (int (*)(void *))GetProcAddress(m, "PyObject_IsTrue");
    g_py.py_long_as_long = (long (*)(void *))GetProcAddress(m, "PyLong_AsLong");
    g_py.py_err_print = (void (*)(void))GetProcAddress(m, "PyErr_Print");
    g_py.py_err_clear = (void (*)(void))GetProcAddress(m, "PyErr_Clear");
    g_py.py_dec_ref = (void (*)(void *))GetProcAddress(m, "Py_DecRef");
    g_py.py_run_simple_string = (int (*)(const char *))
        GetProcAddress(m, "PyRun_SimpleString");

    if (g_py.py_is_initialized == NULL || g_py.py_gil_ensure == NULL ||
        g_py.py_gil_release == NULL || g_py.py_import_module == NULL ||
        g_py.py_get_attr_string == NULL || g_py.py_call_object == NULL ||
        g_py.py_build_value == NULL || g_py.py_object_istrue == NULL ||
        g_py.py_long_as_long == NULL ||
        g_py.py_err_print == NULL || g_py.py_err_clear == NULL ||
        g_py.py_dec_ref == NULL || g_py.py_run_simple_string == NULL) {
        /* Do not keep a half-resolved module: a later call would skip
         * validation and could call a NULL function pointer. */
        g_py.mod = NULL;
        return 0;
    }

    return 1;
}

static void run_python_script(const wchar_t *path)
{
    if (path == NULL || path[0] == L'\0')
        return;

    char utf8Path[MAX_PATH * 3];
    utf8Path[0] = '\0';
    WideCharToMultiByte(CP_UTF8, 0, path, -1, utf8Path, (int)sizeof(utf8Path), NULL, NULL);
    if (utf8Path[0] == '\0')
        return;

    char escaped[MAX_PATH * 6];
    size_t j = 0;
    for (const char *p = utf8Path; *p != '\0' && j + 6 < sizeof(escaped); ++p) {
        if (*p == '\\' || *p == '\'') {
            escaped[j++] = '\\';
        }
        escaped[j++] = *p;
    }
    escaped[j] = '\0';

    char code[16384];
    _snprintf_s(code, sizeof(code), _TRUNCATE,
        "import os\n"
        "os.environ['NOBLANKROTATE_INPROCESS'] = '1'\n"
        "import runpy\n"
        "try:\n"
        "    runpy.run_path('%s', run_name='__main__')\n"
        "except BaseException:\n"
        "    import traceback\n"
        "    traceback.print_exc()\n"
        "finally:\n"
        "    os.environ.pop('NOBLANKROTATE_INPROCESS', None)\n",
        escaped);

    void *gil = g_py.py_gil_ensure();
    int rc = g_py.py_run_simple_string(code);
    g_py.py_gil_release(gil);
    (void)rc;
}

static int python_module_present(void)
{
    if (g_py.mod == NULL || g_py.py_import_module == NULL)
        return 0;
    void *gil = g_py.py_gil_ensure();
    void *mod = g_py.py_import_module("zb_noleftclickrotation");
    if (mod != NULL)
        g_py.py_dec_ref(mod);
    else
        g_py.py_err_clear();
    g_py.py_gil_release(gil);
    return mod != NULL;
}

static int install_python_bridge(void)
{
    if (g_py.g_query_fn != NULL)
        return 1;
    if (!resolve_python())
        return 0;
    if (!g_py.py_is_initialized())
        return 0;

    void *gil = g_py.py_gil_ensure();
    void *mod = g_py.py_import_module("zb_noleftclickrotation");
    if (mod == NULL) {
        g_py.py_err_print();
        g_py.py_gil_release(gil);
        return 0;
    }
    void *fn = g_py.py_get_attr_string(mod, "query");
    void *kind_fn = g_py.py_get_attr_string(mod, "point_kind");
    if (fn == NULL || kind_fn == NULL) {
        /* Version mismatch between DLL and init.py: never install a partial
         * bridge, otherwise blank->mesh crossing would silently stop working. */
        if (fn != NULL)
            g_py.py_dec_ref(fn);
        if (kind_fn != NULL)
            g_py.py_dec_ref(kind_fn);
        g_py.py_dec_ref(mod);
        g_py.py_err_print();
        g_py.py_gil_release(gil);
        return 0;
    }
    g_py.g_query_fn = fn;
    g_py.g_point_kind_fn = kind_fn;
    g_py.py_dec_ref(mod);
    g_py.py_gil_release(gil);
    return 1;
}

static void CALLBACK PythonReadyTimer(HWND hwnd, UINT msg, UINT_PTR idEvent, DWORD dwTime)
{
    (void)msg;
    (void)dwTime;

    if (++g_pyTimerTicks > 300) { /* ~90 s: stop polling if Python never comes up */
        KillTimer(hwnd, idEvent);
        return;
    }

    int pyReady = resolve_python() && g_py.py_is_initialized();
    if (!pyReady) {
        /* Pre-2026 has no embedded Python: legacy mode. Tell the user once,
         * but only when neither the ZScript state feed nor a calibrated
         * cursor is available yet. */
        if (++g_pyMissingTicks == 12 && !g_legacyNoticeShown && read_enabled()) {
            g_legacyNoticeShown = 1;
            if (!zs_fresh() && g_blankSig.w <= 0)
                PostMessageW(hwnd, WM_APP + 2, 0, 0);
        }
        return; /* Python VM is not up yet; keep polling. */
    }

    if (!InterlockedCompareExchange(&g_scriptRun, 1, 0))
        run_python_script(g_scriptPath);

    if (install_python_bridge()) {
        KillTimer(hwnd, idEvent);
        return;
    }

    /* init.py did not register the query module yet; allow a later retry. */
    if (g_scriptRun && !python_module_present())
        InterlockedExchange(&g_scriptRun, 0);
}

static int query_python(int screen_x, int screen_y, int is_down)
{
    if (g_py.mod == NULL || g_py.g_query_fn == NULL)
        return 0;

    void *gil = g_py.py_gil_ensure();
    int result = 0;
    void *args = g_py.py_build_value("(iii)", screen_x, screen_y, is_down);
    if (args != NULL) {
        void *res = g_py.py_call_object(g_py.g_query_fn, args);
        if (res != NULL) {
            result = (g_py.py_object_istrue(res) == 1);
            g_py.py_dec_ref(res);
        } else {
            g_py.py_err_print();
        }
        g_py.py_dec_ref(args);
    } else {
        g_py.py_err_clear();
    }
    g_py.py_gil_release(gil);
    return result;
}

static int call_point_kind(int screen_x, int screen_y)
{
    if (g_py.mod == NULL || g_py.g_point_kind_fn == NULL)
        return 2;
    void *gil = g_py.py_gil_ensure();
    int result = 2;
    void *args = g_py.py_build_value("(ii)", screen_x, screen_y);
    if (args != NULL) {
        void *res = g_py.py_call_object(g_py.g_point_kind_fn, args);
        if (res != NULL) {
            result = (int)g_py.py_long_as_long(res);
            g_py.py_err_clear(); /* never leave a stale Python exception behind */
            g_py.py_dec_ref(res);
        } else {
            g_py.py_err_print();
        }
        g_py.py_dec_ref(args);
    } else {
        g_py.py_err_clear();
    }
    g_py.py_gil_release(gil);
    return result;
}

static WPARAM current_button_flags(void)
{
    WPARAM w = MK_LBUTTON;
    if (GetKeyState(VK_CONTROL) & 0x8000) w |= MK_CONTROL;
    if (GetKeyState(VK_SHIFT) & 0x8000) w |= MK_SHIFT;
    return w;
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
        std[14] = LoadCursorW(NULL, (LPCWSTR)MAKEINTRESOURCE(32671)); /* IDC_PIN */
        std[15] = LoadCursorW(NULL, (LPCWSTR)MAKEINTRESOURCE(32672)); /* IDC_PERSON */
    }
    if (h == NULL)
        return 0; /* hidden cursor: ZBrush canvas, not a standard UI cursor */
    for (int i = 0; i < 16; ++i) {
        if (std[i] != NULL && std[i] == h)
            return 1;
    }
    return 0;
}

/* ---- legacy cursor-signature detection (pre-2026, no Python) ---- */

static unsigned __int64 hash_buf(const unsigned char *p, size_t n,
                                 unsigned __int64 h)
{
    for (size_t i = 0; i < n; ++i) {
        h ^= p[i];
        h *= 0x100000001B3ULL; /* FNV-1a 64-bit */
    }
    return h;
}

static int cursor_signature(HCURSOR hc, CursorSig *out)
{
    if (hc == NULL || out == NULL)
        return 0;
    ICONINFO ii;
    if (!GetIconInfo(hc, &ii))
        return 0;

    int w = 0, ht = 0;
    unsigned __int64 h = 1469598103934665603ULL;
    unsigned char *color = NULL, *mask = NULL;
    size_t colorBytes = 0, maskBytes = 0;

    if (ii.hbmColor) {
        BITMAP b;
        if (GetObjectW(ii.hbmColor, sizeof(b), &b) && b.bmWidth > 0) {
            w = b.bmWidth;
            ht = b.bmHeight;
            int rowBytes = b.bmWidth * b.bmBitsPixel / 8;
            if (rowBytes > 0) {
                colorBytes = (size_t)rowBytes * (size_t)b.bmHeight;
                color = (unsigned char *)malloc(colorBytes ? colorBytes : 1);
                if (color == NULL || !GetBitmapBits(ii.hbmColor,
                                                    (LONG)colorBytes, color)) {
                    colorBytes = 0;
                }
            }
        }
    }
    if (ii.hbmMask) {
        BITMAP b;
        if (GetObjectW(ii.hbmMask, sizeof(b), &b) && b.bmWidth > 0) {
            if (w == 0) {
                w = b.bmWidth;
                ht = b.bmHeight;
            }
            int rowBytes = b.bmWidth * b.bmBitsPixel / 8;
            if (rowBytes > 0) {
                maskBytes = (size_t)rowBytes * (size_t)b.bmHeight;
                mask = (unsigned char *)malloc(maskBytes ? maskBytes : 1);
                if (mask == NULL || !GetBitmapBits(ii.hbmMask,
                                                   (LONG)maskBytes, mask)) {
                    maskBytes = 0;
                }
            }
        }
    }

    if (w > 0) {
        h = hash_buf((const unsigned char *)&w, sizeof(w), h);
        h = hash_buf((const unsigned char *)&ht, sizeof(ht), h);
        if (colorBytes > 0 && color != NULL)
            h = hash_buf(color, colorBytes, h);
        if (maskBytes > 0 && mask != NULL)
            h = hash_buf(mask, maskBytes, h);
    }
    if (color != NULL)
        free(color);
    if (mask != NULL)
        free(mask);
    if (ii.hbmColor)
        DeleteObject(ii.hbmColor);
    if (ii.hbmMask)
        DeleteObject(ii.hbmMask);

    if (w <= 0) {
        out->w = 0;
        out->h = 0;
        out->hash = 0;
        return 0;
    }
    out->w = w;
    out->h = ht;
    out->hash = h;
    return 1;
}

static int cursor_matches_blank(HCURSOR hc)
{
    if (g_blankSig.w <= 0 || hc == NULL)
        return 0;
    CursorSig cur;
    if (!cursor_signature(hc, &cur))
        return 0;
    return (cur.w == g_blankSig.w && cur.h == g_blankSig.h &&
            cur.hash == g_blankSig.hash);
}

static int zs_fresh(void)
{
    DWORD last = (DWORD)g_zsTicks;
    if (last == 0)
        return 0;
    return ((DWORD)(GetTickCount() - last)) <= 1500;
}

/* 1 = blank canvas press to cancel; 0 = do nothing. */
static int query_legacy(int screen_x, int screen_y)
{
    (void)screen_x;
    (void)screen_y;
    if (!read_enabled())
        return 0;

    /* Preferred path: exact state pushed by the documented ZScript [Sleep]
     * loop (IGet Transform:Edit + MouseHPos/VPos + PixolPick). */
    if (zs_fresh()) {
        if (g_zsState != 1)
            return 0;
        CURSORINFO ci;
        ci.cbSize = sizeof(ci);
        if (GetCursorInfo(&ci) && ci.hCursor != NULL &&
            is_standard_ui_cursor(ci.hCursor))
            return 0; /* standard cursor: interface control */
        return 1;
    }

    /* Fallback: another macro/plugin took over the single ZScript slot, so
     * the state feed is stale. Use the calibrated blank cursor, if any. */
    if (g_blankSig.w <= 0)
        return 0;
    CURSORINFO ci;
    ci.cbSize = sizeof(ci);
    if (!GetCursorInfo(&ci))
        return 0;
    if (ci.hCursor == NULL)
        return 0; /* hidden cursor: unknown, never guess */
    if (is_standard_ui_cursor(ci.hCursor))
        return 0;
    return cursor_matches_blank(ci.hCursor) ? 1 : 0;
}

/*
 * 0 = still blank (stay armed), 1 = reached mesh/canvas (inject a fresh
 * down), 2 = UI/unknown (abort the armed state).
 */
static int point_kind_legacy(int screen_x, int screen_y)
{
    (void)screen_x;
    (void)screen_y;
    if (!read_enabled())
        return 2;

    CURSORINFO ci;
    ci.cbSize = sizeof(ci);
    int ui = 0;
    if (GetCursorInfo(&ci) && ci.hCursor != NULL)
        ui = is_standard_ui_cursor(ci.hCursor);

    if (zs_fresh()) {
        if (ui)
            return 2;
        switch (g_zsState) {
        case 1: return 0;  /* still blank: stay armed */
        case 2: return 1;  /* reached the mesh: inject a fresh down */
        default: return 2; /* off-canvas / unknown: abort */
        }
    }

    /* Stale fallback: cursor based. */
    if (!GetCursorInfo(&ci) || ci.hCursor == NULL)
        return 1; /* canvas drag in progress; likely entering the mesh */
    if (ui)
        return 2;
    if (cursor_matches_blank(ci.hCursor))
        return 0;
    return 1;
}

/* ---- calibration (F2 = remember current cursor as blank canvas) ---- */

static void calibrate_blank(void)
{
    CURSORINFO ci;
    ci.cbSize = sizeof(ci);
    CursorSig cur;
    if (!GetCursorInfo(&ci) || !cursor_signature(ci.hCursor, &cur))
        return;
    g_blankSig = cur;
    save_blank_sig();
    if (g_hwnd != NULL)
        PostMessageW(g_hwnd, WM_APP + 3, 0, 0); /* confirm to the user */
}

static LRESULT CALLBACK KeyHookProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode == HC_ACTION) {
        KBDLLHOOKSTRUCT *k = (KBDLLHOOKSTRUCT *)lParam;
        if (k != NULL && k->vkCode == VK_F2 &&
            (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN)) {
            HWND fg = GetForegroundWindow();
            DWORD pid = 0;
            if (fg != NULL)
                GetWindowThreadProcessId(fg, &pid);
            if (pid == GetCurrentProcessId())
                calibrate_blank();
        }
    }
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

/* ---- subclass ---- */
static LRESULT CALLBACK SubclassProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam,
                                     UINT_PTR uIdSubclass, DWORD_PTR dwRefData)
{
    (void)hWnd;
    (void)uIdSubclass;
    (void)dwRefData;

    if (msg == WM_APP + 2) {
        /* Pre-2026 legacy mode: ask for a one-time F2 calibration. */
        if (((GetUserDefaultUILanguage() & 0x3FF) == 0x04)) {
            MessageBoxW(hWnd,
                L"旧版兼容模式已启用。\n\n"
                L"插件会优先用 ZScript 精确判定空白画布；若被其他插件/宏"
                L"打断，可把鼠标移到空白画布上按 F2 记录光标作为备用。\n\n"
                L"界面控件和带修饰键的操作不受影响。",
                L"NoLeftClickRotation", MB_OK | MB_ICONINFORMATION);
        } else {
            MessageBoxW(hWnd,
                L"Legacy compatibility mode is active.\n\n"
                L"The plugin prefers the exact ZScript canvas check; if another "
                L"plugin/macro interrupts it, move the cursor over ZBrush's "
                L"blank canvas and press F2 once as a fallback.\n\n"
                L"UI controls and modifier gestures are not affected.",
                L"NoLeftClickRotation", MB_OK | MB_ICONINFORMATION);
        }
        return 0;
    }
    if (msg == WM_APP + 3) {
        /* F2 calibration confirmation. */
        if (((GetUserDefaultUILanguage() & 0x3FF) == 0x04)) {
            wchar_t buf[256];
            _snwprintf_s(buf, 256, _TRUNCATE,
                L"已记录空白画布光标（%d x %d）。\n\n"
                L"按住空白画布拖动将不再旋转视图。"
                L"更换显示缩放或 ZBrush 版本后请重新按 F2 校准。",
                g_blankSig.w, g_blankSig.h);
            MessageBoxW(hWnd, buf, L"NoLeftClickRotation",
                        MB_OK | MB_ICONINFORMATION);
        } else {
            wchar_t buf[256];
            _snwprintf_s(buf, 256, _TRUNCATE,
                L"Blank-canvas cursor recorded (%d x %d).\n\n"
                L"Left-drag on blank canvas will no longer rotate the view. "
                L"Recalibrate with F2 after changing display scaling or "
                L"ZBrush version.",
                g_blankSig.w, g_blankSig.h);
            MessageBoxW(hWnd, buf, L"NoLeftClickRotation",
                        MB_OK | MB_ICONINFORMATION);
        }
        return 0;
    }

    if (g_state != ST_IDLE &&
        msg != WM_LBUTTONUP && msg != WM_LBUTTONDBLCLK &&
        !(GetKeyState(VK_LBUTTON) & 0x8000)) {
        LONG prev = InterlockedExchange(&g_state, ST_IDLE);
        if (prev == ST_STROKING)
            PostMessageW(hWnd, WM_LBUTTONUP, 0, 0);
    }

    if (g_state == ST_ARMED) {
        switch (msg) {
        case WM_MOUSEMOVE:
        {
            POINT pt;
            pt.x = (short)LOWORD(lParam);
            pt.y = (short)HIWORD(lParam);
            if (ClientToScreen(hWnd, &pt)) {
                int kind = (g_py.g_point_kind_fn != NULL)
                               ? call_point_kind(pt.x, pt.y)
                               : point_kind_legacy(pt.x, pt.y);
                if (kind == 1) {
                    /*
                     * The cursor crossed from blank onto the mesh. ZBrush
                     * never started a rotation drag (we cancelled it with an
                     * immediate up at the press), so synthesize a fresh down
                     * to begin the brush stroke at this point.
                     */
                    WPARAM downW = current_button_flags();
                    InterlockedExchange(&g_state, ST_STROKING);
                    SendMessageW(hWnd, WM_LBUTTONDOWN, downW, lParam);
                } else if (kind == 2 && g_py.g_point_kind_fn == NULL) {
                    /* Legacy mode: the cursor entered a UI control; abort. */
                    InterlockedExchange(&g_state, ST_IDLE);
                }
            }
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        }
        case WM_LBUTTONUP:
        case WM_LBUTTONDBLCLK:
            InterlockedExchange(&g_state, ST_IDLE);
            return DefSubclassProc(hWnd, msg, wParam, lParam);
        default:
            break;
        }
    } else if (g_state == ST_STROKING) {
        if (msg == WM_LBUTTONUP) {
            LRESULT r = DefSubclassProc(hWnd, msg, wParam, lParam);
            InterlockedExchange(&g_state, ST_IDLE);
            return r;
        }
        if (msg == WM_LBUTTONDBLCLK) {
            InterlockedExchange(&g_state, ST_IDLE);
        }
    } else if (msg == WM_LBUTTONDOWN) {
        /*
         * Never touch modifier gestures: in ZBrush, Ctrl+left drag on blank
         * canvas draws a rectangular mask selection, Shift/Alt also have
         * their own meanings. Only a plain left-button press on blank canvas
         * triggers the unwanted view rotation this plugin disables.
         */
        if ((wParam & (MK_CONTROL | MK_SHIFT)) != 0 ||
            (GetKeyState(VK_MENU) & 0x8000))
            return DefSubclassProc(hWnd, msg, wParam, lParam);

        POINT pt;
        pt.x = (short)LOWORD(lParam);
        pt.y = (short)HIWORD(lParam);
        CURSORINFO ci;
        ci.cbSize = sizeof(ci);
        int ui_cursor = 0;
        if (GetCursorInfo(&ci) && ci.hCursor != NULL)
            ui_cursor = is_standard_ui_cursor(ci.hCursor);
        int blank = (g_py.g_query_fn != NULL)
                        ? query_python(pt.x, pt.y, 1)
                        : query_legacy(pt.x, pt.y);
        if (!ui_cursor && ClientToScreen(hWnd, &pt) && blank) {
            /*
             * Blank press while the cursor is a ZBrush canvas cursor (not a
             * standard UI cursor). Let ZBrush receive the click, then
             * immediately send a matching up so the view rotation drag is
             * cancelled before any movement happens. The click itself is not
             * removed.
             */
            LRESULT r = DefSubclassProc(hWnd, msg, wParam, lParam);
            SendMessageW(hWnd, WM_LBUTTONUP, current_button_flags(), lParam);
            InterlockedExchange(&g_state, ST_ARMED);
            return r;
        }
    }

    return DefSubclassProc(hWnd, msg, wParam, lParam);
}

/* ---- exported API (official [FileExecute] signature) ---- */

/*
 * ZScript [FileExecute] entry point. The signature is fixed by ZBrush:
 * optional text, optional number, input memory block, output memory block.
 * Returns a nonzero value on success (ZScript shows 0 on error).
 */
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
    read_config();
    InterlockedExchange(&g_state, ST_IDLE);
    g_pyMissingTicks = 0;
    g_legacyNoticeShown = 0;

    HWND h = find_zbrush_window();
    if (h == NULL)
        return 0.0f;
    if (!SetWindowSubclass(h, SubclassProc, SUBCLASS_ID, 0))
        return 0.0f;
    g_hwnd = h;
    g_pyTimerTicks = 0;

    SetEnvironmentVariableW(L"NOBLANKROTATE_INPROCESS", L"1");
    if (!SetTimer(h, PYTHON_TIMER_ID, 300, PythonReadyTimer)) {
        RemoveWindowSubclass(h, SubclassProc, SUBCLASS_ID);
        g_hwnd = NULL;
        return 0.0f;
    }
    {
        HMODULE self = NULL;
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                           GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCWSTR)(void *)&Install, &self);
        if (self != NULL)
            g_keyHook = SetWindowsHookExW(WH_KEYBOARD_LL, KeyHookProc,
                                          self, 0);
    }

    return 1.0f;
}

__declspec(dllexport) BOOL WINAPI Uninstall(void)
{
    if (g_hwnd != NULL) {
        KillTimer(g_hwnd, PYTHON_TIMER_ID);
        RemoveWindowSubclass(g_hwnd, SubclassProc, SUBCLASS_ID);
        g_hwnd = NULL;
    }
    if (g_keyHook != NULL) {
        UnhookWindowsHookEx(g_keyHook);
        g_keyHook = NULL;
    }
    if (g_py.mod != NULL && g_py.py_gil_ensure != NULL &&
        g_py.py_gil_release != NULL && g_py.py_dec_ref != NULL) {
        void *gil = g_py.py_gil_ensure();
        if (g_py.g_query_fn != NULL) {
            g_py.py_dec_ref(g_py.g_query_fn);
            g_py.g_query_fn = NULL;
        }
        if (g_py.g_point_kind_fn != NULL) {
            g_py.py_dec_ref(g_py.g_point_kind_fn);
            g_py.g_point_kind_fn = NULL;
        }
        g_py.py_gil_release(gil);
    }
    InterlockedExchange(&g_state, ST_IDLE);
    return TRUE;
}

__declspec(dllexport) BOOL WINAPI IsInstalled(void)
{
    return (g_hwnd != NULL && IsWindow(g_hwnd)) ? TRUE : FALSE;
}

/* Persists the UI switch state (1=enabled, 0=disabled). */
__declspec(dllexport) float SetEnabled(const char *optional_text,
                                       double optional_number,
                                       char *input_memory,
                                       char *output_memory)
{
    (void)optional_text;
    (void)input_memory;
    (void)output_memory;
    write_enabled(optional_number != 0.0 ? 1 : 0);
    return optional_number != 0.0 ? 1.0f : 0.0f;
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
    return read_enabled() ? 1.0f : 0.0f;
}

/* Returns 0 for a Chinese system UI, 1 otherwise. */
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

/*
 * Returns 1 when the ZBrush installation ships the embedded CPython runtime
 * (2026+). The .zsc uses this to decide whether to create the ZScript UI
 * (legacy) - the Python UI replaces it later on 2026+.
 */
__declspec(dllexport) float HasPythonFile(const char *optional_text,
                                          double optional_number,
                                          char *input_memory,
                                          char *output_memory)
{
    (void)optional_text;
    (void)optional_number;
    (void)input_memory;
    (void)output_memory;

    wchar_t exe[MAX_PATH], pattern[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, exe, MAX_PATH);
    if (n == 0 || n >= MAX_PATH)
        return 0.0f;
    wcscpy_s(pattern, MAX_PATH, exe);
    wchar_t *slash = wcsrchr(pattern, L'\\');
    if (slash == NULL)
        return 0.0f;
    slash[1] = L'\0';
    wcsncat_s(pattern, MAX_PATH, L"python*.dll", _TRUNCATE);

    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE)
        return 0.0f;
    FindClose(h);
    return 1.0f;
}

/*
 * State feed for legacy mode (2022-2025). The .zsc [Sleep] loop computes
 * the exact canvas state with documented ZScript commands and pushes it here:
 * 0 = not Edit / off-canvas, 1 = blank canvas, 2 = mesh.
 */
__declspec(dllexport) float UpdateState(const char *optional_text,
                                        double optional_number,
                                        char *input_memory,
                                        char *output_memory)
{
    (void)optional_text;
    (void)input_memory;
    (void)output_memory;
    InterlockedExchange(&g_zsState, (LONG)optional_number);
    InterlockedExchange(&g_zsTicks, (LONG)GetTickCount());
    return (float)optional_number;
}
