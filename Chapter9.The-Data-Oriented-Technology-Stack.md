---
layout: default
title: "Chapter 9 DOTS 技术栈"
nav_order: 10
---

# Chapter 9 DOTS 技术栈
最近几年，我们已经在多线程编程上见证了很大的发展。原因很明显：当我们在单核上已达到技术极限时，我们发现了如何有效地在硬件上利用上千个核心，并并行执行每段代码来获得性能上的加速。
然而，从单线程编程转移到多线程编程并不简单，并不是每一个算法都可以轻易地切分成片段。即便可以，也有很多细节需要注意，用来避免一些奇怪和不可预测的情况。
当 Unity 的第一个版本于 2005 年发布时，多线程编程还只是一种期望。然而，经过 14 年的游戏开发基础建设，游戏引擎需要调整自己以适应前沿技术的步伐。
Unity 现在正经历一系列努力来调整其核心，以掌控一个成熟的多线程世界，这个努力被命名为 DOTS。

在这个章节，我们会介绍 DOTS 的组件：
- Job 系统
- Entity Component System（ECS）
- Burst 编译

DOTS 技术栈在 Unity 里还处于实验阶段，它的一些组件还在 Preview 版本中，也就是说尽量避免在重要项目中使用，并且它的迭代非常快。官方的 ECS 教程现在不可用，因为已经过时了；未来有新的发展也不奇怪。我会在结尾放上链接，以便了解最新的 DOTS 技术。
   
## 多线程的问题
电子游戏有很大的多线程潜力。理论上，每个 GameObject 可以被当作一个独立的 entity，拥有自身的生命周期和计算路径。这会在有很多 GameObject 实例的时候显著提高游戏性能表现。假如处理一个 GameObject 的 Update 需要 1ms，如果你有上千个类似的 GameObject 实例，将会消耗将近 1 整秒；但是如果你可以把每个 GameObject 的 Update 绑定到一个核心，所有的 Update 都并行运行，那总消耗时间就会接近 1ms，提升了 1000 倍的效率！

但是，这并不简单。之前说了，你不能把每段代码轻易地和一个核心绑定在一起让一切都顺利运行。多线程编程有很多风险，包括：条件竞争、死锁、难以调试和处理的 bug。

条件竞争是两个以上的计算需要一个期望顺序，但事实上顺序取决于它们以什么顺序完成。例如一个线程需要把 1 个数字加上 3，另一个线程需要把它乘 4，结果就完全不一样，取决于哪个操作在前。

死锁是当两个以上的线程共同争夺同一个共享资源时的问题。每个线程都需要完整的资源来完成任务，但每个线程只持有一部分资源而拒绝放弃对它们的控制权。这种情况下，任何线程都不能做任何事，因为它们都没有完成自己的任务。

基于这种情况，Unity 的 API 是线程不安全的，意味着它们不能被不同的线程并行调用。结果，几乎所有的 Unity 代码都在主线程运行，包括所有的 GameObject 和 MonoBehaviour（这就是为什么如果你把一个线程锁住，你会看到 Unity Editor 卡死的情况）。
   
因为多线程是一个复杂的话题，我们会一步步浏览一个小例子。

## 一个小例子

想象如果你有上千个相似的东西在你的场景里。这不是一个奇怪的需求，有很多合理的情况：如果你想在一个巨大的银河战斗中渲染一条船，或者你想为 RTS 游戏表现上千个单位，或者你想处理上千个粒子。

为了简化，在我们的 demo 中，我们用 10000 个旋转的方块。现在开始：

- 每个方块有一个单独的 MonoBehaviour 实例执行一个很简单的旋转方块：
    
      using UnityEngine;
      namespace Classic
      {
        public class Rotator:MonoBehaviour
        {
          public float rotationSpeed;
        
          void Update()
          {
            transform.Rotate(0f,rotationSpeed * Time.deltaTime, 0f);
          }
        }
      }
    
- 现在，我们想要在场景中插入 10000 个方块，所以我们创建一个 game manager 来做以下几件事：
  - 给场景中加入 10000 个方块
  - 给每个方块设置一个随机的速度

