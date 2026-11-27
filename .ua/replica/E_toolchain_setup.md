# E 工具链安装指引：Unity、Blender 与两端 MCP 接入 DSH

调研日期：2026-11-27。适用机器：本机（Windows 11，用户 OVO）。读者：第一次装 Unity 和 Blender 的独立开发者。

证据标记：[实查] 表示调研当天从网页、GitHub API 或本机命令直接取到；[经验] 表示行业通用做法，没有取到官方原文；[未查到] 表示查了但没拿到可靠来源。第 8 节列出全部来源链接。

本文只是安装指引。调研过程没有安装任何软件，没有改项目里其他文件，也没有改 DSH 配置。文中所有配置片段都没有在本机实际跑通过（因为 Unity 和 Blender 都还没装），装好后按第 9 节把结果回传。

---

## 0 一页结论

| 项 | 推荐 | 一句理由 |
|---|---|---|
| Unity | Unity 6.3 LTS，具体版本 6000.3.29f1（2026-11-19 发布的补丁；Hub 里若有更新的 6000.3.x 就装更新的） | 当前唯一处于标准支持期的 LTS，支持到 2027-12-04；Cinemachine 3、URP、VFX Graph、Input System 的包组合稳定 |
| Unity 备选 | 团结引擎 1.11.2（2026-11-25，内核为 Unity 2022.3 代码线） | 仅当国际版 Unity 6 在你的网络和账号下拿不到时使用，见下方“先决问题” |
| Blender | Blender 5.2 LTS，具体版本 5.2.5（2026-11-23） | LTS 维护到 2028-07；两个 Blender MCP 都支持；比刚发布的 5.3.0 稳 |
| Unity MCP 主方案 | CoplayDev/unity-mcp（MCP for Unity）v10.3.0，HTTP 方式接 DSH | 星数最高、覆盖最全，唯一明确带 VFX Graph、Trail、Line、粒子工具和截图；同时兼容 Unity 6 与 2021.3 以上 |
| 与 unity-skills 的关系 | 互补，两个都装 | unity-skills 走 REST（端口 8090 到 8100），强在批量事务、dryRun、审计；它的粒子模块不含 VFX Graph，这块交给 MCP |
| Blender MCP 主方案 | ahujasid/mcp-for-blender（原 blender-mcp），PyPI 包 mcp-for-blender 2.3.3 | 更新最活跃，本机 blender-skills 技能就是按它写的；能执行 Python、能取视口截图 |

先决问题（建工程前必须定）：Unity 中国在 2025-04-07 公告“Unity 6 及后续版本将不再向中国用户提供，相关需求将由团结引擎承接”[实查]。本机调研时直连 unity.com 的下载页不通，发布页被导向 unity.cn 的团结引擎页面[实查]。所以 6000.3.29f1 是有条件的首选：能从 Unity Hub 国际版正常登录并在安装列表里看到 6000.3.x 就用它；看不到就用团结引擎 1.11.2。两条线的工程不能互相降级（Unity 6 工程打不开 2022.3 内核的团结引擎），工程建好后不要再换线。

预计下载体积与磁盘占用：

| 项 | 下载 | 装好后占用 | 来源 |
|---|---|---|---|
| Blender 5.2.5 安装包（msi） | 349.0 MB | 约 1.5 GB | 下载体积[实查]，占用[经验] |
| Unity Hub | 约 0.15 GB | 约 0.5 GB | [经验]，官方数字[未查到] |
| Unity 编辑器 6000.3 本体 | 约 3 到 5 GB | 约 7 到 10 GB | [经验]，官方数字[未查到] |
| Android Build Support 含 SDK、NDK、OpenJDK | 约 3 到 5 GB | 约 8 到 12 GB | [经验] |
| Windows IL2CPP、iOS 模块、中文语言包 | 约 1.5 到 2.5 GB | 约 3 到 5 GB | [经验] |
| 新建 URP 工程（含 Library 缓存） | 无 | 约 2 到 5 GB，随资源增长 | [经验] |
| 合计 | 约 9 到 13 GB | 约 22 到 34 GB | 以 Hub 安装界面显示的数字为准 |

本机 C 盘剩 103 GB，D 盘剩 85 GB，都够。建议编辑器装 C 盘（默认位置），工程放 D 盘。

---

## 1 本机现状检查结果

检查时间 2026-11-27，全部为本机命令实测[实查]。

| 项目 | 结果 |
|---|---|
| 系统 | Windows 内核号 10.0.26300.10075（Windows 11） |
| 磁盘 | C 盘共 365 GB，剩 103 GB；D 盘共 367 GB，剩 85 GB |
| Unity 编辑器 | 未安装。`C:\Program Files\Unity`、`D:\Unity` 不存在，注册表卸载项里没有 Unity |
| Unity Hub | 未安装。`C:\Program Files\Unity Hub` 不存在，`%APPDATA%\UnityHub` 不存在 |
| 团结引擎、Tuanjie Hub | 未安装。`C:\Program Files\Tuanjie`、`C:\Program Files\Tuanjie Hub` 不存在 |
| Blender | 未安装。`C:\Program Files\Blender Foundation`、`D:\Blender` 不存在，`where blender` 无结果，`%APPDATA%\Blender Foundation` 不存在 |
| `D:\Program Files` 下现有 | Docker、Git、Google、Java、Microsoft Visual Studio、NVIDIA GPU Computing Toolkit、SuYou、Tencent |
| git | 2.56.0.windows.2，位于 `C:\Program Files\Git\cmd\git.exe` |
| git-lfs | 3.8.0，已安装 |
| .NET SDK | 10.0.302，位于 `C:\Program Files\dotnet`，没有其他版本 |
| Node.js | v26.0.0，npm 11.12.1，位于 `D:\nodejs` |
| Python | 3.12.8，位于 `D:\TmpProject\miniconda3\python` |
| uv、uvx | 0.11.26，两处都有：`D:\TmpProject\miniconda3\Scripts\uvx.exe` 和 `C:\Users\OVO\AppData\Local\hermes\bin\uvx.exe` |
| Java | 17.0.12 LTS，位于 `D:\Program Files\Java\jdk-17`，JAVA_HOME 未设置 |
| adb | 1.0.41（platform-tools 37.0.1，winget 安装）。ANDROID_HOME、ANDROID_SDK_ROOT 都为空，没有独立的 Android SDK |
| Visual Studio | 已装两套：`C:\Program Files\Microsoft Visual Studio\18\Community` 和 `D:\Program Files\Microsoft Visual Studio\2022`（Community）。是否装了 Unity 工作负载没有检查 |
| Rider、VS Code | Rider 未装；`where code` 无结果（VS Code 不在 PATH，可能未装） |

DSH 相关：

