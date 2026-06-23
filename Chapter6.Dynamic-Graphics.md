---
layout: default
title: "Chapter 6 渲染优化"
nav_order: 7
---

# Chapter 6 渲染优化

现代图形设备的渲染管线无疑非常复杂。即使只是把单个三角形绘制到屏幕上，也需要调用大量图形 API，包括创建与操作系统对接的相机视图缓冲、分配顶点数据缓冲、建立从 RAM 到 VRAM 的数据通道、配置数据格式、确定相机可见对象、发起绘制调用、等待渲染管线完成，最后把图像呈现到屏幕。这种看似“过度设计”的流程其实有充分的理由：渲染往往是在反复执行相同的任务，前期的大量设置能让后续渲染变得非常快。

CPU 擅长处理各种通用计算场景，但并行能力有限；GPU 则专为大规模并行而生，但复杂度一旦过高就会破坏并行性。GPU 的并行特性需要极快地搬运海量数据，因此渲染管线中的数据通道必须针对数据类型正确配置，否则效率会大打折扣。

图形渲染是 CPU 与 GPU 协同完成的高速舞蹈，跨越软件、硬件、多种内存空间、编程语言、处理器类型以及大量特殊功能。更麻烦的是，不同 GPU、不同 API 的能力差异很大，同一应用在不同设备上的表现往往没有直接可比性。要在如此复杂的系统中定位瓶颈，Profiling（性能分析）再次成为关键工具。

本章将探讨以下内容：

- 渲染管线的核心流程，重点关注 CPU 与 GPU 的交互
- 如何判断渲染受限于 CPU 还是 GPU
- 一系列渲染优化技术，包括 GPU Instancing、LOD、遮挡剔除、粒子系统优化、Unity UI 优化、Shader 优化、光照贴图以及移动端优化

## 探索渲染管线

渲染性能差通常表现为两种情况：CPU 受限（CPU bound）或 GPU 受限（GPU bound）。CPU 受限相对容易分析，因为 CPU 工作主要集中在从磁盘/内存加载数据以及调用图形 API 指令。GPU 受限则更难定位，因为瓶颈可能出现在管线的多个环节中。

### CPU 与 GPU 的协作

CPU 通过图形 API 和硬件驱动向 GPU 发送渲染指令，这些指令会累积在一个叫 **命令缓冲（command buffer）** 的队列中。GPU 依次处理这些命令，只要它能在下一帧开始前跟上指令的速率和复杂度，帧率就能保持稳定。一旦 GPU 跟不上，或者 CPU 生成指令耗时过长，帧率就会下降。

### GPU 前端（Frontend）

前端负责处理顶点数据：

1. 接收来自 CPU 的网格数据，发起一次绘制调用（draw call）。
2. 把顶点数据送入顶点着色器（vertex shader），进行 1 对 1 的变换。
3. 生成图元（primitive，通常是三角形）。
4. 光栅器（rasterizer）根据顶点位置和相机视图决定最终图像需要绘制哪些像素，这些潜在的像素称为 **片元（fragments）**，随后进入后端处理。

顶点着色器是一些类似 C 的小程序，负责声明输入数据、决定如何操作并输出信息给光栅器。曲面细分（tessellation）则由几何着色器处理，它可以 1 对多地输出顶点，从而程序化地生成更多几何体。

### GPU 后端（Backend）

后端负责处理片元：

1. 每个片元经过片元着色器（fragment shader，也称 pixel shader），执行深度测试、透明度测试、上色、纹理采样、光照、阴影、后处理等复杂操作。
2. 处理后的数据写入帧缓冲（frame buffer），最终发送到显示设备。
3. 图形 API 默认使用两个帧缓冲：一个用于当前显示，另一个由 GPU 绘制下一帧。
4. 当 GPU 遇到 swap buffers 指令时，两个缓冲交换，新帧被呈现。
5. 下一帧继续使用旧的帧缓冲绘制，循环往复。

### Fill Rate（填充率）

Fill Rate 指 GPU 绘制片元的速度，只统计通过所有条件测试、最终实际写入的片元。例如 **Z-test（深度测试）** 可以剔除被更近物体遮挡的片元，从而节省大量 Fill Rate。高分辨率屏幕需要处理更多片元，多个物体重叠时容易产生 **Overdraw（过度绘制）**，即同一像素被反复绘制，浪费 Fill Rate。

Overdraw 可以通过 Scene 窗口的 Overdraw 着色模式直观查看：越亮的区域 Overdraw 越严重。需要注意：不透明队列中的物体可以通过 Z-test 剔除片元，但透明队列中的物体无法这样做，因此 UI 等透明对象往往是 Overdraw 的重要来源。

