# 破晓·潮汐 音乐模式接入补丁（V9.2 → V9.3）

> 原则：**ControlMode = 0 / 1 的判定一行不动**，只在旁边加 =2 分支。
> 平滑链（TargetHeight → Height）、灯光映射（Height1↔Light1 … Height11↔Light21）全部原样保留。

---

## 改动 1 / 共 4：新增模式指示灯

**找到这段**（原第 31-34 行）：
~~~
IF ControlMode = 0 AND RunState = 1 AND StopOK = 1 AND EStopOK = 1 THEN
    ContinuousModeLamp = 1
ELSE
    ContinuousModeLamp = 0
ENDIF
~~~

**在这段之后插入**：
~~~
' —— 音乐模式（ControlMode=2）——
IF ControlMode < 0 THEN
    ControlMode = 0
ENDIF
IF ControlMode > 2 THEN
    ControlMode = 2
ENDIF
IF ControlMode = 2 AND RunState = 1 AND StopOK = 1 AND EStopOK = 1 THEN
    MusicModeLamp = 1
ELSE
    MusicModeLamp = 0
ENDIF
~~~

---

## 改动 2 / 共 4：音乐模式不跑 RunTimer（原第 80-81 行）

**找到**：
~~~
IF RunState = 1 THEN
    RunTimer = RunTimer + 1
~~~

**替换成**：
~~~
IF RunState = 1 THEN
    IF ControlMode <> 2 THEN
        RunTimer = RunTimer + 1
    ENDIF
~~~

> 为什么：40 秒一轮的计时器在音乐模式下乱跑，切回连续演出时位置就不对了。

---

## 改动 3 / 共 4：音乐模式写入目标高度

**找到这段**（原第 108-113 行）：
~~~
    TargetHeight11 = 0

    ' 场景1：环形追逐。外圈1-6依次接力，内圈7-10错位加入，中心11最后抬升。
    ' 以RunTimer/5形成每0.25秒一个节拍；相邻水柱短暂重叠，视觉更连贯。
    IF (ControlMode = 1 AND SceneSelect = 1) OR (ControlMode = 0 AND RunTimer < 250) THEN
~~~

**替换成**：
~~~
    TargetHeight11 = 0

    ' —— 音乐模式：M1..M11 由外部程序每 100ms 通过 Modbus 4区[0..10] 写入 ——
    IF ControlMode = 2 THEN
        TargetHeight1  = M1
        TargetHeight2  = M2
        TargetHeight3  = M3
        TargetHeight4  = M4
        TargetHeight5  = M5
        TargetHeight6  = M6
        TargetHeight7  = M7
        TargetHeight8  = M8
        TargetHeight9  = M9
        TargetHeight10 = M10
        TargetHeight11 = M11
    ENDIF

    ' 场景1：环形追逐。外圈1-6依次接力，内圈7-10错位加入，中心11最后抬升。
    ' 以RunTimer/5形成每0.25秒一个节拍；相邻水柱短暂重叠，视觉更连贯。
    IF ControlMode <> 2 AND ((ControlMode = 1 AND SceneSelect = 1) OR (ControlMode = 0 AND RunTimer < 250)) THEN
~~~

---

## 改动 4 / 共 4：另两个场景也加 ControlMode <> 2 包裹

**原第 160 行**：
~~~
    IF (ControlMode = 1 AND SceneSelect = 2) OR (ControlMode = 0 AND RunTimer >= 250 AND RunTimer < 600) THEN
~~~
**改成**：
~~~
    IF ControlMode <> 2 AND ((ControlMode = 1 AND SceneSelect = 2) OR (ControlMode = 0 AND RunTimer >= 250 AND RunTimer < 600)) THEN
~~~

**原第 227 行**：
~~~
    IF (ControlMode = 1 AND SceneSelect = 3) OR (ControlMode = 0 AND RunTimer >= 600) THEN
~~~
**改成**：
~~~
    IF ControlMode <> 2 AND ((ControlMode = 1 AND SceneSelect = 3) OR (ControlMode = 0 AND RunTimer >= 600)) THEN
~~~

> 为什么要包一层：三个场景块里都会**重新给 TargetHeight 赋值**。
> 不挡住的话，音乐写进去的高度会被下一行场景动画覆盖掉。

---

## 新增变量（MCGS 实时数据库）

| 变量名 | 类型 | 说明 |
|---|---|---|
| MusicModeLamp | **整数** | 音乐模式指示灯（当开关用，0/1） |
| M1 … M11 | **整数** | 各喷头目标高度 0..100，绑定 Modbus 4区 地址 0..10 |

> MCGS Pro 的对象类型只有四种：**整数 / 浮点数 / 字符串 / 组对象**（没有「数值型」「开关型」，那是旧叫法）。
> 这里全用**整数**：Modbus 4 区保持寄存器是 16 位整数，用浮点数反而要额外转换。

## Modbus 通道配置

设备窗口 → 双击「设备0」→ **增加设备通道**：

| 项 | 值 |
|---|---|
| 通道类型 | **读写**（不是「只读」） |
| 数据类型 | 16 位无符号整数 |
| 起始地址 | 0 |
| 数量 | 11 |

然后 **快速连接变量** → 依次绑到 M1..M11。

> 通道名叫「只读10001」不代表不能写。实测：写 55 能读回 55。

---

## 验证顺序

1. MCGS 里编译 → 应无错误
2. 启动运行环境（**502 端口开始监听**）
3. 跑 preview.bat 看 11 个数在动
4. 跑 run.bat 真正写进去
5. MCGS 画面里设 ControlMode = 2、RunState = 1、StopOK = 1、EStopOK = 1
6. 放音乐，看喷头跟着动

## 出问题怎么回退

ControlMode = 0 → 立刻回到原来的连续演出。
三场景判定行加了 ControlMode <> 2 之后，对 0/1 完全等价。