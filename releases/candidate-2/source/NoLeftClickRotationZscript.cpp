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
constexpr UINT_PTR kF12PollTimer = 0x4E4C5235;
constexpr UINT_PTR kRelockTimer = 0x4E4C5236;
constexpr UINT_PTR kRightReplayTimer = 0x4E4C5237;
constexpr UINT kClassifyMs = 20;
// Match the stable Python V1 permanent poll cadence.
constexpr UINT kF12PollMs = 5;
constexpr UINT kRelockMs = 2;
constexpr UINT kRightReplayMs = 1;
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
    Background,
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
std::atomic<bool> g_physicalLeftDown{false};
std::atomic<bool> g_hoverReady{false};
std::atomic<double> g_hoverMat{0.0};
std::atomic<ULONGLONG> g_lastHoverMs{0};
std::atomic<bool> g_rightDown{false};
std::atomic<bool> g_rightPending{false};
std::atomic<bool> g_rightUpPending{false};
std::atomic<bool> g_rightReplayScheduled{false};
std::atomic<bool> g_rightReplayDelivered{false};
std::atomic<ULONGLONG> g_rightRelockUntil{0};
std::atomic<int> g_lockState{-1};
std::atomic<ULONGLONG> g_lockAssertAt{0};
std::atomic<bool> g_timerPeriodSet{false};
std::atomic<SampleRequest> g_sampleRequest{SampleRequest::None};
std::atomic<bool> g_bridgeOutstanding{false};
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

LPARAM ScreenPointLParam(HWND hwnd, POINT point) {
    ScreenToClient(hwnd, &point);
    return MAKELPARAM(static_cast<short>(point.x),
                      static_cast<short>(point.y));
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
    return g_enabled.load() && g_editMode.load() && !rightHeld &&
           GetTickCount64() >= g_rightRelockUntil.load();
}

int CameraAction() {
    const int want = WantLockNow() ? 1 : 0;
    const ULONGLONG now = GetTickCount64();
    if (want != g_lockState.load() || now >= g_lockAssertAt.load()) {
        g_lockState.store(want);
        g_lockAssertAt.store(now + 200);
        return want;
    }
    return -1;
}

void DeliverRightReplay() {
    if (!g_zbrush || !g_rightReplayScheduled.exchange(false)) return;
    KillTimer(g_zbrush, kRightReplayTimer);
    if (!g_enabled.load() || !g_editMode.load() ||
        !g_rightPending.exchange(false)) {
        return;
    }
    SendMouse(g_zbrush, WM_RBUTTONDOWN, Modifiers() | MK_RBUTTON);
    if (!g_rightDown.load() || g_rightUpPending.exchange(false)) {
        SendMouse(g_zbrush, WM_RBUTTONUP, Modifiers());
        g_rightReplayDelivered.store(false);
    } else {
        g_rightReplayDelivered.store(true);
    }
}

void ResetDbgLog() {
    char path[MAX_PATH];
    if (GetTempPathA(MAX_PATH, path)) {
        std::strcat(path, "nlr2022_dbg.log");
        FILE* stream = nullptr;
        if (fopen_s(&stream, path, "w") == 0 && stream) fclose(stream);
    }
}

LRESULT SendMouseAt(HWND hwnd, UINT message, WPARAM wparam,
                    POINT screenPoint) {
    g_injecting.store(true, std::memory_order_release);
    const LRESULT result = SendMessageW(
        hwnd, message, wparam, ScreenPointLParam(hwnd, screenPoint));
    g_injecting.store(false, std::memory_order_release);
    return result;
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
    wchar_t text[640]{};
    swprintf_s(
        text,
        L"NLR RC2  F12:%s(%llu)  主窗口:%llu  ZScript桥:%s(%llu)  热键:%d>%d  修复:%llu\r\n"
        L"启用:%s  Edit:%s  IGet:%d  Flags:%d  ViewID:%d  mat:%.3f  状态:%s",
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
        g_mat.load(),
        GestureName(g_gesture.load()));
    SetWindowTextW(g_overlay, text);
    InvalidateRect(g_overlay, nullptr, TRUE);
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
        WS_EX_TRANSPARENT | WS_EX_NOACTIVATE,
        kOverlayClass, L"NLR诊断：等待启动", WS_CHILD | WS_VISIBLE,
        4, 4, 1120, 44, g_zbrush, nullptr, g_module, nullptr);
    if (!g_overlay) return false;
    SetWindowPos(g_overlay, HWND_TOP, 4, 4, 1120, 44,
                 SWP_NOACTIVATE | SWP_SHOWWINDOW);
    UpdateDiagnosticOverlay();
    return true;
}

