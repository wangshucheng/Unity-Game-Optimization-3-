---
layout: default
title: "Chapter 10 奇淫技巧"
nav_order: 11
---

# Chapter 10 奇淫技巧

软件工程师往往比较乐观，容易低估完整实现新功能或修改现有代码库所需的工作量。常见的错误是只考虑写代码本身，而忽略了重构其他子系统、测试和文档所需的时间。性能优化工作同样有一个恒定成本：时间。因此，提升工作流效率、熟悉工具细节，能为我们节省宝贵时间。

本章把 Unity 开发中一些零散但实用的技巧集中在一起，帮助大家提高日常开发效率。主要涵盖：

- 编辑器快捷键
- 编辑器 UI 技巧
- 脚本编写技巧
- 自定义 Editor 脚本与菜单技巧
- 外部资源与社区
- 其他技巧

## 编辑器快捷键

以下快捷键以 Windows 为主，macOS 对应键放在括号中。

### GameObject 操作

- **Ctrl + D（cmd + D）**：复制选中的 GameObject。
- **Ctrl + Shift + N（cmd + shift + N）**：创建新的空 GameObject。
- **Ctrl + Shift + A（cmd + shift + A）**：打开 Add Component 菜单，可直接输入组件名称。

### Scene 窗口

- **Shift + F**：锁定相机到选中对象，适合追踪高速运动物体或查找掉出场景的对象。
- **Alt + 左键拖拽**：让 Scene 相机围绕选中对象轨道旋转。
- **Alt + 右键拖拽**：缩放 Scene 相机。
- **Ctrl + 左键拖拽**：移动对象时按网格吸附；旋转时按住 Ctrl 也可吸附。
- **V 键移动**：移动对象时按住 V 键，会自动把选中对象的顶点吸附到最近对象的最近顶点，方便对齐地板、墙壁、平台等。
- 右键按住场景时，可用 **W/A/S/D** 像第一人称视角一样飞行，**Q/E** 上升/下降。

### 数组

- **Ctrl + D（cmd + D）**：复制 Inspector 中数组的某个元素。
- 对于引用类型数组，右键元素选择 **Delete Array Element** 删除。
- 对于基础类型数组（int、float 等），选中元素后直接按 Delete 删除。

### 界面

- **Alt + 点击 Hierarchy 箭头**：展开/折叠整个子树，而不是只展开一级。对 Project 窗口文件夹、Prefab、Inspector 列表同样有效。
- **Ctrl + Alt + <0-9>（cmd + alt + <0-9>）**：保存当前选择。
- **Ctrl + Shift + <0-9>（cmd + shift + <0-9>）**：恢复保存的选择。也可以在 **Edit | Selection** 中找到对应命令。
- **Shift + 空格**：让鼠标下的窗口充满整个编辑器，再按一次恢复。
- **Ctrl + Shift + P（cmd + shift + P）**：切换 Playmode 暂停。也可以自己写个快捷键脚本：

```csharp
void Update() {
    if (Input.GetKeyDown(KeyCode.P)) {
        Debug.Break();
    }
}
```

### 在编辑器中查看文档

- 在 Visual Studio Community 中选中 Unity 关键字或类，按 **Ctrl + '（cmd + '）**，会自动在浏览器中搜索 Unity 文档。
- 在 Visual Studio 中也可以按 **Ctrl + Alt + M**，然后 **Ctrl + H**。

## 编辑器 UI 技巧

### Script Execution Order

通过 **Edit | Project Settings | Script Execution Order** 可以调整脚本 `Update()` / `FixedUpdate()` 的调用顺序。除非是音频等时间敏感系统，否则如果需要大量依赖此功能，可能是组件耦合过紧的警告信号。

### 编辑器文件

- **版本控制**：确保把 Unity 生成的 `.meta` 文件纳入版本控制。路径：**Edit | Project Settings | Editor | Version Control | Mode | Visible Meta Files**。
- **强制文本序列化**：把资源序列化格式从二进制改为 YAML 文本，方便手动编辑和 diff。路径：**Edit | Project Settings | Editor | Asset Serialization | Mode | Force Text**。
- **Editor Log**：打开 Console 窗口，点击右上角汉堡菜单选择 **Open Editor Log**，可以查看构建失败信息或构建后资源压缩大小 breakdown。
- **Add Tab**：右键窗口标题选择 **Add Tab**，可以开多个 Project 或 Inspector 窗口。
- **锁定 Inspector**：Inspector 窗口右上角的锁图标可以锁定当前选择，方便对比两个对象或在 Playmode 中观察依赖对象。

### Inspector 窗口

