import re
import json
import requests
import datetime
from bs4 import BeautifulSoup

def get_active_trains():
    url = 'https://www.mta.maryland.gov/marc-tracker/fetchvehicles'

    response = requests.get(url)

    if response.status_code != 200:
        return []

    data = json.loads(response.text)

    if 'vehicleArr' not in data or 'trains' not in data['vehicleArr']:
        return []
    
    rv = data['vehicleArr']['trains']

    for each in rv:
        each['train_num'] = each['trip_name'].split()[1]
        
    return rv

def get_train_status(train_num):
    url = f'https://www.mta.maryland.gov/marc-tracker/fetchtrips/{train_num}'

    response = requests.get(url)

    if response.status_code != 200:
        return []

    data = json.loads(response.text)

    if 'vehicleArr' not in data or 'stopevents' not in data['vehicleArr']:
        return {}
    
    stops = data['vehicleArr']['stopevents']

    # Collapse the JS array into a single dict
    rv = {}
    for stop in stops:
        for k in stop:
            rv[k] = stop[k]
            
    return rv

def get_train_schedule(train_num):
    url = f'https://www.mta.maryland.gov/marc-tracker/train/{train_num}'

    response = requests.get(url)
    
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'lxml')

    trip_info_block = soup.find(id='tripinfoblock')

    schedule = []

    trip_segments = trip_info_block.select('div.stop-route-wrapper-rt')

    for segment in trip_segments:
        station_div = segment.select_one('.row.detail-header > div:nth-child(1)')
        scheduled_time_div = segment.select_one('.row.detail-header > div:nth-child(2)')

        if station_div and scheduled_time_div:
            station_text = station_div.get_text(strip=True)
            time_text = scheduled_time_div.get_text(strip=True)
            
            schedule.append((station_text, time_text))
            
    # Remove the header row
    schedule = schedule[1:]

    return schedule

def timestamp_diff(t1, t2):
    obj1 = datetime.datetime.strptime(t1, '%I:%M %p')
    obj2 = datetime.datetime.strptime(t2, '%I:%M %p')

    # Train departed at / ahead of schedule
    if obj2 < obj1:
        return 0
    
    delta = obj2 - obj1

    minutes = delta.seconds // 60

    return minutes

def calculate_delays(schedule, actual):
    
    if len(schedule) != len(actual):
        print('Cannot calculate delays! Schedule length differs from actual!')
        return {}

    rv = {}
    for idx, (stop, stop_time) in enumerate(schedule):
        delay = timestamp_diff(stop_time, actual[str(idx + 1)])
        rv[stop] = delay

    return rv
    
    
if __name__ == '__main__':
    trains = get_active_trains()
    for t in trains:
        schedule = get_train_schedule(t['train_num'])
        actual = get_train_status(t['train_num'])
        delays = calculate_delays(schedule, actual)
        print(delays)
        
