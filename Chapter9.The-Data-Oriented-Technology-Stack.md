# DOTS 技术栈
最近几年，我们已经在多线程编程上见证很大的发展，原因很明显：当我们在单核上已达到了技术上的极限时，我们发现了如何有效的在硬件上利用上千核，并平行执行每段代码来获得性能上的加速
然而，从单线程编程转移到多线程编程并不简单，并不是每一个算法都可以轻易地切分成片段，即便可以，这里也有很多细节你需要注意，用来避免一些奇怪和不可预测的情况
当Unity的第一个版本发布的时候，回到2005年，多线程编程是一个期望，然而，经过14年的游戏开发的基础建设，游戏引擎需要调整自己以适应前沿技术的步伐
Unity现在经历了一系列努力来调整他的核用来掌控一个成熟的多线程世界，这个努力命名为DOTS
   
在这个章节，我们会经历DOTS的组件：
- Job系统
- Entity Component System(ECS)
- Burst编译
   
DOTS技术栈在Unity 里还是实验期，它的一些组件还在preview版本里，也就是说尽量避免在重要的项目中使用，并且它的迭代非常快。官方的ECS教程现在不可用，因为已经过时了，未来有新的发展也不奇怪，我会把在结尾放上链接 ，来了解最新的DOTS技术
   
## 多线程的问题
电子游戏有很大的多线程潜力，理论上，每个GameObject可以被当作一个独立的entity和它的自身的生命周期和计算路径。这会在有很多GameObject实例的时候显著提高你的游戏性能表现。假如处理一个GameObject的Update需要1ms，如果你有上千个类似的GameObject实例，将会消耗将近1整秒，但是如果你可以把每个GameObject的update绑定一个核，所有的Update都平行运行，那你总消耗时间就会将近1秒，提升了1000倍的效率！
   
但是，这并不简单，之前说了，你不能把每段代码轻易的和一个核绑定在一起让一切都顺利运行，一个很大的问题是多线程编程有一些风险包括：条件竞争，死锁，难以调试和处理的bug
   
条件竞争是两个以上的计算需要同一个期望顺序，但事实上顺序取决于他们是以什么顺序完成的。例如一个线程需要把1个数字加上3，另一个线程需要把它乘4，结果就完全不一样，取决于哪个操作在前。
   
死锁是一个当两个以上的线程共同争夺同一个共享资源的时候的问题，每个线程都需要一个完整的资源来完成任务，但是每个死锁都只提供一部分资源而拒绝放弃对他们的控制权，这种情况下，任何线程都不能做任何事因为他们都没有完成自己的任务。
   
基于这种情况，Unity的api是线程不安全的，意味着他们不能被不同的线程平行调用。结果，几乎所有的Unity代码在主线程运行，包括所有的GameObject和MonoBehaviour(这就是为什么如果你把一个线程锁住，你会看到Unity Editor卡死的情况了)
   
因为多线程是一个复杂的话题，我们会一步步浏览一个小例子
   
## 一个小例子
   
想象如果你有上千个相似的东西在你的场景里。这不是一个奇怪的需求，有很多合理的情况：你如果想在一个巨大的银河战斗中渲染一条船，或者你想为RTS游戏表现上千个单位，或者你想处理上千个粒子
   
为了简化，在我们的demo中，我们用10000个旋转的方块，现在开始：
   
- 每个方块有一个单独的MonoBehaviour的实例执行一个很简单的旋转方块：
    
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
    
- 现在，我们想要在场景中插入10000个方块，所以我们创建一个game manager会做以下几件事：
  - 给场景中加入10000个方块
  - 给每个方块设置一个随机的速度
  
- 所以我们创建了一个空的GameObject，我们给它绑定一个game manager的脚本如下：
        
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
     
     这个脚本用cubePrefab然后把他们投入到一个宽x高的一个矩形空间里，最关键的是SpawnCubes方法，这个方法从初始位置开始一直投入方块直到达到尽头，这是一个标准的脚本
- 现在我们可以开始运行了，你可以看到，帧率没有优化，在右上角可以看到帧率大概在22fps左右