| 项目 | 结果 |
|---|---|
| MCP 配置文件 | `C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml`（共 315 行）。格式是 YAML，不是 Claude Desktop 那种 mcpServers JSON |
| 已配置的 MCP 服务器 | 两个，都在该文件第 29 行 `- insert:` 列表下：`mcp-kicad`（第 30 行起）和 `mcp-claude-video-vision`（第 42 到 52 行） |
| unity-skills 技能 | 两份：项目级 `D:\GameDev\the-shuttle-badminton-glory\.dsh\skills\unity-skills\`（优先级高，本项目实际生效）和用户级 `C:\Users\OVO\.dsh\skills\unity-skills\`。来源仓库 Besty0728/Unity-Skills。项目级那份的 Python 客户端 `scripts\unity_skills.py` 第 26 行写的是 `__version__ = "2.9.1"`，上游最新发布是 v3.0.3（2026-11-21） |
| unity-skills 的要求 | Unity 2022.3 以上或 6000.x；Unity 工程里要装 UnitySkills 包；包在编辑器里起本地 REST 服务，端口 8090 到 8100 先到先得；Python 3 跑自带客户端 |
| blender-skills 技能 | 两份：项目级 `.dsh\skills\blender-skills\` 和用户级。来源仓库 arjun988/blender-skills，94 个子技能 |
| blender-skills 的要求 | 它的 `references\mcp-integration.md` 和 `references\mcp-tools.md` 明确以 ahujasid 的 Blender MCP 为优先执行通道，MCP 不可用时退回给出 bpy 脚本让人手动跑。项目里 `.dsh\skills\SKILLS.md` 第 38 行把它记成“咨询型技能包，不驱动 Blender 进程”，这句话不完整：装好 Blender MCP 后它是能驱动 Blender 的 |

结论：Unity、Unity Hub、Blender 三样都要从零装。uv、Node、Python、git、git-lfs、Java 17、adb 这些 MCP 和安卓调试需要的周边工具本机都已具备，不用再装。

---

## 2 Unity 安装步骤

### 2.1 先判断走哪条线

Unity 6 的版本现状[实查，来源 endoflife.date 数据集，2026-11-27 读取]：

| 分支 | 发布日期 | 状态 | 最新补丁 |
|---|---|---|---|
| Unity 6.0 LTS（6000.0） | 2024-04-29，2024-10-16 转 LTS | 标准支持已于 2026-10-16 结束，扩展支持到 2027-10-16 | 6000.0.85f2（2026-11-03） |
| Unity 6.1（6000.1） | 2025-04-23 | 已于 2025-08-12 停止支持 | |
| Unity 6.2（6000.2） | 2025-08-12 | 已于 2025-12-04 停止支持 | |
| Unity 6.3 LTS（6000.3） | 2025-12-04 | 支持到 2027-12-04，扩展支持到 2028-12-04 | 6000.3.29f1（2026-11-19） |
| Unity 6.4（6000.4） | 2026-03-18 | 已于 2026-06-17 停止支持 | |
| Unity 6.5（6000.5） | 2026-06-15 | 已于 2026-08-31 停止支持 | 6000.5.11f1 |
| Unity 6.6（6000.6） | 2026-08-31 | 当前最新的 Update 版，非 LTS | 6000.6.11f1（2026-11-26） |
| Unity 2022.3 LTS | | 支持已于 2025-05-07 结束 | 2022.3.62f3 |

为什么选 6.3 LTS 而不是 6.6：

1. 手游要跟着应用商店每年提高的目标 API 走，LTS 会持续收到这类补丁，Update 版三个月左右就停更。
2. 6.3 LTS 的开发环境要求明确：Android SDK 35、NDK r27c、OpenJDK 17，全部由 Unity Hub 自动安装[实查，Unity 6.3 系统需求页]。
3. Cinemachine 3 在 6.3 里仍从 Package Manager 安装；到 6.6 它变成随编辑器分发的核心包，包管理方式变了[实查，Cinemachine 3.1 文档]。原型期用包组合稳定的版本省事。
4. 本项目要用的 URP、Shader Graph、VFX Graph、粒子系统、Input System、Animation Rigging、Timeline 在 6.3 里都是现成的包。
5. 确定性帧同步不依赖引擎版本。逻辑层应写成不引用 UnityEngine 的纯 C# 程序集，用定点数，60 tick 固定步长，不用引擎自带物理和浮点[经验]。所以联机需求不构成选新版的理由。

国际版与中国线的取舍：

| 对比项 | 国际版 Unity 6.3 LTS | 团结引擎 1.11.2 |
|---|---|---|
| 内核 | Unity 6（6000.3） | Unity 2022.3 代码线，内部版本号形如 2022.3.62t19[实查] |
| 在大陆能否直接获取 | 官方公告称 Unity 6 不再向中国用户提供；本机直连下载页不通[实查] | 能，unity.cn 直接下载[实查] |
| 个人版条件 | Unity Personal：过去 12 个月收入加融资低于 20 万美元可免费用[实查] | 团结个人版：财务规模低于 20 万美元的个人和小企业免费，2025-06 起与全球定价一致[实查，媒体转述] |
| 账号与许可 | Unity ID，在 Unity Hub 里登录后领个人版许可 | 在 Tuanjie Hub 里激活[实查，团结手册] |
| 两边账号、许可是否互通 | [未查到] 权威说明。按两个 Hub 各自激活来处理，不要假设互通 | 同左 |
| 能否发布到海外 | 能 | 公告称基于团结引擎的项目可继续在全球发布[实查] |
| 本文推荐的两个 Unity 接入方案能否用 | 都能 | CoplayDev 和 Unity-Skills 都有用户在团结引擎上使用的反馈，但两个仓库都没有官方声明支持[实查] |
| Unity 官方 CLI 和 Pipeline 包 | 能，要求 Unity 6.0 以上 | 是否支持[未查到]，按版本要求推断大概率不能 |

判断流程：按 2.2 装 Unity Hub 并登录，打开安装编辑器的列表。列表里有 6000.3.x 就走国际版；Hub 下不动、登录不了，或者列表里只有团结引擎，就走 2.6 的团结引擎路线。是否符合 Unity 的地区条款由你自己确认，本文不做法律判断。

### 2.2 安装 Unity Hub

1. 打开 Unity 官方下载页，下载 Windows 版 Unity Hub 安装程序：

```
https://unity.com/download
```

2. 双击安装程序，安装位置保持默认 `C:\Program Files\Unity Hub`。
3. 启动 Unity Hub，点左上角头像，选 Sign in，在弹出的浏览器里用 Unity ID 登录（没有就先注册）。
4. 登录后点右上角齿轮进 Preferences，选 Licenses，点 Add，选 Get a free personal license，同意条款。看到一条 Personal 许可就算成功。
5. 在 Preferences 的 Appearance 里可以把 Hub 语言改成简体中文。

如果下载页打不开：本机调研时 `https://unity.com/download` 用命令行访问超时，`https://unity.com/releases/...` 被导向 `https://unity.cn/tuanjie/releases`[实查]。这种情况直接跳到 2.6。

### 2.3 安装编辑器并勾选模块

1. 在 Unity Hub 左侧点 Installs（安装），右上角点 Install Editor（安装编辑器）。
2. 在 Official releases 页签里找 Unity 6.3 LTS，版本号 6000.3.29f1 或更新的 6000.3.x，点 Install。
3. 模块勾选如下：

| 模块 | 勾不勾 | 说明 |
|---|---|---|
| Microsoft Visual Studio Community | 不勾 | 本机已有 Visual Studio，见 2.5 |
| Android Build Support | 勾 | 展开后把 OpenJDK 和 Android SDK & NDK Tools 两个子项都勾上。本机虽有 Java 17 和 adb，仍建议用 Hub 自带的整套，版本与编辑器匹配 |
| iOS Build Support | 勾（可后补） | 在 Windows 上只能导出 Xcode 工程，真正出包需要一台 Mac 和 Xcode 16 以上[实查] |
| Windows Build Support (IL2CPP) | 勾 | PC 试玩包用 IL2CPP 后端时需要 |
| Language packs 里的 简体中文 | 勾 | 编辑器界面中文。装完在 Edit > Preferences > Languages 里切换 |
| Documentation | 可选 | 离线文档，联网不便时有用 |
| 其余平台（WebGL、Linux、Mac、主机等） | 不勾 | 用不到，以后可以补装 |

4. 点 Continue，同意 Android SDK 的许可，等待下载安装。体积见第 0 节。
5. 以后要补模块：Installs 页里点该版本右侧的齿轮，选 Add modules。

### 2.4 新建工程

1. 先用资源管理器建好父目录 `D:\GameDev\the-shuttle-badminton-glory\unity`。
2. Unity Hub 左侧点 Projects（项目），右上角点 New project（新建项目）。
3. 顶部 Editor Version 选刚装的 6000.3.x。
4. 模板选 Universal 3D。不要选 Universal 3D sample（带一堆示例资源），也不要选 Built-in 或 HDRP。Universal 3D 是预配好 URP 3D 渲染器的空工程[实查，Unity 6.3 手册]。
5. Project name 填 `TheShuttle`，Location 选 `D:\GameDev\the-shuttle-badminton-glory\unity`。最终工程路径是：

```
D:\GameDev\the-shuttle-badminton-glory\unity\TheShuttle
```

6. Connect to Unity Cloud 和 Use Unity Version Control 两个勾都取消。版本管理用现有的 git。
7. 点 Create project，第一次打开要几分钟。

为什么选 URP：

1. 目标平台是 Android 和 iOS，URP 是 Unity 为移动端到中端 PC 设计的可伸缩管线，HDRP 不面向手机[经验]。
2. 3D 卡通风需要自定义着色（描边、色阶光照），URP 配 Shader Graph 是最常见的做法[经验]。
3. VFX Graph 和 Shader Graph 都只在可编程渲染管线下可用，Built-in 管线用不了 VFX Graph[经验]。
4. 本机 unity-skills 技能的评测集 41 个任务全部跑在 URP 上[实查]，AI 工具链在 URP 下路径最熟。

为什么工程不放 References 里：`References/` 在本项目是只读的参考资料区，里面有带零宽空格的文件名和 7 个超过 100 MB 被 .gitignore 排除的视频。Unity 工程会生成几个 GB 的 Library 缓存并频繁读写，放进去会破坏只读纪律，也容易把参考素材误导入成游戏资源。独立的 `unity\TheShuttle` 路径没有中文和空格，对 Unity、Android 构建和各 MCP 工具都最安全。

建好工程后要装的包（Window > Package Manager，左上角 Packages 下拉切到 Unity Registry，搜索后点 Install）：

| 包 | 用途 |
|---|---|
| Cinemachine（3.x） | 镜头 |
| Input System | 摇杆和三键输入。装完会提示重启编辑器，点 Yes |
| Visual Effect Graph | 高级粒子特效 |
| Animation Rigging | 持拍手、击球姿态的程序化修正 |
| Timeline | 觉醒演出等过场。Universal 3D 模板通常已带 |
| Shader Graph | 随 URP 已带，确认存在即可 |
| Test Framework | 跑逻辑层单元测试。通常已带 |

### 2.5 代码编辑器

本机已有 Visual Studio，不必再装别的。推荐做法：

1. 开始菜单打开 Visual Studio Installer，在已装的 Visual Studio 上点“修改”，勾选工作负载“使用 Unity 的游戏开发”，点修改完成安装。
2. 回到 Unity，Edit > Preferences > External Tools，External Script Editor 选对应的 Visual Studio，点 Regenerate project files。

其他选择：JetBrains Rider 对 Unity 的支持最完整，对非商业用途有免费许可[经验，具体条款以 JetBrains 官网为准]；VS Code 需要装微软的 Unity 扩展和 C# Dev Kit，并依赖 .NET SDK（本机已有 10.0.302）[经验]。

### 2.6 备选路线：团结引擎

仅在国际版 Unity 6 拿不到时使用。

1. 打开团结引擎下载页：

```
https://unity.cn/tuanjie/releases
```

2. 下载 Tuanjie Hub 并安装，用 Unity 中国账号登录，在 Hub 里激活个人版许可。调研时该页面里没有找到 Hub 的直链，按页面上的按钮下载[实查]。
3. 在 Tuanjie Hub 里安装团结引擎 1.11.2（2026-11-25 发布），模块勾选同 2.3。
4. 新建工程同 2.4，模板选 URP 的 3D 模板。

走这条线要知道的差别：内核是 2022.3，URP、Shader Graph、VFX Graph 是 14.x 这一代；Cinemachine 3、Input System、Animation Rigging、Timeline 是否都能在团结引擎的包管理器里装到对应版本没有实查，装的时候留意。Unity 官方 CLI 要求 Unity 6.0 以上，这条线大概率用不了；第 4 节推荐的两个接入方案不受影响。

