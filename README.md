# Telemetry2021

#### SD card need to be formated to SAT32 or SAT 16 (and use SAT 16 where possible)
#### '<rec2db.py>' need to be loaded to the pi and start on startup (and maybe restart when fail in case the xbee is not inserted on startup)
#### '<rec2db.py>' need to start after the influx db server have started (systemd servce called '<influxdb.service>')
#### '<main.ino>' to load onto the mega (waah..)
