---
layout: default
title: "Chapter 5 物理优化"
nav_order: 6
---

# Chapter 5 物理优化

## 0. 理解物理引擎

Unity 有两个物理引擎：Nvidia PhysX（3D）和 Box2D（2D）。它们都以固定时间步长（fixed timestep）运行，而不是以渲染帧率运行。这意味着 `FixedUpdate()` 以固定间隔被调用，与 `Update()` 不同。

### 0.1 物理和时间

- 物理引擎假设时间以固定值推进。
- `Time.fixedDeltaTime` 控制固定更新的间隔，默认值通常是 0.02 秒（50 Hz）。
- 如果一帧耗时过长，物理引擎可能需要在同一帧内多次调用 `FixedUpdate()` 来追赶时间。

### 0.2 Maximum Allowed Timestep

- `Time.maximumAllowedDeltaTime`（或 Physics 设置中的 **Maximum Allowed Timestep**）限制了物理引擎在单帧内追赶的最大时间。
- 如果一帧耗时超过这个值，物理引擎会限制 `FixedUpdate()` 的调用次数，避免陷入"死亡螺旋"（即物理计算导致更长的帧，进而需要更多物理计算）。
- 合理设置可以防止卡顿导致物理爆炸或性能崩溃。

### 0.3 静态碰撞体与动态碰撞体

- **静态碰撞体（Static Collider）**：没有 Rigidbody 的碰撞体。它应该保持静止，移动它会带来较大的性能开销，因为物理引擎需要重新构建其空间数据结构。
- **动态碰撞体（Dynamic Collider）**：带有 Rigidbody 的碰撞体。它们由物理引擎模拟。
- 如果需要移动一个没有物理模拟的碰撞体，最好给它加上 Rigidbody 并勾选 **Is Kinematic**，而不是直接移动 Static Collider。

### 0.4 碰撞检测模式

- **Discrete（离散）**：默认模式。每帧根据速度移动物体，然后进行边界体积检查。最快，但可能穿过高速小物体。
- **Continuous（连续）**：对静态碰撞体进行连续碰撞检测，更精确但更贵。
- **Continuous Dynamic（动态连续）**：对静态和动态碰撞体都进行连续检测，最贵。
- **Continuous Speculative（推测连续）**：较新的模式，在某些情况下比 Continuous Dynamic 更高效。

### 0.5 碰撞器类型

- 从快到慢排序：Sphere / Capsule / Box < Mesh Collider（简单网格）< TerrainCollider / WheelCollider / Cloth / 复杂 Mesh Collider
- 优先使用原始碰撞器（球体、胶囊体、盒子），用多个简单碰撞器组合近似复杂形状。

### 0.6 调试物理

- 使用 **Window | Analysis | Physics Debugger** 可视化碰撞体、休眠状态、接触点等。
- 在 Profiler 的 Physics 区域查看物理耗时。

## 1. 场景设置

### 1.1 缩放

*   尽量使所有物体的缩放为 (1, 1, 1)。

### 1.2 位置

*   所有物理物体尽量接近 (0, 0, 0) 的位置，以便提升浮点运算精度。

### 1.3 质量

*   避免有超大质量值。
*   相互碰撞的物体，质量比尽量控制在 1:100 以内。否则可能出现浮点精度丢失和不稳定的物理现象。
*   如果质量比确实需要过大，可以使用碰撞矩阵进行剔除，来避免问题发生。

## 2. 恰当使用静态碰撞体

*   不要让没有 Rigidbody 的碰撞体移动。如果必须移动，添加 Rigidbody 并勾选 **Is Kinematic**。
*   静态碰撞体适合地面、墙壁、不可破坏的建筑等固定物体。

## 3. 负责任地使用触发器

*   Trigger 碰撞体也会产生碰撞检测开销。尽量减少同时存在的大型触发器数量。
*   使用 Layer Mask 让触发器只与需要检测的对象交互。
*   在 `OnTriggerEnter/Stay/Exit` 中避免复杂计算。

## 4. 优化碰撞矩阵

