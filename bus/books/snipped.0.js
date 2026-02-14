console.clear();

let value = 21;
value = value.toString(2).padStart(8, "0");

function severity2string(value, sep=" ") {

    let severity = value.slice(0, 4);
    let reason = value.slice(4, 8);

    let ignore = parseInt(reason, 2) & 1;

    severity = parseInt(severity, 2);
    reason = parseInt(reason, 2) & ~1;

    let payload = [];

    let severities = ['INFORMATION', 'WARNING', 'ERROR', 'CRITICAL'];
    ['1000', '0100', '0010', '0001'].forEach(function (s, i) {
        let a = parseInt(s, 2);
        let b = severity;
        if (a == b) {
            payload.push(severities[i]);
        }
    });

    let reasons = ['TEMPERATURE', 'LOCK', 'PRESSURE', 'TIME', 'DISTANCE', 'SYSTEM'];

    ['1100', '1010', '1000', '0110', '0100', '0010'].forEach(function (r, i) {
        let a = parseInt(r, 2)
        let b = reason;
        if (a == b) {
            payload.push(reasons[i]);
        }
    });

    if (ignore) {
        payload.push("IGNORE");
    }

    return payload.join(sep).toLowerCase();

}

rc = severity2string(value);

console.log(rc)

