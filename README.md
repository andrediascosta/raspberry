# Use at Your Own Risk #


# Raspberry Pi projects

## Temperature Sensor

1. Material

- Rapb 3 B+
- DS18B20 (temperature sensor)
- 4.7k resistor

2. enable 1 wire gpio

```
$ echo "dtoverlay=w1-gpio" | sudo tee -a /boot/config.txt
$ sudo reboot
$ sudo modprobe w1-gpio
$ sudo modprobe w1-therm

```

3. Verify values

```
$ cat /sys/bus/w1/devices/28-......../w1_slave
```