![碰撞矩阵示例](https://img-blog.csdnimg.cn/c7bbe95fb4ff44f48843b67e7d331db5.png)

*   将不需要碰撞的层都去掉，这样能减少每次 FixedUpdate 时必须检查的边界体积数量。

## 5. 首选离散碰撞（Discrete Collision）

*   连续检查（Continuous）消耗高出一个数量级。
*   动态连续检查（Continuous Dynamic）再高出一个数量级。

## 6. 修改 Fixed Update 频率

*   为了让离散碰撞更容易被检测到，可以通过修改 `Time.fixedDeltaTime` 来完成。
*   最好使用测试场景测试修改后的效果，看是否符合碰撞要求。

## 7. 调整 Maximum Allowed Timestep

*   在 **Edit | Project Settings | Time** 中调整 **Maximum Allowed Timestep**。
*   这个值限制了单帧内物理引擎追赶的最大时间。设置过小可能导致物理在卡顿后"跳过"；设置过大可能导致卡顿后物理计算过多，进一步拖慢帧率。
*   根据项目需求测试并选择合适的值。

## 8. 最小化射线检查和边界体积检查

*   使用 Layer Mask 把不需要检查的直接过滤掉。
*   减少射线数量，合并多次检查，或使用空间分区结构（如 Octree）提前剔除。

## 9. 避免使用复杂的网格碰撞器

*   使用几个基本碰撞器进行拼装组合
    ![基本碰撞器组合](https://img-blog.csdnimg.cn/67abf33f8e8d4f94b514b913e88efdd1.png)
*   使用更简单的网格用于碰撞
    ![简化碰撞网格](https://img-blog.csdnimg.cn/0c3ac0554cfb4ffcad468c942d857cd6.png)

## 10. 避免使用复杂的物理组件

*   例如 TerrainCollider、Cloth、WheelCollider。
*   这几个组件的消耗高出几个数量级。

## 11. 使物理对象休眠

*   Unity 会对速度小于设定阈值的 Rigidbody 对象进行休眠，以提升性能。（在 Physics / Sleep Threshold 中设定阈值）
*   修改 Rigidbody 的任何属性都会重新唤醒对象。
*   避免出现岛屿效应：大量刚体互相接触，任意一个刚体被唤醒时，由于碰撞，会导致其他大量刚体同时唤醒，然后出现性能尖峰。

## 12. 修改处理器迭代次数（Solver Iteration Count）

*   当关节（Joint）、弹簧（Spring）等方法连接刚体时，由于刚体间相互依赖的交互作用，系统需要进行多次迭代计算来得到精确的结果。
*   在不影响物理表现的情况下，可降低最大迭代次数。默认设置：Physics / Default Solver Iterations。
*   在出现高需求时，可以用 `Physics.defaultSolverIterations` 来增加迭代次数。这个属性只影响之后新生成的刚体，所以我们可以在生成特定刚体前增加迭代次数，生成后再将这个属性改回来。
*   `Physics.defaultSolverVelocityIterations` 能改变基于关节碰撞期间的速度迭代次数。如果布娃娃出现碰撞问题，可尝试增加此值。
*   2D 中对应的是：Position Iterations 和 Velocity Iterations。

## 13. 优化布娃娃（Ragdolls）

### 13.1 减少关节和碰撞器

*   Unity 默认创建的布娃娃有 13 个碰撞器。很多时候只用 7 个也有过得去的效果（骨盆、胸部、头部、四肢）。

### 13.2 避免布娃娃之间碰撞

*   布娃娃之间的碰撞消耗性能是指数级的。
*   合理使用碰撞图层来规避不必要的碰撞。

### 13.3 替换、禁用或移除不活跃的布娃娃

*   当敌人死亡并进入布娃娃状态后，如果不再需要精细的物理表现，可以在几秒后禁用 Rigidbody、切换到预设的死亡姿势动画，或完全移除布娃娃组件。
*   这可以释放物理计算资源，避免大量尸体持续消耗 CPU。

## 14. 知道何时使用物理

*   不是所有移动都需要物理。简单的移动、旋转、碰撞检测可以用代码或射线检测实现，而不必引入 Rigidbody。
*   对于不需要真实物理反馈的物体，考虑使用 `Collider` + 手动代码处理，而不是完整的物理模拟。
*   在大量对象需要简单碰撞时，考虑自定义碰撞系统或空间分区，而不是依赖 PhysX。

