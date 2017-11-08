import datetime
import Queue
import threading
import time
import traceback
from pytz import timezone

client = None
queue = None
thread = None

def init(dsn):
    from influxdb import InfluxDBClient
    global client
    global thread
    global queue
    print "Initing InfluxDB"
    client = InfluxDBClient.from_dsn(dsn)
    print dsn
    print "Inited InfluxDB"
    queue = Queue.Queue(10000)
    thread = threading.Thread(target = influxWorker)
    thread.start()

def influxWorker():
    while True:
        data = []
        # Loop over all events, if at least one is queued, do not block at next poll,
        # i.e. grab all events there are and then send them
        block = True
        try:
            while True:
                data.append(queue.get(block))
                block = False 
        except Queue.Empty:
            pass

        try:
            client.write_points(data)
        except:
            traceback.print_exc()
        # Explicit sleep to encourage multi-event writes and (hopefully) always keep the
        # InfluxDB backend respsonsive for visualization queries
        time.sleep(0.05) 

def write(title, data_y, eventId, kwds):
    if client is None:
        return
    data = {"measurement": title,
             "tags": {},
             "time": datetime.datetime.fromtimestamp(eventId, tz=timezone('utc')),
             "fields": { "data": data_y} }
    for key in kwds:
        data["fields"][key] = kwds[key]
    
    queue.put(data)
