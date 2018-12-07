# Copyright (C) 2018 DataArt
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

# This file was adapted form devicehive examples site
import os
import glob
import hashlib
import sched
import time
import threading
import logging

from devicehive import Handler
from devicehive import DeviceHive

import inspect
#print(inspect.getsource(logging))

logging.basicConfig()
logger = logging.getLogger('logger')


#http://playground.devicehive.com/api/rest
SERVER_URL = os.environ.get('DEVICEHIVE_SERVER_URL')
SERVER_REFRESH_TOKEN = os.environ.get('DEVICEHIVE_SERVER_REFRESH_TOKEN')

logger.info('connecting to server...')
logger.info(SERVER_URL)

print(SERVER_REFRESH_TOKEN)

logger.info(hashlib.md5(SERVER_REFRESH_TOKEN.encode()))

DEVICE_ID = 'raspi-thermo-' + hashlib.md5(SERVER_REFRESH_TOKEN.encode()).hexdigest()[0:8]
LED_PIN = 17


''' Real or fake GPIO handler.
'''
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    class FakeGPIO(object):
        OUT = "OUT"

        def __init__(self):
            logger.warn('Fake gpio initialized')

        def setup(self, io, mode):
            logger.warn('Set gpio {0}; Mode: {1};'.format(io, mode))

        def output(self, io, vlaue):
            logger.warn('Set gpio {0}; Value: {1};'.format(io, vlaue))

    GPIO = FakeGPIO()


"""
Temperature sensor wrapper. Gets temperature readings form file.
"""
class TempSensor(object):
    def __init__(self):
        files = glob.glob('/sys/bus/w1/devices/28-*/w1_slave')
        if len(files) > 0:
            self.file_name = files[0]
        else:
            self.file_name = None
        self.last_good_temp = 0.0

    def get_temp(self):
        if self.file_name is None:
            return self.last_good_temp
        with open(self.file_name) as f:
            content = f.readlines()
            for line in content:
                # sometimes CRC is bad, so we will return last known good temp
                if line.find('crc=') >= 0 and line.find('NO') >= 0:
                    return self.last_good_temp
                p = line.find('t=')
                if p >= 0:
                    self.last_good_temp = float(line[p+2:]) / 1000.0
                    return self.last_good_temp
        return self.last_good_temp


class SampleHandler(Handler):
    INTERVAL_SECONDS = 5*60
    COORDINATES = {'lat': 40.20328995345767, 'lng': -8.4270206263202}
    UNITS = 'c'
    DEVICE_TYPE = 'Thermostats'

    def __init__(self, api, device_id=DEVICE_ID):
        super(SampleHandler, self).__init__(api)
        self._device_id = device_id
        self._device = self.DEVICE_TYPE #None
        self._sensor = TempSensor()
        self._scheduler = sched.scheduler(time.time, time.sleep)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, 0)
        logger.info('DeviceId: ' + self._device_id)

    def _timer_loop(self):
        t = self._sensor.get_temp()
        self._device.send_notification('temperature', parameters={
			'id': DEVICE_ID,
			'coordinates': self.COORDINATES,
			'parameters': {'type': self.DEVICE_TYPE, 'value': t, 'units': self.UNITS}
		}
	)
        self._scheduler.enter(self.INTERVAL_SECONDS, 1, self._timer_loop, ())

    def handle_connect(self):
        self._device = self.api.put_device(self._device_id)
        self._device.subscribe_insert_commands()
        logger.warn('Connected')
        self._timer_loop()
        t = threading.Thread(target=self._scheduler.run)
        t.setDaemon(True)
        t.start()

    def handle_command_insert(self, command):
        if command.command == 'led/on':
            GPIO.output(LED_PIN, 1)
            command.status = "Ok"
        elif command.command == 'led/off':
            GPIO.output(LED_PIN, 0)
            command.status = "Ok"
        else:
            command.status = "Unknown command"
        command.save()


dh = DeviceHive(SampleHandler)
dh.connect(SERVER_URL, refresh_token=SERVER_REFRESH_TOKEN)
