# CS2 Control System Database Introduction

> **Document note:** This document introduces the background, structure, and purpose of each table in the CS2 (Control System 2) database, intended to help team members quickly understand the database as a whole.

---

## 1. Background

### What is CS2?

CS2 (Control System 2) is the control and monitoring system for the **Bluefors dilution refrigerator**. A dilution refrigerator is an ultra-low-temperature experimental device widely used in quantum computing and low-temperature physics research, capable of cooling samples to near absolute zero (approximately 10 millikelvin, or −273.14 °C).

The CS2 system is responsible for:
- Real-time acquisition of all sensor data (temperature, pressure, flow, power, etc.)
- Control of actuators such as valves, pumps, and heaters
- Logging of system alerts and automated operation records

### Basic Database Information

| Item | Details |
|------|---------|
| Database type | PostgreSQL 14.9 |
| Backup file size | ~2.1 GB |
| Data time range | 2026-05-21 to 2026-06-12 |
| Data entries (sensor value tables only) | ~12 million+ |
| Database owner | postgres / admin |
| Data acquisition frequency | 1 sample/second (some devices) |

---

## 2. What is a Schema?

A **schema** is a named namespace within a database, analogous to a folder, used to organize and group tables.

This database uses PostgreSQL's default `public` schema — all tables live under this namespace, so the full table name format is:

```
public.table_name
```

For example: `public.alerts`, `public.device_states`

> In simple terms: the schema is just a folder called `public` that holds all the tables together.

---

## 3. Overall Database Structure

The database contains **13 core tables**, grouped into four categories:

```
CS2 Database (public schema)
│
├── [Sensor Data] — split by value type
│   ├── double_value_change_events   → floating-point (temperature, pressure, power, etc.)
│   ├── int_value_change_events      → integer values
│   ├── boolean_value_change_events  → boolean values (on/off states)
│   ├── string_value_change_events   → string states
│   └── json_value_change_events     → complex data in JSON format
│
├── [Device State]
│   ├── device_states   → latest state snapshot for each device
│   └── device_events   → record of device state-change events
│
├── [Alerts & Logs]
│   ├── alerts           → system alert records (errors/warnings)
│   └── user_log_entries → manually entered user log entries
│
└── [Automation & Control]
    ├── automation_events  → automation procedure execution records
    ├── automation_state   → current state of automation programs
    ├── core_statemachine  → core state machine
    └── flyway_schema_history → database schema migration history
```

---

## 4. Table Details

### 4.1 Sensor Value Tables (Most Critical)

Sensor data is split across 5 tables by value type; the structure is essentially the same for all of them.

#### `double_value_change_events` — Floating-Point Sensor Data

This is the largest table (12 million+ rows), storing the historical readings of all numerical sensors.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Unique identifier, auto-increment |
| `time` | timestamp with time zone | Data acquisition time |
| `mapping` | varchar(255) | Human-readable sensor name (may be null) |
| `value` | double precision | Sensor reading |
| `value_id` | varchar(255) | Unique sensor path identifier in the system |

**Key named sensors (mapping field):**

| mapping | Meaning |
|---------|---------|
| `4K_TEMPERATURE` | 4K cold stage temperature |
| `50K_TEMPERATURE` | 50K cold stage temperature |
| `MXC_TEMPERATURE` | Mixing chamber temperature (coldest point) |
| `MXC_TEMPERATURE_FAR` | Mixing chamber far-end temperature |
| `MXC_TARGET_TEMPERATURE` | Mixing chamber target setpoint |
| `STILL_TEMPERATURE` | Still temperature |
| `STILL_TARGET_TEMPERATURE` | Still target setpoint |
| `B1A_TEMPERATURE` | B1A stage temperature |
| `B2_TEMPERATURE` | B2 stage temperature |
| `P1_PRESSURE` ~ `P7_PRESSURE` | Pressure sensors P1 through P7 |
| `MXC_HEATING_POWER` | Mixing chamber heater power |
| `STILL_HEATING_POWER` | Still heater power |
| `COM_PUMP_POWER` | Compressor pump power |
| `R1A_PUMP_POWER` | R1A pump power |
| `R2_PUMP_POWER` | R2 pump power |
| `FLOW_VALUE` | Helium gas flow rate |
| `HELIUM_TANK_VALUE` | Helium tank liquid level |

**Sample data:**
```
id  | time                          | mapping           | value      | value_id
----+-------------------------------+-------------------+------------+-----------------------------
4   | 2026-05-21 11:40:20 -05:00   | STILL_TEMPERATURE | 43.683     | bftc-device-1.channels.5.temperature
13  | 2026-05-21 11:40:22 -05:00   | P1_PRESSURE       | 6.186e-09  | plc.IO.P1.fActualPressure
14  | 2026-05-21 11:40:22 -05:00   | P2_PRESSURE       | 7.850e-05  | plc.IO.P2.fActualPressure
```

#### `boolean_value_change_events` — Boolean Sensor Data

Stores on/off state-change records, such as valve positions and relay states.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Unique identifier |
| `time` | timestamp | Time of change |
| `mapping` | varchar | Human-readable name |
| `value` | boolean | true (on) / false (off) |
| `value_id` | varchar | Sensor path identifier |

#### `int_value_change_events` / `string_value_change_events` / `json_value_change_events`

Same structure as above, storing integer values, string states, and complex JSON data respectively.

---

### 4.2 `device_states` — Device Real-Time State Snapshot

Stores the **current complete state** of each device in JSON format; overwritten each time the device updates.

