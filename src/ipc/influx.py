client = None

import datetime
from pytz import timezone

def init(dsn):
    from influxdb import InfluxDBClusterClient
    global client
    client = InfluxDBClusterClient.from_DSN(dsn)

def write(title, data_y, eventId, kwds):
    if client is None:
        return
    data = [{"measurement": title,
             "tags": {},
             "time": datetime.datetime.fromtimestamp(eventId, tz=timezone('utc')),
             "fields": { "data": data_y} }]
    for key in kwds:
        print key
        data[0]["fields"][key] = kwds[key]

    client.write_points(data)