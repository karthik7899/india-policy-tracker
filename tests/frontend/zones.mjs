// Run a check with the process in each of several timezones. Node re-reads
// TZ whenever it is assigned, so one process can stand in for readers in
// India, California and either side of the date line.

export function inZones(zones, fn) {
  const original = process.env.TZ;
  try {
    for (const tz of zones) {
      process.env.TZ = tz;
      fn(tz);
    }
  } finally {
    if (original === undefined) delete process.env.TZ;
    else process.env.TZ = original;
  }
}
