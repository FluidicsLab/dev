
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

import datetime
import os, csv, sys
import pandas as pd
import numpy as np

_measurement = sys.argv[1]
_delay = float(sys.argv[2])
_filename = sys.argv[3]

org = "hot"

root_folder = r"C:\Develop\py\FluidicsLab\Drafts\report"
config_folder = os.path.join(root_folder, "config")

store_folder = r"C:\Data\store"
data_folder = os.path.join(store_folder, "reports")

connection_file = os.path.join(config_folder, f"connection.{org}.ini")

# ---------------------------------------------------------------------------------------------------
# duration

_moving = 0

_stop = datetime.datetime.now() - datetime.timedelta(hours=_moving)
_start = _stop - datetime.timedelta(hours=_delay) - datetime.timedelta(hours=_moving)

# ---------------------------------------------------------------------------------------------------
# query

_bucket = "ed1f"

param = {
    "_start": _start,
    "_stop": _stop, 
    "_every": datetime.timedelta(seconds=1),
    "_unit": datetime.timedelta(milliseconds=1),
    "_measurement": _measurement,
    "_bucket": _bucket
}

db_query = 'from(bucket: _bucket) \
        |> range(start: _start, stop: _stop) \
        |> filter(fn: (r) => r["_measurement"] == _measurement) \
        |> filter(fn: (r) => r["_field"] == "pressure" or r["_field"] == "temperature") \
        |> aggregateWindow(every: _every, fn: mean, createEmpty: false) \
        |> pivot(rowKey: ["_time"], columnKey: ["_field","no"], valueColumn: "_value") \
        |> map(fn: (r) => ({ r with _time: int(v: r._time) })) \
        |> yield(name: _measurement)'

db_data = None
data_file = None

client = None
try:

    client = InfluxDBClient.from_config_file(connection_file)       
    db_data = client.query_api().query_csv(db_query, params=param).to_values()       
    data_file = os.path.join(data_folder, f"{_filename}")    
    with open(data_file, 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        w.writerows(db_data)

except InfluxDBError as ixe:
    print(f"ERROR(InfluxDBError) {ixe}")

except Exception as ex:
    print(f"ERROR(Exception) {ex}")

finally:
    if client is not None:
        client.close()


frame = pd.read_csv(data_file, skiprows=[0,1,2])

frame_cols = []
for col in frame.columns:
    if col == "_time" or col.startswith("pressure") or col.startswith("temperature"):
        frame_cols.append(col)

frame = frame[frame_cols]

for col in frame_cols[1:]:
    frame.loc[:,(col)] = frame.loc[:,(col)].astype(float)

pd.DataFrame.to_csv(frame, f"{data_file}", sep=";", index=None)

print(f"{data_file}")