- 所以我们创建一个空的 GameObject，并给它绑定一个 game manager 脚本如下：
        
      using UnityEngine;
      using System;
           
      namespace Classic
      {
        public class ClassicCubeManager:MonoBehaviour
        {
          #region COMMON_GAME_MANAGER_DATA
          public float cubeSpacing = 0.1f;
          public int width = 10;
          public int height = 10;
          
          public GameObject cubePrefab;
          #endregion
          
          void Start()
          {
            SpawnCubes();
          }
          
          private void SpawnCubes()
          {
            Debug.Log(String.Format("Spawing {0} cubes", (width/cubeSpacing) * (height/cubeSpacing)));
            Vector3 position = new Vector3();
            while(position.x < width)
            {
              while(position.y < height)
              {
                var newCube = GameObject.Instantiate(cubePrefab);
                newCube.transform.position = position;
                newCube.GetComponent<Rotator>().rotationSpeed = UnityEngine.Random.Range(25.0f,50.f);
                position = new Vector3(position.x,position.y + cubeSpacing, 0f);
              }
              position = new Vector3(position.x + cubeSpacing,0f,0f);
            }
          }
        }
      }
     
这个脚本使用 cubePrefab，然后把它们投入到一个宽 × 高的矩形空间里。最关键的是 `SpawnCubes` 方法，这个方法从初始位置开始一直投入方块直到达到尽头，这是一个标准的脚本。
- 现在我们可以开始运行了，你可以看到帧率没有优化，在右上角可以看到帧率大概在 22 FPS 左右。

- FPS 值没有提高，然而我们打开 Profiler 窗口试着理解这个程序的表现。图像清晰地展示了我们占用了几乎 1GB 的内存，消耗 45ms 每帧，10ms 用在脚本上。这是错的，Update 脚本是简单的，我们只是每帧旋转了几度而已。

我们接下来可以做得更好。

## Unity Job 系统

DOTS 中主要可以大幅提升性能的特色技术板块是 C# Job 系统。像其他 DOTS 组件一样，这个特色一直处于活跃开发状态，从 2019.1 版本开始公开，所以越早开始熟悉越好，它会介绍几个 Unity 开发者写高性能脚本的变化：

C# Job 系统可以在副线程创建很多简单的小任务来给主线程减负。C# Job 系统会很聪明地应对并行任务，比如成千上万的 AI 任务，或者任何可以切分成小的独立操作的问题。当然，也可以用在多线程上表现一样好。Job 系统同样引入了一些编译技术，相比单纯的多线程能得到更好的性能加速。

## 一个基本的 Job

一个 job 就是一个运行在单独线程中的方法：

    using Unity.Collections;
    using Unity.Jobs;
    using UnityEngine;

    public struct SimpleJob : IJob
    {
      // Put here a bunch of data...

      public float number;

      public NativeArray<float> data;

      // Write your Execute() function.
      public void Execute()
      {
        data[0] += number;
      }
    }

每个 job 就是一个继承了 `IJob` 接口的 struct，这个 struct 包含任何我们想用来执行 `Execute` 方法的参数。上面的例子中，只是给数组的第一个元素加了一个值。

但是，我们之前说过了，多线程是一个非常繁杂的工作，Unity 提供了一些限制，当你给 job 传输和接受数据的时候。基本原则是 `Execute` 方法不接受任何参数并且不能有任何返回值，所有 job 需要的数据都必须拷贝在 struct 里，并且所有的结果也必须写在 struct 里。

事实上，我们需要拷贝进 struct 里看起来有一个明显的限制：你不能给它传递一个 MonoBehaviour 的实例或一个 List 的引用作为参数。幸运的是，Unity 提供了一个解决办法用来获取 job 中的共享内存：用一个线程安全的容器 wrapper。

容器包括以下：
- `NativeArray`：一个简单的数据容器（和 C# 的基本数组一样，但是线程安全）
- `NativeList`：和 NativeArray 类似，但是可变长
- `NativeHashMap`：HashMap 的线程安全版
- `NativeMultiHashMap`：和 NativeHashMap 类似，但可以用多个值做 key
- `NativeQueue`：一个先进先出的线程安全 Queue

因此，在我们的 job 中，我们用一个单元素容量的 NativeArray 变量来存储输入和输出数据。

