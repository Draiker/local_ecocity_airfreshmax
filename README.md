


# Eco-City AirHome for Home Assistant

## About
This custom component for Home Assistant integrates your own [Ecocity Airhome sensor](https://beegreen.com.ua/airhome-pristrij-monitoringu-jakosti-povitrja-primishhennjah-16518)  (air quality/particle sensor). 
![screenshot](https://user-images.githubusercontent.com/1454659/83942505-9add1a00-a7fc-11ea-92b2-cd33e6b3909a.png)

## Installation
### HACS
If you use [HACS](https://hacs.xyz/) you can install and update this component.
1. Go into HACS -> CUSTOM REPOSITORIES and add url: https://github.com/mykhailog/local_ecocity_airhome with type "integration"
2. Go to integration, search "airhome" and click *Install*.


### Manual
Download and unzip or clone this repository and copy `custom_components/local_ecocity_airhome/` to your configuration directory of Home Assistant, e.g. `~/.homeassistant/custom_components/`.

In the end your file structure should look like that:
```
~/.homeassistant/custom_components/local_ecocity_airhome/__init__.py
~/.homeassistant/custom_components/local_ecocity_airhome/manifest.json
~/.homeassistant/custom_components/local_ecocity_airhome/sensor.py
```

## Configuration
Create a new sensor entry in your `configuration.yaml` and adjust the host name or the ip address.

```yaml
sensor:
  - platform: local_ecocity_airhome
    host: 192.168.0.123
    name: AirHome
    monitored_conditions:
      - BME280_temperature
      - BME280_humidity
      - BME280_pressure
      - PMS_P0
      - PMS_P1
      - PMS_P2
      - CO2
```

Following sensor data can be read:

- BME280_temperature
- BME280_humidity
- BME280_pressure
- CO2
- PMS_P0
- PMS_P1
- PMS_P2

Sensor type `signal` gives the wifi signal strength of the sensor device.



## Examples

### Rounding and offset

Use [Template Sensors](https://www.home-assistant.io/integrations/template/) to round the values or to give them a offset.
```
sensor:
  - platform: template
    sensors:
      temperature:
        value_template: '{{ (states("sensor.airhome_temperature") | float) | round(1) - 2}}'
        friendly_name: 'Temperature'
        unit_of_measurement: '°C'
```



