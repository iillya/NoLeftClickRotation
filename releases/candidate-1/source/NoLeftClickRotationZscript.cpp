#include <windows.h>
#include <commctrl.h>
#include <mmsystem.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <cstdio>
#include <string>
#include <type_traits>
#include <vector>

namespace {

constexpr UINT_PTR kSubclassId = 0x4E4C5232;
constexpr UINT_PTR kClassifyTimer = 0x4E4C5233;
constexpr UINT_PTR kStartTimer = 0x4E4C5234;
constexpr UINT_PTR kWaitModelTimer = 0x4E4C5235;
constexpr UINT_PTR kRelockTimer = 0x4E4C5236;
constexpr UINT_PTR kRightReplayTimer = 0x4E4C5237;
constexpr UINT kClassifyMs = 5;
constexpr UINT kWaitModelPollMs = 5;
constexpr UINT kRelockMs = 2;
constexpr UINT kRightReplayMs = 1;
constexpr ULONGLONG kBridgeTimeoutMs = 25;
constexpr int kCanvasWindowId = 1004;
constexpr wchar_t kOverlayClass[] = L"NLR2022DiagnosticOverlay";

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

enum class SampleRequest : int {
    None,
    Sync,
    WaitModel,
};

HINSTANCE g_module = nullptr;
HWND g_zbrush = nullptr;
HWND g_overlay = nullptr;
std::atomic<bool> g_enabled{false};
std::atomic<bool> g_editMode{false};
std::atomic<int> g_editValueRaw{-1};
std::atomic<int> g_editFlagsRaw{-1};
std::atomic<int> g_windowId{-1};
std::atomic<double> g_mat{0.0};
std::atomic<int> g_startDelayMs{0};
std::atomic<Gesture> g_gesture{Gesture::Idle};
std::atomic<bool> g_injecting{false};
std::atomic<bool> g_arrowSeen{false};
std::atomic<bool> g_rightDown{false};
std::atomic<bool> g_rightPending{false};
std::atomic<bool> g_rightUpPending{false};
std::atomic<bool> g_rightReplayScheduled{false};
std::atomic<bool> g_rightReplayDelivered{false};
std::atomic<ULONGLONG> g_rightRelockUntil{0};
std::atomic<bool> g_timerPeriodSet{false};
std::atomic<SampleRequest> g_sampleRequest{SampleRequest::None};
std::atomic<bool> g_bridgeOutstanding{false};
std::atomic<ULONGLONG> g_bridgeSentAt{0};
std::atomic<bool> g_bridgeConfirmed{false};
std::atomic<unsigned long long> g_f12Sent{0};
std::atomic<unsigned long long> g_f12WindowSeen{0};
std::atomic<int> g_bridgeHotkeyRaw{-1};
std::atomic<int> g_bridgeHotkeyBefore{-1};
std::atomic<unsigned long long> g_hotkeyRepairCount{0};
std::atomic<unsigned long long> g_bridgeReceived{0};
std::atomic<bool> g_lastSendOk{false};
std::atomic<ULONGLONG> g_lastBridgeReceivedAt{0};
POINT g_downPoint{};
HCURSOR g_arrow = nullptr;

bool WantLockNow();
void UpdateDiagnosticOverlay();

void DbgLog(const char* msg) {
    char path[MAX_PATH];
    if (GetTempPathA(MAX_PATH, path)) {
        std::strcat(path, "nlr2022_dbg.log");
        FILE* stream = nullptr;
        if (fopen_s(&stream, path, "a") == 0 && stream) {
            fprintf(stream, "%llu %s\n",
                    static_cast<unsigned long long>(GetTickCount64()), msg);
            fclose(stream);
        }
    }
}

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

std::wstring ParentDirectory(std::wstring path) {
    while (!path.empty() && (path.back() == L'\\' || path.back() == L'/')) {
        path.pop_back();
    }
    const size_t separator = path.find_last_of(L"\\/");
    return separator == std::wstring::npos ? std::wstring() :
                                             path.substr(0, separator);
}

std::wstring StartupHotkeysPath() {
    wchar_t modulePath[32768]{};
    const DWORD length = GetModuleFileNameW(
        g_module, modulePath, static_cast<DWORD>(std::size(modulePath)));
    if (length == 0 || length >= std::size(modulePath)) return {};
    // DLL: ZStartup/ZPlugs64/NoLeftClickRotation2022Data/*.dll
    std::wstring startup = ParentDirectory(modulePath);
    startup = ParentDirectory(startup);
    startup = ParentDirectory(startup);
    if (startup.empty()) return {};
    return startup + L"\\HotKeys\\StartupHotkeys.txt";
}

template <typename String>
void UpsertBridgeHotkeyLine(String& contents) {
    using Char = typename String::value_type;
    const String marker = [] {
        if constexpr (std::is_same_v<Char, wchar_t>) {
            return String(L"[ZPLUGIN:NO LEFT CLICK ROTATION:PIXOL BRIDGE,");
        } else {
            return String("[ZPLUGIN:NO LEFT CLICK ROTATION:PIXOL BRIDGE,");
        }
    }();
    const String replacement = [] {
        if constexpr (std::is_same_v<Char, wchar_t>) {
            return String(L"[ZPLUGIN:NO LEFT CLICK ROTATION:PIXOL BRIDGE,91] // F12");
        } else {
            return String("[ZPLUGIN:NO LEFT CLICK ROTATION:PIXOL BRIDGE,91] // F12");
        }
    }();
    const String block = [] {
        if constexpr (std::is_same_v<Char, wchar_t>) {
            return String(L"// No Left Click Rotation internal bridge (F12)\r\n"
                          L"[ZPLUGIN:NO LEFT CLICK ROTATION:PIXOL BRIDGE,91] // F12\r\n");
        } else {
            return String("// No Left Click Rotation internal bridge (F12)\r\n"
                          "[ZPLUGIN:NO LEFT CLICK ROTATION:PIXOL BRIDGE,91] // F12\r\n");
        }
    }();

    size_t found = contents.find(marker);
    if (found == String::npos) {
        if (!contents.empty() && contents.back() != static_cast<Char>('\n') &&
            contents.back() != static_cast<Char>('\r')) {
            contents.append(1, static_cast<Char>('\r'));
            contents.append(1, static_cast<Char>('\n'));
        }
        contents += block;
        return;
    }

    // Replace the first entry and remove any accidental duplicate entries.
    size_t lineStart = contents.rfind(static_cast<Char>('\n'), found);
    lineStart = lineStart == String::npos ? 0 : lineStart + 1;
    size_t lineEnd = contents.find(static_cast<Char>('\n'), found);
    const bool hasLf = lineEnd != String::npos;
    if (!hasLf) lineEnd = contents.size();
    size_t contentEnd = lineEnd;
    if (contentEnd > lineStart &&
        contents[contentEnd - 1] == static_cast<Char>('\r')) {
        --contentEnd;
    }
    contents.replace(lineStart, contentEnd - lineStart, replacement);

    size_t searchFrom = lineStart + replacement.size();
    while ((found = contents.find(marker, searchFrom)) != String::npos) {
        size_t duplicateStart = contents.rfind(static_cast<Char>('\n'), found);
        duplicateStart = duplicateStart == String::npos ? 0 : duplicateStart + 1;
        size_t duplicateEnd = contents.find(static_cast<Char>('\n'), found);
        if (duplicateEnd == String::npos) {
            duplicateEnd = contents.size();
        } else {
            ++duplicateEnd;
        }
        contents.erase(duplicateStart, duplicateEnd - duplicateStart);
        searchFrom = lineStart + replacement.size();
    }
}

bool EnsureBridgeHotkeyConfig() {
    const std::wstring path = StartupHotkeysPath();
    if (path.empty()) return false;
    const std::wstring directory = ParentDirectory(path);
    CreateDirectoryW(directory.c_str(), nullptr);

    std::vector<unsigned char> bytes;
    HANDLE input = CreateFileW(path.c_str(), GENERIC_READ,
                               FILE_SHARE_READ | FILE_SHARE_WRITE |
                                   FILE_SHARE_DELETE,
                               nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL,
                               nullptr);
    if (input != INVALID_HANDLE_VALUE) {
        LARGE_INTEGER size{};
        if (GetFileSizeEx(input, &size) && size.QuadPart >= 0 &&
            size.QuadPart <= 16 * 1024 * 1024) {
            bytes.resize(static_cast<size_t>(size.QuadPart));
            DWORD read = 0;
            if (!bytes.empty() &&
                (!ReadFile(input, bytes.data(), static_cast<DWORD>(bytes.size()),
                           &read, nullptr) || read != bytes.size())) {
                bytes.clear();
            }
        }
        CloseHandle(input);
    }

    if (bytes.empty()) {
        const char header[] = "//ZBrush Hotkeys\r\n";
        bytes.assign(header, header + sizeof(header) - 1);
    }

    if (bytes.size() >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE) {
        std::wstring text;
        const size_t characters = (bytes.size() - 2) / sizeof(wchar_t);
        text.assign(reinterpret_cast<const wchar_t*>(bytes.data() + 2),
                    characters);
        UpsertBridgeHotkeyLine(text);
        bytes.resize(2 + text.size() * sizeof(wchar_t));
        bytes[0] = 0xFF;
        bytes[1] = 0xFE;
        if (!text.empty()) {
            std::memcpy(bytes.data() + 2, text.data(),
                        text.size() * sizeof(wchar_t));
        }
    } else if (bytes.size() >= 2 && bytes[0] == 0xFE && bytes[1] == 0xFF) {
        DbgLog("hotkey config: UTF-16BE is unsupported");
        return false;
    } else {
        std::string text(reinterpret_cast<const char*>(bytes.data()),
                         bytes.size());
        UpsertBridgeHotkeyLine(text);
        bytes.assign(text.begin(), text.end());
    }

    const std::wstring temporary = path + L".nlr.tmp";
    HANDLE output = CreateFileW(temporary.c_str(), GENERIC_WRITE, 0, nullptr,
                                CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (output == INVALID_HANDLE_VALUE) return false;
    DWORD written = 0;
    const bool wrote = WriteFile(output, bytes.data(),
                                 static_cast<DWORD>(bytes.size()), &written,
                                 nullptr) &&
                       written == bytes.size();
    if (wrote) FlushFileBuffers(output);
    CloseHandle(output);
    if (!wrote || !MoveFileExW(temporary.c_str(), path.c_str(),
                               MOVEFILE_REPLACE_EXISTING |
                                   MOVEFILE_WRITE_THROUGH)) {
        DeleteFileW(temporary.c_str());
        return false;
    }
    return true;
}

bool AnyKeyboardModifierHeld() {
    return (GetAsyncKeyState(VK_SHIFT) & 0x8000) ||
           (GetAsyncKeyState(VK_CONTROL) & 0x8000) ||
           (GetAsyncKeyState(VK_MENU) & 0x8000);
}

struct HeldModifier {
    WORD vk;
    DWORD flags;
};

size_t CaptureHeldModifiers(HeldModifier (&held)[6]) {
    const HeldModifier candidates[] = {
        {VK_LSHIFT, 0},
        {VK_RSHIFT, 0},
        {VK_LCONTROL, 0},
        {VK_RCONTROL, KEYEVENTF_EXTENDEDKEY},
        {VK_LMENU, 0},
        {VK_RMENU, KEYEVENTF_EXTENDEDKEY},
    };
    size_t count = 0;
    for (const HeldModifier& candidate : candidates) {
        if (GetAsyncKeyState(candidate.vk) & 0x8000) {
            held[count++] = candidate;
        }
    }
    return count;
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

bool WantLockNow() {
    const bool rightHeld = g_rightDown.load() ||
                           (GetAsyncKeyState(VK_RBUTTON) & 0x8000);
    const bool relockGrace = GetTickCount64() < g_rightRelockUntil.load();
    return g_enabled.load() && g_editMode.load() && !rightHeld && !relockGrace;
}

void DeliverRightReplay() {
    if (!g_zbrush || !g_rightReplayScheduled.exchange(false)) return;
    KillTimer(g_zbrush, kRightReplayTimer);
    if (!g_enabled.load() || !g_editMode.load()) {
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightReplayDelivered.store(false);
        return;
    }
    if (!g_rightPending.exchange(false)) return;

    {
        char line[128];
        snprintf(line, sizeof(line),
                 "right replay timer: DOWN ctrl=%d alt=%d shift=%d",
                 (GetAsyncKeyState(VK_CONTROL) & 0x8000) ? 1 : 0,
                 (GetAsyncKeyState(VK_MENU) & 0x8000) ? 1 : 0,
                 (GetAsyncKeyState(VK_SHIFT) & 0x8000) ? 1 : 0);
        DbgLog(line);
    }
    SendMouse(g_zbrush, WM_RBUTTONDOWN, Modifiers() | MK_RBUTTON);
    if (!g_rightDown.load() || g_rightUpPending.exchange(false)) {
        DbgLog("right replay timer: immediate UP for quick click");
        SendMouse(g_zbrush, WM_RBUTTONUP, Modifiers());
        g_rightReplayDelivered.store(false);
    } else {
        g_rightReplayDelivered.store(true);
    }
    UpdateDiagnosticOverlay();
}

void ResetDbgLog() {
    char path[MAX_PATH];
    if (GetTempPathA(MAX_PATH, path)) {
        std::strcat(path, "nlr2022_dbg.log");
        FILE* stream = nullptr;
        if (fopen_s(&stream, path, "w") == 0 && stream) fclose(stream);
    }
}

const wchar_t* GestureName(Gesture gesture) {
    switch (gesture) {
        case Gesture::Idle: return L"空闲";
        case Gesture::UiPass: return L"界面放行";
        case Gesture::Classify: return L"灯箱判断";
        case Gesture::LightBoxClickDone: return L"灯箱点击";
        case Gesture::LightBoxPass: return L"灯箱拖动";
        case Gesture::WaitModel: return L"等待模型";
        case Gesture::StartPending: return L"等待起笔";
        case Gesture::Sculpting: return L"雕刻";
        case Gesture::ModelPass: return L"模型放行";
    }
    return L"未知";
}

void UpdateDiagnosticOverlay() {
    if (!g_overlay) return;
    const ULONGLONG now = GetTickCount64();
    const ULONGLONG receivedAt = g_lastBridgeReceivedAt.load();
    const bool bridgeAlive = receivedAt != 0 && now - receivedAt < 1000;
    wchar_t text[768]{};
    swprintf_s(
        text,
        L"NLR诊断  F12系统发送:%s(%llu)  主窗按下:%llu  ZScript桥:%s(%llu)  热键:%d>%d  修复:%llu\r\n"
        L"启用:%s  Edit:%s  IGet:%d  Flags:%d  ViewID:%d  锁定请求:%s  右键:%s  待重放:%s  mat:%.3f  状态:%s",
        g_lastSendOk.load() ? L"成功" : L"失败",
        g_f12Sent.load(),
        g_f12WindowSeen.load(),
        bridgeAlive ? L"正常" : (g_bridgeConfirmed.load() ? L"超时" : L"未收到"),
        g_bridgeReceived.load(),
        g_bridgeHotkeyBefore.load(),
        g_bridgeHotkeyRaw.load(),
        g_hotkeyRepairCount.load(),
        g_enabled.load() ? L"开" : L"关",
        g_editMode.load() ? L"是" : L"否",
        g_editValueRaw.load(),
        g_editFlagsRaw.load(),
        g_windowId.load(),
        WantLockNow() ? L"锁定" : L"解锁",
        g_rightDown.load() ? L"按下" : L"抬起",
        g_rightPending.load() ? L"是" : L"否",
        g_mat.load(),
        GestureName(g_gesture.load()));
    SetWindowTextW(g_overlay, text);
    InvalidateRect(g_overlay, nullptr, TRUE);
}

void PositionDiagnosticOverlay() {
    if (!g_zbrush || !g_overlay) return;
    RECT window{};
    if (!GetWindowRect(g_zbrush, &window)) return;
    constexpr int margin = 4;
    constexpr int height = 44;
    const int available = std::max(1, static_cast<int>(window.right - window.left) - margin * 2);
    const int width = std::min(1120, available);
    const int x = window.left + margin;
    const int y = std::max(window.top + margin, window.bottom - height - margin);
    SetWindowPos(g_overlay, HWND_TOP, x, y, width, height,
                 SWP_NOACTIVATE | SWP_SHOWWINDOW);
}

LRESULT CALLBACK OverlayProc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_NCHITTEST) return HTTRANSPARENT;
    if (message == WM_ERASEBKGND) return 1;
    if (message == WM_PAINT) {
        PAINTSTRUCT paint{};
        HDC dc = BeginPaint(hwnd, &paint);
        RECT rect{};
        GetClientRect(hwnd, &rect);
        HBRUSH background = CreateSolidBrush(RGB(18, 18, 18));
        FillRect(dc, &rect, background);
        DeleteObject(background);
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, RGB(255, 170, 35));
        HFONT font = static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
        HGDIOBJ oldFont = SelectObject(dc, font);
        wchar_t text[768]{};
        GetWindowTextW(hwnd, text, static_cast<int>(_countof(text)));
        RECT textRect{8, 4, rect.right - 8, rect.bottom - 4};
        DrawTextW(dc, text, -1, &textRect, DT_LEFT | DT_TOP | DT_NOPREFIX);
        SelectObject(dc, oldFont);
        EndPaint(hwnd, &paint);
        return 0;
    }
    return DefWindowProcW(hwnd, message, wparam, lparam);
}