现在，我们想要运行这个 job。为了实现，我们用一个 MonoBehaviour 来初始化和运行它：

    using Unity.Collections;
    using Unity.Jobs;
    using UnityEngine;
    
    public class SimpleJobRunner:MonoBehaviour
    {
      public float numberToAdd = 5;
      
      private NativeArray<float> theData;
      
      private JobHandle simpleJobHandle;
      
      void Start()
      {
        theData = new NativeArray<float>(1,Allocator.Persistent);
        theData[0] = 2;
        
        SimpleJob simpleJob = new SimpleJob
        {
          number = numberToAdd;
          data = theData
        };
        
        simpleJobHandle = simpleJob.Schedule();
        
        JobHandle.ScheduleBatchedJobs();
        
        simpleJobHandle.Complete();
        
        if(simpleJobHandle.IsCompleted)
        {
          Debug.Log(simpleJob.data[0]);
        }
        
        theData.Dispose();
      }
    }
    
在 `Start` 中，我们首先创建了一个空的 NativeArray。NativeArray 构造方法第一个参数是容器大小，第二个参数是 Allocator。这里实际上有 3 种调用：
- `Allocator.Temp`：这是最快的，但是必须在一帧内完成。实际上，Unity 强迫你在方法返回之前在数组上调用 `Dispose`。因此我们不能用这个给 jobs 传参，因为 jobs 不保证在开始后一帧内完成。
- `Allocator.TempJob`：这个比 Temp 版本慢一点，并且生命周期在 4 帧以下，这是一个给简单 job 的完美方案，比如这个例子中。
- `Allocator.Persistent`：这个是最慢的，但它的生命周期是无限制的，这个版本你可以存持久的数据用来给 job 提供。

在此之后，我们创建了一个 SimpleJob 的实例，传一个 number 和 data 作为参数。接着，我们通过 `Schedule` 方法安排好，这会返回一个 `JobHandle` 实例，可以用来控制这个 job 的执行。最后，我们等待这个 job 完成并打印结果。一切都看起来像标准的 C# 代码，但 job 运行在一个单独的线程里。

记住当一个好的 C# 公民，总是记得手动把用过的容器 dispose 掉。你不想污染内存，就像你不想污染环境一样！

在此，如果你给一个空对象绑定 SimpleJobRunner，你应该在控制台看到打印结果，一切都是被多线程影响的形式。

## 一个更复杂的例子

投入一个 job 只是用来给两个数字做加法，实在不能作为一个好的优化程序的例子。Unity 创造 job 是用来多线程运行上千个繁重的任务的。

因此，我们现在需要把之前旋转方块的例子调整一下，让它实际上通过 jobs 工作。我们的第一步是创建 job，如下：
   
      using Unity.Collections;
      using UnityEngine;
      using UnityEngine.Jobs;
      
      namespace JobSystem
      {
        public struct RotatorJob:IJobParallelForTransform
        {
          [ReadOnly]
          public NativeList<float> speeds;
          
          [ReadOnly]
          public float deltaTime;
          
          public void Execute(int index,TransformAccess transform)
          {
            Vector3 currentRotation = transform.rotation.eulerAngles;
            currentRotation.y += speeds[index] * deltaTime;
            transform.rotation = Quaterion.Euler(currentRotation);
          }
        }
      }
  
这个 job 有一点复杂，但不用担心。首先，它继承自 `IJobParallelForTransform`，这是一个特殊的 job 接口，用来并行运行 GameObject 实例的 transform。你可以通过扩展 `IJob` 来做同样的事，但因为这是一个非常常见的情况，Unity 为我们写了大部分的代码。你可以看到，最大的区别是 `Execute` 现在有 2 个参数。在我们的 demo 中，我们想要运行一个同样的 10000 个方块的任务，这种情况下，参数如下：
- `index`：代表方块的编号
- `transform`：代表方块的 transform 引用

我们的 job 需要 2 个输入：
- `speeds`：这是一个包含所有方块速度的 NativeList。记住，我们不能拿到某个特定 GameObject 数据的引用，所以我们需要把所有速度写在共享内存中。这块区域是只读的，我们不想让某个方块影响到其他方块。
- `deltaTime`：因为 job 完全脱离 Unity 引擎，它不能用 `Time` 或者其他 Unity 线程不安全的部分，因此我们需要自己传入 `deltaTime`。