- **数值字段支持计算**：在 int/float 字段中输入 `4*128`，会自动计算为 512。
- **数组元素右键菜单**：可快速复制或删除数组元素。
- **Reset 组件**：点击组件右上角齿轮或右键组件名，选择 **Reset**，所有值恢复默认值。对 Transform 特别有用。
- **Revert Value to Prefab**：右键单个值选择 **Revert Value to Prefab**，只恢复该值到 Prefab 原始状态。
- **Debug 模式**：点击 Inspector 右上角汉堡菜单选择 **Debug**，会禁用自定义 Inspector，显示所有原始数据，包括私有字段（只读）。还能看到内部 ObjectID，有助于排查序列化问题。
- **数组元素命名**：如果序列化对象/结构体的第一个字段是字符串，Inspector 会用该字符串作为数组元素名。
- ** detached Preview 窗口**：选中网格时，右键 Inspector 底部 Preview 面板的顶部栏，可把它拆成独立大窗口，方便查看细节。关闭后自动归位。

### Project 窗口

- **类型过滤**：搜索栏右侧小图标可按类型过滤，实际就是在搜索框填入 `t:<type>`。例如：
  - `t:prefab`：查找所有 Prefab
  - `t:texture`：查找所有纹理
  - `t:scene`：查找所有场景
  - `t:texture normalmap`：查找名称包含 normalmap 的纹理
- **标签过滤**：如果使用 Asset Bundle 标签，可用 `l:<label>` 搜索。
- **脚本默认值**：如果 MonoBehaviour 有 `[SerializeField]` 或 public 引用类型字段，可以在 Project 窗口选中脚本文件，在 Inspector 中给这些字段设置默认值。
- **One Column Layout**：点击 Project 窗口右上角汉堡菜单选择单列布局，可节省空间。
- **Select Dependencies**：右键资源选择 **Select Dependencies**，可查看该资源依赖的所有对象，便于清理。

### Hierarchy 窗口

- **组件过滤**：在 Hierarchy 搜索框输入 `t:<component>`，例如 `t:light` 显示所有带 Light 组件的对象，`t:renderer` 显示所有 Renderer 派生组件。搜索不区分大小写，但必须输入完整组件名。

### Scene 和 Game 窗口

- **对齐视图**：选中对象后，**GameObject | Align with View（Ctrl + Shift + F / cmd + shift + F）** 可把对象放到 Scene 相机位置和朝向上。
- **Align View to Selected**：把 Scene 相机对齐到选中对象，方便检查方向。
- **Scene 窗口组件过滤**：与 Hierarchy 一样可用 `t:<component>` 过滤 Scene 中渲染的对象。
- **Layers 过滤**：编辑器右上角 **Layers** 下拉可显示/隐藏或锁定特定层，防止误选背景对象。
- **Gizmos**：Game 窗口右上角 Gizmos 按钮可决定在 Game 视图中显示哪些 gizmo。
- **对象图标**：给无 Renderer 的对象设置图标，方便在 Scene 窗口中定位。

### Playmode

- **Playmode tint**：通过 **Edit | Preferences | Colors | Playmode tint** 修改 Playmode 时的窗口色调，提醒自己当前处于播放模式。
- **保存 Playmode 修改**：Playmode 中的修改不会自动保存。可以：
  - 选中对象按 **Ctrl + C（cmd + C）**，退出 Playmode 后 **Ctrl + V（cmd + V）** 粘贴。
  - 使用组件右键菜单的 **Copy Component / Paste Component**。
  - 直接把运行时调整好的对象拖到 Project 窗口生成 Prefab（Playmode 中也可覆盖原 Prefab，但需谨慎）。
- **Frame Skip**：暂停模式下按 Frame Skip 按钮可逐帧推进，观察物理或 gameplay 行为。注意每按一次会调用一次 `FixedUpdate` 和一次 `Update`，可能与实际运行时比例不同。
- **启动即暂停**：如果 Playmode 开始前 Pause 按钮已启用，游戏会在第一帧后暂停，便于观察初始化异常。

## 脚本编写技巧

### 通用

