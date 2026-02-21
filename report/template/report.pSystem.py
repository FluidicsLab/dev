from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

import datetime
import os, csv, sys
import pandas as pd
import numpy as np

_delay = float(sys.argv[1])
_filename = sys.argv[2]

root_folder = r"C:\Develop\py\FluidicsLab\Drafts\report"
config_folder = os.path.join(root_folder, "config")

store_folder = r"C:\Data\store"
data_folder = os.path.join(store_folder, "reports")

query_file = os.path.join(root_folder, "queries", "report.pSystem.flux")

# ---------------------------------------------------------------------------------------------------
# duration

_moving = 0

_stop = datetime.datetime.now() - datetime.timedelta(hours=_moving)
_start = _stop - datetime.timedelta(hours=_delay) - datetime.timedelta(hours=_moving)

# ---------------------------------------------------------------------------------------------------
# queries

org = "hot"
connection_file = os.path.join(config_folder, f"connection.{org}.ini")

param = {
    "_start": _start,
    "_stop": _stop
}

db_query = None
with open(query_file, 'r') as f:
    db_query = f.readlines()

db_query = "".join(db_query)

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
    if col == "_time" or col.startswith("pressure") or col.startswith("velocity") or col.startswith("heating"):
        frame_cols.append(col)

frame = frame[frame_cols]

for col in frame_cols[1:]:
    frame.loc[:,(col)] = frame.loc[:,(col)].astype(float)

anots = []
for col in frame_cols:
    if col == "_time":
        anots.append("")
    elif col.startswith("pressure"):
        addr = col.split("_")[-1]
        if addr in ["161","162","163"]:
            anots.append("AP" + str(int(addr) - 160))
        else:
            anots.append("dP")
    elif col.startswith("velocity"):
        addr = col.split("_")
        anots.append("" + addr[1] + "/stroke" + str(1 if int(addr[-1])%2 == 1 else 2) + "")
    elif col.startswith("heating"):
        addr = col.split("_")[-1]
        if addr in ["1","2","3","4"]:
            anots.append("PA" + addr)
        else:
            anots.append("MM")

units = []
for col in frame_cols:
    if col == "_time":
        units.append("")
    elif col.startswith("pressure"):
        units.append("bar")
    elif col.startswith("velocity"):
        units.append("ul/min")
    elif col.startswith("heating"):
        units.append("degC")

with open(f"{data_file}", 'w') as f:
    f.write(";".join(anots) + "\n")
    f.write(";".join(units) + "\n")

pd.DataFrame.to_csv(frame, f"{data_file}", sep=";", index=None, mode="a")

print(f"{data_file}")