这个 `Execute` 方法很简单，我们只是旋转了方块。

现在我们需要给每个方块调用这个 job，我们用一个 game manager 来做这些：

    namespace JobSystem
    {
      public class JobCubeManager : MonoBehaviour
      {
        #region COMMON_GAME_MANAGER_DATA
        public float cubeSpacing = 0.1f;
        public int width = 10;
        public int height = 10;
        
        public GameObject cubePrefab;
        #endregion
        
        TransformAccessArray transformAccessArray;
        Unity.Jobs.JobHandle jobHandle;
        NativeList<float> speeds;
        
        void Start()
        {
          transformAccessArray = new TransformAccessArray(0, -1);
          speeds = new NativeList<float>(1, Allocator.Persistent);
          SpawnCubes();
        }
        
        private void SpawnCubes()
        {
          Debug.Log(String.Format("Spawning {0} cubes", (width / cubeSpacing)));
          Vector3 position = new Vector3();
          while(position.x < width)
          {
            while(position.y < height)
            {
              var newCube = Instantiate(cubePrefab);
              newCube.transform.position = position;
              position = new Vector3(position.x,position.y + cubeSpacing,0f);
              transformAccessArray.Add(newCube.transform);
              speeds.Add(UnityEngine.Random.Range(25.0f,50.0f));
            }
            position = new Vector3(position.x + cubeSpacing,0f,0f);
          }
        }
        void Update()
        {
          jobHandle.Complete();
          if (jobHandle.IsCompleted)
          {
            var rotatorJob = new RotatorJob()
            {
              deltaTime = Time.deltaTime,
              speeds = speeds,
            };
            jobHandle = rotatorJob.Schedule(transformAccessArray);
            JobHandle.ScheduleBatchedJobs();
          }
        }
      }
    }
我们一开始定义了和经典案例相同的数据，后面 3 个比较有趣：
- `transformAccessArray`：我们会保存所有方块的 transform 实例引用，这是 job 访问它们的方式。
- `jobHandle`：一个 handle，用来查询 job 系统当前工作进度。
- `speeds`：一系列随机速度。

在 `Start` 中，我们只是初始化了本地容器，然后投入方块。注意我们用 `Allocator.Persistent`，因为我们想在 `Start` 中初始化，然后在剩下的时间中用相同的列表。

这个 `SpawnCubes` 方法和之前的非常相似，然而，这里有 2 个地方不同：
- 我们实例化方块之后，把它的 transform 添加到 `transformAccessArray`。
- 我们把 speed 放进 `speeds` 数组中，用来代替方块中的旋转速度。事实上，我们这个 prefab 不需要 rotator 组件！

现在，每帧我们需要给每个方块并行运行这些任务。

我们使用和之前一样的模式：检查之前的任务是否完成，实例化一个新 job，设置数据，然后通过整个 `transformAccessArray` 安排 job。

如果一切都对，我们可以运行同样的游戏效果，但可以享受到 35 FPS。

看 Profiler，我们可以发现脚本的时间几乎不见了，从 10ms 到 1ms，这是 90% 的提高！

然而，我们仍然有问题：场景中填满了 10000 个 GameObject 实例、10000 个 Transform、10000 个 MeshRenderer 和 10000 个不同组件的拷贝。MonoBehaviour 和 GameObject 是很重的数据结构，它们消耗了大量的 CPU。我们能做得更好吗？是的，我们可以。

## 新的 ECS

ECS 是一个有卓越勇气的尝试，试图重新设计 Unity 的核心。你可以想象，给基础设计模式做改变不是一个简单的任务。你会问为什么？