bool CreateDiagnosticOverlay() {
    WNDCLASSEXW windowClass{};
    windowClass.cbSize = sizeof(windowClass);
    windowClass.lpfnWndProc = OverlayProc;
    windowClass.hInstance = g_module;
    windowClass.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    windowClass.lpszClassName = kOverlayClass;
    RegisterClassExW(&windowClass);
    g_overlay = CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
        kOverlayClass, L"NLR诊断：等待启动", WS_POPUP | WS_VISIBLE,
        0, 0, 1120, 44, g_zbrush, nullptr, g_module, nullptr);
    if (!g_overlay) return false;
    SetLayeredWindowAttributes(g_overlay, 0, 230, LWA_ALPHA);
    PositionDiagnosticOverlay();
    UpdateDiagnosticOverlay();
    return true;
}

bool InjectProbeHotkey(bool neutralizeModifiers) {
    // ZBrush's hotkey dispatcher rejects posted WM_KEYDOWN messages; it only
    // accepts input that travelled through the system keyboard path. Guard
    // SendInput with the foreground process so no other application receives
    // the probe key while ZBrush is inactive.
    if (!g_zbrush || !IsWindow(g_zbrush)) return false;
    HWND foreground = GetForegroundWindow();
    DWORD foregroundPid = 0;
    GetWindowThreadProcessId(foreground, &foregroundPid);
    if (foregroundPid != GetCurrentProcessId()) {
        g_lastSendOk.store(false);
        // Normal inactive state, not a failed injection attempt.
        return true;
    }

    HeldModifier held[6]{};
    const size_t heldCount = neutralizeModifiers
        ? CaptureHeldModifiers(held)
        : 0;
    INPUT inputs[14]{};
    UINT inputCount = 0;

    // A probe sent while Ctrl/Alt/Shift is physically held becomes a modified
    // shortcut and never reaches the bridge button. For the urgent right-down
    // path only, release the held modifiers, send a plain F12, then restore the
    // exact left/right modifier keys before the deferred right press is replayed.
    for (size_t i = 0; i < heldCount; ++i) {
        inputs[inputCount].type = INPUT_KEYBOARD;
        inputs[inputCount].ki.wVk = held[i].vk;
        inputs[inputCount].ki.dwFlags = held[i].flags | KEYEVENTF_KEYUP;
        ++inputCount;
    }
    inputs[inputCount].type = INPUT_KEYBOARD;
    inputs[inputCount].ki.wVk = VK_F12;
    ++inputCount;
    inputs[inputCount].type = INPUT_KEYBOARD;
    inputs[inputCount].ki.wVk = VK_F12;
    inputs[inputCount].ki.dwFlags = KEYEVENTF_KEYUP;
    ++inputCount;
    for (size_t i = heldCount; i > 0; --i) {
        inputs[inputCount].type = INPUT_KEYBOARD;
        inputs[inputCount].ki.wVk = held[i - 1].vk;
        inputs[inputCount].ki.dwFlags = held[i - 1].flags;
        ++inputCount;
    }

    const UINT sent = SendInput(inputCount, inputs, sizeof(INPUT));
    const bool ok = sent == inputCount;
    g_lastSendOk.store(ok);
    const unsigned long long count = g_f12Sent.fetch_add(1) + 1;
    if (!ok || count == 1 || count % 20 == 0) {
        char line[128];
        snprintf(line, sizeof(line),
                 "F12 SendInput ok=%d sent=%u/%u count=%llu neutral=%d mods=%zu",
                 ok ? 1 : 0, sent, inputCount, count,
                 neutralizeModifiers ? 1 : 0, heldCount);
        DbgLog(line);
    }
    UpdateDiagnosticOverlay();
    return ok;
}

