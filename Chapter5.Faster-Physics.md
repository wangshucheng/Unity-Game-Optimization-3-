# Chapter 5 物理优化

## 1. 场景设置

### 1.1 缩放

*   尽量使得所有物体缩放比为（1，1，1）

### 1.2 位置

*   所有物理物体尽量接近（0，0，0)的位置，以便提升浮点运算精度。

### 1.3 质量

*   避免有超大质量值。
*   相碰撞的物体，质量比尽量控制在1：100之间。否则可能出现浮点精度丢失和不稳定物理现象。
*   如果碰撞比例确实需要过大，那么采用碰撞矩阵进行剔除，来避免问题发生。

## 3. 优化碰撞矩阵

![在这里插入图片描述](https://img-blog.csdnimg.cn/c7bbe95fb4ff44f48843b67e7d331db5.png "在这里插入图片描述")

*   将不需要碰撞的层都去掉，这样能减少每次FixUpdate时，必须检查的边界体积数量。

## 4. 首选离散碰撞（discrete collision）

*   连续检查（continuous）消耗高出一个数量级
*   动态连续检查（continuous dynamic）再高出一个数量级

## 5. 修改Fixed Update频率

*   为了离散碰撞更容易被检测到，可以通过修改Time.fixedDeltaTime 来完成。
*   最好使用测试场景测试修改后的效果，看是否符合碰撞要求。

## 6. 最小化射线检查和边界体积检查

*   使用layer mask 把不需要检查的直接过滤掉

## 7. 避免使用复杂的网格碰撞器

*   使用几个基本网格进行拼装组合\
    ![在这里插入图片描述](https://img-blog.csdnimg.cn/67abf33f8e8d4f94b514b913e88efdd1.png "在这里插入图片描述")
*   使用更简单的网格用于碰撞\
    ![在这里插入图片描述](https://img-blog.csdnimg.cn/0c3ac0554cfb4ffcad468c942d857cd6.png "在这里插入图片描述")

## 8. 避免使用复杂的物理组件

*   例如TerrainCollider Cloth WheelCollider
*   这几个消耗高出几个数量级

## 9. 使物理对象休眠

*   Unity 会对速度小于设定阈值的Rigidbody对象进行休眠，以提升性能。（Physics/Sleep Threshod 设定阈值）
*   修改Rigidbody 的任何属性都会重新唤醒对象
*   避免出现岛屿效应：大量刚体互相接触，任意一个刚体被唤醒时，由于碰撞，会导致其他大量刚体同时唤醒，然后出现性能尖峰。

## 10. 修改处理器迭代次数（solver iteration count）

*   当关节（Joint）、弹簧（Spring）等其他方法连接刚体时，由于刚体见相互依赖的加护作用，系统需要进行多次迭代计算来得到精确的结果。
*   在不影响物理表现情况下，可降低最大迭代次数。默认设置：Physics | Default\
    Solver Iterations
*   在出现高需求时，可以用Physics.defaultSolverIterations 来增加迭代次数。这个属性只影响新生成的刚体。所以我们可以在生成特定刚体前增加迭代次数，生成后再将这个属性改回来。
*   Physics.defaultSolverVelocityIterations 能改变计算基于关节碰撞期间的速度的迭代次数。如果布娃娃出现碰撞问题，可尝试增加此值。
*   2D 中对应的时：Position Iterations 和 Velocity Iterations

## 11. 优化布娃娃（ragdolls）

### 11.1 减少关节和碰撞器

*   Unity 默认创建的布娃娃有13个碰撞器。很多时候只用7个也又过得去的效果（骨盆、胸部、头部、四肢）

### 11.2 避免布娃娃之间碰撞

*   布娃娃之间的碰撞消耗性能是指数级的
*   合理的使用碰撞图层来规避不必要的碰撞