| Column | Type | Description |
|--------|------|-------------|
| `datetime` | timestamp | Time of state update |
| `device_id` | varchar | Unique device identifier (primary key) |
| `values` | jsonb | Full device state (JSON) |

**Device types in the system:**

| Device type | Count | Description |
|-------------|-------|-------------|
| Valve-basic | 24 | Basic valves (V104, V113, V111, V203, etc.) |
| Pfeiffer-RPT200 | 4 | Pfeiffer Pirani gauges |
| Pfeiffer-CPT200 | 2 | Pfeiffer capacitance gauges |
| Pfeiffer-MPT200 | 1 | Pfeiffer multi-function gauge |
| Pfeiffer-TC80 | 1 | Pfeiffer turbopump controller |
| Pfeiffer-TC400EC | 1 | Pfeiffer turbopump driver |
| Turbopump | 1 | Turbomolecular pump |
| Kashiyama-NeoDry | 1 | Kashiyama dry pump |
| Agilent-IDP7 / IDP3 | 1 each | Agilent oil-free scroll pumps |
| Cryomech-CPAXXXX | 1 | Cryomech pulse tube compressor |
| Pulsetube | 1 | Pulse tube refrigerator |
| TemperatureController | 1 | Temperature controller |
| Bluefors TC | 1 | Bluefors temperature control board |
| Bronkhorst-ELFlow | 1 | Mass flow controller |
| 4KHeaterRelay | 1 | 4K heater relay |
| GHSdiagnostics | 1 | Gas handling system diagnostics |
| CSState | 1 | Overall control system state |
| PLCAlarms | 1 | PLC alarm module |
| PLCRemote | 1 | PLC remote control module |
| LN2TrapLed / CoreUnitLed | 1 each | LN2 trap / core unit LED indicators |

**Sample data (single valve state):**
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

### 4.3 `device_events` — Device Event Log

Records every state-change event for each device (full historical stream).

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Unique identifier |
| `time` | timestamp | Time of event |
| `device_id` | varchar | Device identifier |
| `type` | varchar | Event type |
| `mapping` | varchar | Device mapping name |
| `values` | jsonb | Event details (JSON) |
| `correlation_id` | varchar | Correlation ID (for batched operations) |
| `created_by` | varchar | Operator |

---

### 4.4 `alerts` — System Alert Records

Records all alerts and errors generated during system operation; this is the primary reference table for the alert system.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Unique identifier |
| `code` | integer | Alert code |
| `datetime` | timestamp | Time alert was raised |
| `title` | varchar | Alert title |
| `description` | varchar | Detailed description |
| `originator` | varchar | Alert source (e.g. Sentinel) |
| `severity` | integer | Severity level (1 = warning, 2 = error) |
| `resolution_datetime` | timestamp | Resolution time (null if unresolved) |
| `resolved_by` | varchar | Person who resolved the alert |

**Sample alerts observed:**

| Code | Description | Severity |
|------|-------------|----------|
| 1608 | GHS local control activated, automation disabled | 2 (error) |
| 1608 | Manual helium tank valve not open during condensation | 1 (warning) |

---

### 4.5 `automation_events` — Automation Operation Records

Records all automated procedures executed by the CS2 system (e.g. cool-down, warm-up sequences).

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Unique identifier |
| `datetime` | timestamp | Execution time |
| `name` | varchar | Automation program name |
| `state` | varchar | Execution state |
| `start_procedure` | varchar | Starting step |
| `current_procedure` | varchar | Current step |
| `elapsed_time_seconds` | integer | Elapsed time (seconds) |
| `parameters` | jsonb | Input parameters |
| `procedures` | jsonb | Step definitions |
| `created_by` | varchar | Operator |

---

### 4.6 `automation_state` — Current Automation State

Stores the real-time state of any currently running automation program, including all current parameter values.

---

### 4.7 `user_log_entries` — Manual User Log

Records log entries manually written by operators for experiment notes and operation remarks.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Unique identifier |
| `target_datetime` | timestamp | Time the log entry refers to |
| `text` | varchar(2048) | Log content |
| `created_by` | varchar | Author |
| `created_datetime` | timestamp | Creation time |
| `updated_by` | varchar | Last editor |

---

### 4.8 `flyway_schema_history` — Database Version History

Maintained automatically by the Flyway tool; records every schema migration applied to the database, tracking the evolution of the database structure over time.

---

### 4.9 `core_statemachine` — Core State Machine

Stores the current state of the CS2 control system's core state machine, used to coordinate the operation logic of all subsystems.

---

## 5. Data Flow Overview

```
[Sensors / Actuators]
    │  sampled every second
    ▼
[CS2 Control System (separate machine at 172.31.255.23)]
    │  writes to database
    ▼
[PostgreSQL Database]
    ├── *_value_change_events  ← all value history (append-only)
    ├── device_states          ← current state (overwrite)
    ├── device_events          ← state-change events (append-only)
    └── alerts                 ← alerts (append-only)
    │
    │  [Planned] sync to local machine every 1 minute
    ▼
[Local (Raspberry Pi) PostgreSQL]
    │
    ▼
[Alert script] → detects threshold breaches → [Slack notification]
```

---

## 6. Next Steps

| Step | Task | Status |
|------|------|--------|
| 1 | Install PostgreSQL locally, import backup | Complete ✅ |
| 2 | Set up periodic sync script from source system (every 1 minute) | Pending |
| 3 | Write alert script: detect key sensor threshold breaches | Pending |
| 4 | Configure Slack Webhook to receive real-time alert notifications | Pending |

---

*Document generated: 2026-06-17*
*Data source: cs2_backup.sql (backup date: 2026-06-12)*
