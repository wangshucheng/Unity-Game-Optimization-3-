---
layout: default
title: "Chapter 1 分析性能问题"
nav_order: 2
---

# Chapter 1 分析性能问题

性能评估对大多数软件产品来说都是一个科学过程。首先确定最大/最小可接受性能指标，如允许的内存使用、CPU 占用和并发用户数；然后在目标平台上对应用进行负载测试并收集运行时数据；最后分析数据、找到瓶颈、完成根因分析（RCA），修复问题并重复验证。

游戏开发虽然充满艺术性，但同样高度技术化。我们需要明确目标受众和硬件限制，有时还有明确的性能目标（尤其是主机和移动游戏）。我们可以对 CPU、GPU 内存、物理引擎、渲染管线等子系统进行运行时测试，收集性能数据，与可接受标准比较，识别瓶颈，进行额外测量，确定根因，最后应用相应解决方案。

但在动手修复之前，必须先证明性能问题确实存在。盲目优化 rarely worth the hassle。一旦确认问题，下一步是定位瓶颈所在，理解问题发生的原因，否则只会治标不治本，导致问题以其他形式再次出现。

本章将探讨：
- 如何使用 Unity Profiler 收集性能数据
- 如何分析 Profiler 数据以发现性能瓶颈
- 如何隔离问题并确定根因

## 使用 Unity Profiler 获取数据

Unity Profiler 内置于 Unity Editor，可以在运行时生成大量 Unity 子系统的使用情况和统计报告，包括：
- CPU 消耗（按主要子系统）
- 渲染和 GPU 基础/详细信息
- 运行时内存分配和总体消耗
- 音频源/数据使用
- 物理引擎（2D 和 3D）使用
- 网络消息和操作使用
- 视频播放使用
- UI 基础/详细性能
- 全局光照（GI）统计

使用分析工具通常有两种方法：**Instrumentation（插桩分析）** 和 **Benchmarking（基准化分析）**。Instrumentation 深入观察应用内部行为，如目标函数调用、内存分配位置等，能找到根因，但本身有性能开销。Benchmarking 则是表面级测量，在目标硬件上运行测试场景，关注性能明显变差的时刻，常用指标包括 FPS、内存占用、CPU 活动峰值等。

### 启动 Profiler

打开方式：**Window | Analysis | Profiler**。

Profiler 可以连接以下目标：
- **Editor**：直接在编辑器中运行并分析
- **Standalone 实例**：运行构建后的应用并通过网络连接
- **WebGL 实例**：需要特殊配置
- **iOS 设备**：必须在 Mac 上运行 Unity
- **Android 设备**：与 iOS 类似

### 远程连接 iOS

1. 打包时勾选 **Development Build** 和 **Autoconnect Profiler**
2. 电脑和手机连接同一 WiFi
3. 用 USB 连接 iPhone/iPad 和 Mac
4. 构建并运行
5. 在 Unity 中打开 Profiler，选择 iOS 设备