- FPS值没有提高，然而我们打开Profiler窗口试着理解这个程序的表现
图像清晰的展示了我们占用了几乎1GB的内存，消耗45ms每帧，10ms用在脚本上，这是错的，update脚本是简单的，我们只是每帧旋转了几度而已

我们接下来可以做到更好

## Unity Job 系统

DOTS主要的可以大幅提升性能表现的特色技术板块是C# Job 系统。像其他DOTS组件一样，这个特色一直处于活跃开发状态，从2019.1版本开始公开，所以越早开始熟悉越好，它会介绍几个Unity开发者写高性能脚本的变化：

C# Job 系统可以在副线程创建很多简单的小任务去给主线程减负。C# Job 系统将会很聪明的应对平行任务，比如成百上千的AI事件或者任何可以切分成小的独立的操作的问题。当然，也可以用在多线程上表现一样好。Job 系统同样介绍了一些编译技术相比多线程用来得到一个更好的性能加速

## 一个基本的job

一个job就是一个用在单独线程的一个方法：
       
    using Unity.Collections;
    using Unity.Jobs;
    using UnityEngine;
    
    public struct SimpleJob:IJob;
    {
      //Put here a bunch of data...
      
      public float number;
      
      public NativeArray<float> data;
      
      //Write your Execute()  function.
      public void Execute()
      {
        data[0] += number;
      }
    }
 
 每个job就是一个继承了IJobinterface的接口的struct，这个struct包含了任何我们想用来执行Execute方法的参数。上面的例子中，只是给数组的第一个元素加了一个值
 
 但是，我们之前说过了，多线程是一个非常繁杂的工作，Unity提供了一些限制当你用来给job传输和接受数据的时候。基本原则是Execute方法不接受任何参数并且不能有任何返回值，所有的job需要的数据都必须拷贝在struct里，并且所有的结果也必须写在struct里
 
 事实上我们需要拷贝进struct里看起来有一个明显的限制：你不能给它传递一个MonoBehaviour的实例或一个List的引用作为参数，幸运的是，Unity提供了一个解决办法用来获取job中的共享内存：用一个容器装线程安全的wrapper

容器内包括以下：
- NativeArray:一个简单的数据的容器（和C#的基本数组一样的线程安全）
- NativeList:和NativeArray类似，但是是可变长的
- NativeHashMap：HashMap的线程安全版
- NativeMultiHashMap：和NativeHashMap类似，但是可以用多个值做key
- NativeQueue：一个先进先出的线程安全的Queue

因此，在我们的job中，我们用一个元素容量的NativeArray变量来存储输入和输出数据

现在，我们想要运行这个job，为了实现，我们用一个MonoBehaviour来初始化和运行它

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
    
在Start中，我们首先创建了一个空的NativeArray，NativeArray构造方法第一个参数是容器大小，第二个参数是Allocator。这里实际上有3中调用：
- Allocator.Temp：这是最快的，但是必须在一帧内完成，实际上，Unity强迫你在方法返回之前在数组上调用Dispose。因此我们不能用这个给jobs传参。Jobs不保证在开始后一帧内完成
- Allocator.TempJob:这个比Temp版本慢一点并且生命周期在4帧以下，这是一个给简单Job的完美方案，比如这个例子中
- Allocator.Persistent：这个是最慢的，但是它的生命周期是无限制的，这个版本你可以存持久的数据用来给job提供

在此之后，我们创建了一个SimpleJob的实例，传一个number和data作为参数，接着，我们通过Schedule方法安排好，这会返回一个JobHandle实例，可以用来控制这个job的执行，最后，我们等待这个job完成并打印结果，一切都看起来像标准的C#代码，但是job运行在一个单独的线程里

记住当一个好的C#公民，总是记得手动把用过的容器dispose掉，你不想污染内存就像你不想污染环境一样！

在此，如果你给一个空对象绑定SimpleJobRunner，你应该在控制台看看打印结果，一切都是被多线程影响的形式

## 一个更复杂的例子