void RequestHotkeySample(bool forceSync = false, bool urgent = false,
                         bool neutralizeModifiers = false) {
    if (!g_enabled.load()) return;
    // Regular sampling must never inject a bridge key into a modified shortcut
    // or into an active right-button navigation gesture. The right-down unlock
    // request is the sole exception and uses a modifier-neutral F12 sequence.
    if (!neutralizeModifiers &&
        (AnyKeyboardModifierHeld() || g_rightDown.load() ||
         (GetAsyncKeyState(VK_RBUTTON) & 0x8000))) {
        return;
    }
    const ULONGLONG now = GetTickCount64();
    if (g_bridgeOutstanding.load()) {
        if (!urgent && now - g_bridgeSentAt.load() < kBridgeTimeoutMs) return;
        g_bridgeOutstanding.store(false);
        g_sampleRequest.store(SampleRequest::None);
    }

    SampleRequest request = SampleRequest::None;
    if (g_editMode.load() && g_gesture.load() == Gesture::WaitModel) {
        request = SampleRequest::WaitModel;
    } else if (forceSync) {
        request = SampleRequest::Sync;
    }
    if (request == SampleRequest::None) return;

    g_sampleRequest.store(request);
    g_bridgeSentAt.store(now);
    g_bridgeOutstanding.store(true);
    if (!InjectProbeHotkey(neutralizeModifiers)) {
        DbgLog("F12 request FAILED");
        g_bridgeOutstanding.store(false);
        g_sampleRequest.store(SampleRequest::None);
    }
}

