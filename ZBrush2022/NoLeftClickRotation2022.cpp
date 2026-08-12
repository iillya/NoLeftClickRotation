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
constexpr UINT_PTR kRightStartTimer = 0x4E4C5235;
constexpr UINT_PTR kProbeTimer = 0x4E4C5236;
constexpr UINT kClassifyMs = 20;
constexpr UINT kProbeMs = 8;
constexpr ULONGLONG kRightRelockDelayMs = 2;
constexpr int kCanvasWindowId = 1004;

enum class Gesture : int {
    Idle,
    UiPass,
    ModelPass,
    Probe,
    Classify,
    LightBoxClickDone,
    LightBoxPass,
    WaitModel,
    StartPending,
    Sculpting,
};

HINSTANCE g_module = nullptr;
HWND g_zbrush = nullptr;
WNDPROC g_unused = nullptr;
std::atomic<bool> g_enabled{false};
std::atomic<bool> g_editMode{false};
std::atomic<int> g_windowId{-1};
std::atomic<double> g_mat{0.0};
std::atomic<int> g_startDelayMs{0};
std::atomic<Gesture> g_gesture{Gesture::Idle};
std::atomic<bool> g_physicalLeft{false};
std::atomic<bool> g_physicalRight{false};
std::atomic<bool> g_rightPending{false};
std::atomic<bool> g_rightForwarded{false};
std::atomic<bool> g_restartingRight{false};
std::atomic<bool> g_injecting{false};
std::atomic<bool> g_arrowSeen{false};
POINT g_downPoint{};
HCURSOR g_arrow = nullptr;
ULONGLONG g_rightRelockAt = 0;

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

void ResetGesture() {
    const Gesture old = g_gesture.exchange(Gesture::Idle);
    if (g_zbrush) {
        KillTimer(g_zbrush, kClassifyTimer);
        KillTimer(g_zbrush, kStartTimer);
        KillTimer(g_zbrush, kRightStartTimer);
        KillTimer(g_zbrush, kProbeTimer);
    }
    if (old == Gesture::Probe || old == Gesture::WaitModel) EndMiddle();
}

void BeginProbe() {
    if (!g_zbrush || !g_physicalLeft.load()) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    g_gesture.store(Gesture::Probe);
    SendMouse(g_zbrush, WM_MBUTTONDOWN, Modifiers() | MK_MBUTTON);
    SetTimer(g_zbrush, kProbeTimer, kProbeMs, nullptr);
}

void ClassifyAfterProbe() {
    if (g_gesture.load() != Gesture::Probe) return;
    EndMiddle();
    if (!g_physicalLeft.load()) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    g_arrowSeen.store(false);
    g_gesture.store(Gesture::Classify);
    SendMouse(g_zbrush, WM_LBUTTONDOWN, Modifiers() | MK_LBUTTON);
    SendMouse(g_zbrush, WM_LBUTTONUP, Modifiers());
    SetTimer(g_zbrush, kClassifyTimer, kClassifyMs, nullptr);
}

void BeginWaitModel() {
    if (!g_zbrush || !g_physicalLeft.load()) {
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
        g_gesture.store(g_physicalLeft.load() ? Gesture::LightBoxClickDone
                                              : Gesture::Idle);
    } else {
        BeginWaitModel();
    }
}

void StartSculpt() {
    if (!g_zbrush || g_gesture.load() != Gesture::StartPending ||
        !g_physicalLeft.load() || !g_editMode.load() || !g_enabled.load()) {
        g_gesture.store(Gesture::Idle);
        return;
    }
    SendMouse(g_zbrush, WM_LBUTTONDOWN, Modifiers() | MK_LBUTTON);
    SendMouse(g_zbrush, WM_MOUSEMOVE, Modifiers() | MK_LBUTTON);
    g_gesture.store(Gesture::Sculpting);
}

