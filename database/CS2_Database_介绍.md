# CS2 控制系统数据库介绍

> **文件说明：** 本文档介绍 CS2（Control System 2）数据库的背景、结构与各表用途，适合团队成员快速了解数据库全貌。

---

## 一、背景介绍

### CS2 是什么？

CS2（Control System 2）是 **Bluefors 稀释制冷机** 的控制与监控系统。稀释制冷机是一种极低温实验设备，广泛用于量子计算和低温物理研究，可将样品冷却至接近绝对零度（约 10 毫开尔文，即 -273.14°C）。

CS2 系统负责：
- 实时采集所有传感器数据（温度、压力、流量、功率等）
- 控制阀门、泵、加热器等执行器
- 记录系统告警与自动化操作日志

### 数据库基本信息

| 项目 | 内容 |
|------|------|
| 数据库类型 | PostgreSQL 14.9 |
| 备份文件大小 | 约 2.1 GB |
| 数据时间范围 | 2026-05-21 至 2026-06-12 |
| 数据条目（仅传感器数值表） | 约 1,200 万条以上 |
| 数据库所有者 | postgres / admin |
| 数据采集频率 | 每秒 1 次（部分设备） |

---

## 二、什么是 Schema？

**Schema（模式）** 是数据库中的一个"命名空间"，相当于文件夹，用来组织和归类表。

本数据库使用 PostgreSQL 默认的 `public` schema，所有表都在这个命名空间下，因此表的完整名称格式为：

```
public.表名
```

例如：`public.alerts`、`public.device_states`

> 简单理解：Schema 就是把所有表放在同一个叫 `public` 的文件夹里，统一管理。

---

## 三、数据库整体结构

数据库共包含 **13 张核心表**，按功能分为四类：

```
CS2 数据库 (public schema)
│
├── 【传感器数据】按数值类型分表存储
│   ├── double_value_change_events   → 浮点数（温度、压力、功率等）
│   ├── int_value_change_events      → 整数值
│   ├── boolean_value_change_events  → 布尔值（开/关状态）
│   ├── string_value_change_events   → 字符串状态
│   └── json_value_change_events     → JSON 格式复杂数据
│
├── 【设备状态】
│   ├── device_states   → 每台设备当前最新状态快照
│   └── device_events   → 设备状态变化事件记录
│
├── 【告警与日志】
│   ├── alerts           → 系统告警记录（错误/警告）
│   └── user_log_entries → 用户手动日志记录
│
└── 【自动化控制】
    ├── automation_events  → 自动化操作执行记录
    ├── automation_state   → 自动化程序当前状态
    ├── core_statemachine  → 核心状态机
    └── flyway_schema_history → 数据库版本迁移历史
```

---

## 四、各表详细说明

### 4.1 传感器数值表（最核心）

传感器数据根据数值类型拆分为 5 张表，结构基本相同：

#### `double_value_change_events` — 浮点型传感器数据

这是数据量最大的表（超过 1,200 万条），存储所有数值型传感器的历史读数。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | bigint | 唯一标识，自增 |
| `time` | timestamp with time zone | 数据采集时间 |
| `mapping` | varchar(255) | 传感器友好名称（可为空） |
| `value` | double precision | 传感器数值 |
| `value_id` | varchar(255) | 传感器在系统中的唯一路径标识 |

**已命名的关键传感器（mapping 字段）：**

| mapping 名称 | 含义 |
|-------------|------|
| `4K_TEMPERATURE` | 4K 冷台温度 |
| `50K_TEMPERATURE` | 50K 冷台温度 |
| `MXC_TEMPERATURE` | 混合室（Mixing Chamber）温度（最冷端） |
| `MXC_TEMPERATURE_FAR` | 混合室远端温度 |
| `MXC_TARGET_TEMPERATURE` | 混合室目标设定温度 |
| `STILL_TEMPERATURE` | 蒸馏器（Still）温度 |
| `STILL_TARGET_TEMPERATURE` | 蒸馏器目标温度 |
| `B1A_TEMPERATURE` | B1A 级温度 |
| `B2_TEMPERATURE` | B2 级温度 |
| `P1_PRESSURE` ~ `P7_PRESSURE` | 各路压力传感器（P1 至 P7） |
| `MXC_HEATING_POWER` | 混合室加热功率 |
| `STILL_HEATING_POWER` | 蒸馏器加热功率 |
| `COM_PUMP_POWER` | 压缩泵功率 |
| `R1A_PUMP_POWER` | R1A 泵功率 |
| `R2_PUMP_POWER` | R2 泵功率 |
| `FLOW_VALUE` | 氦气流量 |
| `HELIUM_TANK_VALUE` | 氦气储罐液位 |

