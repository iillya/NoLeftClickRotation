#include <windows.h>
#include <shellapi.h>
#include <commctrl.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <iterator>

namespace {

// ASCII "NLCR2" / "NLCR3" / "NLCR4" - unique IDs for this plugin's subclass
// and timers (NLCR = No Left Click Rotation).
constexpr UINT_PTR kSubclassId = 0x4E4C4352;
constexpr UINT_PTR kClassifyTimer = 0x4E4C4353;
constexpr UINT_PTR kStartTimer = 0x4E4C4354;
constexpr UINT kClassifyMs = 5;
constexpr UINT kSleepWatchdogPollMs = 25;
constexpr ULONGLONG kSleepHeartbeatTimeoutMs = 1000;
constexpr ULONGLONG kF12RetryMs = 500;
constexpr int kCanvasWindowId = 1004;

// Numeric resource IDs of the standard Windows system cursors. The IDC_*
// macros expand to pointer-typed values, so plain UINTs are used here to keep
// this list usable in a constexpr array.
constexpr UINT kSystemCursorIds[] = {
    32512,  // IDC_ARROW
    32513,  // IDC_IBEAM
    32514,  // IDC_WAIT
    32515,  // IDC_CROSS
    32516,  // IDC_UPARROW
    32642,  // IDC_SIZENWSE
    32643,  // IDC_SIZENESW
    32644,  // IDC_SIZEWE
    32645,  // IDC_SIZENS
    32646,  // IDC_SIZEALL
    32648,  // IDC_NO
    32649,  // IDC_HAND
    32650,  // IDC_APPSTARTING
    32651,  // IDC_HELP
};

enum class Gesture : int {
    Idle,
    UiPass,
    Classify,
    LightBoxPass,
    WaitModel,
    StartPending,
    Sculpting,
    ModelPass,
};

std::atomic<HWND> g_zbrush{nullptr};
std::atomic<bool> g_enabled{false};
std::atomic<bool> g_cameraLock{true};
std::atomic<bool> g_editMode{false};
std::atomic<int> g_windowId{-1};
std::atomic<int> g_startDelayMs{1};
std::atomic<Gesture> g_gesture{Gesture::Idle};
std::atomic<bool> g_injecting{false};
std::atomic<bool> g_systemCursorSeen{false};
std::atomic<bool> g_rightDown{false};
std::atomic<bool> g_rightPending{false};
std::atomic<bool> g_rightUpPending{false};
std::atomic<ULONGLONG> g_rightRelockUntil{0};
std::atomic<bool> g_hoverReady{false};
std::atomic<double> g_hoverMat{0.0};
std::atomic<ULONGLONG> g_lastHoverMs{0};
std::atomic<ULONGLONG> g_lastSleepHeartbeatMs{0};
std::atomic<ULONGLONG> g_lastF12WakeMs{0};
HANDLE g_sleepWatchdogTimer = nullptr;
HCURSOR g_systemCursors[std::size(kSystemCursorIds)] = {};
HCURSOR g_downCursor = nullptr;

using SetCursorFn = HCURSOR(WINAPI*)(HCURSOR);
SetCursorFn g_originalSetCursor = nullptr;
void** g_setCursorSlot = nullptr;

LPARAM CursorLParam(HWND hwnd) {
    POINT point{};
    GetCursorPos(&point);
    ScreenToClient(hwnd, &point);
    return MAKELPARAM(static_cast<short>(point.x), static_cast<short>(point.y));
}

WPARAM Modifiers() {
    WPARAM value = 0;
    if (GetAsyncKeyState(VK_SHIFT) & 0x8000) value |= MK_SHIFT;
    if (GetAsyncKeyState(VK_CONTROL) & 0x8000) value |= MK_CONTROL;
    return value;
}

LRESULT SendMouse(HWND hwnd, UINT message, WPARAM wparam) {
    g_injecting.store(true, std::memory_order_release);
    const LRESULT result = SendMessageW(hwnd, message, wparam, CursorLParam(hwnd));
    g_injecting.store(false, std::memory_order_release);
    return result;
}

bool ZBrushIsForeground() {
    // Any window owned by the ZBrush process counts as foreground (main
    // window, floating palette, LightBox, ...). The watchdog only fires
    // while ZBrush is foreground, so the synthesized F12 (SendInput) is
    // delivered to ZBrush and never reaches another application.
    const HWND foreground = GetForegroundWindow();
    if (!foreground) return false;
    DWORD pid = 0;
    GetWindowThreadProcessId(foreground, &pid);
    return pid == GetCurrentProcessId();
}

void SendF12Wake() {
    // Synthesize a real F12 press at the system level (same as the upstream
    // GitHub version). The watchdog only fires while a ZBrush-owned window is
    // foreground, so the key always lands in ZBrush and never leaks to
    // another application.
    INPUT input[2]{};
    input[0].type = INPUT_KEYBOARD;
    input[0].ki.wVk = VK_F12;
    input[1] = input[0];
    input[1].ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(2, input, sizeof(INPUT));
}

VOID CALLBACK SleepWatchdogCallback(PVOID, BOOLEAN) {
    const ULONGLONG now = GetTickCount64();
    const ULONGLONG heartbeat = g_lastSleepHeartbeatMs.load();
    const ULONGLONG lastWake = g_lastF12WakeMs.load();
    const bool modifiersHeld =
        (GetAsyncKeyState(VK_SHIFT) & 0x8000) ||
        (GetAsyncKeyState(VK_CONTROL) & 0x8000) ||
        (GetAsyncKeyState(VK_MENU) & 0x8000);
    const bool mouseHeld =
        (GetAsyncKeyState(VK_LBUTTON) & 0x8000) ||
        (GetAsyncKeyState(VK_RBUTTON) & 0x8000) ||
        (GetAsyncKeyState(VK_MBUTTON) & 0x8000);
    if (g_enabled.load() && heartbeat != 0 &&
        now - heartbeat > kSleepHeartbeatTimeoutMs &&
        now - lastWake >= kF12RetryMs &&
        ZBrushIsForeground() && !modifiersHeld && !mouseHeld) {
        g_lastF12WakeMs.store(now);
        SendF12Wake();
    }
}

void StopSleepWatchdog() {
    const HANDLE timer = g_sleepWatchdogTimer;
    g_sleepWatchdogTimer = nullptr;
    if (timer) DeleteTimerQueueTimer(nullptr, timer, INVALID_HANDLE_VALUE);
}

bool StartSleepWatchdog() {
    StopSleepWatchdog();
    return CreateTimerQueueTimer(
               &g_sleepWatchdogTimer, nullptr, SleepWatchdogCallback, nullptr,
               kSleepWatchdogPollMs, kSleepWatchdogPollMs,
               WT_EXECUTEDEFAULT) != FALSE;
}

bool WritePointer(void** slot, void* value) {
    DWORD oldProtect = 0;
    if (!VirtualProtect(slot, sizeof(void*), PAGE_READWRITE, &oldProtect)) return false;
    InterlockedExchangePointer(slot, value);
    DWORD unused = 0;
    VirtualProtect(slot, sizeof(void*), oldProtect, &unused);
    FlushInstructionCache(GetCurrentProcess(), slot, sizeof(void*));
    return true;
}

void** FindImportSlot(HMODULE module, const char* dllName, const char* procName) {
    auto* base = reinterpret_cast<std::uint8_t*>(module);
    auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return nullptr;
    auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return nullptr;
    const auto directory = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!directory.VirtualAddress) return nullptr;
    auto* descriptor = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(base + directory.VirtualAddress);
    for (; descriptor->Name; ++descriptor) {
        const char* importedDll = reinterpret_cast<const char*>(base + descriptor->Name);
        if (_stricmp(importedDll, dllName) != 0) continue;
        auto* names = reinterpret_cast<IMAGE_THUNK_DATA64*>(
            base + (descriptor->OriginalFirstThunk ? descriptor->OriginalFirstThunk
                                                   : descriptor->FirstThunk));
        auto* slots = reinterpret_cast<IMAGE_THUNK_DATA64*>(base + descriptor->FirstThunk);
        for (; names->u1.AddressOfData; ++names, ++slots) {
            if (IMAGE_SNAP_BY_ORDINAL64(names->u1.Ordinal)) continue;
            auto* item = reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(base + names->u1.AddressOfData);
            if (std::strcmp(reinterpret_cast<const char*>(item->Name), procName) == 0) {
                return reinterpret_cast<void**>(&slots->u1.Function);
            }
        }
    }
    return nullptr;
}