void RestartPhysicalRight() {
    INPUT inputs[2]{};
    inputs[0].type = INPUT_MOUSE;
    inputs[0].mi.dwFlags = MOUSEEVENTF_RIGHTUP;
    inputs[1].type = INPUT_MOUSE;
    inputs[1].mi.dwFlags = MOUSEEVENTF_RIGHTDOWN;
    g_restartingRight.store(true);
    if (SendInput(2, inputs, sizeof(INPUT)) != 2) {
        g_restartingRight.store(false);
    }
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
        if (wparam == kRightStartTimer) {
            KillTimer(hwnd, kRightStartTimer);
            if (g_enabled.load() && g_editMode.load() &&
                g_physicalRight.load() && g_rightPending.exchange(false)) {
                RestartPhysicalRight();
                g_rightForwarded.store(true);
            }
            return 0;
        }
        if (wparam == kProbeTimer) {
            KillTimer(hwnd, kProbeTimer);
            ClassifyAfterProbe();
            return 0;
        }
    }
    if (message == WM_LBUTTONDOWN) {
        g_physicalLeft.store(true);
        if (!g_enabled.load() || !g_editMode.load()) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        GetCursorPos(&g_downPoint);
        if (g_windowId.load() != kCanvasWindowId) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Never expose a physical canvas press to ZBrush. Even a nonzero
        // cached PixolPick can belong to the previous pointer/frame and would
        // occasionally start a native rotation before the cache refreshes.
        // Probe the current point under a middle-button gesture instead.
        BeginProbe();
        return 0;
    }
    if (message == WM_RBUTTONDOWN) {
        if (g_restartingRight.exchange(false)) {
            g_physicalRight.store(true);
            g_rightForwarded.store(true);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        g_physicalRight.store(true);
        g_rightRelockAt = 0;
        g_rightPending.store(false);
        g_rightForwarded.store(true);
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_RBUTTONUP) {
        if (g_restartingRight.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        g_physicalRight.store(false);
        g_rightRelockAt = GetTickCount64() + kRightRelockDelayMs;
        if (g_rightPending.exchange(false)) {
            g_rightForwarded.store(false);
            return 0;
        }
        g_rightForwarded.store(false);
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_MOUSEMOVE) {
        if (g_gesture.load() == Gesture::LightBoxClickDone && g_physicalLeft.load()) {
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
        g_physicalLeft.store(false);
        const Gesture state = g_gesture.load();
        if (state == Gesture::Probe) {
            ResetGesture();
            return 0;
        }
        if (state == Gesture::Classify || state == Gesture::LightBoxClickDone) {
            return 0;
        }
        if (state == Gesture::WaitModel || state == Gesture::StartPending) {
            ResetGesture();
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        g_gesture.store(Gesture::Idle);
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_NCDESTROY) {
        ResetGesture();
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

extern "C" __declspec(dllexport) int __cdecl NeedPixolPick(
    unsigned char*, double, void*, void*) {
    const Gesture state = g_gesture.load();
    return (g_enabled.load() && g_editMode.load()) ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl UpdatePixol(
    unsigned char*, double number, void*, void*) {
    g_mat.store(number);
    if (g_gesture.load() == Gesture::Probe && number != 0.0) {
        KillTimer(g_zbrush, kProbeTimer);
        EndMiddle();
        g_gesture.store(Gesture::StartPending);
        SetTimer(g_zbrush, kStartTimer,
                 static_cast<UINT>(std::max(1, g_startDelayMs.load())), nullptr);
    }
    else if (g_gesture.load() == Gesture::WaitModel && number != 0.0) {
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
    ResetGesture();
    if (!g_enabled.load()) {
        g_physicalRight.store(false);
        g_rightPending.store(false);
        g_rightForwarded.store(false);
        g_rightRelockAt = 0;
    }
    return g_enabled.load() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl CameraLockApplied(
    unsigned char*, double number, void*, void*) {
    const bool locked = number != 0.0;
    if (!locked && g_rightPending.exchange(false) &&
        g_physicalRight.load() && g_zbrush) {
        // Defer the real input transition until FileExecute returns to
        // ZBrush's normal message loop.
        g_rightPending.store(true);
        SetTimer(g_zbrush, kRightStartTimer, 1, nullptr);
    }
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl CameraLockWanted(
    unsigned char*, double, void*, void*) {
    return 0;
}

extern "C" __declspec(dllexport) int __cdecl Shutdown(
    unsigned char*, double, void*, void*) {
    if (g_zbrush) {
        ResetGesture();
        RemoveWindowSubclass(g_zbrush, SubclassProc, kSubclassId);
        g_zbrush = nullptr;
    }
    RestoreCursorWatch();
    return 1;
}

BOOL APIENTRY DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_module = module;
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
