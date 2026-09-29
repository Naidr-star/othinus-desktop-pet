# 欧提努斯桌宠

这是一个以《魔法禁书目录》欧提努斯为角色的 Windows 透明桌宠。程序使用 Python 与 PySide6 开发，通过 PyInstaller 生成单文件 EXE。

当前稳定版本为 **v2.6.2**。面向普通用户的安装、操作和分发说明见 [README.txt](README.txt)。

## 功能亮点

- 透明无边框、始终置顶的桌面角色和系统托盘。
- 多动作、多表情、平滑切换、拖动悬垂、自然散步及屏幕边缘互动。
- 主神之枪召唤、战斗、漂浮，以及位置、角度和尺寸调整。
- 自定义休息、低精力长休、上条当麻玩偶睡姿和世界终结演出。
- 三种桌面内小游戏，以及等级、羁绊、熟练度、成就和离线成长系统。
- JSON 自动存档、单实例锁、源码烟雾测试和离屏发布验证。

## 从源码运行

已验证环境：

- Windows 11
- Python 3.13.9
- PySide6 6.9.2
- PyInstaller 6.22.2

安装运行依赖后启动：

```powershell
python -m pip install -r requirements.txt
python othinus_pet.py
```

运行离屏验证：

```powershell
python -m pip install -r requirements-dev.txt
python verify_v25.py
```

构建 Windows EXE：

```powershell
.\build.ps1 -DistPath .\dist
```

构建前请先退出正在运行的桌宠。未经明确美术需求，不要重新运行素材生成脚本。

## 项目结构

- 主程序：`othinus_pet.py`
- 当前素材流水线：`prepare_assets_v2.py`
- 离屏验证：`verify_v25.py`（文件名为历史遗留，实际对应 v2.6.2）
- Windows 构建：`build.ps1`
- 运行素材：`assets/`
- 美术源文件：`assets_v2/`

## 开发文档

- [架构说明](docs/ARCHITECTURE.md)
- [角色与动作规则](docs/DESIGN_RULES.md)
- [版本历史](CHANGELOG.md)
- [当前发布说明](RELEASE_NOTES.md)
- [版权说明](COPYRIGHT.md)

## 项目性质

本项目是非官方、非商业的 AI 辅助同人桌宠。原作及角色权利归相应权利方所有。使用或再分发前请阅读 [COPYRIGHT.md](COPYRIGHT.md)。
