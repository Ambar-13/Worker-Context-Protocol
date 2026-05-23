# MQTT-IoT-to-WCP Adapter

A bridge that exposes an MQTT-attached IoT sensor or actuator fleet as a single WCP worker.

## What MQTT is

MQTT (Message Queuing Telemetry Transport) is the dominant publish-subscribe protocol for IoT. MQTT v5.0 is the current standard; v3.1.1 is widely deployed. Most consumer and industrial IoT sensor fleets publish to an MQTT broker (Mosquitto, EMQX, HiveMQ, AWS IoT Core, Azure IoT Hub, Google Cloud IoT, etc.). MQTT covers an enormous range of devices, from $5 ESP32-based weather stations to certified medical-grade telemetry.

## What this adapter does

- Subscribes to an MQTT broker (typically the one the devices already publish to)
- Accepts WCP `sensor_read_window` tasks: subscribe to a set of named streams for a fixed window, accumulate samples, return them as `mqtt_sensor_window` evidence
- Accepts WCP `sensor_trigger_capture` tasks: publish a trigger to a named command topic, optionally collect a response
- Translates topic-map declarations into a WCP `class_extension`

## What it does NOT do

- Provision IoT devices, manage their credentials, or distribute firmware. Device lifecycle is the operator's responsibility.
- Bridge MQTT QoS or retained-message semantics into WCP. The bridge publishes at QoS 1 and does not use retain.
- Provide MQTT-over-TLS certificate management. Operators MUST configure TLS at deployment.
- Filter or sanitize payloads. The bridge applies the operator's declared `payload_schema` for decoding and otherwise forwards the value as-is. Operators MUST validate device-side payloads independently if data correctness is security-relevant.

## Files

- `bridge.py`: the WCP worker process and MQTT-to-WCP translation
- `capability.py`: builds the `class_extension` from the operator's topic map
- `__init__.py`: package marker

## Dependencies

- `asyncio-mqtt` or `paho-mqtt` (the bridge conforms to a small `MQTTClient` Protocol)

## Example topic map

```python
topic_map = {
    "device_class": "soil_moisture_fleet",
    "device_count": 24,
    "sensor_streams": [
        {
            "name": "soil_moisture_pct",
            "topic": "field/+/soil/moisture",
            "payload_schema": "scalar_float",
            "rate_hz_approx": 0.0167,  # 1/min
        },
        {
            "name": "soil_temperature_c",
            "topic": "field/+/soil/temp",
            "payload_schema": "scalar_float",
            "rate_hz_approx": 0.0167,
        },
        {
            "name": "battery_v",
            "topic": "field/+/system/battery",
            "payload_schema": "scalar_float",
            "rate_hz_approx": 0.0028,  # ~1/6min
        },
    ],
    "command_topics": [
        {"name": "request_immediate_reading",
         "topic": "field/all/cmd/read_now",
         "payload_schema": "trigger"},
    ],
}
```

A `sensor_read_window` task with `descriptor_payload = {"streams": ["soil_moisture_pct", "soil_temperature_c"], "window_seconds": 3600}` returns approximately 60 samples of each (depending on actual device publish rate and broker load).

## Payload schemas supported

| Schema | Decoded as |
|---|---|
| `scalar_float` | `float` from UTF-8 decimal |
| `scalar_int` | `int` from UTF-8 decimal |
| `scalar_bool` | `bool` (true/false/1/0/yes/no) |
| `scalar_string` | UTF-8 string |
| `json` | `application/json` parsed |
| `trigger` | the literal `"fired"` (for command-style messages) |
| (default) | hex-encoded bytes |

## Local testing

### Option A: Mosquitto + mosquitto_pub

```
# Terminal 1: broker
mosquitto -p 1883

# Terminal 2: simulate a sensor publishing once per second
while true; do
  mosquitto_pub -t 'field/12/soil/moisture' -m "$(printf '%.2f' $(echo "$RANDOM/1000" | bc -l))"
  sleep 1
done

# Terminal 3: this bridge (wired with asyncio-mqtt and the topic map above)

# Terminal 4: a WCP agent posting a sensor_read_window task
```

### Option B: unit-only

`_decode_payload`, `_matches_topic_filter`, and `topic_map_to_class_extension` are pure and testable in isolation.

## Evidence kinds produced

| Kind | Source | Notes |
|---|---|---|
| `mqtt_sensor_window` | accumulated samples from named streams over the read window | sample shape: `{t, stream, topic, value}` |
| `mqtt_capture_manifest` | (for `sensor_trigger_capture`) the published trigger + captured response | not yet exercised by the reference bridge; sketch only |

Both kinds are operator-defined; registration per RFC 0003 is required.

## Connectivity considerations

The bridge declares `connectivity_profile = "continuous"` because it runs on stable infrastructure. The underlying *devices* may be intermittent (LoRaWAN gateways, cellular sensors), but the bridge buffers nothing on the device side; samples that arrive late simply land outside the window and are dropped. Operators needing replay across device dropouts MUST configure broker-side retention or use a device-side buffer.

## See also

- `rfcs/0003-evidence-kinds-registry.md` for evidence kind registration
- `docs/limits/real-time-boundary.md` for the orchestration vs control split
- `rfcs/0029-wcp-lite.md` for the intermittent-connectivity model (when the bridge itself runs on an intermittent host)
