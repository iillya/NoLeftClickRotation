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
#include <string>
#include <vector>

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
constexpr ULONGLONG kHoverMaxAgeMs = 40;
constexpr LONG kHoverMaxDistancePx = 3;
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

HINSTANCE g_module = nullptr;
std::atomic<HWND> g_zbrush{nullptr};
std::atomic<bool> g_enabled{false};
std::atomic<bool> g_cameraLock{false};
std::atomic<bool> g_editMode{false};
std::atomic<int> g_windowId{-1};
std::atomic<int> g_startDelayMs{1};
std::atomic<Gesture> g_gesture{Gesture::Idle};
std::atomic<bool> g_injecting{false};
std::atomic<bool> g_systemCursorSeen{false};
std::atomic<bool> g_rightDown{false};
std::atomic<bool> g_rightPending{false};
std::atomic<bool> g_rightReleaseSettling{false};
std::atomic<bool> g_rightReleaseHoldWake{false};
std::atomic<bool> g_hoverReady{false};
std::atomic<double> g_hoverMat{0.0};
std::atomic<ULONGLONG> g_lastHoverMs{0};
std::atomic<ULONGLONG> g_hoverSampleMs{0};
std::atomic<LONG> g_hoverSampleX{0};
std::atomic<LONG> g_hoverSampleY{0};
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

bool StopSleepWatchdog() {
    const HANDLE timer = g_sleepWatchdogTimer;
    if (!timer) return true;
    if (!DeleteTimerQueueTimer(nullptr, timer, INVALID_HANDLE_VALUE)) {
        return false;
    }
    g_sleepWatchdogTimer = nullptr;
    return true;
}

void BeginRightReleaseSettle(HWND hwnd) {
    // The physical right-button release has already passed through ZBrush.
    // Keep the camera unlocked until it consumes a subsequent no-button state,
    // then cross one normal bridge wake before relocking.
    g_rightReleaseSettling.store(true, std::memory_order_release);
    g_rightReleaseHoldWake.store(false, std::memory_order_release);
    if (!PostMessageW(hwnd, WM_MOUSEMOVE, Modifiers(), CursorLParam(hwnd))) {
        g_rightReleaseSettling.store(false, std::memory_order_release);
        g_rightReleaseHoldWake.store(true, std::memory_order_release);
    }
}

bool StartSleepWatchdog() {
    if (!StopSleepWatchdog()) return false;
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
        // Do not overwrite a hook installed after ours. Such a hook may also
        // chain through SetCursorWatch, so keep our callback state alive when
        // the import slot is no longer owned by this plugin.
        if (*g_setCursorSlot == reinterpret_cast<void*>(&SetCursorWatch)) {
            if (WritePointer(g_setCursorSlot,
                             reinterpret_cast<void*>(g_originalSetCursor))) {
                g_setCursorSlot = nullptr;
                g_originalSetCursor = nullptr;
            }
        }
        return;
    }
    g_setCursorSlot = nullptr;
    g_originalSetCursor = nullptr;
}

std::wstring ParentPath(const std::wstring& path) {
    const size_t slash = path.find_last_of(L"\\/");
    return slash == std::wstring::npos ? std::wstring() : path.substr(0, slash);
}

std::wstring FindZFileUtilsPath() {
    std::vector<wchar_t> executablePath(32768, L'\0');
    const DWORD length = GetModuleFileNameW(
        nullptr, executablePath.data(),
        static_cast<DWORD>(executablePath.size()));
    if (!length || length >= static_cast<DWORD>(executablePath.size())) {
        return {};
    }

    const std::wstring root = ParentPath(executablePath.data());
    if (root.empty()) return {};
    const std::wstring candidates[] = {
        root + L"\\ZData\\ZPlugs64\\MacroData\\ZFileUtils64.dll",
        root + L"\\ZData\\ZPlugs64\\ZFileUtils64.dll",
        root + L"\\ZStartup\\ZPlugs64\\ZFileUtils64.dll",
    };
    for (const std::wstring& candidate : candidates) {
        const DWORD attributes = GetFileAttributesW(candidate.c_str());
        if (attributes != INVALID_FILE_ATTRIBUTES &&
            (attributes & FILE_ATTRIBUTE_DIRECTORY) == 0) {
            return candidate;
        }
    }
    return {};
}