- **修改脚本模板**：新脚本、Shader、Compute Shader 的模板位于：
  - Windows：`<Unity install>\Editor\Data\Resources\ScriptTemplates\`
  - macOS：`/Applications/Unity/Editor/Data/Resources/ScriptTemplates/`

  可以移除空的 `Update()` 存根，避免不必要的运行时开销。

- **Assert 调试**：`UnityEngine.Assertions.Assert` 提供断言式调试，适合习惯断言而非异常的开发者。

### 特性（Attributes）

#### 字段特性

- **[Range(min, max)]**：把 int/float 字段在 Inspector 中变成滑块。
- **[FormerlySerializedAs("oldName")]**：重命名字段时，保留旧序列化数据。注意：在所有相关 Prefab 重新保存之前不要移除该特性。

#### 类特性

- **[SelectionBase]**：让 Scene 窗口第一次点击时选中附加该组件的 GameObject，而不是子对象的 MeshRenderer。
- **[RequireComponent(typeof(T))]**：强制同时附加依赖组件。
- **[ExecuteInEditMode]**：让对象在 Edit Mode 下也调用 `Update()`、`OnGUI()`、`OnRenderObject()`。注意：
  - `Update()` 只在场景发生变化时调用。
  - `OnGUI()` 只在 Game 窗口事件时调用，不在 Scene 窗口调用。
  - `OnRenderObject()` 在 Scene 和 Game 窗口重绘时调用。

### 日志

- Debug 字符串支持富文本标签：`<size>`、`<b>`、`<i>`、`<color>` 等。

```csharp
Debug.Log("<color=red>[ERROR]</color>This is a <i>very</i> <size=14><b>specific</b></size> kind of log message");
```

- `MonoBehaviour.print()` 等同于 `Debug.Log()`。
- 可封装自定义 logger，在每条日志末尾自动追加 `\n\n`，减少 Console 中 `UnityEngine.Debug:Log(Object)` 的冗余显示。

### 有用链接

- Unity 官方脚本教程：https://unity3d.com/learn/tutorials/topics/scripting
- Unity Answers 上的脚本与编译错误参考列表：https://learn.unity.com
- 嵌套协程参考文章：http://www.zingweb.com/blog/2013/02/05/unity-coroutine-wrapper

## 自定义 Editor 脚本与菜单技巧

### 菜单快捷键

`[MenuItem]` 不仅可以创建菜单，还可以绑定快捷键：

```csharp
[MenuItem("My Menu/Menu Item _k")] // 按 K 触发
```

修饰键：

- `%` = Ctrl（cmd）
- `#` = Shift
- `&` = Alt

`[MenuItem]` 还支持两个额外参数：是否需要验证方法，以及菜单项优先级。

### Ping 对象

调用 `EditorGUIUtility.PingObject()` 可以在 Hierarchy 中高亮某个对象，效果类似 Inspector 中点击 GameObject 引用。

### PropertyDrawer

相比把所有绘制逻辑写在一个 Editor 类中，使用 `PropertyDrawer` 可以把 Inspector 绘制委托给单独的类，实现按字段的精细控制和代码复用。它基于 `SerializedProperty`，自动支持撤销、重做和多对象编辑。数据验证推荐在属性的 setter 中使用 `OnValidate()`。

### ContextMenu

使用 `[ContextMenu]` 和 `[ContextMenuItem]` 可以为组件或单个字段添加右键菜单项，无需编写完整的自定义 Inspector。

### 其他

- 可通过 `AssetImporter.userData` 在 Unity 元数据文件中存储自定义数据。
- 反射（Reflection）在 Unity Editor 中有很多妙用，Ryan Hipple 在 Unite 2014 的分享中有大量示例。

## 外部资源与社区

- **Twitter #unitytips**：大量 Unity 小技巧，但信息较杂。
- **devdog.io/blog**：每周汇总 #unitytips 中的技巧。
- **Google 搜索技巧**：搜索时以 `site:unity3d.com` 开头，只搜索 Unity 官网内容。
- **崩溃恢复**：如果 Unity 崩溃，可尝试把 `<project folder>\Temp\_EditModeScene` 重命名为 `.unity` 文件并复制到 Assets 文件夹，可能恢复场景。
- **游戏编程模式**：http://gameprogrammingpatterns.com/contents.html，免费在线资源，涵盖单例、观察者、游戏循环、双缓冲等模式。
- **Unite 大会视频**：关注 Unity 员工和资深开发者的分享。
- **社区**：Unity 官方论坛、Twitter、Reddit、Stack Overflow、Unity Answers 等都是获取最新技巧的好地方。

## 其他技巧

- **用空 GameObject 组织场景**：把一组对象作为空 GameObject 的子对象，并取有意义的名称。唯一代价是 transform 参与计算，但良好的组织工作流收益远大于这点开销。
- **Animator Override Controller**：自 Unity 4.3 引入，但常被遗忘。它允许引用现有 Animator Controller 并覆盖特定动画状态，无需复制整个 Controller。
- **Asset Store**：Unity 编辑器高度可定制，Asset Store 上有大量低成本甚至免费的工具和脚本，能节省大量开发时间。只要把时间成本算进去，经常逛 Asset Store 是很划算的投资。

## 小结

本书到此结束。最重要的两点再强调一次：

1. **在做任何改动之前，务必通过 Profiling 确认真正的瓶颈**。5 分钟的 Profiler 测试可能节省一整天盲目优化的时间。
2. **每次修改后都要重新 Profile 和测试**，确保改动确实达到了预期效果，没有引入新的瓶颈。

性能优化本质上是解决问题。现代计算机硬件很复杂，微小的调整往往能带来巨大收益。祝大家做出更优秀的游戏！
