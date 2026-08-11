# NoLeftClickRotation（禁用左键视图旋转）

ZBrush 2026（64 位）单文件 Python 插件：**禁用左键在画布空白处拖动时的视图旋转与平移**。

## 功能

- **空白处左键拖动不旋转**：保持官方 `Draw:Lock Camera` 锁定，左键拖空白不再旋转视图
- **Alt+左键不平移**：锁定状态下 Alt+左键的平移同样被禁用
- **右键照常旋转**：右键按住时临时解锁相机，右键拖动旋转如常；松开后约 1ms 自动重新锁定（避免旋转手势未结束时锁定触发回弹）
- **模型雕刻、Ctrl+左键遮罩、UI 按钮/滑块完全不受影响**：插件不吞任何消息、不合成任何鼠标事件，只维护相机锁定状态
- **界面语言跟随系统**：中文系统显示“禁用左键视图旋转”，其他系统显示 `NoLeftClickRotation`

## 安装

1. 打开 ZBrush 用户插件目录：

   ```
   %APPDATA%\Maxon\Maxon ZBrush 2026_XXXX\ZStartup\ZPlugs64\
   ```

   （`XXXX` 是安装实例标识，以你机器上的实际目录名为准，例如 `Maxon ZBrush 2026_F3C8B4C4`）

2. 将 `NoLeftClickRotation.py` 复制到该目录。

3. 重启 ZBrush，插件自动加载。

> 无需环境变量、无需 DLL、无需安装程序，复制一个文件即可。

## 使用

- 打开 Zplugin 菜单，找到 **“禁用左键视图旋转”**（中文）或 **“NoLeftClickRotation”**（英文）
- 面板中只有一个 **启用** 开关：
  - 勾选：相机锁定生效，左键拖空白不旋转/不平移，右键可旋转
  - 取消：恢复 ZBrush 原始行为（相机解锁）
- 开关状态保存在插件同目录的 `config.txt`，下次启动自动读取

## 卸载

1. 删除 `ZPlugs64\NoLeftClickRotation.py`
2. 删除同目录的 `config.txt`（可选）
3. 重启 ZBrush

## 兼容性

- ZBrush 2026（64 位）
- 仅使用官方 ZBrush Python API（`zbrush.commands`）与 Windows 消息子类化，不修改任何 ZBrush 文件

## 已知限制

- **“空白处按住左键拖到模型上自动起笔雕刻”暂未实现**。ZBrush 在左键按下时即锁定手势模式（空白=导航 / 模型=雕刻），官方 API 无法在按下状态下可靠区分光标位置，故该功能不在本版本支持范围内。

## 文件

```
NoLeftClickRotation.py   插件主文件（部署此文件到 ZPlugs64）
config.txt               开关状态（由插件自动生成）
README.md                本说明
```
