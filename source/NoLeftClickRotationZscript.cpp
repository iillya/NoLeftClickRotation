#include <windows.h>
#include <commctrl.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cwchar>

namespace {

constexpr UINT_PTR kSubclassId = 0x4E4C5232;
constexpr UINT_PTR kClassifyTimer = 0x4E4C5233;
constexpr UINT_PTR kStartTimer = 0x4E4C5234;
constexpr UINT kClassifyMs = 20;
constexpr UINT kSleepWatchdogPollMs = 25;
constexpr ULONGLONG kSleepHeartbeatTimeoutMs = 100;
constexpr ULONGLONG kF12RetryMs = 250;
constexpr int kCanvasWindowId = 1004;

enum class Gesture : int {
    Idle,
    UiPass,
    Classify,
    LightBoxClickDone,
    LightBoxPass,
    WaitModel,
    StartPending,
    Sculpting,
    ModelPass,
};

HINSTANCE g_module = nullptr;
HWND g_zbrush = nullptr;
std::atomic<bool> g_enabled{false};
std::atomic<bool> g_editMode{false};
std::atomic<int> g_windowId{-1};
std::atomic<double> g_mat{0.0};
std::atomic<int> g_startDelayMs{0};
std::atomic<Gesture> g_gesture{Gesture::Idle};
std::atomic<bool> g_injecting{false};
std::atomic<bool> g_arrowSeen{false};
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
POINT g_downPoint{};
HCURSOR g_arrow = nullptr;

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
    const HWND foreground = GetForegroundWindow();
    return foreground && foreground == g_zbrush;
}

