# Chapter 2 脚本策略

## 访问组件

*   GetComponent(string) 最慢，和其他两个差2个数量级
*   GetComponent() 最快
*   GetComponent(typeof(T)) 次快
*   补充一个：在Xlua中 使用 GetComponent(typeof(CS.UnityEngine.UI.xxx) 比\
    GetComponent(“xxxx”) 只快1/4.

## 移除空回调

*   MonoBehaviour的回调，例如Awake() , Start() , Update()等。如果不使用，最好移除，特别是Update()。
*   可以用正则表达式搜索空回调，例如Update():`void\s*Update\s*?\(\s*?\)\s*?\n*?\{\n*?\s*?\}`

## 持有组件引用

*   用变量持有 GetComponent获得的组件，避免重复多次GetComponent方法调用

## 分享计算输出

*   一些复杂计算结果需要多次使用的化，使用一个变量存起来，避免多次计算

## Update，[协程](https://so.csdn.net/so/search?q=%E5%8D%8F%E7%A8%8B\&spm=1001.2101.3001.7020)和InvokeRepeating

*   Update中执行的方法，如果不是每帧必须计算，可以加入一个时间间隔。
*   协程的消耗是普通方法的三倍，并且会占用额外内存
*   InvokeRepeating 消耗的时间和协程差不多。Disable 不能停止，需要使用CancelInvoke()或者销毁GameObject

## 更快的判空检查（null checks）

*   对GameObject 或者MonoBehavior的空检查会比一般的C#对象产生更多的消耗，因为他们在内存中有两个表示，一个是用户编写的代码管理 C#代码的相同系统管理内存中，C#代码是用户编写的（托管代码），而另一个表示存在于另一个单独处理的内存空间中（本机代码）数据可以在这两个内存空间之间移动，但是每次移动都会导致额外的CPU开销和额外的内存分配。
*   使用System.Object.ReferenceEquals(), 运行速度大约是两倍



    if (!System.Object.ReferenceEquals(gameObject, null)) {
    	// do stuff with gameObject
    }

## 避免从GameObject中取出字符串属性

*   主要影响属性：tag 和 name。需要避免在性能相关的地方使用他们。
*   直接使用tag比较会照成额外的内存分配。所以Unity 提供了CompareTage()的方法。避免了本机-托管的桥接

## 使用合适的数据结构

*   避免使用Dictionary遍历，如果需要遍历最好用LIst。性能相差大。

## 避免运行时修改Transform的父节点

*   更换父节点时，需要重新根据子对象的深度分配内存，并排序。如果预分配空间不够还需要扩展缓冲区
*   越深越复杂的结构，消耗越大
*   如果确实有需求，可以在改变前通过Transform的hierachyCapacity属性来提前分配一个更大的缓冲区。

## 注意缓存Transform的变化

*   每次设置Transform的Position或者Scale 等时，会对子对象或者组件发送需要更新的消息，很多时候涉及到矩阵运算。
*   可以把改动值缓存起来，在帧的末尾去更新它。



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

## 避免使用Find（）和SendMessage（）

*   就是一个Unity的烂设计，能不用就不用。

## 禁用未使用的脚本和对象

### 通过可见性激活或者关闭GameObject

在有renderer相关的component下可以用以下两个callback控制

*   OnBecameVisible()
*   OnBecameInvisible()

需要注意：Scene Window的摄像机会影响这两个方法的触发。如果我们想在Playmode下正确的测试，需要保证Scene Window的摄像机什么都看不到，或者直接关闭Scene Window.

### 通过距离来关闭对象

*   一些物体太远了就可以关闭了
*   判断距离时，使用距离的平方来比较，性能较好，**shader中也推荐用平方判断距离**



    float distanceSqrd = (transform.position –
    other.transform.position).sqrMagnitude;
    if (distanceSqrd < (targetDistance * targetDistance)) {
     // do stuff
    }

## 最小化序列化行为

### 减少序列化对象大小

不要让一个prefab过大过深

### 异步加载对象

*   Resources.LoadAsync()
*   Adressable.LoadAssetAsync()

### 减少序列化

在内存允许情况下，将一些对象加载后缓存起来，用于以后重复实例化

### 将一些共享数据放在ScriptableObjects中

将预制件上趋向于共享的数据放到ScriptableObject 中，然后共享使用。这样避免多余的数据序列化到预制中。

### 叠加、异步加载场景

在玩家即将进入下一章节前，开启异步加载。

### 创建自定义的Update()

避免每个MonoBehaviour都使用自己的update方法。制作一个拥有Update的单例对象，把需要Update的MonoBehaviour注册进去，始大多数对象都使用一个Update()进行更新。