这里有几个原因，让我们一起来看看：
- 首先，就像我们之前说的，GameObject 和 MonoBehaviour 是很重的对象，它们携带了大量的代码和数据结构。你将会使用很大的、超出渲染需要的资源，这不是一个好的设计模型。
- 其次，MonoBehaviour 实例在内存中是分散的，这意味着 GameObject 需要在内存中寻找所有和它相关联的 MonoBehaviour 实例，然后依赖这些引用。这会导致 2 个问题：它会让缓存非常无效，更重要的是，我们想用多线程的时候会遇到问题，比如使用 Job 系统。
- 最后，MonoBehaviour 实例从代码设计上有问题，它们既存储数据又存储行为。这是一个大问题，毕竟很多好的游戏都采用了这个设计模式。然而，在软件工程领域更常见的是分离数据（Model）和算法（Controller）。

ECS，从分离数据和行为来看，基于 3 个基本概念：
- 一个 entity 是由它的组件来定义的，字面上这是 0 抽象。
- 一个 component 是纯粹的数据：一个 Health 组件只包含它的生命值，一个 Shield 组件包含 shield 的数量，一个 Rotation 组件只包含朝向，等等。
- 一个 system 定义了 entity 的行为。一个 system 用一组所有 entity 都包含特定组件的特殊行为，比如 `MoveAndRotateEnemy` 可能通过 Rotation、Translation 和 Enemy 组件来变换和旋转每个 entity。

一切准备就绪。

## 把 ECS 和 Jobs 混合

是时候给 10000 个旋转方块应用 ECS 了。在此之前，我们需要安装 package。
- 准备好我们的第一个组件。我们的方块需要旋转，所以我们需要一个确定的 RotationSpeed，这会成为我们的组件：

      [Serializable]
      public struct RotationSpeed : IComponentData
      {
        public float Value;
      }

看，十分简单。我们说过，一个组件就是数据，旋转速度由一个 float 数代表，因此我们只需要存储一个简单的 float 数。

你可能会问：我如何把这个组件绑定在 entity 上呢？我仍然可以使用 Inspector 来设定值吗？我之前在 Unity 中喜欢的方式呢？很遗憾，组件不能被绑定在 GameObject 上。毕竟，GameObject 不是 ECS 的一部分，Entity 不能出现在 scene 中，而组件不能出现在 Inspector 中。

幸运的是，有一个解决办法。如果我们想要把它们保留在 editor 里，比如定义一个 prefab 然后生产 10000 次，把 GameObject-MonoBehaviour 风格和 ECS 混合起来叫 Hybrid ECS 是最好的方案。

- 为了激活我们的组件，我们需要写一个 `IConvertGameObjectToEntity` 声明。`IConvertGameObjectToEntity` 是一系列代码，自动把一个标准的 MonoBehaviour 转化成一个关联的组件：

      using System.Collections;
      using System.Collections.Generic;
      using UnityEngine;
      using Unity.Entities;
      using System;
      using Unity.Mathematics;

      [RequiresEntityConversion]
      public class RotationSpeedAuthoring : MonoBehaviour, IConvertGameObjectToEntity
      {
        public float rotationSpeed = 35f;
        public void Convert(Entity entity, EntityManager dstManager, GameObjectConversionSystem conversionSystem)
        {
          var data = new RotationSpeed
          {
            Value = math.radians(rotationSpeed)
          }; // Convert to speed in radians
          dstManager.AddComponentData(entity, data);
        }
      }

在代码中，`RotationSpeedAuthoring` 是一个 `IConvertGameObjectToEntity` 声明和一个 MonoBehaviour（因此我们可以绑定脚本）。转换的核心在于 `Convert` 这个方法，这个 API 过去改变了很多，并且很可能未来也会再次改变。重要的是内容：这个方法取 MonoBehaviour 的数据，把它加到新组件上（RotationSpeed），做一些处理，最后绑定到 entity 上。
- 我们像以前一样创建 cubePrefab，然后增加 `RotationSpeedAuthoring` MonoBehaviour。在运行时，GameObject 会转化成 entity。
- 现在我们有了一切我们需要的，我们只是需要写我们的游戏 controller：

      using System;
      using UnityEngine;
      using Unity.Entities;
      using Unity.Transforms;
      using Unity.Mathematics;

      namespace ECSJob
      {
        public class ECSJobManager : MonoBehaviour
        {
          #region COMMON_GAME_MANAGER_DATA
          public float cubeSpacing = 0.1f;
          public int width = 10;
          public int height = 10;

          public GameObject cubePrefab;
          #endregion

          EntityManager entityManager;

          void Start()
          {
            entityManager = World.Active.EntityManager;
            SpawnCubes();
          }

          private void SpawnCubes()
          {
            int amount = Mathf.FloorToInt(width / cubeSpacing) * Mathf.FloorToInt(height / cubeSpacing);
            Debug.Log(String.Format("Spawning {0} cubes", amount));

            Vector3 position = new Vector3();

            var entityPrefab = GameObjectConversionUtility.ConvertGameObjectHierarchy(cubePrefab, World.Active);
            while (position.x < width)
            {
              while (position.y < height)
              {
                var instance = entityManager.Instantiate(entityPrefab);
                position = new Vector3(position.x, position.y + cubeSpacing, 0f);
                entityManager.SetComponentData(instance, new Translation() { Value = position });
                entityManager.SetComponentData(instance, new RotationSpeed() { Value = math.radians(UnityEngine.Random.Range(25.0f, 50.0f)) });
                position = new Vector3(position.x + cubeSpacing, 0f, 0f);
              }
            }
          }
        }
      }