**数据示例：**
```
id  | time                          | mapping          | value       | value_id
----+-------------------------------+------------------+-------------+-----------------------------
4   | 2026-05-21 11:40:20 -05:00   | STILL_TEMPERATURE| 43.683      | bftc-device-1.channels.5.temperature
13  | 2026-05-21 11:40:22 -05:00   | P1_PRESSURE      | 6.186e-09   | plc.IO.P1.fActualPressure
14  | 2026-05-21 11:40:22 -05:00   | P2_PRESSURE      | 7.850e-05   | plc.IO.P2.fActualPressure
```

#### `boolean_value_change_events` — 布尔型传感器数据

存储开/关状态变化记录，例如阀门开关、继电器状态。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | bigint | 唯一标识 |
| `time` | timestamp | 变化时间 |
| `mapping` | varchar | 友好名称 |
| `value` | boolean | true（开）/ false（关） |
| `value_id` | varchar | 传感器路径标识 |

#### `int_value_change_events` / `string_value_change_events` / `json_value_change_events`

结构与上面相同，分别存储整数值、字符串状态和 JSON 格式复杂数据。

---

### 4.2 `device_states` — 设备实时状态快照

存储每台设备的**当前最新完整状态**（JSON 格式），每次设备有更新时覆盖写入。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `datetime` | timestamp | 状态更新时间 |
| `device_id` | varchar | 设备唯一标识（主键） |
| `values` | jsonb | 设备完整状态（JSON） |

**系统中的设备类型：**

| 设备类型 | 数量 | 说明 |
|---------|------|------|
| Valve-basic | 24 台 | 基本阀门（V104、V113、V111、V203 等） |
| Pfeiffer-RPT200 | 4 台 | Pfeiffer 皮拉尼规（压力计） |
| Pfeiffer-CPT200 | 2 台 | Pfeiffer 电容薄膜规 |
| Pfeiffer-MPT200 | 1 台 | Pfeiffer 多功能压力计 |
| Pfeiffer-TC80 | 1 台 | Pfeiffer 涡轮泵控制器 |
| Pfeiffer-TC400EC | 1 台 | Pfeiffer 涡轮泵驱动器 |
| Turbopump | 1 台 | 涡轮分子泵 |
| Kashiyama-NeoDry | 1 台 | Kashiyama 干式泵 |
| Agilent-IDP7 / IDP3 | 各 1 台 | Agilent 无油涡旋泵 |
| Cryomech-CPAXXXX | 1 台 | Cryomech 脉管制冷机压缩机 |
| Pulsetube | 1 台 | 脉管制冷机 |
| TemperatureController | 1 台 | 温度控制器 |
| Bluefors TC | 1 台 | Bluefors 温度控制板卡 |
| Bronkhorst-ELFlow | 1 台 | 质量流量控制器 |
| 4KHeaterRelay | 1 台 | 4K 加热继电器 |
| GHSdiagnostics | 1 台 | 气体处理系统诊断 |
| CSState | 1 台 | 控制系统整体状态 |
| PLCAlarms | 1 台 | PLC 告警模块 |
| PLCRemote | 1 台 | PLC 远程控制模块 |
| LN2TrapLed / CoreUnitLed | 各 1 台 | 液氮捕获/核心单元 LED 指示 |

**数据示例（单台阀门状态）：**
```json
{
  "device_id": "plc.ValveGroup.V104",
  "values": {
    "host": "172.31.255.23",
    "port": 4840,
    "valveOnOff": false,
    "execStatus": true,
    "driverState": "RUNNING",
    "instrumentInfo": {
      "name": "V104",
      "type": "Valve-basic"
    }
  }
}
```

---

