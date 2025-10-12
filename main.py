import train_data
import git_helpers

import json
import datetime
import pytz

import functions_framework
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import FieldFilter 
from firebase_functions import scheduler_fn
from firebase_admin import firestore, initialize_app

NUM_SAMPLES = 30

initialize_app()
db = firestore.Client()


@scheduler_fn.on_schedule(schedule="* * * * *")
def get_train_actuals(event):
    now = datetime.datetime.now(pytz.timezone('US/Eastern'))
    base_key = now.strftime('%Y-%m-%d')
    
    running = train_data.get_active_trains()
    for t in running:
        status = train_data.get_train_status(t['train_num'])
        
        doc_ref = db.collection('actuals').document(f'{base_key}_{t["train_num"]}')

        doc_ref.set(status, merge=True)

@scheduler_fn.on_schedule(schedule="30 7 * * *",
                          secrets=['PAT_TOKEN'],
                          timeout_sec=180)
def calculate_train_delays(event):

    db_actuals = db.collection('actuals')
    db_delays = db.collection('delays')
    
    # Clean up train data that's older than 60 days
    clean_up_actuals()

    # Get yesterday's timetables
    now = datetime.datetime.now(pytz.timezone('US/Eastern'))
    yesterday = now - datetime.timedelta(days = 1)
    schedules = train_data.get_all_schedules(yesterday)
    
    # Query for all of the trains that ran yesterday
    base_key = yesterday.strftime('%Y-%m-%d')
    range_start = base_key
    range_end = range_start + '_A'

    range_start_ref = db_actuals.document(range_start)
    range_end_ref = db_actuals.document(range_end)
    print(f'Querying range: {range_start} -> {range_end}')
    
    query = db_actuals.order_by(FieldPath.document_id()) \
         .where(filter=FieldFilter(FieldPath.document_id(), '>=', range_start_ref)) \
         .where(filter=FieldFilter(FieldPath.document_id(), '<', range_end_ref))

    # For each train that ran yesterday:
    trains = query.stream()
    for t in trains:
        print(f'Working with {t.id}')
    
        train_num = t.id.split('_')[-1]

        # Get its schedule and calculate per-station delays
        if train_num not in schedules:
            print(f'Train {train_num} not found in schedule!')
            continue
        
        schedule = schedules[train_num]
        
        delay_data = t.to_dict()
        delays = train_data.calculate_delays(schedule, delay_data)
        print(f'Train {train_num} delays: {delays}')

        # Update the delays document for this train
        # The document has fields for each station; the value is an array
        # of delay durations, most recent to least recent.
        train_doc = db_delays.document(train_num)
        train_doc_meta = train_doc.get()
        if train_doc_meta.exists:
            data = train_doc_meta.to_dict()
        else:
            data = {}

        # Prepend latest observation to array and truncate
        for station in delays:
            if station not in data:
                data[station] = []
                
            data[station].insert(0, delays[station])
            if len(data[station]) > NUM_SAMPLES:
                data[station] = data[station][:NUM_SAMPLES]

        # Update the document
        train_doc.set(data)

        # Generate Markdown
        md = generate_md(schedule, train_num, data)
        
        # Push Markdown File
        created = git_helpers.push_file(f'{train_num}.md',
                                        md,
                                        f'Updating data for train {train_num}')
        if created:
            git_helpers.update_readme(train_num)
            
        git_helpers.push_file(f'data/{t.id}',
                              json.dumps(delay_data),
                              f'Uploading raw data {t.id}')
    print('All done!')
    
def generate_md(schedule, train_num, train_data):
    rv = ''
    rv += f'## Train {train_num}\n\n'
    rv += '| Station | Num Samples | Min | Max | Mean | Median |\n'
    rv += '| :-----: | :---------: | :-: | :-: | :--: | :----: |\n'

    for station, _ in schedule:
        name = station
        if station in train_data:
            count = len(train_data[station])
            minv = min(train_data[station])
            maxv = max(train_data[station])
            mean = '%.2f' % (sum(train_data[station]) / len(train_data[station]))
            median = sorted(train_data[station])[len(train_data[station])//2]
        else:
            print(f'Train {train_num} stops at {station} but we have no data!')
            count = 0
            minv = maxv = mean = median = ''
        rv += f'| {name} | {count} | {minv} | {maxv} | {mean} | {median} |\n'

    now = datetime.datetime.now(pytz.timezone('US/Eastern'))
    rv += f'\n\nLast Updated: {now.isoformat()}'
    return rv
        
def clean_up_actuals():
    db_actuals = db.collection('actuals')
    
    now = datetime.datetime.now(pytz.timezone('US/Eastern'))
    oldest = now - datetime.timedelta(days = 60)
    base_key = oldest.strftime('%Y-%m-%d')
    range_start = base_key    
    range_start_ref = db_actuals.document(range_start)
    print(f'Querying range: older than {range_start}')
    
    query = db_actuals.order_by(FieldPath.document_id()) \
           .where(filter=FieldFilter(FieldPath.document_id(), '<', range_start_ref))

    trains = query.stream()
    for t in trains:
        print(f'Deleting actuals: {t.id}')
        db_actuals.document(t.id).delete()

    print('Done cleaning up old actuals')

if __name__ == '__main__':
    calculate_train_delays(None)
    