投入一个job只是用来给两个数字做加法实在不能作为一个好的优化程序的例子，Unity创造job是用来多线程运行上千个繁重的任务的

因此，我们现在需要把之前的旋转的方块的例子调整一下，让他实际上是通过jobs工作的，我们的第一步是创建job，如下：
   
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
  
这个job有一点复杂，但不用担心。首先，它继承自IJobParallelForTransform，这是一个特殊的job接口用来平行运行GameObject实例的transform。你可以通过扩展Ijob来做同哟的事，但是因为这是一个非常常见的情况，Unity为我们写了大部分的代码，你可以看到，最大的区别是Execute现在有2个参数，在我们的demo中，我们想要运行一个同样的10000个方块的任务，这种情况下，参数如下：
- index代表方块的编号
- transform代表方块的transform的引用

我们的job需要2个输入
- sppeds：这是一个包含所有方块的速度，记住，我们不能拿到特定的某个GameObject的数据的引用，所以我们需要把我们所有的速度写在共享内存中，这块区域是只读的，我们不想让某个方块影响到其他方块
- deltaTime：因为job是完全的脱离Unity引擎，它不能用Time或者其他Unity的线程不安全的部分，因此我们需要自己传入deltaTime

这个Execute方法是很简单的，我们只是旋转了方块