---

## 3 Blender 安装步骤

### 3.1 版本选择

Blender 版本现状[实查，来源 endoflife.date 数据集与阿里云镜像目录]：

| 版本 | 发布日期 | 状态 | 最新补丁 |
|---|---|---|---|
| 4.2 LTS | 2024-07-16 | 支持已于 2026-07-16 结束 | 4.2.23 |
| 4.5 LTS | 2025-07-15 | 维护到 2027-07 | 4.5.17（2026-11-23） |
| 5.0 | 2025-11-18 | 已被后续版本取代 | 5.0.1 |
| 5.1 | 2026-03-17 | 已被 5.2 取代 | 5.1.2 |
| 5.2 LTS | 2026-07-14 | 维护到 2028-07 | 5.2.5（2026-11-23） |
| 5.3 | 2026-11-10 | 当前最新稳定版，非 LTS | 5.3.0 |

推荐 5.2 LTS 的 5.2.5，理由：

1. LTS 维护两年，原型期到正式开发期不用换版本。5.3.0 发布才两周多，还没有补丁版。
2. MCP 兼容：ahujasid 的 mcp-for-blender 要求 Blender 3.0 以上；Blender 官方实验室的 MCP 插件要求 5.1.0 以上[实查]。选 5.2 两个都能用，选 4.5 LTS 就用不了官方那个。
3. 5.x 的变化已经沉淀：5.0 起 EEVEE Next 成为唯一的 EEVEE（引擎标识从 BLENDER_EEVEE_NEXT 改回 BLENDER_EEVEE），5.1 升到 Python 3.13，5.2 调整了几何节点修改器的 Python 接口[实查，第三方梳理]。AI 写 bpy 脚本时要按 5.x 的接口写，网上 4.x 之前的旧脚本可能报错。
4. 与 Unity 的交换格式 FBX 和 glTF 在 5.2 都可用。5.0 起移除了 Collada 导入导出，本项目用不到。
5. 5.3 独有的功能里与本项目有关的只有高斯泼溅导入（mcp-for-blender 的 generate_gaussian_world 工具要求 5.3 以上）[实查]，卡通风羽毛球用不到。

注意文件格式：5.0 改了 .blend 格式，4.5 LTS 能读 5.x 的文件，更早的版本读不了[实查，第三方梳理]。团队里只有你一个人，统一用 5.2 即可。

### 3.2 下载

官方下载页（LTS 版本入口）。调研时这个地址用命令行访问返回 403，没能确认页面内容，5.2 的具体子页面地址[未查到]，请用浏览器打开后在页面里找 5.2 LTS：

```
https://www.blender.org/download/lts/
```

国内镜像（本机实测可达，建议直接用这个；官方下载域名 download.blender.org 从本机访问超时）[实查]：

```
https://mirrors.aliyun.com/blender/release/Blender5.2/
```

在镜像目录里选这个文件（349.0 MB，2026-11-24 上架）：

```
blender-5.2.5-windows-x64.msi
```

同目录还有便携版 `blender-5.2.5-windows-x64.zip`（386.9 MB）。清华和中科大镜像调研时不可达[实查]。

### 3.3 安装

1. 双击 msi，一路 Next。安装位置保持默认 `C:\Program Files\Blender Foundation\Blender 5.2`，路径里不要有中文。
2. 首次启动在欢迎画面的 Language 里可以选简体中文。建议只翻译界面，取消“新建数据”的翻译（偏好设置 > 界面 > 翻译 > 取消勾选“新建数据”），否则新建的物体、材质会叫中文名，导到 Unity 和写脚本时容易出编码问题。
3. 偏好设置 > 系统 > 网络 里有“允许联机访问”开关。主推的 mcp-for-blender 不强制要求打开；如果用 Blender 官方实验室的 MCP 插件，必须打开，否则插件报错[实查]。
4. Blender 自己的工程文件（.blend）建议放在项目里一个单独的源文件目录，例如 `D:\GameDev\the-shuttle-badminton-glory\art_src\vfx\`，不要直接放进 Unity 工程的 Assets。原因见 6.3。这个目录现在不存在，等你确认后再建。

安装版与便携版怎么选：

| 对比 | 安装版（msi） | 便携版（zip） |
|---|---|---|
| 文件关联、开始菜单 | 有 | 没有，解压后直接运行 blender.exe |
| 插件和配置存放 | `%APPDATA%\Blender Foundation\Blender\5.2\` | 默认同左；在解压目录里建 `portable` 文件夹后才存到本地 |
| 多版本并存 | 可以，不同小版本号装不同目录 | 最方便 |
| `uvx mcp-for-blender install-addon` 能否自动找到 | 能找到标准位置 | 用了 portable 目录后可能找不到，需手动从磁盘安装 |

新手用安装版。

---

## 4 Unity MCP 安装与接入 DSH

### 4.1 方案选择

主方案：CoplayDev/unity-mcp（包名 MCP for Unity）。配套：本机已装的 unity-skills 技能所需的 UnitySkills 包。两个都装进同一个 Unity 工程，端口不冲突（一个 8080，一个 8090 起）。完整对比见第 8 节。

分工建议：

| 任务 | 用哪个 |
|---|---|
| 批量建场景、批量改组件、需要整批回滚的操作 | unity-skills（支持最多 50 步的事务批处理和 dryRun 预演） |
| 内置粒子系统的参数调整 | 两者都行。unity-skills 有 31 个粒子技能 |
| VFX Graph、Trail Renderer、Line Renderer、着色器与贴图 | MCP for Unity（manage_vfx、manage_shader、manage_texture） |
| 截图给 AI 看效果 | MCP for Unity（manage_camera 的 screenshot 与多视角截图），unity-skills 的 Scene 模块也有截图 |
| 读 Console、跑测试 | 两者都行 |
| 在编辑器里执行任意 C# | MCP for Unity（execute_code），风险高，见第 7 节 |

同一时间只让一个通道对同一个场景做写操作，避免互相覆盖。

### 4.2 安装 MCP for Unity（主方案）

前置条件[实查，官方安装页]：Unity 2021.3 LTS 或更新；Python 3.10 以上和 uv；git 在 PATH 里。本机三项都满足。

1. 在 Unity 里打开 `TheShuttle` 工程。
2. 菜单 Window > Package Manager，点左上角加号，选 Add package from git URL（通过 git URL 添加包）。
3. 粘贴下面的地址，点 Add。这里钉在调研时最新的正式版 v10.3.0（2026-10-04 发布）：

```
https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#v10.3.0
```

4. 等包导入和脚本编译完成。导入后会自动弹出 setup 向导，检查 Python 和 uv，全绿即可。
5. 菜单 Window > MCP for Unity 打开面板。确认传输方式是 HTTP（默认），点 Start Server。状态显示 Connected 或 Running 就是起来了。默认端点是：

```
http://localhost:8080/mcp
```

6. 面板里的 Configure All Detected Clients 按钮只认识 Claude、Cursor 这类客户端，不认识 DSH。不用点它，DSH 这边按 4.4 手动配置。

国内网络提示：第 3 步要从 github.com 拉代码，本机实测 github.com 可达但较慢（约 3 秒）[实查]。服务器端 Python 包 mcpforunityserver 由 uvx 从 PyPI 下载，可以设置环境变量走阿里云镜像（本机实测该镜像上有这个包）[实查]。在 PowerShell 里执行一次，之后重开 Unity：

```powershell
setx UV_DEFAULT_INDEX "https://mirrors.aliyun.com/pypi/simple/"
```

### 4.3 安装 UnitySkills 包（配套 unity-skills 技能）

前置条件[实查]：Unity 2022.3 以上，完整支持 Unity 6。

1. 同样在 Package Manager 里点加号，选 Add package from git URL。
2. 版本要与本机技能对齐。项目级技能的客户端版本是 2.9.1，上游仓库有对应的 v2.9.1 标签[实查]，先装这个：

```
https://github.com/Besty0728/Unity-Skills.git?path=/SkillsForUnity#v2.9.1
```

如果之后把 DSH 里的 unity-skills 技能更新到 3.x，再把这里换成不带标签的稳定版地址（当前对应 v3.0.3）：

```
https://github.com/Besty0728/Unity-Skills.git?path=/SkillsForUnity
```

3. 菜单 Window > UnitySkills（快捷键 Alt+Shift+U）打开面板，点顶栏的服务开关。Console 里出现下面这行就是起来了：

```
[UnitySkills] REST Server started at http://localhost:8090/
```

4. 想让它每次开工程自动启动：面板里 设置 > 服务器，把“编辑器启动时运行”和“编译后自动重启”两个都打开。只开前一个的话，第一次改脚本触发重编译后服务就停了[实查，官方中文安装指南]。
5. 权限模式有 Approval、Auto、Bypass 三种，新装默认 Auto。原型期保持 Auto；不要一上来就切 Bypass。操作审计写在工程的 `Library\UnitySkillsAudit.jsonl`。
6. 这个方案不需要在 DSH 里加 MCP 配置。技能通过自带的 Python 客户端直接访问 REST 接口。

验证 REST 服务（在 PowerShell 或 Git Bash 里）：

```bash
curl http://localhost:8090/health
```

返回一段 JSON，里面有 instanceId、currentMode 等字段就是通了。再让技能自带客户端列出实例：

```bash
python "D:\GameDev\the-shuttle-badminton-glory\.dsh\skills\unity-skills\scripts\unity_skills.py" --list-instances
```

### 4.4 把 MCP for Unity 接进 DSH

DSH 的 MCP 配置在这个文件里，是 YAML：

```
C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml
```

步骤：

1. 完全退出 DSH。
2. 先备份（同目录已有多份 `.bak-*` 备份，这是既有做法）。PowerShell：

```powershell
Copy-Item "C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml" "C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml.bak-before-unity-blender"
```

3. 用文本编辑器打开该文件，找到第 29 行的 `- insert:`。它下面现在有 `mcp-kicad` 和 `mcp-claude-video-vision` 两条。在 `mcp-claude-video-vision` 那条的最后一行（`failOnStartupError: false`，第 52 行）之后、下一个顶层条目 `- id: dsh-whale-widget` 之前，插入下面这段。缩进必须和上面两条完全一致：`- id` 前面是 4 个空格，不能用 Tab。

```yaml
    - id: mcp-unity
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: unity
        transport: streamable-http
        url: 'http://localhost:8080/mcp'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

