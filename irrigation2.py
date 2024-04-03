# Project IIS (Intelligent Irrigation System)

"""
Software Architecture:
main.py - Main program
constants.py - Constants to be used by main program
weather.py - For accessing the weather API
interface.py - Program for communicating with the User Interface
"""

from machine import Pin, ADC, Timer
import gc
import weather
import urequests
import time
import os
import network
import urequests
import json
import ujson
from constants import PLANTS
import _thread
from dht import DHT11

"""
Next Steps:
1. Calibrate sensor by getting readings of extremely dry soil
2. Water scheduling algorithm (duration, time)
3. Complete algorithm
4. Dashboard
5. Update values every 24 hours

DASHBOARD VALUES:
Every minute
1. Temperature
2. Humidity
3. Moisture Levels
4. Rain Chances

Every 24 hours
1. Growth Stage
2. Number of days past

"""

# CONSTANTS
DRY = 30710#30548#49910
WET = 19641#19893#19135#20709
RANGE = 11069#11575#11413#30775

SOIL = ADC(Pin(26))
PUMP = Pin(16, Pin.OUT)
TEMPERATURE_SENSOR = DHT11(Pin(17))
dht11 = DHT11(Pin(17))
timer = Timer(-1)

DEV_ID = '12345678'
DEV_PASS = 'admin@123'
FILE_NAME = 'data.json'
JSON_PLANT_NAME = 'PLANT_NAME'
JSON_GROWTH_STAGE = 'GROWTH_STAGE'
JSON_DAYS_FOR_NEXT_STAGE = 'DAYS_FOR_NEXT_STAGE'
JSON_TIME = 'TIME'
#SERVER_BASE_URL = "http://irrigation.great-site.net/update_data"
SERVER_BASE_URL = "http://192.168.18.108/irrigation/update_data"
STAGES = {0: 'Germination', 1: 'Vegetative', 2: 'Reproductive', 3: 'Grain-filling', 4: 'Maturation'}
FINAL_GROWTH_STAGE = 4

IRRIGATING = False
TIMESTAMP = 0
WAIT_TIME = 60 * 10  # 10 minutes

# For Recovery
if FILE_NAME in os.listdir():
    file = open(FILE_NAME, 'r+')
    data = json.load(file)
    PLANT_NAME = data[JSON_PLANT_NAME]
    GROWTH_STAGE = data[JSON_GROWTH_STAGE]
    DAYS_FOR_NEXT_STAGE = data[JSON_DAYS_FOR_NEXT_STAGE]
    TIME = data[JSON_TIME]
    file.close()
    
    time_diff_days = (time.time() - TIME) / (60 * 60 * 24) 
    
    if (time_diff_days >= 1):
        DAYS_FOR_NEXT_STAGE -= time_diff_days
        if (DAYS_FOR_NEXT_STAGE <= 0):
            while DAYS_FOR_NEXT_STAGE <= 0:
                if GROWTH_STAGE != FINAL_GROWTH_STAGE:
                    GROWTH_STAGE += 1
                    if PLANTS[PLANT_NAME][GROWTH_STAGE] == None:
                        # harvest
                        pass
                    else:
                        PLANT_UPPER, PLANT_LOWER, NEXT_STAGE = PLANTS[PLANT_NAME][GROWTH_STAGE]
                        DAYS_FOR_NEXT_STAGE += NEXT_STAGE
                else:
                    # harvest
                    pass
    else:
        Timer(-1).init(mode=Timer.ONE_SHOT, period=(time.time()-TIME)*1000, callback=update_values)
        
else:
    PLANT_NAME = 'sugarcane'
    GROWTH_STAGE = 0
    PLANT_LOWER, PLANT_UPPER, DAYS_FOR_NEXT_STAGE = PLANTS[PLANT_NAME][GROWTH_STAGE]#(60, 80)
    PLANT_AGE = 2

TOLERANCE = 5
BIASED_UPPER = PLANT_UPPER + TOLERANCE
BIASED_LOWER = PLANT_LOWER - TOLERANCE
TEMP_LOWER, TEMP_UPPER = PLANTS[PLANT_NAME]['temp']

# FUNCTIONS
def connect_to_wifi():
    SSID = 'Rafae'
    PASS = 'password'
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(SSID, PASS)
        while not sta_if.isconnected():
            pass
        
    print('network config:', sta_if.ifconfig())

def calculate_moisture(n):
    total = 0
    for i in range(0, n):
        total += SOIL.read_u16()
        time.sleep(0.01)
    return total / n

def get_moisture_percentage(moisture):
    inv_percent = (moisture - WET) / RANGE * 100
    return (100 - inv_percent)

