
from(bucket: "ed1f")
  |> range(start: _start, stop: _stop)
  |> filter(fn: (r) => r["_measurement"] == "pump01")
  |> filter(fn: (r) => r["_field"] == "pressure" or r["_field"] == "temperature")
  |> filter(fn: (r) => r["no"] == "1" or r["no"] == "2")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> pivot(rowKey: ["_time"], columnKey: ["_field","no"], valueColumn: "_value")
  |> keep(columns: ["_time", "pressure_1", "pressure_2", "temperature_1", "temperature_2"])