bool IsSystemCursor(HCURSOR cursor) {
    if (!cursor) return false;
    for (HCURSOR systemCursor : g_systemCursors) {
        if (cursor == systemCursor) return true;
    }
    return false;
}

HCURSOR WINAPI SetCursorWatch(HCURSOR cursor) {
    // Any Windows system cursor (arrow, I-beam, hand, resize, ...) means
    // ZBrush handed the cursor back to the OS, i.e. we are over LightBox or
    // some native UI surface rather than the sculpting canvas. Record that
    // during the 5ms classification window so the press passes through.
    if (g_gesture.load(std::memory_order_acquire) == Gesture::Classify &&
        IsSystemCursor(cursor)) {
        g_systemCursorSeen.store(true, std::memory_order_release);
    }
    return g_originalSetCursor(cursor);
}

bool InstallCursorWatch() {
    // Preload every standard system cursor so a handle can be recognised by
    // identity (system cursor handles are process-wide shared handles).
    for (size_t i = 0; i < std::size(kSystemCursorIds); ++i) {
        g_systemCursors[i] =
            LoadCursorW(nullptr, MAKEINTRESOURCEW(kSystemCursorIds[i]));
    }
    g_setCursorSlot = FindImportSlot(GetModuleHandleW(nullptr), "USER32.dll", "SetCursor");
    if (!g_setCursorSlot) return false;
    g_originalSetCursor = reinterpret_cast<SetCursorFn>(*g_setCursorSlot);
    return WritePointer(g_setCursorSlot, reinterpret_cast<void*>(&SetCursorWatch));
}