bool InjectProbeHotkey(bool neutralizeModifiers) {
    // F12 is registered from StartupHotkeys.txt before the plugin starts.
    // ZBrush runs the hotkey routine reliably only when the key travels through
    // the system input path. Never inject while another process is foreground.
    if (!g_zbrush || !IsWindow(g_zbrush)) return false;
    HWND foreground = GetForegroundWindow();
    DWORD foregroundPid = 0;
    GetWindowThreadProcessId(foreground, &foregroundPid);
    if (foregroundPid != GetCurrentProcessId()) {
        g_lastSendOk.store(false);
        return false;
    }

    HeldModifier held[6]{};
    const size_t heldCount = neutralizeModifiers
        ? CaptureHeldModifiers(held)
        : 0;
    INPUT inputs[14]{};
    UINT inputCount = 0;
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
                 "F12 SendInput ok=%d sent=%u/%u count=%llu mods=%zu",
                 ok ? 1 : 0, sent, inputCount, count, heldCount);
        DbgLog(line);
    }
    UpdateDiagnosticOverlay();
    return ok;
}

bool RequestHotkeySample(SampleRequest request,
                         bool neutralizeModifiers = true) {
    if (request == SampleRequest::None) return false;
    // Keep a strict one-request/one-callback mapping. Replacing an outstanding
    // request lets a delayed ZScript callback corrupt the next gesture.
    if (g_bridgeOutstanding.load()) return false;
    g_sampleRequest.store(request);
    g_bridgeOutstanding.store(true);
    if (!InjectProbeHotkey(neutralizeModifiers)) {
        if (request != SampleRequest::Background) {
            DbgLog("F12 request FAILED");
        }
        g_bridgeOutstanding.store(false);
        g_sampleRequest.store(SampleRequest::None);
        return false;
    }
    return true;
}

bool WritableRange(const void* pointer, size_t bytes) {
    if (!pointer) return false;
    MEMORY_BASIC_INFORMATION info{};
    if (!VirtualQuery(pointer, &info, sizeof(info)) ||
        info.State != MEM_COMMIT) return false;
    const DWORD protect = info.Protect & 0xFF;
    if (protect != PAGE_READWRITE && protect != PAGE_EXECUTE_READWRITE &&
        protect != PAGE_WRITECOPY && protect != PAGE_EXECUTE_WRITECOPY) {
        return false;
    }
    const auto begin = reinterpret_cast<std::uintptr_t>(pointer);
    const auto end = reinterpret_cast<std::uintptr_t>(info.BaseAddress) +
                     info.RegionSize;
    return begin <= end && bytes <= end - begin;
}

