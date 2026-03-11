# Phase 8b Observability Plan

## Goal

Prepare an observability path for the RX72N Envision Kit Phase 8b fleet without
blocking the current priority work on AWS connectivity, provisioning, and data ingestion.

This note exists so the project can resume dashboard work quickly after the
`MCU -> AWS IoT Core -> DynamoDB` path becomes stable on the three-device PoC.

## Current Priority

The immediate goal is still the hardware and cloud baseline:

- three main MCU devices are being assembled
- each main MCU will later control two sub MCUs
- AWS IoT Core connectivity must be stable
- DynamoDB ingestion must be stable

Dashboard work should not slow down that baseline work. Observability will be
added after the telemetry path is trustworthy.

## Reference

The current server-side monitoring design is documented in the GitLab
administration project:

- [GitLab monitoring design note](https://shelty2.servegame.com/oss/experiment/generic/devops/gitlab/-/blob/main/docs/monitoring.md)

That document is useful as the reference architecture for:

- collector + database + Grafana separation
- public / internal dashboard split
- JSON dashboard review flow
- deploy automation through Git-backed infrastructure changes

## Proposed Fleet Model

Initial PoC target:

- main MCU x 3
- sub MCU x 2 per main MCU

Logical hierarchy:

```text
main-1
├─ sub-1a
└─ sub-1b

main-2
├─ sub-2a
└─ sub-2b

main-3
├─ sub-3a
└─ sub-3b
```

The main MCU is the AWS-connected edge node. The sub MCUs are controlled through
the main MCU and should be represented as subordinate entities in telemetry and
dashboard views.

## Architecture Direction

### Observe Plane

Use Grafana only as the observe plane.

Typical path:

- MCU telemetry / events
- AWS IoT Core
- storage for query / aggregation
- Grafana dashboard

For the current PoC, `AWS IoT Core -> DynamoDB` is a reasonable first step.

### Control Plane

Do not use Grafana as the primary operator control UI.

Use a separate control plane instead:

- operator UI
- API / Lambda / backend
- AWS IoT Core
- MCU

This keeps "observe" and "operate" separated and makes auditing easier.

## Reverse Operations

Use different AWS IoT mechanisms for different control patterns.

- Device Shadow
  - desired / reported state synchronization
  - configuration changes that must survive reconnects
- MQTT command topic
  - immediate online commands
  - reboot, resync, log collection trigger
- AWS IoT Jobs
  - OTA
  - scheduled or fleet-wide rollout

## First Dashboards To Build

### 1. Fleet Overview

Start with a single fleet summary dashboard:

- online device count
- last heartbeat age
- recent error count
- firmware version distribution
- per-main-MCU health summary

### 2. Device Deep Dive

Then create a per-device dashboard:

- one main MCU
- two sub MCUs under it
- command success / failure
- response latency
- recent device events
- last known state

### 3. Command / Audit Overview

If reverse operations are added later, add an operator-facing audit view:

- issued commands
- accepted / rejected / failed
- OTA rollout status
- retry / timeout visibility

## Data To Stabilize First

Before building dashboards, make sure the project can reliably capture:

- heartbeat timestamp
- connection status
- firmware version
- error code / error count
- command result
- sub MCU result propagated through the main MCU

Without stable event semantics, dashboards will become expensive UI work with
limited operational value.

## Long-Term Storage Note

For the current PoC, DynamoDB can be enough for current state and recent event
inspection.

If the project later needs long-term, high-volume sensor trends, evaluate a
time-series-oriented storage path in addition to DynamoDB.

## Resume Trigger

Resume this observability work when the following are true:

1. the three main MCU devices are physically stable
2. AWS IoT Core connectivity is repeatable
3. DynamoDB ingestion is stable
4. the first telemetry / event schema is agreed

At that point, the next step is to define collectors or aggregation jobs and
build the first `Fleet Overview` dashboard.
