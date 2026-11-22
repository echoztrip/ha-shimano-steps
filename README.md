# Shimano STEPS for Home Assistant

Read Shimano STEPS battery, motor odometer, and estimated range through Home Assistant Bluetooth. The test release targets the EP800 drive unit with an SC-EM800 display and an ESPHome proxy that supports active Bluetooth connections.

## Install

1. Open **Settings → Marketplace** (or HACS) and add this repository as a custom **Integration** repository.
2. Download the latest release and restart Home Assistant.
3. In **Settings → Devices & services**, configure the discovered **Shimano STEPS** device or add **Shimano STEPS** manually with the Bluetooth address of the bike's display.
4. Power on the bike or tap a non-power button on the display while it is awake. The first reading should appear on the **Shimano STEPS** device page.

## Ride history

Each successful sync records **Battery**, **Odometer**, **Eco range**, **Trail range**, **Boost range**, and **Last sync**. **Assist mode** is recorded when the bike sends a recognized mode during the short session. Range values are the bike's estimates in each mode at the time of sync.

**Distance since previous sync** is the difference between two consecutive odometer readings. The first sync after installing this release establishes its baseline, which survives restarts. Sync before leaving and again when you return to measure one ride. If you take several rides between syncs, the result combines their distances. A lower odometer establishes a new baseline.

The integration records snapshots within range of Home Assistant Bluetooth. Use **History** to view or export those readings. Recorder controls how long detailed history is kept. The motor odometer is marked as a cumulative total so Home Assistant can retain long-term statistics. [Home Assistant history](https://www.home-assistant.io/integrations/history/)

Positive distance changes are also saved in a local ride log that survives Recorder purges. Use **Developer tools → Actions → Shimano STEPS: Get ride log** to retrieve distances, sync timestamps, ending odometer readings, and battery percentages. A sync with no movement does not add a ride.

## Battery readings

**Battery** is the pack's state of charge at the last sync. **Battery change since previous sync** shows the net change in percentage points (`pp`). For example, a change from 60% to 48% is −12 pp. The ride log stores this change with a positive-distance record when both charge readings are known. Any charging between syncs is included in the net change.

The first sync after installing v0.3.0 establishes the charge baseline. Earlier ride entries remain available. Battery state of health, remaining capacity, and charge cycles require separate diagnostics beyond the Bluetooth Battery Level and D-Fly telemetry used here.

The integration listens for a fresh advertisement and opens a short connection. It takes one successful sample per advertising burst, accounting for a new burst after at least 30 seconds of silence. It keeps the last readings while the bike sleeps and restores them after a restart.

A proxy must be within Bluetooth range of the display. Disconnect any phone app that is currently using the bike's Bluetooth connection before testing. The standard Bluetooth Battery Level read and the Shimano D-Fly notification subscription are sufficient for displays that allow this telemetry without a passkey prompt.

The EP800 and SC-EM800 transport and payload decoding were validated with a standalone probe over an ESPHome Bluetooth proxy. Support for other Shimano models is unverified.

## Protocol reference

The battery value is the standard Battery Level characteristic (`0x2A19`). The motor odometer and range estimates come from D-Fly notification type `0x03`. Assist mode comes from notification type `0x02`. The decoder follows the published protocol description independently. [Kteps protocol specification](https://github.com/indigo-dev/kteps/blob/9522888351aa85f4c425d597c03f7d35842736bc/docs/ble-protocol.md)

When reporting a problem, include the drive unit, display model, Home Assistant version, and adapter type. Redact Bluetooth addresses, network information, credentials, and actual ride data.