def irrigate():
    """To water plants by starting the pump"""
    global IRRIGATING, TIMESTAMP
    PUMP.value(1)
    IRRIGATING = True
    
    moisture = calculate_moisture(10)
    percentage = get_moisture_percentage(moisture)
    print("pump on")
    while not percentage > BIASED_UPPER:
        moisture = calculate_moisture(10)
        percentage = get_moisture_percentage(moisture)
        print(percentage)
        
    PUMP.value(0)
    print("pump off")
        
    TIMESTAMP = time.time()
    
def update_values(t):
    global DAYS_FOR_NEXT_STAGE, PLANT_LOWER, PLANT_UPPER, BIASED_UPPER, BIASED_LOWER, GROWTH_STAGE
    
    DAYS_FOR_NEXT_STAGE -= 1
    if (DAYS_FOR_NEXT_STAGE == 0):
        if (GROWTH_STAGE == FINAL_GROWTH_STAGE or PLANTS[PLANT_NAME][GROWTH_STAGE+1] == None):
            # Time to harvest
            pass
        else:
            # Next growth stage of plant
            GROWTH_STAGE += 1
            PLANT_LOWER, PLANT_UPPER, DAYS_FOR_NEXT_STAGE = PLANTS[PLANT_NAME][GROWTH_STAGE]
            BIASED_LOWER, BIASED_UPPER = [PLANT_LOWER-TOLERANCE, PLANT_UPPER+TOLERANCE]
    
    log_data()
        
def log_data():
    """Log important data for system recovery incase of power failure"""
    file = open(FILE_NAME, 'w')
    data = {
        JSON_PLANT_NAME: PLANT_NAME,
        JSON_GROWTH_STAGE: GROWTH_STAGE,
        JSON_DAYS_FOR_NEXT_STAGE: DAYS_FOR_NEXT_STAGE,
        JSON_TIME: time.time()
    }
    json.dump(data, file)
    file.close()

thread_lock = _thread.allocate_lock()

def send_data():
    thread_lock.acquire()
    print('sending data')
    dht11.measure()
    temp = dht11.temperature()
    humidity = dht11.humidity()

    moisture = calculate_moisture(10)
    percentage = get_moisture_percentage(moisture)

    rain_chance = 0#get_rain_data()
    print(rain_chance)
    
    post_data = f'device-id={DEV_ID}&password={DEV_PASS}&temperature={temp}&humidity={humidity}&soil_moisture={percentage}&growth_stage={STAGES[GROWTH_STAGE]}&rain_chance={rain_chance}'
    response = urequests.post(SERVER_BASE_URL, headers = {'content-type': 'application/x-www-form-urlencoded'}, data = post_data)
    response.close()
    gc.collect()
    print(response.text)
    """
    #post_data = json.dumps({'device-id':DEV_ID, 'password':DEV_PASS, 'temperature':temp, 'humidity':humidity, 'soil_moisture':percentage, 'growth_stage':STAGES[GROWTH_STAGE], 'rain_chance':rain_chance}, separators=(', ', ':'))
    post_data = {'device-id':DEV_ID, 'password':DEV_PASS, 'temperature':temp, 'humidity':humidity, 'soil_moisture':percentage, 'growth_stage':STAGES[GROWTH_STAGE], 'rain_chance':rain_chance}
    print(post_data)
    res = urequests.post(SERVER_BASE_URL, headers = {'content-type': 'application/x-www-form-urlencoded'}, data = post_data)
    print(res.text)
    #timer.init(period=5*1000, callback=send_data)
    
    req_url = f'{SERVER_BASE_URL}?device-id={DEV_ID}&password={DEV_PASS}&temperature={temp}&humidity={humidity}&soil_moisture={percentage}&growth_stage={STAGES[GROWTH_STAGE]}&rain_chance={rain_chance}'
    res = urequests.get(req_url)
    print(res.json())
    """
    thread_lock.release()

def start_thread(t):
    _thread.start_new_thread(send_data, ())

connect_to_wifi()
#timer.init(period=5*1000, callback=start_thread)
#start_thread(0)

"""
req_url = f'{SERVER_BASE_URL}?device-id=12345678&password=admin@123&temperature=3&humidity=4&soil_moisture=3&growth_stage=Maturation&rain_chance=10'
res = urequests.get(req_url)
time.sleep_ms(650)
gc.collect()
print(res.text)
"""
# MAIN LOOP
while True:
    moisture = calculate_moisture(10)
    percentage = get_moisture_percentage(moisture)
    
    hour_of_day = time.localtime()[3]
    
    if (percentage < PLANT_LOWER and 18 < hour_of_day < 10) or (percentage < BIASED_LOWER) :
        # TODO: Log the start time
        print('irrigating')
        irrigate()
    
    elif IRRIGATING and time.time() - TIMESTAMP > WAIT_TIME:
        if percentage < PLANT_UPPER:
            print('reirrigating')
            irrigate()
        else:
            # TODO: Log the end time
            IRRIGATING = False
    
    print(percentage)
    time.sleep(0.5)