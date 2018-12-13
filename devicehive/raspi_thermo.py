#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import random
import datetime
import uuid

from devicehive import Handler
from devicehive import DeviceHive

#import inspect
#print(inspect.getsource(logging))

logging.basicConfig(filename='/home/pi/raspi-thermo.log', filemode='w', level=logging.INFO)
logger = logging.getLogger('logger')

SERVER_URL = os.environ.get('DEVICEHIVE_SERVER_URL') if os.environ.get('DEVICEHIVE_SERVER_URL') else 'https://playground.devicehive.com/api/rest'
SERVER_REFRESH_TOKEN = os.environ.get('DEVICEHIVE_SERVER_REFRESH_TOKEN')
DEVICE_ID = os.environ.get('DEVICEHIVE_DEVICE_ID') + '-' + hashlib.md5(SERVER_REFRESH_TOKEN.encode()).hexdigest()[0:8]
DEVICE_COORDINATES = os.environ.get('DEVICEHIVE_DEVICE_COORDINATES').split(',')
DEVICE_TYPE = os.environ.get('DEVICEHIVE_DEVICE_TYPE') if os.environ.get('DEVICEHIVE_DEVICE_TYPE') else 'Thermostats'
SI_UNITS = os.environ.get('DEVICEHIVE_SI_UNITS') if os.environ.get('DEVICEHIVE_SI_UNITS') else 'ºC'
READINGS_INTERVAL = os.environ.get('DEVICEHIVE_READINGS_INTERVAL') if os.environ.get('DEVICEHIVE_READINGS_INTERVAL') else 60*60	# in seconds
GENERATE_UNIQUE_IDS = os.environ.get('DEVICEHIVE_GENERATE_UNIQUE_IDS') if os.environ.get('DEVICEHIVE_GENERATE_UNIQUE_IDS') else False

LED_PIN = os.environ.get('DEVICEHIVE_LED_PIN') if os.environ.get('DEVICEHIVE_LED_PIN') else 17

"""

 Real or fake GPIO handler.

"""
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    class FakeGPIO(object):
        OUT = "OUT"

        def __init__(self):
            logger.info('Fake gpio initialized')

        def setup(self, io, mode):
            logger.info('Set gpio {0}; Mode: {1};'.format(io, mode))

        def output(self, io, vlaue):
            logger.info('Set gpio {0}; Value: {1};'.format(io, vlaue))

    GPIO = FakeGPIO()


"""

  Temperature sensor wrapper. Gets temperature readings from file.

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

    def __init__(self, api, device_id=DEVICE_ID):
        super(SampleHandler, self).__init__(api)
        self._device_id = device_id
        self._device = DEVICE_TYPE
        self._sensor = TempSensor()
        self._scheduler = sched.scheduler(time.time, time.sleep)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, 0)
        logger.info('DeviceId: ' + self._device_id)

    def _timer_loop(self):
	id = uuid.uuid1() if GENERATE_UNIQUE_IDS else self._device_id
        temperature = self._sensor.get_temp()
	timestamp = datetime.datetime.now()
        self._device.send_notification('temperature', parameters={
			'id': str(id),
			'device_id': self._device_id,
			'type': DEVICE_TYPE,
			'location': {
				'type': 'Point',
				'coordinates': DEVICE_COORDINATES
			},
			'properties':{
				'name': self._device_id,
				'type': DEVICE_TYPE,
				'temperature': temperature,
				'unit_of_measurement': SI_UNITS,
				'datetime': str(timestamp)
			},
			'timestamp': str(timestamp),
			'temperature': temperature
		}
	)

	logger.info('temperature => '+str(temperature))

        self._scheduler.enter(float(READINGS_INTERVAL), 60, self._timer_loop, ())

    def handle_connect(self):
	logger.info('connecting to server...'+SERVER_URL)
        self._device = self.api.put_device(self._device_id)
#        self._device.subscribe_insert_commands()
        logger.info('Connected!')

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