### 4.3 `device_events` — 设备事件记录

记录设备状态**变化的每一个事件**（历史流水）。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | bigint | 唯一标识 |
| `time` | timestamp | 事件发生时间 |
| `device_id` | varchar | 设备标识 |
| `type` | varchar | 事件类型 |
| `mapping` | varchar | 设备映射名 |
| `values` | jsonb | 事件详情（JSON） |
| `correlation_id` | varchar | 关联 ID（同一批次操作） |
| `created_by` | varchar | 操作人 |

---

### 4.4 `alerts` — 系统告警记录

记录系统运行中产生的所有**告警和错误**，是预警系统的核心参考表。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | bigint | 唯一标识 |
| `code` | integer | 告警代码 |
| `datetime` | timestamp | 告警发生时间 |
| `title` | varchar | 告警标题 |
| `description` | varchar | 详细描述 |
| `originator` | varchar | 告警来源（如 Sentinel） |
| `severity` | integer | 严重程度（1=警告，2=错误） |
| `resolution_datetime` | timestamp | 解决时间（未解决则为空） |
| `resolved_by` | varchar | 解决人 |

**已出现的告警示例：**

| 告警码 | 描述 | 严重程度 |
|--------|------|---------|
| 1608 | GHS 本地控制激活，自动化已禁用 | 2（错误） |
| 1608 | 氦气冷凝时储罐手动阀门未打开 | 1（警告） |

---

### 4.5 `automation_events` — 自动化操作记录

记录 CS2 系统执行的所有**自动化流程**（如冷却程序、预热程序等）。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | bigint | 唯一标识 |
| `datetime` | timestamp | 操作时间 |
| `name` | varchar | 自动化程序名称 |
| `state` | varchar | 执行状态 |
| `start_procedure` | varchar | 起始步骤 |
| `current_procedure` | varchar | 当前步骤 |
| `elapsed_time_seconds` | integer | 已执行时长（秒） |
| `parameters` | jsonb | 输入参数 |
| `procedures` | jsonb | 步骤定义 |
| `created_by` | varchar | 执行人 |

---

### 4.6 `automation_state` — 自动化当前状态

存储当前正在运行的自动化程序的**实时状态**，包含所有参数的当前值。

---

### 4.7 `user_log_entries` — 用户手动日志

记录操作人员手动写入的日志条目，用于记录实验笔记、操作备注等。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | bigint | 唯一标识 |
| `target_datetime` | timestamp | 日志对应的时间点 |
| `text` | varchar(2048) | 日志内容 |
| `created_by` | varchar | 创建人 |
| `created_datetime` | timestamp | 创建时间 |
| `updated_by` | varchar | 最后修改人 |

---

### 4.8 `flyway_schema_history` — 数据库版本历史

由 Flyway 工具自动维护，记录数据库结构的每一次版本升级历史，用于追踪数据库 Schema 的演变。

---

### 4.9 `core_statemachine` — 核心状态机

存储 CS2 控制系统核心状态机的当前状态，用于协调各子系统的运行逻辑。

---

## 五、数据流向示意

```
【传感器/执行器】
    │  每秒采集
    ▼
【CS2 控制系统（另一台电脑 172.31.255.23）】
    │  写入数据库
    ▼
【PostgreSQL 数据库】
    ├── *_value_change_events  ← 所有数值历史（追加写入）
    ├── device_states          ← 当前状态（覆盖写入）
    ├── device_events          ← 状态变化事件（追加写入）
    └── alerts                 ← 告警（追加写入）
    │
    │  【计划】每1分钟同步到本机
    ▼
【本机（树莓派）PostgreSQL】
    │
    ▼
【预警脚本】→ 检测阈值超限 → 【Slack 通知】
```

---

## 六、下一步计划

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | 本机安装 PostgreSQL，导入备份文件 | 待完成 |
| 2 | 建立与源系统的定时同步脚本（每1分钟） | 待完成 |
| 3 | 编写预警脚本：检测关键传感器超限 | 待完成 |
| 4 | 配置 Slack Webhook，接收实时告警通知 | 待完成 |

---

*文档生成时间：2026-06-17*
*数据来源：cs2_backup.sql（备份时间：2026-06-12）*