void SendF12Wake() {
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
    if (g_enabled.load() && heartbeat != 0 &&
        now - heartbeat > kSleepHeartbeatTimeoutMs &&
        now - lastWake >= kF12RetryMs &&
        ZBrushIsForeground() && !modifiersHeld) {
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

HCURSOR WINAPI SetCursorWatch(HCURSOR cursor) {
    if (g_gesture.load(std::memory_order_acquire) == Gesture::Classify && cursor == g_arrow) {
        g_arrowSeen.store(true, std::memory_order_release);
    }
    return g_originalSetCursor(cursor);
}

bool InstallCursorWatch() {
    g_arrow = LoadCursorW(nullptr, IDC_ARROW);
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
    if (g_zbrush) SendMouse(g_zbrush, WM_MBUTTONUP, Modifiers());
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
    const auto* address = static_cast<const std::uint8_t*>(pointer);
    MEMORY_BASIC_INFORMATION info{};
    if (VirtualQuery(address, &info, sizeof(info)) == 0) return false;
    if (info.State != MEM_COMMIT) return false;
    const DWORD protect = info.Protect & 0xFF;
    return protect == PAGE_READWRITE || protect == PAGE_EXECUTE_READWRITE ||
           protect == PAGE_WRITECOPY || protect == PAGE_EXECUTE_WRITECOPY;
}

void ResetGesture() {
    const Gesture old = g_gesture.exchange(Gesture::Idle);
    if (g_zbrush) {
        KillTimer(g_zbrush, kClassifyTimer);
        KillTimer(g_zbrush, kStartTimer);
    }
    if (old == Gesture::WaitModel) EndMiddle();
}

void BeginWaitModel() {
    if (!g_zbrush || !(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    g_gesture.store(Gesture::WaitModel);
    SendMouse(g_zbrush, WM_MBUTTONDOWN, Modifiers() | MK_MBUTTON);
}

void FinishClassification() {
    if (g_gesture.load() != Gesture::Classify) return;
    const bool arrow = g_arrowSeen.load() || GetCursor() == g_arrow;
    if (arrow) {
        // Python V1: only keep waiting for a LightBox drag if the left button
        // is still physically held; a completed quick click returns to idle.
        g_gesture.store((GetAsyncKeyState(VK_LBUTTON) & 0x8000)
                            ? Gesture::LightBoxClickDone
                            : Gesture::Idle);
    } else {
        BeginWaitModel();
    }
}

void StartSculpt() {
    if (!g_zbrush || g_gesture.load() != Gesture::StartPending ||
        !g_enabled.load() || !g_editMode.load() ||
        !(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    SendMouse(g_zbrush, WM_LBUTTONDOWN, Modifiers() | MK_LBUTTON);
    SendMouse(g_zbrush, WM_MOUSEMOVE, Modifiers() | MK_LBUTTON);
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
        if (!g_enabled.load() || !g_editMode.load()) {
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
        // Python V1 relocks the camera 2ms after the right button is released.
        g_rightRelockUntil.store(GetTickCount64() + 2);
        if (!g_enabled.load() || !g_editMode.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
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
        GetCursorPos(&g_downPoint);
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
        // Ambiguous LightBox/blank-canvas point: pass the real down, finish it
        // with a synthetic UP, then classify from the resulting cursor.
        g_arrowSeen.store(false);
        g_gesture.store(Gesture::Classify);
        const LRESULT result = DefSubclassProc(hwnd, message, wparam, lparam);
        SendMouse(hwnd, WM_LBUTTONUP, Modifiers());
        SetTimer(hwnd, kClassifyTimer, kClassifyMs, nullptr);
        return result;
    }
    if (message == WM_MOUSEMOVE) {
        if (g_gesture.load() == Gesture::LightBoxClickDone &&
            (GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
            POINT point{};
            GetCursorPos(&point);
            if (std::abs(point.x - g_downPoint.x) >= GetSystemMetrics(SM_CXDRAG) ||
                std::abs(point.y - g_downPoint.y) >= GetSystemMetrics(SM_CYDRAG)) {
                SendMouse(hwnd, WM_LBUTTONDOWN, Modifiers() | MK_LBUTTON);
                SendMouse(hwnd, WM_MOUSEMOVE, Modifiers() | MK_LBUTTON);
                g_gesture.store(Gesture::LightBoxPass);
                return 0;
            }
            return 0;
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_LBUTTONUP) {
        const Gesture state = g_gesture.load();
        if (state == Gesture::Classify) {
            ResetGesture();
            return 0;
        }
        if (state == Gesture::LightBoxClickDone) {
            g_gesture.store(Gesture::Idle);
            return 0;
        }
        if (state == Gesture::WaitModel || state == Gesture::StartPending) {
            ResetGesture();
            return DefSubclassProc(hwnd, message, wparam, lparam);
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
        g_zbrush = nullptr;
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
    if (g_zbrush) return true;
    EnumWindows(FindZBrush, reinterpret_cast<LPARAM>(&g_zbrush));
    if (!g_zbrush || !InstallCursorWatch()) return false;
    if (!SetWindowSubclass(g_zbrush, SubclassProc, kSubclassId, 0)) {
        RestoreCursorWatch();
        g_zbrush = nullptr;
        return false;
    }
    g_lastSleepHeartbeatMs.store(GetTickCount64());
    g_lastF12WakeMs.store(0);
    if (!StartSleepWatchdog()) {
        RemoveWindowSubclass(g_zbrush, SubclassProc, kSubclassId);
        RestoreCursorWatch();
        g_zbrush = nullptr;
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

// number bit layout: bit0 enabled, bit1 Edit mode; integer Window ID is in text.
extern "C" __declspec(dllexport) int __cdecl UpdateState(
    unsigned char* text, double number, void*, void*) {
    g_enabled.store((static_cast<int>(number) & 1) != 0);
    g_editMode.store((static_cast<int>(number) & 2) != 0);
    g_windowId.store(text ? std::atoi(reinterpret_cast<char*>(text)) : -1);
    if (!g_enabled.load()) ResetGesture();
    return 1;
}

// Reliable DLL -> ZScript channel: the ZScript creates a 16-byte memory block
// and passes it to FileExecute. Per the plugin API the block pointer arrives
// in the input slot; ZBrush 2026 does not provide a usable output pointer, so
// all flags travel through the input block, which ZScript reads back.
extern "C" __declspec(dllexport) int __cdecl NlrSync(
    unsigned char* text, double number, void* memIn, void* memOut) {
    g_enabled.store((static_cast<int>(number) & 1) != 0);
    g_editMode.store((static_cast<int>(number) & 2) != 0);
    g_windowId.store(text ? std::atoi(reinterpret_cast<char*>(text)) : -1);
    g_lastSleepHeartbeatMs.store(GetTickCount64());
    if (!g_enabled.load()) ResetGesture();
    const float want = WantLockNow() ? 1.0f : 0.0f;
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

// Returns 1 when the camera should be locked: enabled + Edit mode + the right
// mouse button is not held and the 2ms post-release grace has elapsed.
extern "C" __declspec(dllexport) int __cdecl WantLock(
    unsigned char*, double, void*, void*) {
    return WantLockNow() ? 1 : 0;
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
    if (g_rightPending.load() && g_zbrush) {
        g_rightPending.store(false);
        SendMouse(g_zbrush, WM_RBUTTONDOWN, Modifiers() | MK_RBUTTON);
        // The physical press may already be released; finish the click now so
        // ZBrush never receives a dangling down.
        if (!g_rightDown.load() || g_rightUpPending.load()) {
            g_rightUpPending.store(false);
            SendMouse(g_zbrush, WM_RBUTTONUP, Modifiers());
        }
        return 1;
    }
    if (g_rightUpPending.load() && g_zbrush) {
        g_rightUpPending.store(false);
        SendMouse(g_zbrush, WM_RBUTTONUP, Modifiers());
        return 1;
    }
    return 0;
}

// Hover cache update from the ZScript idle sampler. The cache is only used
// when the left button is not being pressed (Python V1 behavior).
extern "C" __declspec(dllexport) int __cdecl SetHoverMat(
    unsigned char*, double number, void*, void*) {
    const Gesture state = g_gesture.load();
    const bool pressInProgress = (state == Gesture::Classify ||
                                  state == Gesture::WaitModel ||
                                  state == Gesture::StartPending ||
                                  state == Gesture::LightBoxClickDone ||
                                  state == Gesture::LightBoxPass ||
                                  state == Gesture::Sculpting);
    g_hoverMat.store(number);
    g_hoverReady.store(!pressInProgress);
    return g_hoverReady.load() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl Shutdown(
    unsigned char*, double, void*, void*) {
    if (g_zbrush) {
        StopSleepWatchdog();
        ResetGesture();
        RemoveWindowSubclass(g_zbrush, SubclassProc, kSubclassId);
        g_zbrush = nullptr;
    }
    RestoreCursorWatch();
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl NeedPixolPick(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load() || !g_editMode.load()) return 0;
    const Gesture state = g_gesture.load();
    return (state == Gesture::WaitModel) ? 1 : 0;
}

// Hover cache sampling gate: matching Python V1 _sample_hover (idle only,
// left button up, throttled to 10ms).
extern "C" __declspec(dllexport) int __cdecl NeedHover(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load() || !g_editMode.load()) return 0;
    if (g_windowId.load() != kCanvasWindowId) return 0;
    if (g_gesture.load() != Gesture::Idle) return 0;
    if (GetAsyncKeyState(VK_LBUTTON) & 0x8000) return 0;
    const ULONGLONG now = GetTickCount64();
    if (now - g_lastHoverMs.load() < 10) return 0;
    g_lastHoverMs.store(now);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl UpdatePixol(
    unsigned char*, double number, void*, void*) {
    g_mat.store(number);
    if (g_gesture.load() == Gesture::WaitModel && number != 0.0) {
        EndMiddle();
        g_gesture.store(Gesture::StartPending);
        SetTimer(g_zbrush, kStartTimer,
                 static_cast<UINT>(std::max(1, g_startDelayMs.load())), nullptr);
    }
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl SetDelay(
    unsigned char*, double number, void*, void*) {
    g_startDelayMs.store(std::max(
        0, std::min(10, static_cast<int>(std::lround(number)))));
    return g_startDelayMs.load();
}

extern "C" __declspec(dllexport) int __cdecl SetEnabled(
    unsigned char*, double number, void*, void*) {
    g_enabled.store(number != 0.0);
    if (!g_enabled.load()) {
        // Python V1 _toggle: clear right-button and hover state on disable.
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
        g_module = module;
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