### Memory Bandwidth（内存带宽）

后端另一个常见瓶颈是内存带宽。片元着色器采样纹理时，需要把纹理从 VRAM 拉入更高速的本地纹理缓存。如果纹理已经在缓存中，采样非常快；否则就会发生缓存未命中（cache miss），需要从 VRAM 读取整个纹理，消耗内存带宽。

内存带宽通常按核心给出预算。例如每核心 96 GB/s、目标 60 FPS，则每帧大约可承受 1.6 GB 的纹理数据交换。注意这不是项目或 VRAM 中的总纹理大小限制，而是**每帧内纹理交换量**的限制。如果多个着色器使用不同的高清纹理和次纹理（法线贴图、发射贴图等），且这些对象没有被合批，纹理缓存就无法长时间保留同一份纹理，极易导致带宽瓶颈。

### 光照与阴影

现代游戏中，单个物体很少一次渲染完成，光照和阴影往往需要多遍处理。对于每个光源，GPU 都要对物体进行一次片元着色器处理，最后把结果合并。实时阴影尤其昂贵：需要为阴影投射者和阴影接收者生成阴影贴图（shadow map），大幅增加 draw call、Fill Rate 和内存带宽。

Unity 提供了多种光照方案：

- **Forward Rendering（前向渲染）**：传统方式，每个物体按光源数量多次绘制。Pixel Light Count 和光源的 Render Mode（Important / Not Important）会显著影响 draw call。
- **Deferred Shading（延迟着色）**：先渲染到 G-Buffer，再统一计算光照，适合多光源场景，但不支持抗锯齿、透明物体和动画阴影，且对硬件要求更高。
- **Vertex-Lit（遗留）**：逐顶点计算光照，效果差，主要用于简单 2D 游戏。
- **Global Illumination（全局光照）**：烘焙光照贴图（lightmap），在编辑器中预计算后打包进游戏，运行时几乎不增加开销。Light Probe 可为动态物体提供近似光照，但会占用额外内存和带宽。

### Multithreaded Rendering（多线程渲染）

多线程渲染在桌面和主机平台默认开启。它把“推送命令到 GPU”放到独立渲染线程，把剔除和生成命令放到多个工作线程，从而大幅减轻主线程负担。如果项目 CPU 受限，开启多线程渲染后，主线程优化对渲染性能的影响会变小；但 GPU 受限的情况不受此设置影响。

### 低级渲染 API

Unity 通过 `CommandBuffer` 类暴露了一些底层渲染 API，可以程序化地控制渲染流程。如果需要更底层的控制（如直接调用 OpenGL/DirectX/Metal），可以编写原生插件（native plugin） hook 进 Unity 的渲染管线。

## 检测渲染性能问题

### 使用 Profiler

Profiler 的 **CPU Usage** 和 **GPU Usage** 区域可以快速判断瓶颈所在：

- 如果 CPU 的 Rendering 任务耗时很长，而 GPU 很短，说明 CPU 受限。
- 如果 CPU 和 GPU 时间接近，且 CPU 大量时间花在 `Gfx.WaitForPresent`，说明 CPU 在等待 GPU，实际是 GPU 受限。

进行 GPU 瓶颈测试时，应关闭垂直同步（V Sync Count），否则数据会被污染。

### 暴力测试法

如果Profiler数据仍无法定位，可以使用暴力测试：

- **CPU 受限测试**：增加 draw call 或关闭静态/动态合批，观察性能是否显著恶化。
- **Fill Rate 瓶颈测试**：降低屏幕分辨率，如果性能大幅提升，说明是 Fill Rate 瓶颈。
- **内存带宽瓶颈测试**：降低纹理质量（Edit | Project Settings | Quality | Texture Quality），如果性能大幅提升，说明是内存带宽瓶颈。

## 渲染性能优化技术

### 启用/禁用 GPU Skinning

GPU Skinning 决定蒙皮（根据骨骼位置变换顶点）在 CPU 还是 GPU 前端执行。开启后蒙皮移到 GPU，但 CPU 仍需传输数据和生成命令。CPU 或 GPU 任一设备繁忙时，都可利用此选项把负载转移到较空闲的设备。

### 降低几何复杂度

减少顶点数量有三种方式：

1. 美术团队手动优化或使用网格减面工具。
2. 直接从场景中移除部分网格（最后手段）。
3. 使用 LOD（见下文）。

