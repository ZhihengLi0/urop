# TES 电-热微分方程与能量提取 — 信息汇总

目的:波形纵轴是**电流** I(t),不是功率。∫I dt 是电荷、不是能量。要得到事件能量,
必须用 TES 电路的微分方程把 I(t) 换算成功率 P(t) 再积分。
collection efficiency = E_abs / 10.37 keV。

参考文件(本目录):
- `Transition Edge Sensor Irwin.pdf` — Irwin & Hilton, *Transition-Edge Sensors*,
  Topics in Applied Physics 99 (2005) 63–150。第 72 页是小信号公式汇总表,
  第 74–75 页是电路图与两条微分方程,第 87–88 页是 ETF 能量推导(式 54–58)。
- `Collection Efficiency Analysis_....pdf` — CDMS wiki 导出(CUTE tower, R37 v4.0.0),
  第 2 页给出目前在用的两个近似公式 Method 1 / Method 2 及流程。

---

## 1. 电路(Irwin Fig. 2/3,与实际配置逐项吻合)

偏置电流 `Ib`(= QETbias)进入后分两路:一路经 **Rsh**(shunt),另一路经寄生电阻
**Rp** → **R_TES** → 电感 **L**。Thevenin 等效:

    V (= Vb) = Ib · Rsh
    R_L      = Rp + Rsh
    R0       = R_TES(正常态) / 2        (percentRn = 50)
    I0       = Vb / (R_L + R0)

### 常数来源(已确认)

全部在处理文件的 `detectorConfigDir/detectorConfigZip{N}` 里,**逐通道实测值**:

| 量 | 分支名 | PBS1 | PES2 |
|---|---|---|---|
| Ib (QETbias) | `qetBias` | 229.038 µA | 202.023 µA |
| Rsh | `rshunt` | 5.000 mΩ | 5.000 mΩ |
| Rp | `rp` | 14.240 mΩ | 13.645 mΩ |
| R_TES 正常态 | `rn` | 88.356 mΩ | 77.258 mΩ |
| R0 | `r0` | 44.159 mΩ | 38.935 mΩ |
| I0 | `i0` | **−18.069 µA** | −17.545 µA |
| P0 | `p0` | 1.4417e−11 W | 1.1984e−11 W |
| percentRn | `percentRn` | 50 | 50 |
| dt | `timePerBin` | 1.6 µs | 1.6 µs |
| 采样点数 | `binsPerTrace` | 32768 | 32768 |

**自洽性验证(全部通过)**
- R_L = Rp + Rsh = 19.240 mΩ
- Vb = Ib·Rsh = 1.1452 µV;事件级 RQ `PBS1vb` = −1.14519 µV(符号见 §4)
- Vb/(R_L+R0) = 18.063 µA = 配置里的 |i0| ✓
- I0²R0 = 1.442e−11 W = 配置里的 p0 ✓

## 2. ADC → 安培(已确认,精确)

增益链(`cdmsbats_config/UserSettings/BatRootSettings/analysis/configSNOLAB.R4.UMN.Addison`):

    DigitizerBinsPerVolt = 8192
    driverGain           = 8      (detectorConfig 逐通道)
    LPGain               = 4
    FBgain               = 12000  (= 2.4 匝比 × 5000 Ω 反馈电阻)

    ADC per amp = 8192 × 8 × 4 × 12000 = 3.145728e9
    1 ADC       = 3.1789e−10 A

**这个数被处理链自己确认**:事件级 RQ `PBS1gain` = `PBS1norm` = **3.145728e9**,完全一致。

用法:δI(t) = (ADC(t) − 基线ADC) / 3.145728e9;I0 取配置值(不要用基线的绝对值,
SQUID 锁定点是任意的)。实测基线 28720 ADC 与 RQ `PBS1bs` = 28715.5 一致。

## 3. 两条微分方程(Irwin 式 3、4,第 75 页)

    热:  C dT/dt = −P_bath + P_J + P          (P = 信号功率,我们要 ∫P dt)
    电:  L dI/dt = V − I·R_L − I·R_TES(T, I)

Irwin 第 72 页汇总表给出小信号解:能量脉冲的电流响应
δI(t) ∝ e^(−t/τ₊) − e^(−t/τ₋),**这正是我们双指数模板的理论出处**;
τ_el = L/(R_L + R0(1+β_I)) 是电学时间常数,τ = C/G 是热学时间常数
(对应演讲稿 Q&A 里"上升 = L/R 电学、下降 = C/G 热学"的说法)。

## 4. 符号约定(已查清)

