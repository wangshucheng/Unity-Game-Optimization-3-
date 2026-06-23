---
layout: default
title: "Chapter 2 脚本策略"
nav_order: 3
---

# Chapter 2 脚本策略

## 访问组件

*   `GetComponent(string)` 最慢，和其他两个相差两个数量级。
*   `GetComponent<T>()` 最快。
*   `GetComponent(typeof(T))` 次快。
*   补充：在 xLua 中使用 `GetComponent(typeof(CS.UnityEngine.UI.xxx))` 比 `GetComponent("xxxx")` 只快约 1/4。

## 移除空回调

*   MonoBehaviour 的回调，例如 `Awake()`、`Start()`、`Update()` 等，如果不使用，最好移除，特别是 `Update()`。
*   可以用正则表达式搜索空回调，例如 Update()：`void\s*Update\s*?\(\s*?\)\s*?\n*?\{\n*?\s*?\}`

## 持有组件引用

*   用变量持有 `GetComponent` 获得的组件，避免重复多次调用 `GetComponent`。

## 分享计算输出

*   一些复杂计算结果需要多次使用的话，使用一个变量存起来，避免多次计算。

## Update、[协程](https://so.csdn.net/so/search?q=%E5%8D%8F%E7%A8%8B\&spm=1001.2101.3001.7020)和 InvokeRepeating

*   Update 中执行的方法，如果不是每帧必须计算，可以加入一个时间间隔。
*   协程的消耗是普通方法的三倍，并且会占用额外内存。
*   `InvokeRepeating` 消耗的时间和协程差不多。禁用对象不能停止它，需要使用 `CancelInvoke()` 或者销毁 GameObject。

## 更快的判空检查（null checks）

*   对 GameObject 或者 MonoBehaviour 的空检查会比一般的 C# 对象产生更多消耗，因为它们在内存中有两个表示：一个是 C# 代码管理的托管表示，另一个是 Unity 引擎管理的本机表示。数据可以在这两个内存空间之间移动，但每次移动都会导致额外的 CPU 开销和内存分配。
*   使用 `System.Object.ReferenceEquals()` 进行判空，速度大约是 `== null` 的两倍。



    if (!System.Object.ReferenceEquals(gameObject, null)) {
    	// do stuff with gameObject
    }

## 避免从GameObject中取出字符串属性

*   主要影响属性：`tag` 和 `name`。需要避免在性能相关的地方使用它们。
*   直接使用 `tag` 比较会造成额外的内存分配。Unity 提供了 `CompareTag()` 方法，避免了本机-托管桥接。

## 使用合适的数据结构

*   避免遍历 Dictionary，如果需要遍历最好用 List。性能相差较大。

## 避免运行时修改 Transform 的父节点

*   更换父节点时，需要根据子对象的深度重新分配内存并排序。如果预分配空间不够，还需要扩展缓冲区。
*   越深越复杂的结构，消耗越大。
*   如果确实有需求，可以在改变前通过 Transform 的 `hierarchyCapacity` 属性提前分配一个更大的缓冲区。

## 注意缓存 Transform 的变化

*   每次设置 Transform 的 `position`、`scale` 等属性时，会向子对象或组件发送需要更新的消息，很多时候涉及矩阵运算。
*   可以把改动值缓存起来，在帧的末尾统一更新。



    private bool _positionChanged;
    private Vector3 _newPosition;
    public void SetPosition(Vector3 position) {
    	_newPosition = position;
    	_positionChanged = true;
    }
    void FixedUpdate() {
    	if (_positionChanged) {
    		transform.position = _newPosition;
    		_positionChanged = false;
    	}
    }

## 避免使用 Find() 和 SendMessage()

*   这是 Unity 的两个性能较差的设计，能不用就不用。
*   替代方案之一是为需要频繁通信的对象预存引用（在 Inspector 中拖拽赋值，或在 `Start` / `Awake` 中初始化缓存）。
*   对于大量对象间的解耦通信，可以考虑实现一个全局消息系统（Global Messaging System）：任何对象都可以注册监听特定类型的消息，发送者只需广播消息而不用关心谁在监听。这样能保持模块化和低耦合，但实现和维护成本较高，适合中大型项目。

## 禁用未使用的脚本和对象

### 通过可见性激活或关闭 GameObject

在带有 Renderer 相关组件的对象上，可以用以下两个回调控制：

*   `OnBecameVisible()`
*   `OnBecameInvisible()`

需要注意：Scene 窗口的摄像机会影响这两个方法的触发。如果想在 Play Mode 下正确测试，需要保证 Scene 窗口的摄像机什么都看不到，或者直接关闭 Scene 窗口。

### 通过距离来关闭对象

*   一些物体离得太远就可以关闭了。
*   判断距离时，使用距离的平方来比较，性能较好。**Shader 中也推荐用平方判断距离**。



    float distanceSqrd = (transform.position –
    other.transform.position).sqrMagnitude;
    if (distanceSqrd < (targetDistance * targetDistance)) {
     // do stuff
    }

## 最小化序列化行为

### 减少序列化对象大小

不要让一个 Prefab 过大过深。

### 异步加载对象

*   `Resources.LoadAsync()`
*   `Addressables.LoadAssetAsync()`

### 减少序列化

在内存允许的情况下，将一些对象加载后缓存起来，用于以后重复实例化。

### 将一些共享数据放在 ScriptableObjects 中

将预制件上趋向于共享的数据放到 ScriptableObject 中，然后共享使用。这样可以避免多余的数据序列化到预制中。

### 叠加、异步加载场景

在玩家即将进入下一章节前，开启异步加载。

### 创建自定义的 Update()

避免每个 MonoBehaviour 都使用自己的 Update 方法。可以制作一个拥有 Update 的单例对象，把需要 Update 的 MonoBehaviour 注册进去，使大多数对象都使用一个 Update() 进行更新。

示例：

```csharp
public interface IUpdateable {
    void OnUpdate(float deltaTime);
}

public class UpdateManager : MonoBehaviour {
    private static UpdateManager _instance;
    public static UpdateManager Instance {
        get {
            if (_instance == null) {
                var go = new GameObject("UpdateManager");
                _instance = go.AddComponent<UpdateManager>();
                DontDestroyOnLoad(go);
            }
            return _instance;
        }
    }

    private List<IUpdateable> _updateables = new List<IUpdateable>();

    public void Register(IUpdateable updateable) {
        if (!_updateables.Contains(updateable)) {
            _updateables.Add(updateable);
        }
    }

    public void Deregister(IUpdateable updateable) {
        _updateables.Remove(updateable);
    }

    void Update() {
        float dt = Time.deltaTime;
        for (int i = 0; i < _updateables.Count; ++i) {
            _updateables[i].OnUpdate(dt);
        }
    }
}
```

需要每帧更新的对象实现 `IUpdateable` 并注册到 `UpdateManager` 中，而不是每个对象都有自己的 `Update()`。这样可以显著减少 Unity 回调系统的开销。