这是一个非常标准的 game manager，但是让我们看最精彩的部分：首先，我们有一个属性 `entityManager`，这只是一个基本 entity manager 的引用。一个 entity manager，就像名字一样，是一个数据结构，你可以用来在 entity 上做基本的操作，比如检查 entity 是否还存活，或者创建或编辑 entity。

你不需要创建一个 entity manager，Unity 会给你提供一个。你可以在 `Start` 里看到，你只需要引用一个全局的就行。

- 是时候生成方块了，第一行很有趣：

      var entityPrefab = GameObjectConversionUtility.ConvertGameObjectHierarchy(cubePrefab, World.Active);

  有了这个，我们可以取生成的 prefab，把它转换成一个 entity。每个 MonoBehaviour 都会被转换成组件，有时候超过 1 个。我们已经知道 `RotationSpeedAuthoring` 转换成 `RotationSpeed`，但 Unity 提供了许多为 MonoBehaviour 子类的转换：
    - 每个 Transform 转换成了 Translation、Rotation 和 Scale 组件。
    - 每个 MeshRenderer 转换成 RenderMesh 组件。
- 现在，为了每个方块的位置，我们需要实例化一个新的 entity。这和我们实例化一个 GameObject 很类似，但我们在 `entityManager` 上调用 `Instantiate`，就像下面的代码一样：

      var instance = entityManager.Instantiate(entityPrefab);

- 然后我们在 entity 上设置 Translation 和 RotationSpeed 组件（先设置默认值，再更改）。

到此为止，我们有了组件，也有了实例化 entity 的方法。我们仍然缺少一个系统来实际地移动方块。我们想要一个系统使用每个 entity 的 RotationSpeed 和 Rotation 组件来让它们旋转。不仅如此，我们也想用 C# 的 Jobs，以至于让 10000 个方块并行地运行旋转。这是一个经典的模式，因此 Unity 有一个 class。

然而，我们首先需要写下我们的代码：

    public struct RotatorJob : IJobForEach<Rotation, RotationSpeed>
    {
      [ReadOnly]
      public float deltaTime;

      public void Execute(ref Rotation rotation, [ReadOnly] ref RotationSpeed rotationSpeed)
      {
        rotation.Value = math.mul(math.normalize(rotation.Value), quaternion.AxisAngle(math.up(), rotationSpeed.Value * deltaTime));
      }
    }

这和之前的 job 很相似，但有一系列不同。首先我们继承了 `IJobForEach` 而不是 `IJobParallelForTransform`，因为 entity 没有 Transform。你可能注意到我们传入两个参数给 `IJobForEach` 接口，这是我们在 job 中想要使用的组件类型。就像名字一样，Rotation 和 RotationSpeed。我们想要在那里放入任何数量的组件，重要的是我们添加了相同的组件，以相同的顺序，作为 `Execute` 的参数。

例如，如果我们继承 `IJobForEach<Rotation, RotationSpeed>`，那么 `Execute` 就会取 Rotation 和 RotationSpeed 组件作为参数；然而，如果我们继承 `IJobForEach<Scale>`，那么 `Execute` 就会只取一个参数。这表现在所有 entity 上，确认所有的 entity 都有 Rotation 和 RotationSpeed 作为参数。