void WriteSyncFloats(void* memOut, float want, float right) {
    if (!memOut) return;
    auto* out = static_cast<float*>(memOut);
    out[0] = want;
    out[1] = right;
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
        KillTimer(g_zbrush, kWaitModelTimer);
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
    SetTimer(g_zbrush, kWaitModelTimer, kWaitModelPollMs, nullptr);
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
    if ((message == WM_KEYDOWN || message == WM_SYSKEYDOWN) &&
        wparam == VK_F12) {
        const unsigned long long count = g_f12WindowSeen.fetch_add(1) + 1;
        if (count == 1 || count % 20 == 0) {
            char line[96];
            snprintf(line, sizeof(line), "ZBrush window saw F12 count=%llu", count);
            DbgLog(line);
        }
        UpdateDiagnosticOverlay();
    }
    if (message == WM_SIZE) {
        PositionDiagnosticOverlay();
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
        if (wparam == kRelockTimer) {
            KillTimer(hwnd, kRelockTimer);
            RequestHotkeySample(true, true, true);
            return 0;
        }
        if (wparam == kWaitModelTimer) {
            if (g_gesture.load() != Gesture::WaitModel ||
                !(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
                KillTimer(hwnd, kWaitModelTimer);
                ResetGesture();
                return 0;
            }
            RequestHotkeySample(false, false, true);
            return 0;
        }
        if (wparam == kRightReplayTimer) {
            DeliverRightReplay();
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
        g_rightReplayScheduled.store(false);
        g_rightReplayDelivered.store(false);
        DbgLog("right DOWN swallowed; request unlock");
        RequestHotkeySample(true, true, true);
        UpdateDiagnosticOverlay();
        return 0;
    }
    if (message == WM_RBUTTONUP) {
        // Python V1 relocks the camera 2ms after the right button is released.
        g_rightRelockUntil.store(GetTickCount64() + kRelockMs);
        if (!g_enabled.load() || !g_editMode.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        g_rightDown.store(false);
        // Once the deferred DOWN has reached ZBrush, its physical UP can pass
        // through normally, exactly like the stable Python path.
        if (g_rightReplayDelivered.exchange(false)) {
            DbgLog("right physical UP passed after deferred DOWN");
            SetTimer(hwnd, kRelockTimer, kRelockMs, nullptr);
            UpdateDiagnosticOverlay();
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // A very quick click may release before the deferred DOWN timer fires.
        // Keep that UP and deliver a complete DOWN/UP pair from the timer.
        if (g_rightPending.load() || g_rightReplayScheduled.load()) {
            g_rightUpPending.store(true);
            DbgLog("right UP queued; request relock after 2ms");
            SetTimer(hwnd, kRelockTimer, kRelockMs, nullptr);
            UpdateDiagnosticOverlay();
            return 0;
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_LBUTTONDOWN) {
        RequestHotkeySample(true, true, true);
        if (!g_enabled.load() || !g_editMode.load()) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        GetCursorPos(&g_downPoint);
        if (g_windowId.load() != kCanvasWindowId) {
            g_gesture.store(Gesture::UiPass);
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
        const Gesture state = g_gesture.load();
        // Probe window: the real down was passed and the synthetic UP was
        // replayed; swallow movement so the 5ms cursor classification only
        // sees the probe result, not ZBrush's reaction to the drag.
        if (state == Gesture::Classify) {
            return 0;
        }
        if (state == Gesture::LightBoxClickDone &&
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
        ResetGesture();
        KillTimer(hwnd, kRelockTimer);
        KillTimer(hwnd, kWaitModelTimer);
        KillTimer(hwnd, kRightReplayTimer);
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightRelockUntil.store(0);
        if (g_timerPeriodSet.exchange(false)) {
            timeEndPeriod(1);
        }
        RestoreCursorWatch();
        if (g_overlay) {
            DestroyWindow(g_overlay);
            g_overlay = nullptr;
        }
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
    if (!CreateDiagnosticOverlay()) {
        DbgLog("diagnostic overlay: FAILED");
    } else {
        DbgLog("diagnostic overlay: ok");
    }
    // Make the 5ms probe timer actually fire at ~5ms instead of the default
    // ~15.6ms Windows timer granularity.
    timeBeginPeriod(1);
    g_timerPeriodSet.store(true);
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
    ResetDbgLog();
    DbgLog("No Left Click Rotation Candidate 1: Init entered");
    DbgLog(EnsureBridgeHotkeyConfig()
               ? "hotkey config: F12 persisted"
               : "hotkey config: persistence FAILED");
    const int result = Install() ? 1 : 0;
    DbgLog(result ? "Init: ok" : "Init: FAILED");
    return result;
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

// Reliable DLL -> ZScript channel: the hotkey bridge creates an 8-byte memory
// block and asks for the current camera-lock and right-button state.
// and passes it to FileExecute. Per the plugin API the block pointer arrives
// in the input slot; ZBrush 2026 does not provide a usable output pointer, so
// all flags travel through the input block, which ZScript reads back.
extern "C" __declspec(dllexport) int __cdecl NlrSync(
    unsigned char* text, double number, void* memIn, void* memOut) {
    g_enabled.store((static_cast<int>(number) & 1) != 0);
    g_editMode.store((static_cast<int>(number) & 2) != 0);
    int windowId = -1;
    int editValue = -1;
    int editFlags = -1;
    int bridgeHotkeyBefore = -1;
    int bridgeHotkey = -1;
    if (text) {
        const char* stateText = reinterpret_cast<char*>(text);
        const int fields = sscanf_s(stateText, "%d,%d,%d,%d,%d",
                                    &windowId, &editValue, &editFlags,
                                    &bridgeHotkeyBefore,
                                    &bridgeHotkey);
        if (fields < 1) windowId = std::atoi(stateText);
    }
    g_windowId.store(windowId);
    g_editValueRaw.store(editValue);
    g_editFlagsRaw.store(editFlags);
    g_bridgeHotkeyBefore.store(bridgeHotkeyBefore);
    g_bridgeHotkeyRaw.store(bridgeHotkey);
    if (bridgeHotkeyBefore != -1 && bridgeHotkeyBefore != 91 &&
        bridgeHotkey == 91) {
        const unsigned long long repairs = g_hotkeyRepairCount.fetch_add(1) + 1;
        char repairLine[128];
        snprintf(repairLine, sizeof(repairLine),
                 "hotkey repaired before=%d after=%d repairs=%llu",
                 bridgeHotkeyBefore, bridgeHotkey, repairs);
        DbgLog(repairLine);
    }
    if (!g_enabled.load()) ResetGesture();
    const float want = WantLockNow() ? 1.0f : 0.0f;
    const float right = g_rightDown.load() ? 1.0f : 0.0f;
    if (WritableRange(memIn, 8)) {
        WriteSyncFloats(memIn, want, right);
    } else if (WritableRange(memOut, 8)) {
        WriteSyncFloats(memOut, want, right);
    }
    UpdateDiagnosticOverlay();
    static ULONGLONG lastSyncLog = 0;
    const ULONGLONG now = GetTickCount64();
    if (now - lastSyncLog > 1000) {
        lastSyncLog = now;
        char line[160];
        snprintf(line, sizeof(line),
                 "hb want=%d right=%d bits=%d win=%d edit_get=%d edit_flags=%d hotkey=%d>%d repairs=%llu",
                 static_cast<int>(want), static_cast<int>(right),
                 static_cast<int>(number), g_windowId.load(),
                 g_editValueRaw.load(), g_editFlagsRaw.load(),
                 g_bridgeHotkeyBefore.load(), g_bridgeHotkeyRaw.load(),
                 g_hotkeyRepairCount.load());
        DbgLog(line);
    }
    return 1;
}

// Temporary diagnostic: logs ZScript init steps verbatim (called only on
// script-level events, never in a hot loop).
extern "C" __declspec(dllexport) int __cdecl Trace(
    unsigned char* text, double, void*, void*) {
    DbgLog(text ? reinterpret_cast<char*>(text) : "(null)");
    return 1;
}

// Returns 1 when the camera should be locked: enabled + Edit mode + the right
// mouse button is not held and the 2ms post-release grace has elapsed.
extern "C" __declspec(dllexport) int __cdecl WantLock(
    unsigned char*, double, void*, void*) {
    return WantLockNow() ? 1 : 0;
}

// Called after ZScript changes the camera lock. Only schedule here: ZBrush
// ignores a new rotate gesture while the F12 hotkey routine is still running.
// The timer delivers the mouse message after the routine has returned.
extern "C" __declspec(dllexport) int __cdecl ReplayRightDown(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load()) {
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        return 0;
    }
    if (g_rightPending.load() && g_zbrush) {
        if (!g_rightReplayScheduled.exchange(true)) {
            DbgLog("right replay scheduled after ZScript");
            SetTimer(g_zbrush, kRightReplayTimer, kRightReplayMs, nullptr);
        }
        return 1;
    }
    return 0;
}

extern "C" __declspec(dllexport) int __cdecl Shutdown(
    unsigned char*, double, void*, void*) {
    if (g_zbrush) {
        ResetGesture();
        KillTimer(g_zbrush, kRelockTimer);
        KillTimer(g_zbrush, kWaitModelTimer);
        KillTimer(g_zbrush, kRightReplayTimer);
        RemoveWindowSubclass(g_zbrush, SubclassProc, kSubclassId);
        if (g_overlay && IsWindow(g_overlay)) DestroyWindow(g_overlay);
        g_overlay = nullptr;
        g_zbrush = nullptr;
    }
    if (g_timerPeriodSet.exchange(false)) {
        timeEndPeriod(1);
    }
    RestoreCursorWatch();
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
    DbgLog(g_enabled.load() ? "SetEnabled: ON" : "SetEnabled: OFF");
    if (!g_enabled.load()) {
        // Clear all deferred gesture state on disable.
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightReplayScheduled.store(false);
        g_rightReplayDelivered.store(false);
        g_rightRelockUntil.store(0);
        g_bridgeOutstanding.store(false);
        g_sampleRequest.store(SampleRequest::None);
    }
    ResetGesture();
    UpdateDiagnosticOverlay();
    if (g_enabled.load()) RequestHotkeySample(true, true);
    return g_enabled.load() ? 1 : 0;
}

// PixolPick result delivered by the dedicated ZScript hotkey bridge. The DLL
// owns the request type, so the ZScript callback only has to return one mat.
extern "C" __declspec(dllexport) int __cdecl HotkeyPixol(
    unsigned char*, double number, void*, void*) {
    if (!g_bridgeConfirmed.exchange(true)) {
        DbgLog("hotkey bridge: confirmed");
    }
    const unsigned long long received = g_bridgeReceived.fetch_add(1) + 1;
    g_lastBridgeReceivedAt.store(GetTickCount64());
    if (received == 1 || received % 20 == 0) {
        char line[224];
        snprintf(line, sizeof(line),
                 "ZScript bridge received count=%llu mat=%.3f edit=%d get=%d flags=%d win=%d",
                 received, number, g_editMode.load() ? 1 : 0,
                 g_editValueRaw.load(), g_editFlagsRaw.load(),
                 g_windowId.load());
        DbgLog(line);
    }
    g_bridgeOutstanding.store(false);
    const SampleRequest request =
        g_sampleRequest.exchange(SampleRequest::None);
    g_mat.store(number);
    UpdateDiagnosticOverlay();
    if (request == SampleRequest::WaitModel) {
        g_mat.store(number);
        if (g_gesture.load() == Gesture::WaitModel && number != 0.0) {
            KillTimer(g_zbrush, kWaitModelTimer);
            EndMiddle();
            g_gesture.store(Gesture::StartPending);
            SetTimer(g_zbrush, kStartTimer,
                     static_cast<UINT>(std::max(1, g_startDelayMs.load())),
                     nullptr);
        }
        return 1;
    }
    return 0;
}

BOOL APIENTRY DllMain(HINSTANCE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_module = module;
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
