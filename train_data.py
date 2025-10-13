import re
import json
import requests
import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple

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
        if type(stop) is list:
            rv['0'] = stop[0]
        elif type(stop) is dict:
            for k in stop:
                rv[k] = stop[k]
        else:
            print(f'Unknown data type in stops: {stops}')
            
    return rv

def parse_train_schedule(html_content: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Parses the MARC train schedule HTML table into a dictionary.

    Keys are the train numbers (e.g., 'Train 613'), and values are a list of
    (station_name, scheduled_arrival_time) tuples.

    Args:
        html_content: A string containing the HTML structure of the train schedule table.

    Returns:
        A dictionary mapping train numbers to their stop schedules.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    train_schedule: Dict[str, List[Tuple[str, str]]] = {}
    
    # 1. Extract Train Numbers (Headers)
    table = soup.find('table')
    if not table:
        print("Error: Could not find the main <table> in the HTML content.")
        return train_schedule
    
    header_row = table.find('thead').find('tr')
    
    # Skip the first <th> element, which contains the "Stops" column title
    train_name_elements = header_row.find_all('th')[1:]
    
    train_names = []
    # Regex to capture "Train XXX" where XXX is the number, ignoring (R), <br>, etc.
    train_number_pattern = re.compile(r'(Train\s+\d+)')

    for th in train_name_elements:
        # Get all text content from the header, removing all tags
        text_content = th.get_text(strip=True)
        match = train_number_pattern.search(text_content)
        
        if match:
            # The full train name (e.g., 'Train 613')
            train_names.append(match.group(1).split()[1])
        else:
            # Fallback/Error handling if pattern changes
            train_names.append(f"UNKNOWN_TRAIN_{len(train_names) + 1}")

    # Initialize the schedule dictionary with train names as keys
    train_schedule = {name: [] for name in train_names}
    
    # 2. Extract Station Names and Times (Body Rows)
    body_rows = table.find('tbody').find_all('tr')
    
    for row in body_rows:
        # Get the station name from the first <th> element in the row
        station_th = row.find('th', class_='stop-name')
        if not station_th:
            continue
            
        # The station name is inside a <div> within the <th>
        station_name = station_th.get_text(strip=True)
        
        # Get all the time cells (<td> elements) in this row
        time_cells = row.find_all('td')
        
        # 3. Map Times to the corresponding Trains
        for i, time_td in enumerate(time_cells):
            if i < len(train_names):
                train_name = train_names[i]
                
                # The arrival time is usually inside a <div>
                time_div = time_td.find('div', class_='cell-width')
                arrival_time_raw = time_div.get_text(strip=True) if time_div else time_td.get_text(strip=True)

                arrival_time_raw = arrival_time_raw.replace('(R)', '').replace('(L)', '')
                
                # Clean up the arrival time, removing special characters like (L) or (R)
                # which denote notes, not part of the time itself
                arrival_time = arrival_time_raw.split('\t')[0].strip()

                if arrival_time == '--' or arrival_time == '':
                    continue
                
                # Append the (station_name, arrival_time) tuple to the correct train's list
                train_schedule[train_name].append((station_name, arrival_time))

    return train_schedule

def get_all_schedules(day):

    schedule = {}
    
    day_str = day.strftime('%m/%d/%Y')

    for direction in [0, 1]:
        for line in ['brunswick', 'penn', 'camden']:

            print(line, direction)
            timetable = requests.get(f'https://www.mta.maryland.gov/schedule/timetable/marc-{line}',
                                     params = {'direction' : str(direction),
                                               'schedule_date' : day_str})
            print(timetable)
            
            data = parse_train_schedule(timetable.text)

            schedule.update(data)
            
    for train in schedule:
        print(train)
        for stop in schedule[train]:
            print('    ', stop)
        print('-' * 50)

    return schedule

def timestamp_diff(scheduled_raw, actual_raw):
    scheduled = datetime.datetime.strptime(scheduled_raw, '%I:%M%p')
    actual = datetime.datetime.strptime(actual_raw, '%I:%M %p')

    # Train departed at / ahead of schedule
    if actual < scheduled:
        return 0
    
    delta = actual - scheduled

    minutes = delta.seconds // 60

    return minutes

def calculate_delays(schedule, actual):
    
    rv = {}
    
    # Some trains start their schedule at index 1 (e.g.: 502). Others
    # start it at index 0 (e.g.: 410). Sigh.
    if '0' in actual:
        offset = 0
    else:
        offset = 1

    for idx, (stop, stop_time) in enumerate(schedule):
        if str(idx + offset) in actual:
            delay = timestamp_diff(stop_time, actual[str(idx + offset)])
            rv[stop] = delay
        else:
            print(f'Missing data for {stop}!')
            
    return rv
    
    
if __name__ == '__main__':
    trains = get_active_trains()
    schedules = get_all_schedules(datetime.datetime.today())
    for t in trains:
        print('-' * 50)
        print(f'Train {t["train_num"]}')
        schedule = schedules[t['train_num']]
        print('Schedule')
        for each in schedule:
            print(f'\t{each}')
            
        actual = get_train_status(t['train_num'])
        print('Actual')
        for each in sorted(actual.keys()):
            print('\t', each, actual[each])
            
        delays = calculate_delays(schedule, actual)
        print('Delays')
        for each in delays:
            print('\t', each, delays[each])
        
