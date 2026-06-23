---
layout: default
title: "Chapter 1 分析性能问题"
nav_order: 2
---

# Chapter 1 分析性能问题

## 使用Unity Profiler 获取数据

*   设备上连接profile，数据并不完全准确

    *   由于 Development 模式和连接 Unity Profiler 导致 CPU 负荷增加和内存大量增加。如果在一些大的项目中运行时，会造成内存溢出、脚本不运行、物理效果停止 Update 等情况。
    *   为了规避一些上述情况，我们要使用 benchmarking（基准化分析法）：在一些切换点，性能明显变差时关注一段时间。
    *   Editor 中的 Profiler 数据不可靠，需要在真机中使用。

## Profile 远程连接 iOS

注意：连接 iOS 设备时，Unity 必须是在 Mac 机器上运行。

1.  打包时勾选 Development Build 和 Autoconnect Profiler
2.  电脑和手机连接相同的本地 WiFi
3.  用 USB 连接手机和 Mac 电脑
4.  打包
5.  在 Unity 中打开 Profiler，然后选择 iOS 设备

如果连接还有问题，查看这里：[https:/​/​docs.​unity3d.com/​Manual/TroubleShootingIPhone.​html](https://%E2%80%8B/%E2%80%8Bdocs.%E2%80%8Bunity3d.com/%E2%80%8BManual/TroubleShootingIPhone.%E2%80%8Bhtml)

## Profile 远程连接 Android

和 iOS 相似。\
如果连接有问题，查看 Unity 官方文档的 [TroubleShootingAndroid](https://docs.unity3d.com/Manual/TroubleShootingAndroid.html) 页面。

## Deep Profile

能看到几乎所有的调用方法，但是消耗很大。

## Allocation Callstack（2019 以上）

激活 Call Stacks 按钮后，即使不开启 Deep Profile，Profiler 也会收集更多的内存分配信息。\
然后通过 Show Related Objects 按钮，我们就能看到调用堆栈了。\
![在这里插入图片描述](https://img-blog.csdnimg.cn/76a434df185840afa9ff2b4c34ed2e36.png?x-oss-process=image/watermark,type_d3F5LXplbmhlaQ,shadow_50,text_Q1NETiBARWdnYnJlYWtlcjIwNzc=,size_20,color_FFFFFF,t_70,g_se,x_16 "在这里插入图片描述")

## 性能分析 Check List

1.  验证目标脚本是否出现在场景中
2.  验证目标脚本出现的次数是否正确
3.  验证事件的正确顺序
4.  最小化正在进行的代码更改
5.  尽量减少内部干扰
6.  尽量减少外部干扰

## 自定义脚本分析

使用 `Stopwatch` 类创建计时工具：

    using System.Diagnostics;
    public class CustomTimer : IDisposable {
    private string _timerName;
    private int _numTests;
    private Stopwatch _watch;
    // give the timer a name, and a count of the
    // number of tests we're running
    public CustomTimer(string timerName, int numTests) {
    	_timerName = timerName;
    	_numTests = numTests;
    	
    	if (_numTests <= 0) {
    		_numTests = 1;
    	}
    	_watch = Stopwatch.StartNew();
    }
    	// automatically called when the 'using()' block ends
    	public void Dispose() {
    		_watch.Stop();
    		float ms = _watch.ElapsedMilliseconds;
    		UnityEngine.Debug.Log(string.Format("{0} finished: {1:0.00} " +
    		"milliseconds total, {2:0.000000} milliseconds per-test " +
    		"for {3} tests", _timerName, ms, ms / _numTests, _numTests));
    	}
    }

使用示例：

    const int numTests = 1000;
    using (new CustomTimer("My Test", numTests)) {
    	for(int i = 0; i < numTests; ++i) {
    		TestFunction();
    	}
    } // 执行完成后 timer 的 Dispose() 会被调用

