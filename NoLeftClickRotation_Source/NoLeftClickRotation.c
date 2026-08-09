#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <wchar.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "comctl32.lib")

/*
 * NoLeftClickRotation.dll - in-process ZBrush mouse hook (ZBrush 2026+).
 *
 * The official .zsc plugin loads this DLL through [FileExecute] at ZBrush
 * startup. The DLL subclasses the ZBrush main window and, on every plain
 * left-button press, asks the embedded Python VM (via init.py and the
 * official zbrush.commands API) whether the press is on blank canvas in
 * Edit mode. If it is, the click is passed through and immediately followed
 * by a matching button-up, so the view rotation drag is cancelled before it
 * can start. If the cursor later reaches the mesh, a fresh button-down is
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
    if (!pyReady)
        return; /* Python VM is not up yet; keep polling. */

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

/* ---- subclass ---- */
static LRESULT CALLBACK SubclassProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam,
                                     UINT_PTR uIdSubclass, DWORD_PTR dwRefData)
{
    (void)hWnd;
    (void)uIdSubclass;
    (void)dwRefData;

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
                int kind = call_point_kind(pt.x, pt.y);
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
        if (!ui_cursor && ClientToScreen(hWnd, &pt) &&
            query_python(pt.x, pt.y, 1)) {
            /*
             * Blank press in Edit mode while the cursor is a ZBrush canvas
             * cursor (custom/hidden), i.e. the press is not on a UI control.
             * Let ZBrush receive the click, then immediately send a matching
             * up so the view rotation drag is cancelled before any movement
             * happens. The click itself is not removed.
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
    InterlockedExchange(&g_state, ST_IDLE);

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

    return 1.0f;
}

__declspec(dllexport) BOOL WINAPI Uninstall(void)
{
    if (g_hwnd != NULL) {
        KillTimer(g_hwnd, PYTHON_TIMER_ID);
        RemoveWindowSubclass(g_hwnd, SubclassProc, SUBCLASS_ID);
        g_hwnd = NULL;
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
