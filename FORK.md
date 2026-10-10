# Clash Verge Rev 个人修改版

本仓库基于官方 [clash-verge-rev](https://github.com/clash-verge-rev/clash-verge-rev) 的稳定版 tag 修改，只加了下面列出的功能，其余与官方一致。

| 项目 | 内容 |
|---|---|
| 当前基于 | `v2.5.8` |
| 修改分支 | `feature/tray-mode-icon` |
| 已编译平台 | Windows x64 |

## 修改内容：托盘图标显示出站模式

官方版本只在切换「系统代理 / TUN」时改变托盘图标，切换出站模式（规则 / 全局 / 直连）时图标不变，必须点开托盘菜单才能看到当前模式。

本版本在托盘图标右下角加了字母角标：

| 角标 | 出站模式 | 颜色（彩色图标） |
|---|---|---|
| **R** | 规则 Rule | 青绿 |
| **G** | 全局 Global | 蓝 |
| **D** | 直连 Direct | 深灰 |

底色含义不变：粉紫 = 普通，橙 = 系统代理，绿 = TUN。另外，鼠标悬停提示中增加了一行「出站模式」。

![托盘图标预览](fork/tray-mode-icons-preview.png)

上 3 行是 Windows / Linux 使用的彩色图标，下 3 行是 macOS 使用的黑白模板图标。

说明：

- 设置了「自定义托盘图标」时仍使用自定义图标，不显示角标。
- 通过 Clash Verge 自身（托盘菜单、主界面、代理页、快捷键）切换模式时图标会立即更新。
- 若开启了外部控制器，并通过网页面板（Yacd、MetaCubeXD 等）直接修改 mihomo 的模式，图标和托盘菜单的勾选都不会跟着变（官方版本的托盘菜单也有此问题）。

### 改动的文件

| 文件 | 说明 |
|---|---|
| `src-tauri/src/core/tray/mod.rs` | 按「代理方式 × 出站模式」选择图标，悬停提示增加出站模式 |
| `src-tauri/src/feat/effects.rs` | 修改模式时同时刷新悬停提示 |
| `src-tauri/icons/tray-icon*-{rule,global,direct}.ico` | 18 个新图标（原有图标保留，作为生成脚本的底图） |
| `fork/` | 本修改版专用的脚本、配置与预览图，与官方文件分开存放，减少 rebase 冲突 |
| `FORK.md`、`README.md` 顶部 2 行 | 本说明 |

## 安装使用注意

1. **关闭自动检查更新**（设置 →「杂项设置」→「自动检查更新」）。否则官方发布新版本后会自动更新为官方版，本修改会被覆盖。
2. 安装包没有代码签名：Windows 会提示「未知发布者」，选择「仍要运行」即可。
3. 版本号与官方相同，安装时会直接覆盖已安装的官方版。

## 编译环境（Windows）

为节省 C 盘空间，工具尽量安装在 D 盘：

| 工具 | 位置 | 说明 |
|---|---|---|
| MSVC Build Tools 2022 | `D:\BuildTools\2022` | 只装「VC x64 编译器」+「Windows 11 SDK」；SDK 固定装在 C 盘 |
| Rust（rustup） | `D:\Rust` | 用户环境变量 `RUSTUP_HOME=D:\Rust\rustup`、`CARGO_HOME=D:\Rust\cargo`；工具链版本由仓库的 `rust-toolchain.toml` 自动决定 |
| pnpm（独立版 exe） | `D:\Tools\pnpm\pnpm.exe` | 版本需与 `package.json` 中的 `packageManager` 一致 |
| Node.js | 系统已安装 | 22.x 可用 |

如果官方升级了 pnpm 版本，从 [pnpm releases](https://github.com/pnpm/pnpm/releases) 下载对应版本的 `pnpm-win-x64.exe`，替换 `D:\Tools\pnpm\pnpm.exe` 即可。

## 编译打包

在仓库根目录执行：

```bash
pnpm install --frozen-lockfile
pnpm run prebuild
pnpm build -c fork/tauri-no-updater.json
```

- `prebuild` 会从 GitHub 下载 mihomo 核心和规则数据库，网络不通时需要开代理。
- `-c fork/tauri-no-updater.json` 关闭「生成更新包」。更新包需要官方的签名私钥，不关闭的话打包最后一步会报错。
- 生成的安装包：`target\release\bundle\nsis\Clash Verge_<版本>_x64-setup.exe`
- 首次编译约 15～20 分钟；`target` 目录约 5 GB，可随时删除，删除后下次重新完整编译。

## 跟进官方新稳定版

官方发布新的稳定版（例如 `v2.6.0`）后：

```bash
git fetch upstream --tags
git switch feature/tray-mode-icon
git rebase --onto v2.6.0 v2.5.8
```

`rebase --onto <新 tag> <旧 tag>` 把「旧 tag 之后的本修改」搬到新 tag 上。之后每次升级，把 `<旧 tag>` 换成上一次基于的版本，并更新本文开头表格中的「当前基于」。

可能出现冲突的地方：

- `src-tauri/src/core/tray/mod.rs`：官方改动了 `get_tray_icon` / `default_icon` / `update_tooltip` 附近的代码时。
- `src-tauri/src/feat/effects.rs`：官方改动了 `mode` 对应的 effect 列表或其测试时。
- `README.md` 顶部：官方改动了 README 开头时。

解决冲突后执行 `git rebase --continue`，然后重新执行上面的「编译打包」三条命令，确认没问题后推送：

```bash
git push --force-with-lease origin feature/tray-mode-icon
```

rebase 会改写提交历史，所以推送必须带 `--force-with-lease`，这是正常的。

## 修改图标

图标由脚本生成：在原图标右下角叠加几何绘制的字母角标，不依赖字体。需要 Python（Pillow）和 ImageMagick（`magick` 命令）。

```bash
python fork/gen-tray-mode-icons.py src-tauri/icons <临时输出目录>
python fork/preview-tray-mode-icons.py src-tauri/icons <临时输出目录> fork/tray-mode-icons-preview.png
```

角标颜色（`MODE_COLOR`）、大小（`BADGE`）、透明间隙（`GAP`）都在脚本开头。确认预览满意后，把输出目录中的 `.ico` 复制到 `src-tauri/icons/`。