4. 保存，重新启动 DSH。配置只在启动时加载。
5. `failOnStartupError: false` 的意思是 Unity 没开时 DSH 也能正常启动，只是这个服务器的工具不可用。先开 Unity 并启动 MCP 服务，再开 DSH，顺序别反。如果后开的 Unity，重启一次 DSH。

字段说明[实查，DSH 内置文档与本机现有配置]：`transport` 只能是 `stdio` 或 `streamable-http`；`serverName` 只能用字母、数字、下划线、连字符，最长 32 个字符，工具在 DSH 里的名字会变成 `mcp__unity__工具名`；`toolCallTimeoutMs` 是单次工具调用的超时。

与 Claude Desktop 等价的 JSON 写法，仅供对照，DSH 不读这种格式：

```json
{
  "mcpServers": {
    "unityMCP": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

备用接法（stdio）：如果 HTTP 方式连不上，可以让 DSH 自己拉起服务器进程。把上面那段换成下面这段。uvx 必须写完整路径，因为 DSH 启动子进程时会清洗环境变量，不一定带着你终端里的 PATH。

```yaml
    - id: mcp-unity
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: unity
        transport: stdio
        command: 'D:\TmpProject\miniconda3\Scripts\uvx.exe'
        args:
          - '--from'
          - 'mcpforunityserver'
          - 'mcp-for-unity'
          - '--transport'
          - 'stdio'
        env:
          DISABLE_TELEMETRY: '1'
          UV_DEFAULT_INDEX: 'https://mirrors.aliyun.com/pypi/simple/'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

用 stdio 时要在 Unity 的 MCP for Unity 面板里把传输方式也切到 stdio。stdio 方式同一时间只支持一个客户端。

存疑点：DSH 清洗环境变量后 uvx 是否还能找到缓存目录和用户目录没有实测。如果 stdio 方式启动失败，把报错原文回传。

### 4.5 验证

按顺序做，每一步成功再做下一步：

1. Unity 里 MCP for Unity 面板显示服务器在运行。
2. 浏览器或命令行访问端点，有响应（哪怕是报方法不对的错误）就说明端口通了：

```bash
curl -i http://localhost:8080/mcp
```

3. 重启 DSH 后，在对话里问：

```
列出你现在能用的 mcp__unity__ 开头的工具
```

能列出 manage_scene、manage_gameobject、read_console 等就是接上了。

4. 让 AI 列出场景对象：

```
用 Unity MCP 列出当前场景里所有 GameObject 的名字和层级
```

新建的 Universal 3D 工程应该返回 Main Camera、Directional Light、Global Volume 这几个。

5. 让 AI 创建一个 Cube：

```
用 Unity MCP 在当前场景原点上方 1 米处创建一个 Cube，命名为 MCP_Test_Cube，然后读一下 Console 有没有报错
```

回到 Unity 窗口，Hierarchy 里出现 MCP_Test_Cube 就是成功。

6. 验证 unity-skills 通道：

```
用 unity-skills 技能检查 Unity 服务健康状态，然后创建一个名为 Skills_Test_Sphere 的球体
```

7. 两个测试物体确认后手动删掉，不要保存进场景。

---

## 5 Blender MCP 安装与接入 DSH

### 5.1 方案选择

主方案：ahujasid/mcp-for-blender。这个仓库原名 ahujasid/blender-mcp，已改名；PyPI 包名也从 blender-mcp 换成 mcp-for-blender。旧包名 `uvx blender-mcp` 仍能用（旧包最新 2.0.0，2026-09-16），新功能只进新包（最新 2.3.3，2026-11-26）[实查]。

备选：Blender 官方实验室的 MCP（projects.blender.org/lab/blender_mcp，v1.0.3，2026-09-11，要求 Blender 5.1 以上，GPL 许可）。两者默认都用 9876 端口，不能同时启用。对比见第 8 节。

### 5.2 安装 Blender 端插件

网上很多教程写的是老流程（下载 addon.py，侧边栏 BlenderMCP 面板，点 Connect to Claude）。2.3.x 版的名字和流程有变化，以下按调研当天仓库 README 写[实查]。

方法一，命令自动安装（推荐）。先关掉 Blender，在 PowerShell 里执行：

```powershell
uvx mcp-for-blender install-addon
```

它会把插件装进 Blender 的插件目录。如果下载慢，先设置镜像再执行（本机实测阿里云镜像上有这个包）：

```powershell
$env:UV_DEFAULT_INDEX = "https://mirrors.aliyun.com/pypi/simple/"
uvx mcp-for-blender install-addon
```

方法二，手动从磁盘安装（方法一找不到 Blender 时用）：

1. 浏览器打开仓库，下载根目录下的 `addon.py`（调研时确认该文件存在）：

```
https://github.com/ahujasid/mcp-for-blender/blob/main/addon.py
```

2. 打开 Blender，菜单 编辑 > 偏好设置 > 插件（Edit > Preferences > Add-ons）。
3. 点右上角的下拉箭头，选“从磁盘安装”（Install from Disk），选中刚下载的 `addon.py`[经验，Blender 4.2 之后的界面位置]。

两种方法装完后都要做：

1. 在 编辑 > 偏好设置 > 插件 的列表里搜 MCP，勾选启用“Interface: MCP for Blender”。
2. 回到 3D 视图，鼠标放在视图里按 N 键打开右侧边栏，找到“MCP for Blender”标签页。
3. 插件会随 Blender 启动自动起服务。如果面板显示没在运行，点 Start MCP Server。面板上显示的端口应为 9876。
4. 面板里涉及第三方资产库和 AI 生成（Poly Haven、Sketchfab、Hyper3D、Hunyuan3D 等）的开关先都不勾。本项目特效要自己做，用不到，也避免把内容发给第三方。

### 5.3 把 Blender MCP 接进 DSH

同 4.4：退出 DSH，备份 `cordis.patch.yml`，在 `- insert:` 列表里再加一条，保存后重启 DSH。

```yaml
    - id: mcp-blender
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: blender
        transport: stdio
        command: 'D:\TmpProject\miniconda3\Scripts\uvx.exe'
        args:
          - 'mcp-for-blender'
        env:
          BLENDER_HOST: 'localhost'
          BLENDER_PORT: '9876'
          BLENDER_MCP_SAFE_MODE: '1'
          DISABLE_TELEMETRY: 'true'
          UV_DEFAULT_INDEX: 'https://mirrors.aliyun.com/pypi/simple/'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

各环境变量的作用[实查，仓库 README]：

| 变量 | 作用 |
|---|---|
| BLENDER_HOST、BLENDER_PORT | 连接 Blender 插件的地址和端口，默认 localhost 和 9876 |
| BLENDER_MCP_SAFE_MODE=1 | 执行脚本前做预检，拦截直接读写文件、启动外部程序、联网、驻留代码；正常的建模、材质、渲染、保存、导入导出不受影响 |
| DISABLE_TELEMETRY=true | 关闭遥测。README 称遥测默认就是不开启的，这里显式关掉 |
| UV_DEFAULT_INDEX | 让 uvx 从阿里云镜像下载包，可选 |

与 Claude Desktop 等价的 JSON 写法，仅供对照：

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["mcp-for-blender"],
      "env": {
        "BLENDER_MCP_SAFE_MODE": "1",
        "DISABLE_TELEMETRY": "true"
      }
    }
  }
}
```

常见故障[实查，仓库 README 与 blender-skills 的安装文档]：

| 现象 | 处理 |
|---|---|
| spawn uvx ENOENT | command 没写完整路径。用 `where uvx` 查到的全路径 |
| 连接被拒绝 | Blender 没开，或面板里服务没启动 |
| 端口被占 | 同一时间只让一个客户端连；或同时启用了官方实验室的 MCP 插件 |
| 装了新版但行为还是旧的 | 清缓存后重试，命令见下 |
| uvx 选中了 conda 的 Python 导致异常 | 在 args 最前面加 `--python` 和 `3.11` 两项，让 uv 用自己管理的解释器 |

```powershell
uv cache clean mcp-for-blender blender-mcp
uvx --refresh mcp-for-blender --help
```

### 5.4 验证

1. Blender 开着，N 面板里服务在运行。
2. 重启 DSH 后问：

```
列出你现在能用的 mcp__blender__ 开头的工具
```

应该看到 execute_blender_code、look、get_scene_info、get_addon_status 等九个工具[实查]。

3. 让 AI 读场景：

```
用 Blender MCP 的 get_scene_info 告诉我当前场景里有哪些物体
```

默认启动文件应返回 Cube、Light、Camera。

4. 让 AI 创建一个 Suzanne：

```
用 Blender MCP 在场景里添加一个 Suzanne 猴头，放在 Cube 右边 3 米处，加一级表面细分并平滑着色
```

回到 Blender 窗口能看到猴头就是成功。

5. 让 AI 取视口截图：

```
用 Blender MCP 的 look 工具取一张当前视口的截图给我看，再取一张四个角度的多视角图
```

AI 能描述出画面里有立方体和猴头就是成功。

说明：本机 blender-skills 技能的 `references\mcp-tools.md` 是按旧版工具名写的（单独的视口截图工具）。2.3.x 版把看图统一成了 `look` 工具。让 AI 先列出实际工具再用，不要照技能文档里的旧名字硬调。