std::string NarrowExistingPath(const std::wstring& path) {
    std::wstring compatiblePath = path;
    std::vector<wchar_t> shortPath(32768, L'\0');
    const DWORD shortLength = GetShortPathNameW(
        path.c_str(), shortPath.data(), static_cast<DWORD>(shortPath.size()));
    if (shortLength && shortLength < static_cast<DWORD>(shortPath.size())) {
        compatiblePath.assign(shortPath.data(), shortLength);
    }
    const int bytes = WideCharToMultiByte(
        CP_ACP, 0, compatiblePath.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (bytes <= 1) return {};
    std::string result(static_cast<size_t>(bytes), '\0');
    if (!WideCharToMultiByte(CP_ACP, 0, compatiblePath.c_str(), -1,
                             result.data(), bytes, nullptr, nullptr)) {
        return {};
    }
    result.pop_back();
    return result;
}

bool EnsureF12HotkeyConfig() {
    std::vector<wchar_t> modulePath(32768, L'\0');
    const DWORD length = GetModuleFileNameW(
        g_module, modulePath.data(), static_cast<DWORD>(modulePath.size()));
    if (!length || length >= static_cast<DWORD>(modulePath.size())) return false;

    // DLL -> NoLeftClickRotationData -> ZPlugs64 -> ZStartup.
    const std::wstring dataDir = ParentPath(modulePath.data());
    const std::wstring zplugsDir = ParentPath(dataDir);
    const std::wstring zstartupDir = ParentPath(zplugsDir);
    if (dataDir.empty() || zplugsDir.empty() || zstartupDir.empty()) return false;
    const std::wstring hotkeysDir = zstartupDir + L"\\HotKeys";
    const std::wstring hotkeysPath = hotkeysDir + L"\\StartupHotkeys.txt";

    std::vector<char> existing;
    HANDLE input = CreateFileW(hotkeysPath.c_str(), GENERIC_READ,
                               FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                               OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (input != INVALID_HANDLE_VALUE) {
        LARGE_INTEGER size{};
        if (!GetFileSizeEx(input, &size) || size.QuadPart < 0 ||
            size.QuadPart > 4 * 1024 * 1024) {
            CloseHandle(input);
            return false;
        }
        existing.resize(static_cast<size_t>(size.QuadPart));
        DWORD read = 0;
        if (!existing.empty() &&
            (!ReadFile(input, existing.data(),
                       static_cast<DWORD>(existing.size()), &read, nullptr) ||
             read != static_cast<DWORD>(existing.size()))) {
            CloseHandle(input);
            return false;
        }
        CloseHandle(input);
    }

    std::string upper(existing.begin(), existing.end());
    for (char& ch : upper) {
        if (ch >= 'a' && ch <= 'z') ch = static_cast<char>(ch - 'a' + 'A');
    }
    constexpr char kBinding[] =
        "[ZPLUGIN:NO LEFT CLICK ROTATION:RESET SLEEP,91]";
    if (upper.find(kBinding) != std::string::npos) return true;

    if (!CreateDirectoryW(hotkeysDir.c_str(), nullptr) &&
        GetLastError() != ERROR_ALREADY_EXISTS) {
        return false;
    }
    HANDLE output = CreateFileW(hotkeysPath.c_str(), FILE_APPEND_DATA,
                                FILE_SHARE_READ, nullptr, OPEN_ALWAYS,
                                FILE_ATTRIBUTE_NORMAL, nullptr);
    if (output == INVALID_HANDLE_VALUE) return false;
    std::string append;
    if (!existing.empty() && existing.back() != '\n' && existing.back() != '\r') {
        append = "\r\n";
    }
    append += "\r\n// No Left Click Rotation Sleep watchdog (F12)\r\n";
    append += kBinding;
    append += " // F12\r\n";
    DWORD written = 0;
    const bool ok = WriteFile(output, append.data(),
                              static_cast<DWORD>(append.size()),
                              &written, nullptr) != FALSE &&
                    written == static_cast<DWORD>(append.size());
    CloseHandle(output);
    return ok;
}

void EndMiddle() {
    const HWND hwnd = g_zbrush.load();
    if (hwnd) SendMouse(hwnd, WM_MBUTTONUP, Modifiers());
}

bool WantLockNow() {
    const bool releaseSettling =
        g_rightReleaseSettling.load(std::memory_order_acquire);
    // Once the post-release move has passed through ZBrush, hold exactly one
    // successful sync wake unlocked. NlcrSync clears this latch only after it
    // has actually written the unlock state back to ZScript.
    const bool releaseHoldWake =
        g_rightReleaseHoldWake.load(std::memory_order_acquire);
    const bool rightHeld = g_rightDown.load() ||
                           g_rightPending.load() ||
                           releaseSettling || releaseHoldWake ||
                           (GetAsyncKeyState(VK_RBUTTON) & 0x8000);
    return g_enabled.load() && g_editMode.load() && !rightHeld;
}

bool HoverMatchesCursor() {
    if (!g_hoverReady.load(std::memory_order_acquire)) return false;
    const ULONGLONG sampled = g_hoverSampleMs.load();
    if (!sampled || GetTickCount64() - sampled > kHoverMaxAgeMs) return false;
    POINT point{};
    if (!GetCursorPos(&point)) return false;
    return std::abs(point.x - g_hoverSampleX.load()) <= kHoverMaxDistancePx &&
           std::abs(point.y - g_hoverSampleY.load()) <= kHoverMaxDistancePx;
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
        g_rightDown.store(true);
        g_rightPending.store(true);
        g_rightReleaseSettling.store(false);
        g_rightReleaseHoldWake.store(false);
        // Wake the ZScript Sleep loop on the next message turn instead of
        // waiting for its 5ms timeout. This move carries no button flags and
        // does not move the cursor, so ZBrush cannot start a right gesture
        // before ReplayRightDown delivers the real press after camera unlock.
        (void)PostMessageW(hwnd, WM_MOUSEMOVE, Modifiers(), CursorLParam(hwnd));
        return 0;
    }
    if (message == WM_RBUTTONUP) {
        const bool ownedPress = g_rightDown.exchange(false);
        const bool pendingReplay = g_rightPending.exchange(false);
        if (!g_enabled.load() || !g_cameraLock.load() || !g_editMode.load()) {
            g_rightReleaseSettling.store(false);
            g_rightReleaseHoldWake.store(false);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // The physical DOWN was swallowed, but the physical UP is passed
        // immediately. This ends a replayed gesture without waiting for the
        // ZScript bridge and avoids any synthetic-release tail movement.
        const LRESULT result =
            DefSubclassProc(hwnd, message, wparam, lparam);
        if (ownedPress || pendingReplay) BeginRightReleaseSettle(hwnd);
        return result;
    }
    if (message == WM_LBUTTONDOWN) {
        if (!g_enabled.load() || !g_editMode.load()) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Camera-lock-only checked: the left button is never touched and is
        // passed through unchanged. The camera lock prevents blank-canvas
        // rotation; the right button still unlocks/relocks the camera.
        if (g_cameraLock.load()) {
            g_gesture.store(Gesture::Idle);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (g_windowId.load() != kCanvasWindowId) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Model under the pointer (hover cache) -> normal sculpt, no probe.
        if (HoverMatchesCursor() && g_hoverMat.load() != 0.0) {
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
        if (!SetTimer(hwnd, kClassifyTimer, kClassifyMs, nullptr)) {
            FinishClassification();
        }
        return result;
    }
    if (message == WM_MOUSEMOVE) {
        const Gesture state = g_gesture.load();
        // Swallow movement only while the probe classifies (5ms). After the
        // decision every state passes moves through.
        if (state == Gesture::Classify) {
            return 0;
        }
        const LRESULT result = DefSubclassProc(hwnd, message, wparam, lparam);
        if (g_rightReleaseSettling.load(std::memory_order_acquire) &&
            (wparam & MK_RBUTTON) == 0) {
            // The no-button state has entered ZBrush. Start the grace period
            // here (after the synthetic UP), then let the bridge cross one
            // normal 5ms Sleep cycle before it restores the camera lock.
            g_rightReleaseSettling.store(false, std::memory_order_release);
            g_rightReleaseHoldWake.store(true, std::memory_order_release);
        }
        return result;
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
        (void)StopSleepWatchdog();
        ResetGesture();
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightReleaseSettling.store(false);
        g_rightReleaseHoldWake.store(false);
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
    (void)EnsureF12HotkeyConfig();
    return Install() ? 1 : 0;
}

// Return the path of ZBrush's own ZFileUtils DLL to ZScript. This function
// deliberately does not load or call ZFileUtils: ZBrush invokes it later via
// FileExecute, preserving the host's supported plugin call boundary.
extern "C" __declspec(dllexport) int __cdecl GetZFileUtilsPath(
    unsigned char*, double, void* memIn, void* memOut) {
    constexpr size_t kPathBufferBytes = 1024;
    void* destination = WritableRange(memIn, kPathBufferBytes) ? memIn : nullptr;
    if (!destination && WritableRange(memOut, kPathBufferBytes)) {
        destination = memOut;
    }
    if (!destination) return 0;

    std::memset(destination, 0, kPathBufferBytes);
    const std::string path = NarrowExistingPath(FindZFileUtilsPath());
    if (path.empty() || path.size() >= kPathBufferBytes) return 0;
    std::memcpy(destination, path.c_str(), path.size() + 1);
    return 1;
}

// Reliable DLL -> ZScript channel: the ZScript creates a 16-byte memory block
// and passes it to FileExecute. Per the plugin API the block pointer arrives
// in the input slot; ZBrush 2026 does not provide a usable output pointer, so
// all flags travel through the input block, which ZScript reads back.
extern "C" __declspec(dllexport) int __cdecl NlcrSync(
    unsigned char* text, double number, void* memIn, void* memOut) {
    const bool previousEdit = g_editMode.load();
    const int previousWindow = g_windowId.load();
    const bool editMode = (static_cast<int>(number) & 2) != 0;
    const int windowId = text ? std::atoi(reinterpret_cast<char*>(text)) : -1;
    g_enabled.store((static_cast<int>(number) & 1) != 0);
    g_editMode.store(editMode);
    g_cameraLock.store((static_cast<int>(number) & 4) != 0);
    g_windowId.store(windowId);
    if (previousEdit != editMode || previousWindow != windowId) {
        g_hoverReady.store(false, std::memory_order_release);
        g_hoverSampleMs.store(0);
    }
    if (previousEdit && !editMode) ResetGesture();
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
    // Keep the bridge at 1ms only while a physical/pending right gesture still
    // needs replay. Release settling/grace deliberately returns 0 so ZScript
    // crosses one normal 5ms scheduling boundary before relocking.
    const bool rightActive = g_rightDown.load() || g_rightPending.load();
    const float right = rightActive ? 1.0f : 0.0f;
    bool wrote = false;
    if (WritableRange(memIn, 16)) {
        WriteSyncFloats(memIn, want, needPixol, needHover, right);
        wrote = true;
    } else if (WritableRange(memOut, 16)) {
        WriteSyncFloats(memOut, want, needPixol, needHover, right);
        wrote = true;
    }
    // A heartbeat is valid only when the ZScript-owned memory exchange
    // succeeded. Otherwise the watchdog must restart the bridge instead of
    // treating a one-way FileExecute call as healthy.
    if (wrote) {
        g_lastSleepHeartbeatMs.store(GetTickCount64());
        if (!g_rightReleaseSettling.load(std::memory_order_acquire)) {
            g_rightReleaseHoldWake.store(false, std::memory_order_release);
        }
    }
    return wrote ? 1 : 0;
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
        g_rightReleaseSettling.store(false);
        g_rightReleaseHoldWake.store(false);
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
// Replays the swallowed right-button press after the camera is unlocked.
extern "C" __declspec(dllexport) int __cdecl ReplayRightDown(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load()) {
        g_rightPending.store(false);
        return 0;
    }
    const HWND hwnd = g_zbrush.load();
    if (g_rightPending.load() && hwnd) {
        g_rightPending.store(false);
        if (g_rightDown.load() &&
            (GetAsyncKeyState(VK_RBUTTON) & 0x8000)) {
            SendMouse(hwnd, WM_RBUTTONDOWN, Modifiers() | MK_RBUTTON);
            return 1;
        }
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
    POINT point{};
    const bool havePoint = GetCursorPos(&point) != FALSE;
    g_hoverReady.store(false, std::memory_order_release);
    g_hoverMat.store(number);
    if (!pressInProgress && havePoint) {
        g_hoverSampleX.store(point.x);
        g_hoverSampleY.store(point.y);
        g_hoverSampleMs.store(GetTickCount64());
        g_hoverReady.store(true, std::memory_order_release);
    }
    return g_hoverReady.load() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl UpdatePixol(
    unsigned char*, double number, void*, void*) {
    if (g_gesture.load() == Gesture::WaitModel && number != 0.0) {
        const HWND hwnd = g_zbrush.load();
        if (!hwnd) {
            g_gesture.store(Gesture::Idle);
            return 0;
        }
        EndMiddle();
        g_gesture.store(Gesture::StartPending);
        if (!SetTimer(hwnd, kStartTimer,
                      static_cast<UINT>(std::max(1, g_startDelayMs.load())),
                      nullptr)) {
            StartSculpt();
        }
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
        g_rightReleaseSettling.store(false);
        g_rightReleaseHoldWake.store(false);
        g_hoverMat.store(0.0);
        g_hoverReady.store(false);
        g_hoverSampleMs.store(0);
    }
    ResetGesture();
    return g_enabled.load() ? 1 : 0;
}

// ZBrush 2022 compatibility channel: the ZScript wake loop pushes its current
// switch/edit/window state via the plain FileExecute text+number arguments
// (no memory-block round trip, which is a 2026-only extension) and then reads
// the desired camera state back from the return value.
extern "C" __declspec(dllexport) int __cdecl SyncState(
    unsigned char* text, double number, void*, void*) {
    const bool previousEdit = g_editMode.load();
    const int previousWindow = g_windowId.load();
    const bool editMode = (static_cast<int>(number) & 2) != 0;
    const int windowId = text ? std::atoi(reinterpret_cast<char*>(text)) : -1;
    g_enabled.store((static_cast<int>(number) & 1) != 0);
    g_editMode.store(editMode);
    g_cameraLock.store((static_cast<int>(number) & 4) != 0);
    g_windowId.store(windowId);
    if (previousEdit != editMode || previousWindow != windowId) {
        g_hoverReady.store(false, std::memory_order_release);
        g_hoverSampleMs.store(0);
    }
    if (previousEdit && !editMode) ResetGesture();
    if (!g_enabled.load()) ResetGesture();
    // Every successful state sync proves the ZScript Sleep loop is alive.
    // Refresh the heartbeat exactly like NlcrSync does on the 2026 channel;
    // without this the watchdog treats a healthy 2022 bridge as dead and
    // floods F12, which re-triggers Reset Sleep and stacks Sleep loops until
    // the host crashes.
    g_lastSleepHeartbeatMs.store(GetTickCount64());
    return 1;
}

// Returns 1 = lock, 0 = unlock, -1 = leave the camera switch alone (plugin
// disabled or the camera-lock-only feature is off).
extern "C" __declspec(dllexport) int __cdecl GetCameraLock(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load() || !g_cameraLock.load()) return -1;
    return WantLockNow() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl GetNeedHover(
    unsigned char*, double, void*, void*) {
    return NeedHoverNow() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl GetNeedPixol(
    unsigned char*, double, void*, void*) {
    return NeedPixolNow() ? 1 : 0;
}

BOOL APIENTRY DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_module = module;
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