### 减少曲面细分

几何着色器中的曲面细分会显著增加前端负载。如果前端是瓶颈，应检查曲面细分是否占用了过多预算。

### GPU Instancing

GPU Instancing 利用相同网格和相同渲染状态批量渲染多份实例，draw call 极少。与动态合批类似，但效率更高、可定制性更强。在 Material 上勾选 **Enable Instancing**，并通过 shader 代码引入颜色、缩放等参数变化。适合森林、岩石群等场景。

注意：Skinned Mesh Renderer 不支持 GPU Instancing，且部分平台和 API 不支持。

### 基于网格的 LOD

LOD（Level of Detail）根据物体距离相机的远近动态替换为低精度版本。把多个网格作为子对象挂在一个带 **LODGroup** 组件的父物体下，Unity 会根据包围盒在视口中的大小决定显示哪个 LOD。 LODGroup 配置得当可以显著减少顶点数据、draw call、Fill Rate 和内存带宽。

不过 LOD 会消耗磁盘、内存、CPU 和开发时间，不应过度预优化。广阔开放世界或相机移动频繁的场景收益最大；室内或俯视视角的 RTS/MOBA 游戏收益有限。

### Culling Groups

Culling Group 是 Unity API，允许我们创建自定义 LOD 系统。除了用于渲染，还可以用于游戏逻辑，例如判断敌人刷新点是否在玩家视野内、玩家是否接近某区域等。

### 遮挡剔除（Occlusion Culling）

遮挡剔除是减少 Overdraw 和 Fill Rate 的重要手段。Unity 会把世界划分成小单元，并用虚拟相机遍历场景，记录哪些单元从其他单元视角看不可见。使用时需要把静态物体标记为 **Occluder Static** 和/或 **Occludee Static**。

注意：

- 遮挡剔除只对静态物体有效。
- 被遮挡剔除的物体，其阴影仍然需要计算。
- 会消耗额外的磁盘空间、内存和 CPU。

### 优化粒子系统

粒子系统效果通常很好，但粒子数量、Shader 复杂度会同时影响前端和后端。降低密度、减少粒子数、使用图集（atlasing）都是常见手段。

#### 粒子系统自动剔除

可预测的（确定性）粒子系统在不可见时会被 Unity 自动剔除。如果粒子系统被设置为 World Space、使用外力/碰撞/拖尾/复杂动画曲线等，就会变得不可预测，从而无法自动剔除，即使不可见也会每帧完整计算。Unity 会在 Inspector 中给出相关警告。

#### 避免递归调用

`Start()`、`Stop()`、`Pause()`、`Clear()`、`Simulate()`、`isAlive()` 等方法默认会递归遍历所有子粒子系统。对于深层级结构，代价很高。可以传入 `withChildren: false`，或手动缓存所有 `ParticleSystem` 组件后逐个调用。

注意：Unity 2017.1 及更早版本中，`Stop()` 和 `Simulate()` 每次调用都会分配额外内存，已在 2017.2 修复。

## 优化 Unity UI

### 使用更多 Canvas

Canvas 负责管理其子 UI 元素的网格并发起 draw call。当 Canvas 或其子元素发生变化时，Canvas 会变“脏（dirty）”，需要重新生成所有子元素的网格，这是 UI 性能问题的常见来源。把 UI 拆分到多个 Canvas 中，可以让变化只影响局部 Canvas。注意跨 Canvas 的元素无法合批，因此应尽量把相同材质、相似更新频率的元素放在同一 Canvas。

### 静态与动态 Canvas 分离

把 UI 元素按更新频率分组：

- **静态**：背景图、标签等永不变化的内容
- **偶发动态**：按钮按下、悬停等事件触发的内容
- **持续动态**：动画、每帧变化的内容

将这三类元素分别放到不同 Canvas，可以最小化网格重生成开销。

### 禁用非交互元素的 Raycast Target

只有需要交互的 UI 元素才应开启 **Raycast Target**。关闭它可以减少 `GraphicsRaycaster` 每次事件检测时需要遍历的元素数量。

### 隐藏 UI 时禁用 Canvas 组件

不要逐个禁用 UI 元素，而应直接禁用父 Canvas 组件。这可以避免 UI 布局系统频繁变脏。注意子对象中的 `Update()`、`FixedUpdate()`、`LateUpdate()` 和协程仍会运行，需要单独处理。

### 避免在 UI 上使用 Animator

Animator 每帧修改 UI 元素属性会导致 Canvas 变脏。UI 动画应尽量自己实现 tweening，或使用专门为此设计的工具。

