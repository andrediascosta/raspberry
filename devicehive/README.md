# Use at Your Own Risk #


# Raspberry Pi projects

## Temperature Sensor

1. Clone project

2. Change the .env file vars according with your settings. You can find refresh token at devicehive admin.

3. Configure the service file content to the correct paths


### Service Configuration

Config service (or copy form service folder)
```
$ sudo nano /etc/systemd/system/devicehive_sensor.service
```


Start service
```
$ systemctl start devicehive_sensor
```

Enable at startup
```
$ systemctl enable devicehive_sensor
```

Logs
```
$ journalctl -fu devicehive_sensor.service
```
