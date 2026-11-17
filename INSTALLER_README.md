# Sky City Demo 安装包

安装包为 `dist\SkyCityDemo_Setup.exe`。在 Windows 电脑上双击运行即可安装到当前用户的 `%LOCALAPPDATA%\SkyCityDemo`，不需要安装 Python、pygame 或其他开发工具。

安装程序会创建开始菜单和桌面快捷方式，并将建筑素材、云海、悬瀑、说明文档与游戏执行文件一起复制。卸载入口位于开始菜单的“Uninstall Sky City Demo”。

重新生成安装包：

```powershell
python -m PyInstaller --noconfirm --clean --windowed --name SkyCityDemo --add-data "generated_assets;generated_assets" game.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\make_installer.ps1
```

安装包使用 Windows 自带的 IExpress 和 `tar.exe` 生成，不依赖第三方安装器。目标电脑需要 Windows 10 或更高版本。