void RestoreCursorWatch() {
    if (g_setCursorSlot && g_originalSetCursor) {
        WritePointer(g_setCursorSlot, reinterpret_cast<void*>(g_originalSetCursor));
    }
    g_setCursorSlot = nullptr;
    g_originalSetCursor = nullptr;
}

void EndMiddle() {
    const HWND hwnd = g_zbrush.load();
    if (hwnd) SendMouse(hwnd, WM_MBUTTONUP, Modifiers());
}

bool WantLockNow() {
    const bool rightHeld = g_rightDown.load() ||
                           (GetAsyncKeyState(VK_RBUTTON) & 0x8000);
    const bool relockGrace = GetTickCount64() < g_rightRelockUntil.load();
    return g_enabled.load() && g_editMode.load() && !rightHeld && !relockGrace;
}

bool NeedPixolNow() {
    return g_enabled.load() && g_editMode.load() &&
           g_gesture.load() == Gesture::WaitModel;
}

bool NeedHoverNow() {
    if (!g_enabled.load() || !g_editMode.load()) return false;
    if (g_windowId.load() != kCanvasWindowId) return false;
    if (g_gesture.load() != Gesture::Idle) return false;
    if (GetAsyncKeyState(VK_LBUTTON) & 0x8000) return false;
    const ULONGLONG now = GetTickCount64();
    if (now - g_lastHoverMs.load() < 10) return false;
    g_lastHoverMs.store(now);
    return true;
}

void WriteSyncFloats(void* memOut, float want, float needPixol, float needHover,
                     float right) {
    if (!memOut) return;
    auto* out = static_cast<float*>(memOut);
    out[0] = want;
    out[1] = needPixol;
    out[2] = needHover;
    out[3] = right;
}

// Defensive check before writing into a ZBrush-provided pointer. ZBrush may
// hand the plugin a read-only view of the input memory block; writing to it
// would crash the host, so only writable committed pages are touched.
bool WritableRange(const void* pointer, size_t bytes) {
    if (!pointer) return false;
    if (bytes == 0) return false;
    // Walk every page the range touches: a block can straddle a page whose
    // protection differs from the first page's.
    auto* page = static_cast<const std::uint8_t*>(pointer);
    const auto* const end = page + bytes;
    while (page < end) {
        MEMORY_BASIC_INFORMATION info{};
        if (VirtualQuery(page, &info, sizeof(info)) == 0) return false;
        if (info.State != MEM_COMMIT) return false;
        // Strip only the low 8 bits of protection flags; keep guard/no-access
        // bits so a PAGE_GUARD page is never treated as writable.
        const DWORD protect = info.Protect & 0xFF;
        if (info.Protect & (PAGE_GUARD | PAGE_NOACCESS)) return false;
        const bool writable = protect == PAGE_READWRITE ||
                              protect == PAGE_EXECUTE_READWRITE ||
                              protect == PAGE_WRITECOPY ||
                              protect == PAGE_EXECUTE_WRITECOPY;
        if (!writable) return false;
        const auto* next =
            static_cast<const std::uint8_t*>(info.BaseAddress) + info.RegionSize;
        if (next <= page) return false;  // defensive: guard zero-size region
        page = next;
    }
    return true;
}

