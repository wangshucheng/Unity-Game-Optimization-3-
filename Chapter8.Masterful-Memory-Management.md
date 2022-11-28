
# Chapter 5 内存管理

## 1 内存域概念

### 1.1 托管域（ Managed Domain）

这是Mono平台工作的地方，也是我们重点关注的域. C#类都在此域实例化对象，GC(垃圾回收)在此域工作。

### 1.2 本地域（ Native Domain）

Unity底层使用，主要关系内部内存空间分配。也是大多内建Unity类保存其数据的地方（Transform 和 Rigidbody组件等）。对于一般游戏开发者来说，只能间接的与此互交。

#### 托管桥

托管域也包含储存在本地域中对象描述的包装器（使得开发者在C#中访问Transform等组件的信息）。因此，当和Transform组件交互时，大多数指令会请求Unity进入它的本地代码，在哪里生成结果，然后复制结果回托管域。称之为托管桥。当两个域对相同实体有自己的描述时，跨越托管桥需要进行**上下文切换**，而这会带来很多严重的性能问题。所以需要尽可能最小化此行为。（例如在第二章讲的，不要直接访问tag，而要使用CompareTage()）

### 1.3 外部库

例如DX 和OpenGL库等，在C#中引用也会产生内存上下文切换。

## 2 GC 垃圾回收

### 2.1 垃圾回收完整周期（最坏情况）

1.  验证是否有足够的连续空间用于分配新对象
2.  如果没有足够空间，迭代所有已知的直接和间接引用，标记他们是否可达
3.  再次迭代所有这些引用，标识未标记的对象用于回收
4.  迭代所有标识对象，检查回收一些对象是否能为新对象创建足够大的连续空间。
5.  如果没有，从操作系统请求新的内存块，以便拓展堆。
6.  在新分配的块前面分配新对象，并返回给调用者。

### 2.2 回收策略

#### 2.2.1 回收时机

垃圾回收一般会自动执行。但是为了避免回收时突然性能下载打断游戏，选择在性能不敏感期进行手动垃圾回收（System.GC.Collect）。比如加载场景时和暂停游戏时。

#### 2.2.2 指定回收

一般的MonoBehaviour 或者实现了IDisposable接口类的对象。都可以通过调用Dispose()来及时释放内存。比如通过网络拉取的大数据集，在获取后可能希望立刻析构，来腾出内存空间。

#### 2.2.3 加快回收

因为垃圾回收要多次遍历所有引用对象。所以减少场景中不必要的对象，可以提升回收速度。

### 2.3 值类型和引用类型

值类型保持在栈上，释放时非常块，不会参与垃圾回收。\
引用类型在堆上，释放时会触发垃圾回收。

如果使用类的唯一目的是在程序中向某处发送数据块，且数据的持续存在时间不需要超过当前作用域，那么可以使用struct来代替class，避免垃圾回收。

但是注意，如果传递的值是极大数据集，并且多次传递。这时候因为struck在传递时会复制整个数据，而class只是传递指针。此时struck在性能表现上可能非常差（复制的开销过大）。

### 2.4 字符串

*   字符串本质是字符数组，所以是引用类型。在堆上分配内存。
*   字符串生成后，不可改变。每次拼接、修改等操作都是生成新的字符串。旧字符串如没引用则要进行垃圾回收。
*   所以尽量避免多次使用 “+” 号进行字符串拼接。每次拼接都会产生新字符串，然后丢弃之前的字符串。例如以下代码：

<!---->

    void CreateFloatingDamageText(DamageResult result) {
     string outputText = result.attacker.GetCharacterName() + "
     dealt " + result.totalDamageDealt.ToString() + " " +
     result.damageType.ToString() + " damage to " +
     result.defender.GetCharacterName() + " (" +
     result.damageBlocked.ToString() + " blocked)";
     // ...
    }

*   最终会产生多个字符串：\
    “3 blocked)”\
    " (3 blocked)"\
    “Orc (3 blocked)”\
    " damage to Orc (3 blocked)"\
    “Slashing damage to Orc (3 blocked)”\
    " Slashing damage to Orc (3 blocked)"\
    “15 Slashing damage to Orc (3 blocked)”\
    " dealt 15 Slashing damage to Orc (3 blocked)"\
    “Dwarf dealt 15 Slashing damage to Orc (3 blocked)”
*   使用sting.format() sting.Join() string.Concat() 等方法，一步完成，没有多余的字符串分配。
*   如果能够基本估计字符串的长度范围，并且此字符串变化频繁。可使用StringBuilder。并在new 时分配缓冲区。

<!---->

    using System.Text;
    // ...
    StringBuilder sb = new StringBuilder(100);
    sb.Append(result.attacker.GetCharacterName());
    sb.Append(" dealt " );
    sb.Append(result.totalDamageDealt.ToString());
    // etc.
    string result = sb.ToString();

### 2.5 装箱（Boxing）

就是C#的万物皆对象。值类型也能用system.object 表达。\
对象强制转换为system.object时就是装箱。\
但是装箱后，就会视为引用对象，导致堆分配。

所以尽量避免使用object 来作为参数传入。而多使用泛型来代替类似需求。

### 2.6 数据布局

我们希望将大量引用类型和大量值类型分开，如果结构体中有一个引用类型，那么GC将关注整个对象。放发生标记-清除时，GC必须在验证对象的所有字段。如果将不同类型分配到不同的数组中，那么GC可跳过大量数据。\
例如：

    public struct MyStruct {
    	 int myInt;
    	 float myFloat;
    	 bool myBool;
    	 string myString;
    	}
    MyStruct[] arrayOfStructs = new MyStruct[1000];

因为 myString 是引用。所以GC会迭代所有成员。\
现在改为：

    int[] myInts = new int[1000];
    float[] myFloats = new float[1000];
    bool[] myBools = new bool[1000];
    string[] myStrings = new string[1000];

那么GC只会检查字符串数组。

### 2.7 UnityAPI 中的数组

Unity API中，所有返回数组数据的指令，都会导致在堆上分配内存。\
例如：

    GetComponents<T>(); // (T[])
    Mesh.vertices; // (Vector3[])
    Camera.allCameras; // (Camera[])

所以需要避免频繁的进行此类调用。或者缓存结果。

### 2.8 Foreach 问题

foreach 在unity旧版本中会产生很不必要的堆分配。但是在2018.1之后，使用Mono4.0. 这个Bug被修复了。\
但是还是不建议在类似Update()中使用foreach。因为至少每次还是会分配一个Enumerator 对象在堆上。

### 2.9 协程

每个协程都会产生堆分配，所以要尽量避免太多的短时间协程。一些计时功能可以用一个monobehaivor 的单例实现。例如一个简单的计时器：[计时器代码](https://blog.csdn.net/zzyynn_bb/article/details/117793046)

### 使用对象池

这是个稍微复杂但对内存管理非常有效的技术，相关的技术文章很多，这里就不展开讲解了。
