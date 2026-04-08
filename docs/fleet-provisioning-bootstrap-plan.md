# Fleet Provisioning Bootstrap Plan

## Goal

Introduce Fleet Provisioning on top of the current MQTT-stable RX72N baseline
without losing a recoverable manual credential path during bring-up.

This document defines the initial design boundary for issue `#36`.

## Current State

Current `master` is still based on manual provisioning through the UART command
path and dataflash writes.

Observed current ownership:

- MQTT broker endpoint is written by `dataflash write aws mqttbrokerendpoint`
- Thing name is written by `dataflash write aws iotthingname`
- client certificate is written by `dataflash write aws clientcertificate`
- client private key is written by `dataflash write aws clientprivatekey`
- OTA code signer certificate is written by `dataflash write aws codesignercertificate`

That means the repository currently has:

- a manual credential/bootstrap path
- a stable MQTT validation path based on pre-generated credentials
- no in-repo Fleet Provisioning enrollment flow yet

## Design Constraints

- Keep the current custom RX72N boot path unchanged in this issue.
- Do not use Fleet Provisioning to hide unrelated layout or OTA regressions.
- Do not remove the manual dataflash write path until the Fleet Provisioning
  path is reproducible on hardware.

## Ownership Questions To Settle

Fleet Provisioning introduces three distinct ownership areas that must be made
explicit.

### 1. Bootstrap credential ownership

One bootstrap identity is needed before the device can enroll itself.

Candidate models:

- claim certificate/key embedded in the application image
- claim certificate/key stored in dataflash
- claim certificate/key injected by CI at bring-up time

Initial preference for this repository:

- keep bootstrap ownership outside the bootloader contract
- start with an application/runtime-managed bootstrap path
- preserve a manual override path while the new flow is immature

### 2. Post-enrollment runtime credential ownership

After enrollment, the repository needs a single source of truth for:

- runtime client certificate
- runtime private key
- Thing name and endpoint metadata

The likely first implementation remains dataflash-backed, because the current
runtime already reads credentials from there.

### 3. Fallback / rollback ownership

When Fleet Provisioning fails, the device must fall back to something explicit.

Required fallback rules:

- manual UART/dataflash provisioning remains supported during the initial
  Fleet Provisioning rollout
- a failed enrollment attempt must not leave the device in an ambiguous state
- the expected operator recovery path must be documented

## Proposed Introduction Sequence

### Phase 1: Design and path freeze

- document bootstrap ownership
- decide where claim credentials live
- define how enrolled credentials replace or coexist with manual credentials

### Phase 2: Host/test harness support

- add CI/test helpers that can observe enrollment attempts
- define how to provision or inject bootstrap credentials for test hardware
- keep the current manual provisioning scripts as fallback tools

### Phase 3: Hardware enrollment prototype

- implement the first enrollment path on RX72N set #2
- validate end-to-end enrollment on hardware
- confirm that post-enrollment MQTT connect / publish / subscribe still work

### Phase 4: Fallback hardening

- document recovery when enrollment fails
- decide whether manual provisioning remains a supported production path or
  becomes a lab-only escape hatch

## Exit Criteria For Issue #36

Issue `#36` is complete when:

- Fleet Provisioning enrollment is reproducible on hardware
- bootstrap credential ownership is explicit
- post-enrollment credential ownership is explicit
- rollback/fallback expectations are documented
- the manual path is either intentionally retained or intentionally retired

## Immediate Follow-up Work

The next code-bearing MR under `#36` should answer these concrete questions:

1. Where do bootstrap claim credentials live during the first implementation?
2. Which existing dataflash labels remain authoritative after enrollment?
3. How does CI distinguish bootstrap provisioning from post-enrollment runtime
   credential validation?