### 5.5 备选：Blender 官方实验室 MCP

只在主方案出问题时考虑。要点[实查，Blender 官方 Gitea 仓库]：

1. 插件在 Blender 里从 Blender Lab 扩展仓库 `https://lab.blender.org/` 安装并启用，要求 Blender 5.1.0 以上，并且要在偏好设置里打开联机访问。
2. 服务器端要把仓库克隆到本地（下面的 git 地址）。
3. 能力：查看场景、执行任意 Python、渲染、界面导航，并把完整的 Python API 文档和用户手册作为 MCP 资源提供给 AI。

```
https://projects.blender.org/lab/blender_mcp.git
```

假设克隆到 `C:\blender_mcp`，DSH 配置如下：

```yaml
    - id: mcp-blender
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: blender
        transport: stdio
        command: 'D:\TmpProject\miniconda3\Scripts\uv.exe'
        args:
          - '--directory'
          - 'C:\blender_mcp\mcp'
          - 'run'
          - 'blender-mcp'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

---

## 6 Blender 到 Unity 的特效分工与导出导入

### 6.1 先说边界

Blender 里做的特效，下面这些带不进 Unity。这是两个软件的数据模型不同决定的，不是导出设置没调对：

| Blender 里的东西 | 能否进 Unity | 说明 |
|---|---|---|
| 粒子系统（发射器、毛发） | 不能 | FBX 和 glTF 都不携带粒子系统 |
| 几何节点的节点树、模拟区 | 不能 | 只能把某一帧“应用”成普通网格，或把整段烘焙成顶点动画再导 |
| 着色器节点（材质节点图） | 基本不能 | 只有基础色、金属度、粗糙度、法线这类标准贴图槽能跟着走；程序纹理、渐变、混合节点都丢失 |
| EEVEE 或 Cycles 的渲染效果（辉光、体积、运动模糊） | 不能 | 这些是渲染结果，只能渲成图片序列再用 |
| 流体、烟雾、布料、刚体模拟 | 不能直接进 | 只能烘焙成序列帧贴图、顶点动画贴图或 Alembic |
| 修改器、驱动器、约束 | 不能 | 导出时会被应用或烘焙成关键帧 |

能从 Blender 带进 Unity 的：

| 类别 | 内容 | 格式 |
|---|---|---|
| 特效网格体 | 拖尾条带、冲击环、光柱、锥形气浪、烟团、碎片、弧形刀光 | FBX |
| 网格上的数据 | UV（可以多套）、顶点色、法线、软硬边 | FBX |
| 变形动画 | 骨骼动画、形态键（Unity 里叫 BlendShape） | FBX |
| 贴图 | 手绘或烘焙的噪声、渐变、遮罩、溶解图、法线图 | PNG 或 TGA |
| 序列帧图集（flipbook） | 把一段 Blender 渲染的烟、火、爆炸渲成 N×N 的图集 | PNG，带透明通道 |
| 顶点动画贴图（VAT） | 把模拟结果的每帧顶点位置烘进贴图，Unity 里用着色器回放 | 网格 FBX 加 EXR 或 PNG |
| Alembic 缓存 | 逐帧网格 | .abc，手机端不建议，见下 |

在 Unity 里仍然要做的：

| Unity 模块 | 负责什么 |
|---|---|
| Particle System（内置粒子） | 发射、生命周期、速度、大小、颜色随时间变化、序列帧播放、拖尾模块、碰撞。手机上的主力 |
| VFX Graph | 大量粒子的 GPU 模拟。依赖计算着色器，低端安卓机可能不支持，手游里要节制使用[经验] |
| Shader Graph | UV 滚动、溶解、菲涅尔、扭曲、顶点偏移、读顶点色做遮罩、HDR 发光。特效的“动起来”大多靠它 |
| Trail Renderer、Line Renderer | 跟随运动物体实时生成的拖尾和连线 |
| Animator、Timeline | 特效的触发时机、多层特效的编排 |
| URP 后处理 Volume | Bloom 辉光、色彩调整 |
| C# 脚本 | 把游戏状态（球速、蓄力进度、体力值）喂给材质参数和粒子参数 |

一句话：Blender 负责“形状和贴图”，Unity 负责“运动、发光和触发”。指望在 Blender 里把特效完整做好再一键导入 Unity 是走不通的。

关于 Alembic：Unity 的 Alembic 包在手机平台运行时的支持情况没有实查，印象中不支持移动端[未查到]。本项目不要把 Alembic 作为方案。

关于 VAT：Blender 没有内置 VAT 导出，需要第三方插件或脚本[经验]。原型期用不到，列在这里只是让你知道有这条路。

### 6.2 本项目特效分工表

| 特效 | Blender 做什么 | Unity 做什么 | 导出格式 |
|---|---|---|---|
| 球拖尾 | 画拖尾用的条带贴图（头亮尾淡的渐变加噪声）；可选做一个羽毛球形状的残影网格 | Trail Renderer 挂在球上实时生成条带；Shader Graph 做 UV 滚动和按球速变色变宽；速度越快拖尾越长由脚本驱动 | 贴图 PNG；残影网格 FBX |
| 击球火花 | 做星芒、十字闪光、冲击环的面片网格和贴图；可渲一张 4×4 的爆点序列帧图集 | Particle System 的 Burst 一次性发射，Texture Sheet Animation 播序列帧；冲击环用网格加 Shader Graph 做扩散和溶解；按击球质量切换大小和颜色 | 网格 FBX；图集 PNG |
| 移动烟尘 | 用烟雾模拟或手绘做一张 4×4 或 8×8 的烟团序列帧图集，卡通风可以直接做几个烟团网格 | Particle System 在脚底按移动速度发射；急停、起跳、落地各一套发射参数 | 图集 PNG；或烟团网格 FBX |
| 蓄力聚气 | 做向内收拢的螺旋条带网格、能量球网格，展好 UV，用顶点色标出淡出区域 | Shader Graph 做 UV 向心滚动和菲涅尔边缘光；Particle System 做向中心吸入的粒子；蓄力进度由脚本传给材质参数 | 网格 FBX（带顶点色）；贴图 PNG |
| 救球 | 做地面滑行的擦痕条带、扑救时的速度线面片 | Particle System 加 Trail；配合镜头震动和短暂顿帧；动作本身是角色动画 | 网格 FBX；贴图 PNG |
| 觉醒火焰 | 做包裹角色的火焰片层网格（多层弯曲面片）；画火焰噪声和遮罩贴图；可选渲一张火焰循环序列帧 | Shader Graph 用两层噪声滚动加溶解做卡通火焰；Particle System 补火星上升粒子；Bloom 提亮；Timeline 编排觉醒开场 | 网格 FBX；贴图 PNG；可选图集 PNG |
| 落点环 | 做一个贴地的圆环网格或一张环形贴图 | 贴地面片或 URP Decal Projector；Shader Graph 做收缩、脉冲和随落地倒计时变色；位置由弹道预测脚本给出 | 贴图 PNG 即可，网格可用 Unity 自带 Quad |
| 脚下体力环（界面） | 基本不需要。最多画一张环形渐变贴图 | 世界空间 Canvas 上的 Image，填充方式设为 Radial 360；或贴地面片加 Shader Graph 做弧度裁切；体力值由脚本驱动 | 贴图 PNG；或直接在 Unity 里做 |
| 蓄力弧形环（界面） | 基本不需要。最多画弧形底图和高光贴图 | 界面 Image 的径向填充，或 Shader Graph 做的界面着色器按角度裁切；完美区间的高亮也在着色器里做 | 贴图 PNG；或直接在 Unity 里做 |
| 觉醒按键储水效果（界面） | 不需要。水面波纹贴图可以用 Blender 的噪声烘一张，也可以用任何绘图工具画 | Shader Graph 界面着色器：用一个填充高度参数裁切，加正弦波纹和 UV 滚动，满了以后加发光和溢出粒子 | 贴图 PNG；或纯着色器 |

后三项是界面特效，本质是着色器和界面系统的活，放在 Blender 里做没有收益。建议和用户确认：这三项直接在 Unity 里做，Blender 只管前七项的网格和贴图。

### 6.3 FBX 导出设置（Blender 端）

说明：Blender 5.x 手册的 FBX 导出选项页调研时没有取到原文（旧路径已失效，新页面只写了导入）。下面的设置来自通用做法和本机 blender-skills 技能里的示例[经验]，第一次导出后必须按 6.5 用测试件校验。

导出前的准备：

1. 场景单位用公制、单位缩放 1.0（Blender 默认）。按真实尺寸建模，1 个 Blender 单位等于 1 米。羽毛球场长 13.4 米、宽 6.1 米，球网中间高 1.524 米。
2. 物体模式下选中要导出的物体，按 Ctrl+A 选“全部变换”，把位置之外的旋转和缩放应用掉，让缩放回到 1、旋转回到 0。
3. 有修改器的，确认导出时会应用，或者先手动应用。
4. 命名用英文，不要中文、空格。建议 `VFX_HitRing_01` 这种格式。

文件 > 导出 > FBX 里的设置：

| 选项 | 设置 | 说明 |
|---|---|---|
| 限定为 > 选定的物体 | 勾选 | 只导选中的，避免把灯光相机带出去 |
| 物体类型 | 只选 网格 和 骨架 | 特效体不需要相机、灯光、空物体 |
| 变换 > 缩放 | 1.00 | |
| 变换 > 应用缩放（Apply Scalings） | FBX 全部（FBX All） | 让 Unity 里导入后缩放是 1 而不是 100。另一种常见设置是 FBX 单位缩放（FBX Units Scale），两种都见得到，以 6.5 的校验结果为准 |
| 变换 > 前进轴 | -Z 向前 | |
| 变换 > 向上轴 | Y 向上 | |
| 变换 > 应用变换（Apply Transform） | 不勾 | 这是实验性选项，会把轴向转换烘进顶点，对带骨骼和动画的物体容易出错。轴向问题改由 Unity 端的 Bake Axis Conversion 解决 |
| 几何数据 > 平滑 | 仅面 或 法线 | 需要软硬边时选 面 |
| 几何数据 > 应用修改器 | 勾选 | 注意：勾了以后形态键不会导出。要导形态键的物体不能有未应用的修改器 |
| 几何数据 > 顶点色 | sRGB 或 线性 | 用顶点色当遮罩时选线性，Unity 着色器里按数值读 |
| 骨架 > 添加叶骨 | 不勾 | 否则每根末端骨骼多出一根 _end 骨 |
| 骨架 > 仅形变骨骼 | 勾选 | 不导控制器骨骼 |
| 烘焙动画 | 有动画就勾，静态网格不勾 | |
| 烘焙动画 > NLA 片段、全部动作 | 按需要 | 每个动作导成一个片段时勾“全部动作”，并保证每个动作名字清楚 |
| 烘焙动画 > 采样率 | 1.0 | |
| 烘焙动画 > 简化 | 0 | 特效动画要精确，不让它删关键帧 |

用脚本导出时的等价调用（本机 blender-skills 技能里的示例写法，AI 通过 MCP 执行时会用到）：

```python
import bpy
bpy.ops.export_scene.fbx(
    filepath=r"D:\GameDev\the-shuttle-badminton-glory\unity\TheShuttle\Assets\Art\VFX\Meshes\VFX_HitRing_01.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',
    axis_up='Y',
    object_types={'MESH', 'ARMATURE'},
    bake_anim=False,
)
```

不要把 .blend 文件直接丢进 Unity 的 Assets。Unity 手册说明：直接导入 .blend 需要本机装着对应软件，由 Unity 调它的 FBX 导出；最佳做法是自己导出 FBX 再放进 Assets[实查]。.blend 留在 `art_src` 这类源文件目录里。

什么时候用 glTF（.glb）：本机 blender-skills 的 unity-export 子技能建议静态网格可用 GLB、带动画和人形用 FBX。Unity 要读 glTF 需要另装 glTFast 包[经验]。本项目统一用 FBX，少一个变量。

### 6.4 Unity 导入设置

把 FBX 拖进 `Assets\Art\VFX\Meshes\` 后，选中它，在 Inspector 里设置：

Model 页签：

| 选项 | 设置 | 说明 |
|---|---|---|
| Scale Factor | 1 | |
| Convert Units | 勾选 | |
| Bake Axis Conversion | 勾选 | 让 Unity 把轴向转换烘进网格，导入后物体旋转是 0,0,0，不会带一个 -90 度的 X 旋转 |
| Import BlendShapes | 有形态键才勾 | |
| Import Cameras、Import Lights | 不勾 | |
| Mesh Compression | Off | 特效网格面数少，不压缩，避免 UV 精度损失 |
| Read/Write | 不勾 | 除非脚本要在运行时读顶点 |
| Normals | Import | 用 Blender 里做好的法线 |

Rig 页签：没有骨骼的特效体选 None；有骨骼动画的选 Generic。

Animation 页签：静态网格取消 Import Animation；有动画的检查片段名和起止帧，循环特效勾 Loop Time。

Materials 页签：Material Creation Mode 选 None。特效材质一律在 Unity 里用 Shader Graph 新建，不要用 FBX 带进来的材质。

贴图导入（选中贴图，Inspector 里）：

| 贴图类型 | 设置 |
|---|---|
| 颜色贴图、序列帧图集 | sRGB 勾选；Alpha Is Transparency 勾选；Wrap Mode 按需要（滚动用 Repeat，图集用 Clamp） |
| 噪声、遮罩、溶解图等数据贴图 | sRGB 不勾 |
| 法线图 | Texture Type 选 Normal map |
| 手机端压缩 | Android 和 iOS 的 Format 选 ASTC，特效贴图用 6×6 或更高质量的 4×4 |
| 序列帧图集 | 不在贴图上切片，直接在 Particle System 的 Texture Sheet Animation 模块里填行列数 |

### 6.5 第一次导出必须做的校验

在 Blender 里做一个测试件：一个 1 米边长的立方体，在它 +Y 方向的面上加一个明显的箭头凸起，顶面再加一个小凸起。按 6.3 导出，按 6.4 导入 Unity，拖进场景后检查：

1. Transform 的 Rotation 是 0,0,0，Scale 是 1,1,1。
2. 在它旁边放一个 Unity 自带的 Cube（边长 1 个单位），两者一样大。
3. 顶面的凸起朝 Unity 的 +Y（上），箭头朝向符合预期。

三条都对，这套设置就固定下来，以后所有特效网格照此导出。有一条不对，把现象回传，不要自己反复试。

---

## 7 安全与注意事项

1. MCP 能执行任意代码。Blender 这边的 execute_blender_code 能跑任何 Python；Unity 这边 MCP for Unity 的 execute_code 能在编辑器里跑任何 C#，create_script 能写任意脚本。这等于把你的用户权限交给 AI。mcp-for-blender 的 README 明确警告它的 socket 没有鉴权、没有加密[实查]。
2. 只在本机回环地址监听。Unity MCP 用 localhost:8080，UnitySkills 用 localhost:8090 起，Blender 用 localhost:9876。不要把这些端口映射到局域网或公网，不要在路由器上做端口转发，不要在咖啡馆之类的公共网络里开着服务。Windows 防火墙弹窗问是否允许公用网络访问时选否。
3. 用不到的时候把服务关掉。Blender 的 N 面板里停服务，Unity 的两个面板里停服务，或者直接关软件。
4. 先提交 git 再让 AI 动工程。每次让 AI 做一批改动之前，先把当前状态提交：

```bash
cd /d/GameDev/the-shuttle-badminton-glory
git status
git add unity/TheShuttle
git commit -m "checkpoint before AI edits"
```

AI 改坏了可以用 `git restore` 或 `git reset` 回去。Blender 文件同理，让 AI 动之前先另存一份。

5. Unity 编辑器必须开着，而且不能处于编译错误状态。脚本有编译错误时，编辑器里的 MCP 和 REST 服务本身也可能不工作。脚本重新编译（Domain Reload）期间服务会短暂不可达，UnitySkills 这时返回 503 或拒绝连接，等几秒重试即可，不是故障[实查]。
6. 不要在 Play 模式下让 AI 改场景。Play 模式里的改动退出后会丢失。
7. UnitySkills 的写操作带实例校验：请求里要带 `expectProject=TheShuttle`，不匹配会返回 409 INSTANCE_MISMATCH[实查]。同时开多个 Unity 工程时这能防止改错工程。尽量只开一个。
8. 删除和高风险操作先预演。UnitySkills 支持 `mode=dryRun`；让 AI 做删除、批量替换之前要求它先 dryRun 给你看计划。
9. Blender 端保持 `BLENDER_MCP_SAFE_MODE=1`。它不是沙箱，只是脚本预检，但能挡住最明显的读写文件和联网。
10. 第三方数据外发。Blender MCP 里的 AI 生成模型和资产搜索功能会把提示词发给第三方服务；IvanMurzak 的方案默认走云端中继。本项目都不启用。
11. 端口冲突排查。先看谁占了端口：

```powershell
netstat -ano | findstr ":8080 :8090 :9876"
```

最后一列是进程号，再查是哪个程序：

```powershell
tasklist /FI "PID eq 12345"
```

已知的冲突点：

| 端口 | 谁在用 | 冲突风险 |
|---|---|---|
| 8080 | MCP for Unity 的 HTTP 服务 | 8080 是很多开发服务器的默认端口，本机有 Docker，容器映射过 8080 的话会撞。可在 MCP for Unity 面板里改端口，DSH 配置里的 url 同步改 |
| 8090 到 8100 | UnitySkills REST | CoderGamester 的 mcp-unity 默认 WebSocket 端口也是 8090，两者不要同时装 |
| 9876 | 两个 Blender MCP 都用 | 只启用一个插件 |
| 6401 附近 | MCP for Unity 的 stdio 桥接 | 只在 stdio 模式下用 |
| 7800 附近 | Unity 官方 Pipeline 包 | 只在装了官方 CLI 方案时用 |

12. 修改 `cordis.patch.yml` 前一定备份。YAML 缩进错一格 DSH 可能起不来，这时把备份文件改回原名即可恢复。

---

## 8 方案对比表与参考链接

### 8.1 Unity 接入方案对比

数据为 2026-11-27 从 GitHub API 和各仓库 README、文档站读取[实查]。

| 维度 | CoplayDev/unity-mcp | CoderGamester/mcp-unity | IvanMurzak/Unity-MCP | Unity 官方（CLI 加 Pipeline 包） | Besty0728/Unity-Skills（本机技能的后端） |
|---|---|---|---|---|---|
| 类型 | MCP 服务器 | MCP 服务器 | MCP 服务器，也能生成技能 | 命令行工具，自带 MCP 模式 | REST 服务加代理技能，不是 MCP |
| Star | 16228 | 2022 | 4705 | 不适用（非开源仓库形式分发） | 1976 |
| 最近发布 | v10.3.0，2026-10-04 | 1.5.0，2026-09-03 | 1.14.3，2026-11-24 | CLI 1.0，2026-11-17 | v3.0.3，2026-11-21 |
| 最近代码推送 | 2026-11-17 | 2026-10-11 | 2026-11-24 | 不适用 | 2026-11-26 |
| 许可证 | MIT | MIT | Apache-2.0 | 官方技能库为 Unity Companion License；CLI 本体许可[未查到] | MIT |
| 支持的 Unity 版本 | 2021.3 LTS 到 6.x | Unity 6 及以上 | 2022.3 及以上 | 驱动编辑器需 Unity 6.0 LTS 及以上 | 2022.3 及以上，完整支持 Unity 6 |
| 团结引擎 | 有用户使用反馈，无官方声明 | [未查到] | [未查到] | [未查到] | 有用户使用反馈，无官方声明 |
| 安装方式 | UPM git URL，或 OpenUPM，或 Asset Store | UPM git URL | unitypackage 安装器，或 OpenUPM | Unity Hub 自带 CLI，或 winget；工程里执行 `unity pipeline install` | UPM git URL |
| 服务器端依赖 | Python 3.10 以上加 uv | Node.js 18 以上 | 自带可执行文件，CLI 另需 Node 22.14 以上 | 无额外依赖 | 无（服务在编辑器内）；客户端可选 Python |
| 传输与端口 | HTTP，localhost:8080/mcp（默认）；或 stdio | stdio 进 Node，Node 与 Unity 之间 WebSocket，默认 8090 | 本地 stdio 或 HTTP，端口在面板里看；默认走云端中继 | 编辑器在 127.0.0.1 开 HTTP 接口，带令牌校验 | REST，localhost:8090 到 8100 |
| 自定义客户端配置 | 支持，文档给了手动 JSON | 支持，面板可复制配置 | 支持 | `unity mcp configure` 只列出了 claude、cursor、vscode、windsurf 等，DSH 不在其中 | 面板支持自定义技能安装路径 |
| 场景与 GameObject | 有 | 有 | 有（查询语言 RQL） | 有 | 有 |
| 脚本读写 | 有，带 Roslyn 校验 | 仅触发重编译 | 有，可直接执行 C# | 有（eval） | 有 |
| 资源、材质、Prefab | 有 | 材质和 Prefab 有 | 有 | 有 | 有 |
| 粒子与 VFX | 有：粒子、VFX Graph、Line、Trail | 无专用工具 | 无专用工具，靠执行 C# | [未查到] | 内置粒子 31 个技能，不含 VFX Graph |
| 动画 | 有（manage_animation） | 无专用工具 | 有扩展包 | [未查到] | 有（animator、timeline 模块） |
| 运行与读 Console | 有 | 有 | 有 | 有 | 有 |
| 截图 | 有，含多视角 | 无 | 有 | [未查到] | 有 |
| 跑测试 | 有 | 有 | 有 | 有 | 有 |
| 特有优点 | 覆盖最全，文档站完整，有中文 README | 轻量 | 省 token，能在打出的游戏包里运行 | 官方维护，有鉴权令牌 | 事务批处理、dryRun、审计、权限模式 |
| 主要顾虑 | 工具多，占上下文；要拉 Python 包 | 不支持 Unity 6 以下；8090 端口与 UnitySkills 冲突 | 默认云端中继要登录，数据经第三方 | 很新；大陆和团结引擎可用性不明；MCP 启动参数没查到 | 本机技能版本落后上游一个大版本 |

关于 Unity 官方方案的现状[实查]：2026-05-11 Unity 随 AI Assistant 包（com.unity.ai.assistant）推出过编辑器内的官方 MCP 服务器，需要 Unity AI 订阅或试用。这个编辑器内的服务器现已被弃用，由 Unity CLI 的 `unity mcp` 取代。Unity CLI 1.0 和 Pipeline 包（com.unity.pipeline）于 2026-11-17 正式发布，免费，不需要 Unity AI 订阅。官方同时提示：代理能跑命令行时，直接用 `unity command` 和 `unity eval` 比走 MCP 更快更省。第三方的 GitHub MCP 包不受这次弃用影响。

为什么主方案不选官方：它发布才十天；要求 Unity 6.0 以上，走团结引擎就用不了；`unity mcp` 作为 stdio 服务器的启动参数在官方文档里没查到原文；在大陆的可用性不明。建议等国际版 Unity 6.3 装好后作为第三通道试装，命令如下（在工程目录里的 PowerShell 执行）：

```powershell
winget install Unity.CLI
unity --version
unity auth login
unity pipeline install
unity pipeline editors
unity mcp configure --list
```

### 8.2 各方案在 DSH 里的配置示例

CoplayDev/unity-mcp：见 4.4，HTTP 和 stdio 两种都给了。

CoderGamester/mcp-unity（不推荐与 UnitySkills 同装）。路径里的哈希目录名每次装包会变，要到工程的 `Library\PackageCache` 里看实际名字：

```yaml
    - id: mcp-unity
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: unity
        transport: stdio
        command: 'D:\nodejs\node.exe'
        args:
          - 'D:\GameDev\the-shuttle-badminton-glory\unity\TheShuttle\Library\PackageCache\com.gamelovers.mcp-unity@实际哈希\Server~\build\index.js'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