### 为 World Space Canvas 指定 Event Camera

World Space Canvas 默认 `eventCamera` 为 null，每次需要事件相机时都会调用 `FindObjectWithTag()`。应手动把主相机赋给 World Space Canvas 的 Event Camera。

### 不要用 alpha=0 隐藏 UI

alpha 为 0 的 UI 元素仍会产生 draw call。应通过 `IsActive` 禁用元素，或使用 Canvas Group：把 Canvas Group 的 alpha 设为 0 会剔除子对象，不产生 draw call。

### 优化 ScrollRect

- **使用 RectMask2D**：不要只用深度排序实现滚动，RectMask2D 可以裁剪并剔除不可见的子元素。
- **为 ScrollRect 单独禁用 Pixel Perfect**：Pixel Perfect 会让快速移动的元素进行像素对齐，开销较大。把 ScrollRect 放在独立 Canvas 下再关闭 Pixel Perfect。
- **手动停止微小滚动**：当 ScrollRect 速度低于阈值时，调用 `ScrollRect.StopMovement()` 冻结运动，减少网格重生成。

### 全屏交互遮罩

常见做法是用一个覆盖全屏的透明 UIImage 阻止玩家操作弹窗后的内容，但这会破坏合批并引入透明开销。一个取巧办法是使用没有 Font 和 Text 的 UIText，它不生成可渲染信息，只处理交互包围盒检测。

### 查看 Unity UI 源码

如果 UI 性能问题严重，可以查看 Unity UI 的源码（Bitbucket 仓库）来定位问题，甚至自己修改后手动引入项目。

## Shader 优化

片元着色器是 Fill Rate 和内存带宽的主要消费者。其开销取决于纹理采样次数、数学函数复杂度等因素。GPU 的并行特性意味着：任何一个线程上的瓶颈都会限制整条“流水线”的产出。

### 使用移动平台 Shader

Unity 内置的移动平台 Shader 并不仅限于移动设备使用，它们只是被优化为资源占用最小。桌面平台也可以尝试，但可能损失画质。

### 使用较小的数据类型

GPU 处理较小数据类型更快，尤其是移动平台。可把 `float`（32 位）替换为 `half`（16 位）甚至 `fixed`（12 位定点）。颜色值通常适合降低精度，但需要在画质和性能间测试权衡。

### 避免在 Swizzling 时转换精度

Swizzling 是从现有向量按指定顺序创建新向量的技术。在 swizzling 的同时转换精度类型代价较高。应统一使用高精度类型，或整体降低精度以避免转换。

### 使用 GPU 优化的辅助函数

尽量使用 Cg 标准库和 `UnityCG.cginc` 中的内置函数，例如 `abs()`、`lerp()`、`mul()`、`step()`、`WorldSpaceViewDir()`、`Luminance()` 等，而不是自己写等价代码。

### 禁用不必要的特性

检查 Shader 是否真的需要透明度、Z-write、alpha test、alpha blending。移除非关键特性可以节省 Fill Rate。

### 移除不必要的输入数据

Shader 开发过程中常遗留一些不再使用的顶点、几何或片元输入数据，GPU 仍会从内存中读取它们。应定期清理 Shader 输入。

### 只暴露必要的变量

暴露给 Material 的变量会被 CPU 每帧推送，编译器无法将其优化为常量。如果某些变量最终值固定不变，应在 Shader 中硬编码为常量。

### 降低数学复杂度

复杂数学运算会严重拖慢渲染。可以预先把函数结果计算好并存入纹理，运行时直接采样。`sin()`、`cos()` 已经被高度优化，通常不需要替换；但 `pow()`、`exp()`、`log()` 等复杂函数以及自定义计算是优化候选。如果 Shader 已经在采样一张纹理且 alpha 通道未使用，可把预计算数据塞进 alpha 通道，不增加运行时开销。

### 减少纹理采样

纹理采样是内存带宽的核心来源。应尽量少用纹理、尽量使用小纹理，并确保采样顺序与纹理存储顺序一致（避免 `tex2D(y,x)` 这种导致缓存未命中的写法）。

### 避免条件分支

GPU 的并行执行模型使得条件分支代价很高：除非所有核心走同一路径，否则 GPU 必须依次执行所有可能路径。如果条件不依赖逐像素行为，通常宁愿多做一点无意义的数学运算，也不要引入分支。

### 减少数据依赖