void ResetGesture() {
    const Gesture old = g_gesture.exchange(Gesture::Idle);
    const HWND hwnd = g_zbrush.load();
    if (hwnd) {
        KillTimer(hwnd, kClassifyTimer);
        KillTimer(hwnd, kStartTimer);
    }
    if (old == Gesture::WaitModel) EndMiddle();
}

void BeginWaitModel() {
    const HWND hwnd = g_zbrush.load();
    if (!hwnd || !(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    g_gesture.store(Gesture::WaitModel);
    SendMouse(hwnd, WM_MBUTTONDOWN, Modifiers() | MK_MBUTTON);
}

void FinishClassification() {
    if (g_gesture.load() != Gesture::Classify) return;
    const HWND hwnd = g_zbrush.load();
    if (!hwnd) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    KillTimer(hwnd, kClassifyTimer);
    const bool systemCursor = g_systemCursorSeen.load() ||
                              IsSystemCursor(g_downCursor) ||
                              IsSystemCursor(GetCursor());
    if (systemCursor) {
        if (GetAsyncKeyState(VK_LBUTTON) & 0x8000) {
            // The real down is still active in ZBrush: keep it, let moves flow
            // so click/drag behave naturally (no click-before-drag side
            // effect). The real up completes the gesture.
            g_gesture.store(Gesture::LightBoxPass);
        } else {
            // Quick click: the real up already passed through during Classify.
            g_gesture.store(Gesture::Idle);
        }
    } else {
        // Blank canvas: end the real press with a synthetic up, then enter the
        // middle-button wait (the press must not stay active on empty canvas).
        SendMouse(hwnd, WM_LBUTTONUP, Modifiers());
        BeginWaitModel();
    }
}

void StartSculpt() {
    const HWND hwnd = g_zbrush.load();
    if (!hwnd || g_gesture.load() != Gesture::StartPending ||
        !g_enabled.load() || !g_editMode.load() ||
        !(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    SendMouse(hwnd, WM_LBUTTONDOWN, Modifiers() | MK_LBUTTON);
    SendMouse(hwnd, WM_MOUSEMOVE, Modifiers() | MK_LBUTTON);
    g_gesture.store(Gesture::Sculpting);
}

LRESULT CALLBACK SubclassProc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam,
                              UINT_PTR, DWORD_PTR) {
    if (g_injecting.load(std::memory_order_acquire)) {
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_TIMER) {
        if (wparam == kClassifyTimer) {
            KillTimer(hwnd, kClassifyTimer);
            FinishClassification();
            return 0;
        }
        if (wparam == kStartTimer) {
            KillTimer(hwnd, kStartTimer);
            StartSculpt();
            return 0;
        }
    }
    if (message == WM_RBUTTONDOWN) {
        if (!g_enabled.load() || !g_cameraLock.load() || !g_editMode.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Swallow the press while the camera may still be locked; the ZScript
        // wake loop unlocks the camera and then replays the press.
        g_rightRelockUntil.store(0);
        g_rightDown.store(true);
        g_rightPending.store(true);
        g_rightUpPending.store(false);
        return 0;
    }
    if (message == WM_RBUTTONUP) {
        if (!g_enabled.load() || !g_cameraLock.load() || !g_editMode.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Relock the camera 2ms after the right button is released.
        g_rightRelockUntil.store(GetTickCount64() + 2);
        // If a swallowed press is still pending, keep the release too so the
        // replay delivers a complete click even for fast right clicks.
        if (g_rightDown.exchange(false) || g_rightPending.load()) {
            g_rightUpPending.store(true);
            return 0;
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_LBUTTONDOWN) {
        if (!g_enabled.load() || !g_editMode.load()) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (g_windowId.load() != kCanvasWindowId) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Model under the pointer (hover cache) -> normal sculpt, no probe.
        if (g_hoverReady.load() && g_hoverMat.load() != 0.0) {
            g_gesture.store(Gesture::ModelPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Ctrl keeps its native canvas gesture (marquee mask, etc).
        if (GetAsyncKeyState(VK_CONTROL) & 0x8000) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Ambiguous LightBox/blank-canvas point: pass the real down but keep it
        // active; swallow moves while classifying (so ZBrush cannot arm its
        // background-rotate gesture). The synthetic UP is deferred to the
        // classification result: LightBox keeps the press (natural click/drag),
        // blank canvas ends it before the middle-button wait.
        g_downCursor = GetCursor();
        g_systemCursorSeen.store(false);
        g_gesture.store(Gesture::Classify);
        const LRESULT result = DefSubclassProc(hwnd, message, wparam, lparam);
        SetTimer(hwnd, kClassifyTimer, kClassifyMs, nullptr);
        return result;
    }
    if (message == WM_MOUSEMOVE) {
        const Gesture state = g_gesture.load();
        // Swallow movement only while the probe classifies (5ms). After the
        // decision every state passes moves through.
        if (state == Gesture::Classify) {
            return 0;
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_LBUTTONUP) {
        const Gesture state = g_gesture.load();
        if (state == Gesture::Classify) {
            // The real down is still active; the real up completes the click.
            // No replay needed for quick clicks.
            const HWND zb = g_zbrush.load();
            if (zb) KillTimer(zb, kClassifyTimer);
            g_gesture.store(Gesture::Idle);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (state == Gesture::WaitModel || state == Gesture::StartPending) {
            // The probe already ended the press with a synthetic UP, so ZBrush
            // is not holding a left down here; swallow the physical UP instead
            // of delivering an orphan button-up.
            ResetGesture();
            return 0;
        }
        g_gesture.store(Gesture::Idle);
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_CANCELMODE || message == WM_CAPTURECHANGED) {
        if (!(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
            ResetGesture();
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_NCDESTROY) {
        StopSleepWatchdog();
        ResetGesture();
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightRelockUntil.store(0);
        RestoreCursorWatch();
        RemoveWindowSubclass(hwnd, SubclassProc, kSubclassId);
        g_zbrush.store(nullptr);
    }
    return DefSubclassProc(hwnd, message, wparam, lparam);
}

BOOL CALLBACK FindZBrush(HWND hwnd, LPARAM parameter) {
    wchar_t name[64]{};
    GetClassNameW(hwnd, name, 64);
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == GetCurrentProcessId() && std::wcscmp(name, L"ZBrush") == 0) {
        *reinterpret_cast<HWND*>(parameter) = hwnd;
        return FALSE;
    }
    return TRUE;
}

bool Install() {
    if (g_zbrush.load()) return true;
    HWND found = nullptr;
    EnumWindows(FindZBrush, reinterpret_cast<LPARAM>(&found));
    if (!found || !InstallCursorWatch()) return false;
    g_zbrush.store(found);
    if (!SetWindowSubclass(found, SubclassProc, kSubclassId, 0)) {
        RestoreCursorWatch();
        g_zbrush.store(nullptr);
        return false;
    }
    g_lastSleepHeartbeatMs.store(GetTickCount64());
    g_lastF12WakeMs.store(0);
    if (!StartSleepWatchdog()) {
        RemoveWindowSubclass(found, SubclassProc, kSubclassId);
        RestoreCursorWatch();
        g_zbrush.store(nullptr);
        return false;
    }
    // FileExecute may release its LoadLibrary reference after returning.
    // Pin this DLL because ZBrush now owns callbacks into it.
    HMODULE pinned = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                       GET_MODULE_HANDLE_EX_FLAG_PIN,
                       reinterpret_cast<LPCWSTR>(&Install), &pinned);
    return true;
}

}  // namespace

extern "C" __declspec(dllexport) int __cdecl Init(
    unsigned char*, double, void*, void*) {
    return Install() ? 1 : 0;
}

// Reliable DLL -> ZScript channel: the ZScript creates a 16-byte memory block
// and passes it to FileExecute. Per the plugin API the block pointer arrives
// in the input slot; ZBrush 2026 does not provide a usable output pointer, so
// all flags travel through the input block, which ZScript reads back.
extern "C" __declspec(dllexport) int __cdecl NlcrSync(
    unsigned char* text, double number, void* memIn, void* memOut) {
    g_enabled.store((static_cast<int>(number) & 1) != 0);
    g_editMode.store((static_cast<int>(number) & 2) != 0);
    g_cameraLock.store((static_cast<int>(number) & 4) != 0);
    g_windowId.store(text ? std::atoi(reinterpret_cast<char*>(text)) : -1);
    g_lastSleepHeartbeatMs.store(GetTickCount64());
    if (!g_enabled.load()) ResetGesture();
    // want = 1 lock, 0 unlock, -1 leave the camera switch alone. The -1 state
    // applies whenever the plugin is disabled or the camera lock feature is
    // off, so a disabled plugin never touches the camera (all features off).
    float want = -1.0f;
    if (g_enabled.load() && g_cameraLock.load()) {
        want = WantLockNow() ? 1.0f : 0.0f;
    }
    const float needPixol = NeedPixolNow() ? 1.0f : 0.0f;
    const float needHover = NeedHoverNow() ? 1.0f : 0.0f;
    const float right = g_rightDown.load() ? 1.0f : 0.0f;
    if (WritableRange(memIn, 16)) {
        WriteSyncFloats(memIn, want, needPixol, needHover, right);
    } else if (WritableRange(memOut, 16)) {
        WriteSyncFloats(memOut, want, needPixol, needHover, right);
    }
    return 1;
}

// Toggles whether the plugin owns the camera lock (and therefore also
// handles the right-button rotate gesture). When disabled the camera switch
// is left untouched and mouse input passes through unchanged.
extern "C" __declspec(dllexport) int __cdecl SetCameraLock(
    unsigned char*, double number, void*, void*) {
    g_cameraLock.store(number != 0.0);
    if (!g_cameraLock.load()) {
        // Abort any in-flight right-button or gesture handling.
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightRelockUntil.store(0);
        ResetGesture();
    }
    return g_cameraLock.load() ? 1 : 0;
}

// Opens an http(s) URL in the default browser. ZScript's ShellExecute is
// unreliable in ZBrush 2026, so the URL is passed through FileExecute and
// opened with the plain Win32 ShellExecuteA call instead.
extern "C" __declspec(dllexport) int __cdecl OpenUrl(
    unsigned char* text, double, void*, void*) {
    if (!text) return 0;
    const char* url = reinterpret_cast<char*>(text);
    if (std::strncmp(url, "http://", 7) != 0 &&
        std::strncmp(url, "https://", 8) != 0) {
        return 0;
    }
    const HINSTANCE result =
        ShellExecuteA(nullptr, "open", url, nullptr, nullptr, SW_SHOWNORMAL);
    return reinterpret_cast<INT_PTR>(result) > 32 ? 1 : 0;
}

// Called by the ZScript wake loop after it has released the camera lock.
// Replays the swallowed right-button press so ZBrush starts the rotate
// gesture with the camera already unlocked.
extern "C" __declspec(dllexport) int __cdecl ReplayRightDown(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load()) {
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        return 0;
    }
    const HWND hwnd = g_zbrush.load();
    if (g_rightPending.load() && hwnd) {
        g_rightPending.store(false);
        SendMouse(hwnd, WM_RBUTTONDOWN, Modifiers() | MK_RBUTTON);
        // The physical press may already be released; finish the click now so
        // ZBrush never receives a dangling down.
        if (!g_rightDown.load() || g_rightUpPending.load()) {
            g_rightUpPending.store(false);
            SendMouse(hwnd, WM_RBUTTONUP, Modifiers());
        }
        return 1;
    }
    if (g_rightUpPending.load() && hwnd) {
        g_rightUpPending.store(false);
        SendMouse(hwnd, WM_RBUTTONUP, Modifiers());
        return 1;
    }
    return 0;
}

// Hover cache update from the ZScript idle sampler. The cache is only used
// when the left button is not being pressed.
extern "C" __declspec(dllexport) int __cdecl SetHoverMat(
    unsigned char*, double number, void*, void*) {
    const Gesture state = g_gesture.load();
    const bool pressInProgress = (state == Gesture::Classify ||
                                  state == Gesture::WaitModel ||
                                  state == Gesture::StartPending ||
                                  state == Gesture::LightBoxPass ||
                                  state == Gesture::Sculpting);
    g_hoverMat.store(number);
    g_hoverReady.store(!pressInProgress);
    return g_hoverReady.load() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl UpdatePixol(
    unsigned char*, double number, void*, void*) {
    if (g_gesture.load() == Gesture::WaitModel && number != 0.0) {
        EndMiddle();
        g_gesture.store(Gesture::StartPending);
        SetTimer(g_zbrush.load(), kStartTimer,
                 static_cast<UINT>(std::max(1, g_startDelayMs.load())), nullptr);
    }
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl SetEnabled(
    unsigned char*, double number, void*, void*) {
    g_enabled.store(number != 0.0);
    if (!g_enabled.load()) {
        // Clear right-button and hover state when the plugin is disabled.
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightRelockUntil.store(0);
        g_hoverMat.store(0.0);
        g_hoverReady.store(false);
    }
    ResetGesture();
    return g_enabled.load() ? 1 : 0;
}

BOOL APIENTRY DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