对应的 JSON：

```json
{
  "mcpServers": {
    "mcp-unity": {
      "command": "node",
      "args": ["ABSOLUTE/PATH/TO/mcp-unity/Server~/build/index.js"]
    }
  }
}
```

IvanMurzak/Unity-MCP 的本地模式（面板里连接方式选 Custom，端口从面板读）：

```yaml
    - id: mcp-unity
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: unity
        transport: stdio
        command: 'D:\GameDev\the-shuttle-badminton-glory\unity\TheShuttle\Library\mcp-server\win-x64\gamedev-mcp-server.exe'
        args:
          - 'port=面板里显示的端口'
          - 'client-transport=stdio'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

对应的 JSON：

```json
{
  "mcpServers": {
    "ai-game-developer": {
      "command": "<project>/Library/mcp-server/win-x64/gamedev-mcp-server.exe",
      "args": ["port=<port>", "client-transport=stdio"]
    }
  }
}
```

Unity 官方 CLI：stdio 启动参数[未查到]。下面这段是按命令名推测的写法，没有官方原文支持，不要直接用；装好 CLI 后执行 `unity mcp --help` 看实际参数，再把输出回传：

```yaml
    - id: mcp-unity-official
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: unity-official
        transport: stdio
        command: 'unity 可执行文件的完整路径'
        args:
          - 'mcp'
        toolCallTimeoutMs: 300000
        failOnStartupError: false