编译器会尝试把可并行的数据获取优化为并行执行。但如果代码中存在长链数据依赖，例如每次纹理采样都依赖上一次采样的结果，编译器无能为力，性能会大幅下降。

### Surface Shader 优化

Surface Shader 是片元着色器的简化形式，Unity 会自动转换，但会牺牲一些优化空间。可通过以下属性微调：

- `approxview`：近似视角方向，节省开销。
- `halfasview`：降低视角向量精度。
- `noforwardadd`：只考虑一个方向光，减少 draw call 和光照复杂度。
- `noambient`：禁用环境光。

### Shader-Based LOD

可在 Shader 中使用 `LOD` 关键字设置该 Shader 支持的最小屏幕占比。如果当前 LOD 不匹配，Unity 会降级到 fallback Shader。也可在运行时通过 `Shader.maximumLOD` 调整。

### 减少纹理数据

降低纹理分辨率或位深、使用 Mipmap 都能减少纹理数据。Scene 窗口的 Mipmaps 着色模式可以高亮显示哪些纹理在当前相机距离下分辨率不合适（蓝色表示过大，红色表示过小）。

### 测试不同 GPU 纹理压缩格式

不同平台支持 DXT、PVRTC、ETC、ASTC 等压缩格式。在纹理的 Platform-specific settings 中可以覆盖默认压缩格式，可能获得空间或性能收益。但应优先使用通用方案，避免为每台设备单独调优。

### 最小化纹理交换

如果内存带宽是瓶颈，需要减少纹理采样总量。可以降低分辨率、在不同网格上复用同一张纹理（通过材质参数变化外观）、或将总是一起使用的纹理合并为图集。

### VRAM 限制

VRAM 不足时，GPU 需要把旧纹理刷出再把新纹理载入，造成严重的 **texture thrashing**。现代主机（PS4、Xbox One、Wii U）使用统一内存，这个问题较轻；但大多数平台 CPU 和 GPU 内存分离，必须确保当前纹理总用量低于目标硬件 VRAM。

### 预加载纹理

为避免运行时异步加载出现“空白纹理”，可以创建一个使用目标纹理的隐藏 GameObject 放在玩家必经之路上，让它提前进入视野从而触发纹理从 RAM 复制到 VRAM。也可通过脚本设置 `Renderer.material.texture` 来预加载。

## 光照优化

### 负责任地使用实时阴影

实时阴影是 draw call 和 Fill Rate 的大户。在 Edit | Project Settings | Quality | Shadows 中：

- **Soft Shadows** 昂贵，**Hard Shadows** 便宜，**No Shadows** 免费。
- **Shadow Distance**：根据游戏实际需要设置，远距离渲染阴影毫无意义。
- **Shadow Resolution** 和 **Shadow Cascades**：提高这两项会增加阴影贴图大小，从而增加内存带宽和 VRAM。
- Soft Shadows 不额外消耗内存或 CPU，只是片元着色器更复杂。

### 使用 Culling Mask

Light 组件的 Culling Mask 可以限制受光照影响的层，从而减少光照开销。Deferred Shading 对 Culling Mask 支持有限，只能禁用 4 个层。

### 使用烘焙光照贴图

把光照和阴影烘焙到场景中的开销远低于实时计算。代价是更大的磁盘占用、内存占用和潜在的内存带宽压力。除非项目只使用 Vertex-Lit 或单个方向光，否则通常都应使用 lightmapping。

## 移动端渲染优化

移动设备性能受限，需要额外注意以下几点：

- **避免 alpha testing**：移动 GPU 上 alpha testing 开销很高，优先使用 alpha blending。
- **最小化 draw call**：移动应用更容易受 draw call 瓶颈影响，应尽早使用网格合并、合批、图集。
- **最小化 Material 数量**：Material 越少，draw call 越少，也有助于降低 VRAM 和带宽压力。
- **最小化纹理尺寸**：移动设备纹理缓存很小。要确保目标设备支持所使用的纹理尺寸，过大的纹理会在初始化时被 CPU 降采样，既浪费加载时间又导致画质不可控。
- **纹理保持正方形且为 2 的幂**：这关系到 GPU 纹理压缩能否生效。
- **Shader 中使用最低精度格式**：移动 GPU 对精度很敏感，优先使用 `half`，避免精度转换。

## 小结

渲染管线是 Unity 中最复杂的子系统，涉及的优化技术也最多。记住：除了算法层面的改进，每一项性能增强几乎都伴随某种代价。我们应始终通过 Profiling 定位真正的瓶颈，再选择合适的技术组合，并愿意为消除某个瓶颈承担相应成本。