如仍有问题，参考 [TroubleShootingIPhone](https://docs.unity3d.com/Manual/TroubleShootingIPhone.html)。

### 远程连接 Android

步骤与 iOS 类似。如连接有问题，参考 [TroubleShootingAndroid](https://docs.unity3d.com/Manual/TroubleShootingAndroid.html)。

### Editor 中分析的局限性

在 Development Build 下运行时，应用会生成额外的运行时事件供 Profiler 记录，带来额外的 CPU 和内存开销。如果通过 Unity Editor 分析，开销更大（Editor 需要更新界面、渲染 Scene 窗口、处理后台任务等）。在大型项目中，启用 Profiler 可能导致内存不足、脚本不运行、物理停止更新等问题。因此：
- Editor 中的 Profiler 数据不可靠，应在真机上验证
- 先用 Benchmarking 定位问题区间，再用 Instrumentation 深入分析
- 避免在性能测试时频繁开关 Deep Profile 等重开销选项

## Profiler 窗口

Profiler 窗口主要由 **Timeline View（时间线视图）** 和 **Breakdown View（细分视图）** 组成。

### 控制栏

- **Add Profiler**：添加要分析的子系统区域
- **Playmode / Record**：是否在 Play 模式下自动记录
- **Deep Profile**：深入分析整个调用栈，开销很大，建议只在必要时使用
- **Allocation Callstack**（Unity 2019.1+）：即使不开启 Deep Profile，也能收集更多内存分配信息。点击红色内存分配块可查看来源，或在 Hierarchy 视图中选择分配调用，切换到 **Show Related Objects** 查看调用堆栈
- **Clear**：清空 Timeline View 数据
- **Load / Save**：加载或保存 Profiler 数据。每次最多保存 300 帧
- **Frame Selection**：帧计数器、前后帧切换、Current 按钮

### Timeline View

右侧是运行时数据的图形表示，左侧是一系列复选框，用于启用/禁用不同数据类型。点击图形区域可以选择某一帧，出现白色竖线标识当前选中帧。

### Breakdown View Controls

根据当前选中的区域显示不同的下拉菜单和开关选项，决定 Breakdown View 中信息的呈现方式。

### Breakdown View

显示当前选中帧的详细信息，内容取决于 Timeline View 中选择的区域和 Breakdown View Controls 的设置。

#### CPU Usage 区域

最常用的区域，覆盖 MonoBehaviour、相机、部分渲染和物理、UI、音频、Profiler 自身等。Breakdown View 有三种模式：
- **Hierarchy**：合并相似的调用和全局 Unity 函数，适合初步定位耗时函数
- **Raw Hierarchy**：把全局 Unity 函数拆分成独立条目，更难读，但有助于统计调用次数或发现某个调用异常耗时
- **Timeline**：按调用栈展开/收缩组织 CPU 使用，垂直方向代表不同线程（主线程、渲染线程、Unity Job System 等），水平方向代表时间。宽块表示耗时多，深链表示调用栈深。这是定位具体耗时方法最有用的模式

#### GPU Usage 区域

显示 GPU 上的方法调用和处理时间，包括相机、不透明/透明几何体、光照和阴影等。适合配合 Chapter 6 的渲染优化。

#### Rendering 区域

提供通用渲染统计，主要关注 CPU 上为 GPU 准备渲染的活动，如 SetPass Call（Draw Call）、Batch 总数、动态/静态合批节省的批次、纹理内存等。还提供按钮打开 Frame Debugger。

#### Memory 区域

- **Simple 模式**：显示总内存、堆内存、纹理内存、网格内存、渲染纹理内存等概览
- **Detailed 模式**：可以截取快照，查看各类资源的详细内存占用

#### Audio 区域

显示音频源数量、播放中的音频数、音频 CPU 和内存使用等。

#### Physics 3D / Physics 2D 区域

显示物理引擎的使用情况，如刚体数量、碰撞体数量、物理更新耗时等。

#### Network Messages / Network Operations 区域

显示网络消息和操作的统计。

#### Video 区域

显示视频播放的性能数据。

#### UI / UI Details 区域

显示 UI 批处理、顶点数、布局重建、渲染等统计。

#### Global Illumination 区域

显示全局光照的统计信息。

## 性能分析的最佳实践

### 验证脚本存在

使用 Profiler 的 Timeline 或 Hierarchy 模式，确认目标脚本/方法确实在运行，没有被意外禁用或条件跳过。

### 验证脚本数量

确认目标脚本实例的数量是否正确。Prefab 意外重复实例化、场景中存在多个副本、DontDestroyOnLoad 对象累加等都会导致数量异常。

### 验证事件顺序

Unity 有固定的执行顺序（Awake、OnEnable、Start、FixedUpdate、Update、LateUpdate 等），但脚本之间的调用顺序默认不确定。通过 Profiler 可以观察事件实际触发顺序，排查时序相关 bug。

### 最小化正在进行的代码更改

分析期间避免同时修改多处代码，否则无法判断哪处改动影响了性能。

### 尽量减少内部干扰

- 关闭不必要的 Editor 窗口（尤其是 Scene 窗口）
- 移除或禁用不相关的 GameObject 和脚本
- 在 Standalone 或真机上运行，而不是 Editor
- 避免在测试期间进行 GC、资源加载等后台操作

### 尽量减少外部干扰

- 关闭其他应用程序
- 确保目标设备电量充足（低电量模式可能降频）
- 避免在设备发热时测试
- 使用发布版本或 Development Build（但要知道 Development Build 本身有开销）

## 代码段的目标分析

当默认 Profiler 不够详细时，可以使用 Unity 提供的 Profiler API 进行目标分析：

```csharp
void DoSomethingCompletelyStupid() {
  Profiler.BeginSample("My Profiler Sample");
  List<int> listOfInts = new List<int>();
  for(int i = 0; i < 1000000; ++i) {
    listOfInts.Add(i);
  }
  Profiler.EndSample();
}
```

需要 `using UnityEngine.Profiling;`。

### 自定义 CPU 分析

使用 `System.Diagnostics.Stopwatch` 创建自定义计时工具：

```csharp
using System.Diagnostics;

public class CustomTimer : IDisposable {
  private string _timerName;
  private int _numTests;
  private Stopwatch _watch;

  public CustomTimer(string timerName, int numTests) {
    _timerName = timerName;
    _numTests = numTests > 0 ? numTests : 1;
    _watch = Stopwatch.StartNew();
  }

  public void Dispose() {
    _watch.Stop();
    float ms = _watch.ElapsedMilliseconds;
    UnityEngine.Debug.Log(string.Format(
      "{0} finished: {1:0.00} milliseconds total, " +
      "{2:0.000000} milliseconds per-test for {3} tests",
      _timerName, ms, ms / _numTests, _numTests));
  }
}
```

使用示例：

```csharp
const int numTests = 1000;
using (new CustomTimer("My Test", numTests)) {
  for(int i = 0; i < numTests; ++i) {
    TestFunction();
  }
} // 执行完成后 timer 的 Dispose() 会被调用
```

## 理解 Profiler

### 减少噪声

Profiler 本身会引入噪声。应：
- 在真机上测试
- 使用 Benchmarking 确定问题区间
- 关闭 Deep Profile 等重开销功能，除非必要
- 多次运行取平均

### 聚焦问题

不要试图同时优化所有东西。选择一个明确的性能问题：
- 是帧率低？
- 是帧时间不稳定？
- 是加载时间长？
- 是内存占用高？

然后使用 Profiler 的相应区域深入分析。

## 小结

性能优化的第一步是证明问题存在并找到根因。Unity Profiler 是强大的工具，但使用它时要意识到自身的开销。结合 Benchmarking 和 Instrumentation，在真机上验证，逐步缩小问题范围，才能高效地解决性能问题。