```

Besty0728/Unity-Skills：不需要 MCP 配置。DSH 通过已安装的 unity-skills 技能和它的 Python 客户端访问 `http://localhost:8090`。

### 8.3 Blender MCP 方案对比

| 维度 | ahujasid/mcp-for-blender（原 blender-mcp） | Blender 官方实验室 blender_mcp |
|---|---|---|
| 维护方 | 个人开发者，社区项目 | Blender 基金会的 Blender Lab |
| Star | 35954（GitHub） | 40（Blender 自家 Gitea，不能与 GitHub 直接比） |
| 最近发布 | PyPI mcp-for-blender 2.3.3，2026-11-26；GitHub 上不打发布标签 | v1.0.3，2026-09-11 |
| 最近更新 | 2026-11-26 | 2026-09-29 |
| 许可证 | MIT | GPL-3.0-or-later |
| 支持的 Blender 版本 | 3.0 及以上；个别工具要求 5.3 以上 | 5.1.0 及以上 |
| 服务器端依赖 | Python 3.10 以上加 uv，`uvx mcp-for-blender` | Python 3.10 以上加 uv，需克隆仓库 |
| 传输与端口 | DSH 到服务器 stdio；服务器到 Blender 用 TCP socket，localhost:9876 | 同左，默认也是 localhost:9876 |
| 执行任意 Python | 能（execute_blender_code） | 能 |
| 视口截图 | 能（look：视口、相机、多角度、动画帧条） | 能（1.0.3 修复了截图工具） |
| 场景信息 | 能（get_scene_info） | 能 |
| 额外功能 | AI 生成三维模型、高斯泼溅场景、Poly Haven 等资产搜索导入 | 内置 Python API 文档和用户手册作为资源 |
| 安全措施 | 可选安全模式预检；遥测可关；socket 无鉴权无加密 | 仓库里有一个弱沙箱模块；需打开 Blender 联机访问 |
| 与本机 blender-skills 的配合 | 技能就是按它写的 | 工具名不同，技能文档对不上 |
| 结论 | 主方案 | 备选 |

两者都能执行任意代码，安全风险同级，都只应在本机使用。

相关的技能仓库 arjun988/blender-skills：5085 star，最近推送 2026-11-06，MIT。它本身不是 MCP，是给 AI 看的 Blender 操作知识库，依赖上面的 MCP 才能真正驱动 Blender。

### 8.4 其它建议

| 项 | 建议 |
|---|---|
| Git LFS | 本机已装 git-lfs 3.8.0，但项目没有 `.gitattributes`，也就是没启用。GitHub 普通 git 单文件上限 100 MB；LFS 在免费账号下单文件上限 2 GB[实查]。项目此前把 7 个超 100 MB 的参考视频写进 .gitignore 而没走 LFS，可能的原因是当时没启用 LFS 或顾虑免费额度，不深究。Unity 工程开始后，贴图、FBX、音频这些二进制文件建议走 LFS，启用前先和 Lead 确认 |
| Unity 的 .gitignore | 用 GitHub 官方模板，放在 Unity 工程根目录 `unity\TheShuttle\.gitignore`。它会忽略 Library、Temp、Obj、Build、Builds、Logs、UserSettings 等目录。.meta 文件必须提交 |
| .NET SDK | 本机有 10.0.302。Unity 自带运行时，不依赖它。它的用处是在 Unity 之外用 `dotnet test` 跑确定性逻辑层的单元测试，逻辑库目标框架设 netstandard2.1 以便 Unity 引用[经验] |
| 代码编辑器 | 见 2.5 |
| Android 真机调试 | 手机上：设置 > 关于手机，连点版本号 7 次打开开发者选项，再打开 USB 调试。电脑上 adb 已装。Unity 里 File > Build Profiles 切到 Android，Run Device 选你的手机，勾 Development Build，点 Build And Run。看日志可在 Package Manager 里装 Android Logcat 包。Unity 6.3 支持的最低安卓版本是 7.1（API 25）[实查] |
| iOS | 需要 Mac 和 Xcode 16 以上，最低 iOS 15[实查]。原型期先不管 |

