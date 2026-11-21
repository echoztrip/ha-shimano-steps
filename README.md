# Shimano STEPS for Home Assistant

Read the battery percentage and motor odometer of a Shimano STEPS e-bike through Home Assistant Bluetooth. The initial test version targets the EP800 drive unit with an SC-EM800 display and an ESPHome proxy that supports active Bluetooth connections.

## Install

1. Open **Settings → Marketplace** (or HACS) and add this repository as a custom **Integration** repository.
2. Download version **0.1.0** and restart Home Assistant.
3. In **Settings → Devices & services**, configure the discovered **Shimano STEPS** device or add **Shimano STEPS** manually with the Bluetooth address of the bike's display.
4. Power on the bike or tap a non-power button on the display while it is awake. The first reading should appear in the device's **Battery** and **Odometer** sensors.

The integration listens for a fresh advertisement and opens a short connection. It takes one successful sample per advertising burst, accounting for a new burst after at least 30 seconds of silence. It keeps the last successful readings while the bike sleeps and restores them after a Home Assistant restart. Home Assistant Recorder can retain their history.

A proxy must be within Bluetooth range of the display. Disconnect any phone app that is currently using the bike's Bluetooth connection before testing. If a separate passkey entry is required, this initial release has no prompt for it. The normal sensor session reads the standard Battery Level characteristic and subscribes to Shimano's D-Fly notifications.

The EP800 and SC-EM800 transport and payload decoding were validated with a standalone probe over an ESPHome Bluetooth proxy. Support for other Shimano models is unverified.

## Protocol reference

The battery value is the standard Battery Level characteristic (`0x2A19`). The motor odometer is an unsigned little-endian count of metres in bytes 1–4 of D-Fly notification type `0x03`. The decoder follows the published protocol description independently. [Kteps protocol specification](https://github.com/indigo-dev/kteps/blob/9522888351aa85f4c425d597c03f7d35842736bc/docs/ble-protocol.md)

When reporting a problem, include the drive unit, display model, Home Assistant version, and adapter type. Redact Bluetooth addresses, network information, credentials, and actual ride data.