配置里 `i0` 与事件级 `vb` **都是负值**,而原始波形的脉冲是**向上**的。
自洽的解释:电流与电压取负号约定,脉冲使 |I| 减小 → 有符号的 I 增大 →
ADC 上升。因此计算时必须用**带符号的** I0 = −18.069 µA、Vb = I0(R_L+R0) = −1.1456 µV,
配合 δI = (ADC−基线)/gain > 0。用正的 I0 会得到负能量。

## 5. 严格的能量表达式(本文档的推导)

对热方程整脉冲积分(脉冲完全衰减 ⇒ ∫C dT = 0):

    E_abs = ∫P dt = −∫δP_J dt + ∫ΔP_bath dt

用电学方程精确展开焦耳功率 P_J = I·V_TES,V_TES = V − I·R_L − L dI/dt:

    δP_J = V·δI − R_L(2 I0 δI + δI²) − L·I·dδI/dt

整脉冲积分时电感项 L[I0 δI + δI²/2] 的端点值为零(Irwin 式 57 同结论),于是

    −∫δP_J dt = I0(R_L − R0) ∫δI dt + R_L ∫δI² dt          ……(★)

★ 的线性系数 I0(R_L−R0) 与 **Irwin 式 (54)** ΔP_ETF = −I0(R0−R_L)δI 完全一致。

### 与现有三个公式的对照

| 公式 | 线性项系数 | 二次项 | 结论 |
|---|---|---|---|
| **★ 严格式** | I0(R_L−R0) | **+R_L** | 基准 |
| CollEff **Method 1**(Noah) | (2R_L/(R_L+R0) − 1)·Vb = I0(R_L−R0) ✓ | **+2R_L** | 线性项正确,二次项大 2 倍 |
| CollEff **Method 2**(Watkins) | Vb − 2I0R_L = −I0(R_L−R0) | **−R_L** | 整体差一个负号(ΔI 定义相反),二次项符号也反 |
| Irwin 式 (58) | I0R_L − V = −I0R0 | +R_L | 定义不同:它算的是 −∫V_TES δI dt,不是 −∫δP_J dt |

数值验证(PBS1,单事件):★ 与 M1 相差约 1–2%(二次项占比小),M2 = −★。

## 6. 三级修正(待做)

1. **一级**:用 ★ 的二次项 +R_L(纠正 M1 的 2 倍、M2 的符号)。
2. **二级(积分窗截断)**:实际积分在衰减 90% 处截断,电感边界项
   L[I0 δI + δI²/2] 不再为零,应从数据端点直接算出补上。**需要 L**(见 §7)。
3. **三级(bath 泄漏)**:∫ΔP_bath dt = G∫ΔT dt。ΔT 可由 R_TES(t) 反演:
   R_TES(t) = V_TES(t)/I(t),V_TES(t) = V − I·R_L − **L·dI/dt**(Irwin 式 56,
   电感项常被忽略),再经 R(T) 关系(α_I)换成 ΔT。**需要 L、α_I、G**(见 §7)。

## 7. 缺失信息

- **dIdV 拟合参数全部为空**:事件级 RQ `L`、`l`(loop gain)、`beta`、`tau0`、
  `taum`、`taup`、`p0`、`r0`、`rp`、`rsh`、`i0` 在这批处理里**全是哨兵值 −999999**,
  即 dIdV 拟合没有填。因此目前**没有** L、β_I、ℒ_I、α_I、C、G。
  配置里 `SAVE_DIDV_RQ = 1`、`DIDV_FIT_POLES = 3`,说明流程支持,只是这批没跑出来。
  → dI/dV 若能算出(用户表示可以),即可解锁二级和三级修正。
- **`Eabs` RQ 已存在但对不上**:`PBS1Eabs` 在 K 线事件上中位 263.5(疑似 eV),
  但用 ★/M1/M2 从原始波形复现时比值约 0.43 且逐事件不稳定,说明它的**积分窗
  定义与基线定义**和我们不同(CollEff 流程:前 5000 bin 定基线、积分到衰减 90%)。
  复现它需要确认这两个定义。
- **`collectionEfficiency` RQ 全为 0**(未填),`energyResolution` 同。
- **Rp 数值有分歧**:文档记录 1 mΩ(损坏后 17 mΩ),而 detectorConfig 逐通道实测
  13.6–14.2 mΩ。三者不同,需确认用哪个(直接影响 R_L 及所有公式)。

## 8. 下一步

1. 确认 Rp 用哪个值;
2. 拿到 dI/dV(或其拟合参数 L、β_I、ℒ_I、τ),补齐二级、三级修正;
3. 确认 `Eabs` 的积分窗/基线定义,复现现有 RQ 后再逐级改进;
4. 逐通道算 E_abs,求和后除以 10.37 keV 得 collection efficiency,与现有方法对比。