Unity 官方 .gitignore 模板地址：

```
https://raw.githubusercontent.com/github/gitignore/main/Unity.gitignore
```

### 8.5 参考链接

Unity 版本与政策：

| 结论 | 来源 | 日期或版本 |
|---|---|---|
| Unity 各分支发布日期、支持期限、最新补丁号 | https://endoflife.date/api/unity.json | 2026-11-27 读取；6000.3.29f1 为 2026-11-19 |
| Unity 6.3 LTS 发布公告 | https://discussions.unity.com/t/unity-6-3-lts-is-now-available/1697328 | 2025-12-04 |
| 新项目选 6.3 LTS 的第三方建议 | https://devforgeunity.com/which-unity-version-should-you-use/ | 2026-10-27 更新 |
| Unity 6.3 系统需求（Android SDK 35、NDK r27c、OpenJDK 17、iOS 15、Xcode 16） | https://docs.unity.com/en-us/engine/6000.3/manual/get-started/install-and-upgrade/getting-started-installing-unity/system-requirements | Unity 6.3 手册 |
| Unity Personal 条件（20 万美元） | https://unity.com/cn/products/unity-personal | 2026-11-27 读取 |
| Unity Hub 下载入口 | https://unity.com/download | 本机直连超时 |
| Unity 6 在中国大陆及港澳下架、由团结引擎承接 | http://www.gamelook.com.cn/2025/04/568127/ | 2025-04-10，转述 Unity 中国 2025-04-07 公告 |
| 上述公告原文（页面正文未能抽取，仅取到标题） | https://developer.unity.cn/projects/67ee5a4bedbc2a001e9ec5e3 | 2025-04 |
| 团结引擎版本列表（1.11.2 等） | https://unity.cn/tuanjie/releases | 1.11.2 为 2026-11-25 |
| 团结引擎许可与激活 | https://docs.unity.cn/cn/tuanjiemanual/Manual/LicensesAndActivation.html | 手册 1.11，2026-11-24 |
| Cinemachine 在 6.6 成为核心包 | Unity Cinemachine 3.1 文档页内提示 | 2026-11-27 读取 |

Unity 接入方案：

| 结论 | 来源 | 日期或版本 |
|---|---|---|
| CoplayDev/unity-mcp 仓库数据 | https://github.com/CoplayDev/unity-mcp | 16228 star；v10.3.0，2026-10-04 |
| 安装、传输方式、工具目录 | https://coplaydev.github.io/unity-mcp/ | 工具页 2026-10-06 更新 |
| 服务器 Python 包 | https://pypi.org/project/mcpforunityserver/ | 10.3.0 |
| CoderGamester/mcp-unity | https://github.com/CoderGamester/mcp-unity | 2022 star；1.5.0，2026-09-03 |
| IvanMurzak/Unity-MCP | https://github.com/IvanMurzak/Unity-MCP | 4705 star；1.14.3，2026-11-24 |
| Besty0728/Unity-Skills | https://github.com/Besty0728/Unity-Skills | 1976 star；v3.0.3，2026-11-21 |
| Unity-Skills 中文安装指南 | https://github.com/Besty0728/Unity-Skills/blob/main/docs/SETUP_GUIDE_CN.md | 2026-11-27 读取 |
| Unity 官方 MCP 首次推出 | https://unity.com/blog/unity-ai-mcp-how-to-get-started | 2026-05-11 |
| 编辑器内 MCP 弃用，改用 Unity CLI | https://docs.unity.com/en-us/unity-cli/replace-mcp-server-unity-cli | 页面标注约 20 天前更新 |
| Unity CLI 1.0 发布 | https://unity.com/the-unity-cli-1.0-is-here | 2026-11-17 |
| Unity CLI 用法与安装 | https://docs.unity.com/en-us/unity-cli/use-unity-cli | 页面标注约 15 天前更新 |
| Pipeline 包安装步骤 | https://docs.unity.com/en-us/unity-cli/unity-pipeline/unity-pipeline-package | 页面标注约 15 天前更新 |
| Unity CLI 安全模型 | https://docs.unity.com/en-us/unity-cli/unity-cli-security | 页面标注约 10 天前更新 |
| Unity 官方技能库 | https://github.com/Unity-Technologies/skills | star 数[未查到] |

Blender：

| 结论 | 来源 | 日期或版本 |
|---|---|---|
| Blender 各版本发布日期与 LTS 期限 | https://endoflife.date/api/blender.json | 2026-11-27 读取；5.2.5 为 2026-11-23 |
| Blender 发布说明总目录 | https://developer.blender.org/docs/release_notes/ | |
| 5.x 兼容性变化梳理 | https://geturna.com/en/guides/blender-5 | 2026-10-25 |
| 国内镜像与安装包体积 | https://mirrors.aliyun.com/blender/release/Blender5.2/ | blender-5.2.5-windows-x64.msi，349.0 MB，2026-11-24 |
| ahujasid/mcp-for-blender | https://github.com/ahujasid/mcp-for-blender | 35954 star；2026-11-26 推送 |
| PyPI 包 | https://pypi.org/project/mcp-for-blender/ | 2.3.3，2026-11-26 |
| Blender 官方实验室 MCP | https://projects.blender.org/lab/blender_mcp | v1.0.3，2026-09-11 |
| 官方说明页（正文未能读取） | https://www.blender.org/lab/mcp-server/ | |
| arjun988/blender-skills | https://github.com/arjun988/blender-skills | 5085 star；2026-11-06 推送 |
| Blender 5.3 手册 FBX 页（只含导入说明） | https://docs.blender.org/manual/en/latest/files/import_export/fbx.html | Blender 5.3 手册 |

其它：

| 结论 | 来源 |
|---|---|
| Unity 的 .gitignore 模板 | https://github.com/github/gitignore/blob/main/Unity.gitignore |
| GitHub 文件大小与 LFS 限制 | https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage |
| DSH 的 MCP 配置格式 | 本机 `C:\Users\OVO\.dsh\profiles\desktop\cordis.patch.yml` 第 29 到 52 行，以及 DSH 安装包内置文档 |

### 8.6 没查到或没验证的事项汇总

1. 国际版 Unity 6 在你的网络和账号下到底能不能下载和激活。只有你实际装一次才知道。
2. Unity 国际账号与 Unity 中国账号、两边个人版许可是否互通。
3. Unity Hub 和各模块的官方下载体积。第 0 节是经验估计。
4. Unity 官方 CLI 的 `unity mcp` 作为 stdio 服务器的确切启动参数，以及它是否支持团结引擎。
5. Blender 5.x 的 FBX 导出选项官方手册原文。6.3 的设置靠 6.5 的测试件校验。
6. DSH 清洗环境变量后，uvx 子进程能否正常工作。
7. 团结引擎 1.11 的包管理器里 Cinemachine 3 等包的可用版本。
8. Unity 的 Alembic 包在手机平台的支持情况。
9. 本文所有 DSH 配置片段都没有在本机实际加载过。
10. Blender 官网下载页的确切地址（命令行访问返回 403）。镜像地址是实测可用的。

---

## 9 装好后请回传给 AI 的信息

装完一项回传一项，不用等全部装完。报错请贴原文，不要转述。

Unity：

1. 走的是哪条线：国际版 Unity 6 还是团结引擎。如果国际版没装成，卡在哪一步（Hub 下载不了、登录不了、列表里没有 6000.3）。
2. 编辑器完整版本号。在 Unity 里 Help > About Unity 能看到，形如 6000.3.29f1。
3. 实际勾选安装了哪些模块。
4. 工程的完整路径，以及建工程时选的模板名。
5. Package Manager 里 2.4 表格那几个包是否都装上了，各自的版本号。
6. Hub 里许可类型显示的是什么。

Blender：

7. 完整版本号（帮助 > 关于 Blender），安装路径，装的是安装版还是便携版。
8. 插件列表里“Interface: MCP for Blender”是否启用，N 面板里显示的端口号和运行状态。

MCP 接入：

9. `cordis.patch.yml` 里你实际加进去的那几段内容。
10. Unity 的 MCP for Unity 面板截图（能看到传输方式、端口、连接状态）。
11. UnitySkills 面板截图，以及下面命令的输出：

```bash
curl http://localhost:8090/health
```

12. 重启 DSH 后，AI 是否能列出 `mcp__unity__` 和 `mcp__blender__` 开头的工具。列不出来的话，DSH 启动日志或界面上的报错原文。
13. 4.5 和 5.4 的每一步验证结果：哪步成功，哪步失败，失败的报错原文和截图。
14. 端口检查命令的输出：

```powershell
netstat -ano | findstr ":8080 :8090 :9876"
```

导出校验：

15. 6.5 的测试件导入 Unity 后，Transform 的 Rotation 和 Scale 数值，和 Unity 自带 Cube 比大小的结果，最好附一张截图。

需要你做决定的事：

16. 界面类三项特效（脚下体力环、蓄力弧形环、觉醒按键储水）是否同意直接在 Unity 里做，不经过 Blender。
17. 是否现在为 Unity 工程启用 Git LFS。
18. Blender 源文件目录是否用 `D:\GameDev\the-shuttle-badminton-glory\art_src\`。
19. 是否把 DSH 里的 unity-skills 技能从 2.9.1 更新到上游 3.x（更新的话 Unity 里的包也要一起换）。