void ResetGesture() {
    const Gesture old = g_gesture.exchange(Gesture::Idle);
    if (g_zbrush) {
        KillTimer(g_zbrush, kClassifyTimer);
        KillTimer(g_zbrush, kStartTimer);
    }
    if (old == Gesture::WaitModel) EndMiddle();
    g_physicalLeftDown.store(false);
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
        g_gesture.store(g_physicalLeftDown.load()
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
            return 0;
        }
        if (wparam == kRightReplayTimer) {
            DeliverRightReplay();
            return 0;
        }
        if (wparam == kF12PollTimer) {
            const Gesture state = g_gesture.load();
            SampleRequest request = SampleRequest::None;
            if (state == Gesture::WaitModel &&
                       g_physicalLeftDown.load() &&
                       (GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
                request = SampleRequest::WaitModel;
            } else {
                const bool nativeLeftGesture =
                    g_physicalLeftDown.load() &&
                    (state == Gesture::UiPass ||
                     state == Gesture::ModelPass ||
                     state == Gesture::LightBoxClickDone ||
                     state == Gesture::LightBoxPass ||
                     state == Gesture::StartPending ||
                     state == Gesture::Sculpting ||
                     state == Gesture::Classify);
                const bool nativeRightGesture =
                    g_rightDown.load() && g_rightReplayDelivered.load();
                // Python's 5ms timer keeps running during native gestures,
                // but its API calls do not emit keyboard input. Our F12
                // transport must pause only the key injection or it cancels
                // ZBrush's active sculpt/rotate gesture.
                if (!nativeLeftGesture && !nativeRightGesture) {
                    request = SampleRequest::Background;
                }
            }
            if (request != SampleRequest::None) {
                RequestHotkeySample(request);
            }
            return 0;
        }
    }
    if (message == WM_RBUTTONDOWN) {
        g_rightDown.store(true);
        g_rightRelockUntil.store(0);
        if (!g_enabled.load() || !g_editMode.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // ZScript applies the unlocked camera state from this permanent F12
        // cycle, then schedules the native right press after the routine exits.
        g_rightPending.store(true);
        g_rightUpPending.store(false);
        g_rightReplayDelivered.store(false);
        return 0;
    }
    if (message == WM_RBUTTONUP) {
        g_rightDown.store(false);
        g_rightRelockUntil.store(GetTickCount64() + kRelockMs);
        SetTimer(hwnd, kRelockTimer, kRelockMs, nullptr);
        if (!g_enabled.load() || !g_editMode.load()) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (g_rightReplayDelivered.exchange(false)) {
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (g_rightPending.load() || g_rightReplayScheduled.load()) {
            g_rightUpPending.store(true);
            return 0;
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_LBUTTONDOWN) {
        g_physicalLeftDown.store(true);
        if (!g_enabled.load() || !g_editMode.load()) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        GetCursorPos(&g_downPoint);
        if (g_windowId.load() != kCanvasWindowId) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (g_hoverReady.load() && g_hoverMat.load() != 0.0) {
            g_gesture.store(Gesture::ModelPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        if (GetAsyncKeyState(VK_CONTROL) & 0x8000) {
            g_gesture.store(Gesture::UiPass);
            return DefSubclassProc(hwnd, message, wparam, lparam);
        }
        // Python V1: pass the real down, immediately finish it with a fake UP,
        // then classify LightBox versus blank canvas from the cursor.
        g_arrowSeen.store(false);
        g_gesture.store(Gesture::Classify);
        const LRESULT result = DefSubclassProc(hwnd, message, wparam, lparam);
        SendMouse(hwnd, WM_LBUTTONUP, Modifiers());
        SetTimer(hwnd, kClassifyTimer, kClassifyMs, nullptr);
        return result;
    }
    if (message == WM_MOUSEMOVE) {
        const Gesture state = g_gesture.load();
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
        if (state == Gesture::WaitModel && g_physicalLeftDown.load()) {
            RequestHotkeySample(SampleRequest::WaitModel);
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }
    if (message == WM_LBUTTONUP) {
        g_physicalLeftDown.store(false);
        const Gesture state = g_gesture.load();
        if (state == Gesture::Classify) {
            // The synthetic UP already completed the ambiguous click.
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
        KillTimer(hwnd, kF12PollTimer);
        KillTimer(hwnd, kRelockTimer);
        KillTimer(hwnd, kRightReplayTimer);
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
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
    // Python V1 starts its poll timer once during installation and leaves it
    // alive until window destruction. F12 follows the same lifetime here.
    SetTimer(g_zbrush, kF12PollTimer, kF12PollMs, nullptr);
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
    DbgLog("No Left Click Rotation Candidate 2: Init entered");
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

// Synchronize enabled/Edit/ViewID and hotkey diagnostics from ZScript.
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
    float* stateOut = nullptr;
    if (WritableRange(memIn, sizeof(float))) {
        stateOut = static_cast<float*>(memIn);
    } else if (WritableRange(memOut, sizeof(float))) {
        stateOut = static_cast<float*>(memOut);
    }
    if (stateOut) stateOut[0] = static_cast<float>(CameraAction());
    UpdateDiagnosticOverlay();
    static ULONGLONG lastSyncLog = 0;
    const ULONGLONG now = GetTickCount64();
    if (now - lastSyncLog > 1000) {
        lastSyncLog = now;
        char line[160];
        snprintf(line, sizeof(line),
                 "hb rc2 bits=%d win=%d edit_get=%d edit_flags=%d hotkey=%d>%d repairs=%llu",
                 static_cast<int>(number), g_windowId.load(),
                 g_editValueRaw.load(), g_editFlagsRaw.load(),
                 g_bridgeHotkeyBefore.load(), g_bridgeHotkeyRaw.load(),
                 g_hotkeyRepairCount.load());
        DbgLog(line);
    }
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl WantLock(
    unsigned char*, double, void*, void*) {
    return WantLockNow() ? 1 : 0;
}

extern "C" __declspec(dllexport) int __cdecl ReplayRightDown(
    unsigned char*, double, void*, void*) {
    if (!g_enabled.load() || !g_editMode.load()) {
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        return 0;
    }
    if (g_rightPending.load() && g_zbrush &&
        !g_rightReplayScheduled.exchange(true)) {
        SetTimer(g_zbrush, kRightReplayTimer, kRightReplayMs, nullptr);
        return 1;
    }
    return 0;
}

// Temporary diagnostic: logs ZScript init steps verbatim (called only on
// script-level events, never in a hot loop).
extern "C" __declspec(dllexport) int __cdecl Trace(
    unsigned char* text, double, void*, void*) {
    DbgLog(text ? reinterpret_cast<char*>(text) : "(null)");
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl Shutdown(
    unsigned char*, double, void*, void*) {
    if (g_zbrush) {
        ResetGesture();
        KillTimer(g_zbrush, kF12PollTimer);
        KillTimer(g_zbrush, kRelockTimer);
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
        g_rightDown.store(false);
        g_rightPending.store(false);
        g_rightUpPending.store(false);
        g_rightReplayScheduled.store(false);
        g_rightReplayDelivered.store(false);
        g_rightRelockUntil.store(0);
        g_hoverReady.store(false);
        g_hoverMat.store(0.0);
        g_lockState.store(-1);
        g_lockAssertAt.store(0);
    }
    ResetGesture();
    UpdateDiagnosticOverlay();
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
            DbgLog("wait model: hit -> replay left down");
            EndMiddle();
            g_gesture.store(Gesture::StartPending);
            SetTimer(g_zbrush, kStartTimer,
                     static_cast<UINT>(std::max(1, g_startDelayMs.load())),
                     nullptr);
        }
        return 1;
    }
    if (request == SampleRequest::Background) {
        // Python V1 samples hover mat only when active, idle, over the canvas,
        // and with the left button up. The permanent bridge still runs in all
        // other states; those results are simply not cached for direct press.
        if (g_enabled.load() && g_editMode.load() &&
            g_windowId.load() == kCanvasWindowId &&
            g_gesture.load() == Gesture::Idle &&
            !(GetAsyncKeyState(VK_LBUTTON) & 0x8000)) {
            const ULONGLONG now = GetTickCount64();
            if (now - g_lastHoverMs.load() >= 10) {
                g_hoverMat.store(number);
                g_hoverReady.store(true);
                g_lastHoverMs.store(now);
            }
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
