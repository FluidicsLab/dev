
from(bucket: _bucket)
  |> range(start: _start, stop: _stop)
  |> filter(fn: (r) => r["_measurement"] == "pump01" or r["_measurement"] == "mcv")
  |> filter(fn: (r) => (r["_field"] == "pressure" and r["no"] == "1") or (r["_field"] == "velocity" and r["no"] == "1") or (r["_field"] == "volume" and r["no"] == "1") or (r["_field"] == "state" or r["_field"] == "heatingvalue"))  
  |> aggregateWindow(every: _every, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time"],columnKey: ["_field"],valueColumn: "_value")
  |> keep(columns: ["_time", "state", "heatingvalue", "pressure", "velocity","volume"])