现在我们需要给每个方块调用这个job，我们用一个game manager来做这些：

    namespace JobSystem
    {
      public slass JobCubeManager:MonoBehaviour
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
          transformAccessArray = new TransformmAccessArray(0,-1);
          speeds = new NativeList<float>(1,Allocator.Persistent);
          SpawnCubes();
        }
        
        private void SpawnCubes()
        {
          Debug.Log(String.Format("Spawing {0} cubes",(width/cubeSpacing)));
          Vector3 position = new Veotor3();
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
          if(jobHandle.IsCompleted)
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
我们一开始定义了一个数据作为经典案例，第一个属性是相同的，后面3个比较有趣：
- transformAccessArray 是一个我们会保存所有方块的transform的实例引用，这是我们job访问他们的方式
- jobHandle是一个handle我们用来查询job系统当前工作进度
- speeds是一系列随机speeds

在Start中我们只是初始化了本地的容器，我们然后投入方块，注意我们用Allocator.Persisten因为哦我们想在Start中初始化然后在剩下的时间中用相同的列表

这个SpawnCubes方法和之前的非常相似，然而，这里有2个地方不同
- 我们实例化方块之后，我们添加了它的transform和transformAccessArray
- 我们把speed放进speeds数组中用来代替方块中的旋转速度，事实上我们这个prefab不需要rotator这个组件！

现在，每帧我们需要给每个方块平行运行这些任务

我们使用和之前一样的模式，我们检查之前的任务是否完成了，我们实例化一个新job，我们设置数据，然后我们通过整个transformAccessArray安排job

如果一切都对 ，我们可以运行同样的游戏效果，但是，我们可以享受35fps

看Profiler，我们可以发现脚本的时间几乎不见了，从10ms到1ms，这是90%的提高！

然而，我们仍然有问题，我们的场景填满了10000个GameObject实例，10000个Transform,10000个MeshRenderer和10000个不同组件的拷贝，MonoBehaviour和GameObject是很重的数据结构，他们消耗了大量的cpu，我们能做的更好嘛？是的，我们可以

## 新的ECS

ECS是一个有卓越勇气的，试图重新设计Unity核心的设计，你可以想象，给基础设计模式改变不是一个简单的任务，你会问为什么？

这里有几个原因，让我们一起来看看：
- 首先，就像我们之前说的，GameObject和MonoBehaviour是很重的对象，他们携带了大量的代码和数据结构额，你将会使用很大的超出渲染需要的资源，这不是一个好的设计模型
- 其次，MonoBehaviour实例在内存中是分散的，这意味着GameObject需要在内存中寻找所有和他相关联的MonoBehaviour实例，然后依赖这些引用，这会导致2个问题：它会让缓存非常的无效，更重要的是，我们想用多线程 的时候会遇到问题，比如，使用jobs系统
- 最后，MonoBehaviour实例从代码设计上有问题，他们既存储数据又存储行为，这是一个大问题，毕竟，很多好的游戏都采用了这个设计模式，然而，在软件工程领域更常见的是分离数据（model）和算法（controller）

ECS，另一方面，从分离数据和行为来看，基于3个基本组件：
- 一个entity是由他的组件来定义的， 字面上这是0抽象
- 一个component是一个纯粹的数据，一个Health组件只包含了它的生命点，一个shield组件包含了shield的数目，一个rotation组件只包含了面向对象，等等
- 一个system定义了entity的行为，一个sysytem用一个所有entity都包含特定组件的特殊的行为，比如，MoveAndRotateEnemy可能通过Rotation，Translation和Enemy组件用来变换和旋转每个entity

一切准备就绪

## 把ECS和JObs混合

是时候给10000个旋转方块应用ECS了，在此之前，我们需要安装package
- 准备好我们的第一个组件，我们的方块需要旋转，所以我们需要一个确定的RotationSpeed,这会成为我们的组件：
    
      [Serializable]
      public struct RotationSpeed:ICompponentData
      {
        publi float Value;
      }

看，十分简单，我们说过，一个组件就是一个数据，旋转速度由一个float数代表，因此我们只需要存储一个简单的float数

你可能会问：我如何把这个组件绑定在entity上呢？我可以仍然使用inspector来设定值嘛？我之前在Unity中我喜欢的方式呢？很遗憾，组件不能被绑定在GameObject上，毕竟，GameObject不是ECS的一部分，Entity不能出现在scene而组件不能出现在inspector

幸运的是，这有一个解决办法，如果我们想要把他们保留在editor里，比如，定义一个prefab我们可以生产10000次，把GameObject-MonoBehaviour风格和ECS混合起来叫hybrid-ECS是最好的方案

- 为了激活我们的组件，我们需要写一个IConvertGameObjectToEntity声明，IConvertGameObjectToEntity是一系列代码自动转化一个标准的MonoBehaviour到一个有联系的组件：

      using System.Collections;
      using System.COllections.Generic;
      using UnityEngine;
      using Unity.Entities;
      using System;
      using Unity.Mathematics;
      
      [RequiresEntityConversion]
      public class RotationSpeedAuthoring:MonoBehaviour,IconvertGameObjectToEntity
      {
        public float rotationSpeed = 35f;
        public void Convert(Entity entity,EntityManager dstManager,GameObjectConversionSystem conversionSystem)
        {
          var data = new RotationSpeed
          {
            Value = math.radians(rotationSpeed);
          }//Convert to speed in radians
          dstManager.AddComponentData(entity,data);
        }
      }
在代码中，RotationSpeedAuthoring是一个IConvertGameObjectToEntity声明和一个MonoBehaviour（因此我们可以绑定脚本），转换的核心在于Convert这个方法，这个意义很迷惑：它过去改变了很多，并且很可能未来也再次改变，重要的是内容：这个方法取MonoBehaviour的数据，把他加到新组件上（RotationSpeed），用一些处理，最绑定到entity上
- 我们创建cubePrefab像以前一样然后增加RotationSpeedAuthoring，MonoBehaviour然后在运行时，GameObject会转化成entity
- 现在我们有一切我们需要的，我们只是需要写我们的游戏contorller

      using System;
      using UnityEngine;
      using Unity.Entities;
      using Unity.Transforms;
      using Unity.Mathematics;
      
      namespace ECSJob
      {
        public class ECSJobManager:MonoBehaviour
        {
          #region COMMON_GAME_MANAGER_DATA
          public float cubeSpacing = 0.1f;
          public int width - 10;
          public int height = 10;
          
          public GameObject cubePrefab;
          #endregion
          
          EntityManager entityManager;
          
          void Start()
          {
            entityManager = World.Active.EntityManger;
            SpawnCubes();
          }
          
          private void SpawnCubes()
          {
            int amount = Mathf.FloorToInt(width/cubeSpacing) * Mathf.FloorToInt(height/cubeSpacing);
            Debug.Log(String.Format("Spawing {0} cubes",amount));
            
            Vector3 position = new Vector3();
            
            var entityPrefab = GameObjectConversionUtility.ConvertGameObjectHierarchy(cubePrefab,World.Active);
            while(position.x < width)
            {
              while(position.y < height)
              {
                var instance = entityManager.Instantiate(entityPrefab);
                position = new Vector3(position.x,position.y+cubeSpacing,0f);
                entityManager.SetComponentData(instance,new Translation() { Value = position });
                entityManager.SetComponentData(instance,new RotationSpeed() { Value = math.radians(UntiyEngine.Random.Range(25.0f,50.0f) } );
                position = new Vector3(position.x + cubeSpacing,0f,0f);
              }
            }
          }
        }
      }
    
这是一个非常标准的game manager，但是让我们看最精彩的部分：首先，我们有一个属性entityManager，这只是一个基本entity manager的引用，一个entitymanager，就像名字一样，是一个数据结构你可以用来在entity上做基本的操作，比如检查entity是否还存货，或者创建或编辑entity

你不需要创建一个entitymanager，Unity会给你提供一个，你可以在Start里看到，你只需要引用一个全局的就行

- 是时候生成方块了，第一行很有趣：   var entityPrefab = GameObjectConversionUtility.ConvertGameObjectHierarchy(cubePrefab,World.Active);

有了这个，我们可以取我们生成的prefab，我们把它转换成一个entity，每个monobehaviour都会被转换成组件，有时候超过1个，我们已经知道RotationSpeedAuthoring转换成RotationSpeed，但是Unity提供了许多为了MonoBehaviour的子类转换：
    - 每一个Transform转换成了Translation Rotation 和Scale组件
    - 每个MeshRenderer转换成RenderMesh组件
- 现在，为了每个方块的位置，我们需要实例化一个新的entity，这和我们实例化一个GameObject很类似，但是我们在entityManager上调用Instantiate，就像下面的代码一样： var instance = entityManager.Instantiate(entityPrefab);
- 然后我们在entity上设置Translation和RotationSpeed组件（先设置默认值，再更改）

到此位置，我们有了组件，有了实例化entity得到方法，我们仍然缺少一个系统来实际的移动方块，我们想要一个系统使用每个entity荣国RotationSpeed和Rotation组件来让他们旋转，不仅如此，我们也想用C# 的jobs以至于让10000个方块平行的运行旋转，这是一个经典的模式，因此，Unity有一个class

然而，我们首先需要写下我们的代码：

    public struct RotatorJob:IJobForeach<Rotation,RotationSpeed>
    {
      [ReadOnly]
      public float deltaTime;
      
      public void Execute(ref Rotation rotation,[ReadOnly] ref RotationSpeed rotaionSpeed)
      {
        rotation.Value = math.mul(math.normalize(rotation.Value),quaternion.AxisAngle(math.up(),rotationSpeed.Value * deltaTime));
      }
    }
    
这和之前的job很相似，但是有一系列不同，首先我们继承了IJobForEachinstead的IJobParallelForTransform因为entity没有Transform，你可能注意掉我们传入两个参数给IJobForEach接口，这是我们在job中想要使用的组件的类型，就像名字一样，Rotation和RotationSpeed，我们想要在那里放入组件的任何数字，重要的是我们添加了相同的组件，以相同的顺序，作为Execute的参数

例如，如果我们继承IJobForeach<Rotation,RotationSpeed>，那么Execute就会取Rotation和RotationSpeed组件作为参数，然而，如果我们继承IJobForeach<Scale>那么Execute就会只取一个参数，这表现会用在所有entity上，确认所有的entity都有Rotation和RotationSpeed作为参数
   
最后，你可能注意我们用一些奇怪的类型：quaterion，用一个小写字母q，这是因为Unity开发出新的类型对于vector和quatrains在ECS中对于jobs系统和组件有优化

现在我们有一个job，我们需要利用它的优点创造一个组件.

                                                                                                                                                                                  
