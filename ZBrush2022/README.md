# ZBrush 2022 兼容版（实验）

本版本面向不支持 Python 插件的 ZBrush 2022，采用 ZScript 与原生 Windows DLL 协作：

- ZScript 使用 `Sleep/SleepAgain` 监听计时器和鼠标事件。
- ZScript 原生执行 `[PixolPick,5,x,y]`。
- DLL 负责鼠标状态机、中键伪装、LightBox 光标判断和重新起笔。

## 当前状态

这是首个实验实现。x64 DLL 已使用 Visual Studio 2022 Build Tools 成功编译，导出函数已经检查；但尚未在 ZBrush 2022 中实机验证，因为当前电脑没有安装 ZBrush 2022。

## 构建

需要 Visual Studio 2022（Desktop development with C++）或兼容的 x64 C++ 编译器。

```powershell
cmake -S . -B build -A x64
cmake --build build --config Release
```

生成文件：

`build/Release/NoLeftClickRotation2022.dll`

已经整理好的安装文件位于：

`package/ZPlugs64`

## 安装布局

```text
ZStartup/ZPlugs64/
├─ NoLeftClickRotation2022.txt
└─ NoLeftClickRotation2022Data/
   └─ NoLeftClickRotation2022.dll
```

启动 ZBrush 后，入口位于：

`ZPlugin > No Left Click Rotation > V2022`

## 首轮验证重点

1. 插件是否能加载且不闪退。
2. 普通 UI 点击是否被正确延迟后重放。
3. 中键伪装期间 `PixolPick mat` 是否持续变化。
4. 空白处拖入模型是否能重新起笔。
5. LightBox 单击、双击和拖动是否正常。