最后，你可能注意到我们用一些奇怪的类型：`quaternion`，用一个小写字母 q。这是因为 Unity 为 vector 和 quaternion 在 ECS 中针对 Job 系统和组件开发了新的优化类型。

Unity.Mathematics 中还有很多类似的类型，而且它们仍在持续开发中。要获取最新信息，可以查看 Unity.Mathematics 模块文档：<https://docs.unity3d.com/Packages/com.unity.mathematics@1.0/manual/index.html>。

现在我们有一个 job，我们需要利用它的优点创造一个 system：

    public class RotationSystem : JobComponentSystem
    {
      protected override JobHandle OnUpdate(JobHandle inputDeps)
      {
        RotatorJob rotatorJob = new RotatorJob()
        {
          deltaTime = Time.deltaTime
        };
        return rotatorJob.Schedule(this, inputDeps);
      }
    }

`JobComponentSystem` 是一个用来构建可以使用 C# Job 的 system 的类。

我们首先定义一个 `RotationSystem` 类，继承自 `JobComponentSystem`。在这个类中，我们重写 `OnUpdate`（注意：是 `OnUpdate` 而不是 `Update`）方法，在其中创建一个新的 `RotatorJob` 并安排它执行。

现在，我们只需要把 `ECSJobManager` 绑定到一个空的 GameObject 上并运行应用，就能看到所有方块像往常一样旋转。经过这些改动后，我们终于达到了 100 FPS 以上！

看 Profiler，时间短到可以看到 v-sync 的小尖峰。每一帧耗时不到 10ms，这比经典非 DOTS 方案中仅脚本就消耗的时间还要少！这是一个不可思议的速度提升，而且应用的内存占用还不到原来的一半。

但猜猜看，我们还能做得更好。

## Burst 编译器

DOTS 的最后一个组件是 Burst 编译器。Burst 编译器是一个可以把 C# 的一个子集编译成优化后的本地代码的编译器。它的主要目标是编译 job，使它们尽可能快速和轻量。

很酷的是，使用 Burst 编译器极其简单。首先，你需要从 **Window | Package Manager** 安装 Burst 包。然后，唯一需要做的改变就是在 job 定义上添加 `[BurstCompile]` 特性：

    [BurstCompile]
    public struct RotatorJob : IJobForEach<Rotation, RotationSpeed>
    {
      [ReadOnly]
      public float deltaTime;

      public void Execute(ref Rotation rotation, [ReadOnly] ref RotationSpeed rotationSpeed)
      {
        rotation.Value = math.mul(math.normalize(rotation.Value), quaternion.AxisAngle(math.up(), rotationSpeed.Value * deltaTime));
      }
    }

就这些！现在 job 会用 Burst 编译，这能从我们的应用中再挤出一点性能。我们的 demo 很简单，Burst 编译的效果有限——在我的机器上可以达到 110 FPS——但对于更复杂的 job，影响会更加显著。

## 小结

DOTS 是 Unity 为推动引擎进入游戏未来所做的努力的巅峰。我坚信在未来，DOTS 将成为任何优化工作的核心组件，而随着 DOTS 变得更稳定、得到社区更多支持，这一章肯定会扩展成好几章。

不幸的是，在这个阶段，C# Job 和 ECS 仍然非常不稳定，它们的 API 变化很快，因此我不建议在大型、重要的商业游戏中使用它们。不过，我认为开始尝试它们是很重要的，这样当它们的时机到来时我们就能做好准备。

这一章只是触及了 DOTS 的表面。Job 和 ECS 中还有很多细节、配置和优化可以实现。要了解更多信息，Unity DOTS 官方主页 <https://unity.com/dots> 是你最好的朋友。

这一章实际上总结了我们能传授的所有明确旨在提升应用性能的技术。然而，优化你的工作流也同样非常有益。正如之前提到的，性能优化工作的一个恒定成本是开发时间。但是，如果你能加快开发工作流程，在繁琐的工作中节省一些时间，那么希望你就能腾出足够的时间来实际实现我们讨论过的尽可能多的优化技术。

                                                                                                                                                                                  
