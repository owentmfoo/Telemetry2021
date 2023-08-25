# Telemetry Operation Guide


Check Arduino is reading CAN msg: 
* Serial connection to it with the car running. 

Check Pi is receiving packets from the xBee: 
* Check xBee is plugged into the right port: 
```shell 
$ cd /dev	
$ ls -la
```
and check 
if there is a `ttyUSB0` in the list.
* Restart `telem.service`: 
```shell
$ systemctl restart telem.service
```
* Check that `telem.service` is running: 
```shell
$ systemctl status telem.service
```
* Check the log and see if there are CAN msgs coming in:
```shell
$ journalctl -u telem.service -f
```


Check that the script is writing data to influx
* Check if influx is good: 
```shell
$ systemctl status influxd.service
$ curl -sl -I http://localhost:8086/ping
```
* Check that the connection info in telemetryStorer.py is correct.
  * cd to the directory and open the file using nano
  ```shell
    $ nano telemtryStorer.py 
    ```
  * exit using ctrl+x

## Maintainence

Set up new database in influx:
``` shell
$ influx
> CREATE DATABASE "DatabaseName"
> exit
```

Export a measurement from influxdb
``` shell
$ influx
> SHOW DATABASES
> use database_name
> SHOW MEASUREMENTS
> SELECT * FROM measurement_name
> SELECT * FROM measurement_name > /path/to/export.csv
```

## Updating code from GitHub to Pi
1. Get the latest code from GitHub. Navigate to Telemetry2021 and run the 
    following command. You'll need internet access for this. 
    ```shell
   git switch nick-22Library
   git pull origin nick-22Library
   git status
    ```
   and the console should show 
    ```
    On branch nick-22Library
    Your branch is up to date with 'origin/nick-22Library'
    ``` 
     
2. Switch over to the telemetry LAN. Copy the files over onto the pi with the 
    following command. Enter the password when prompted.  
    ```shell
	scp -r * pi@raspberrypi.local:~/telemetry22/Telemetry2021/
    ``` 
   
## Files on the Pi
```
~
|- telemetry22
|  |- Telemetry2021
|  |  |- Receiver
|  |  |  |- LiveTelemetry.py
|  |  |  |- telemetryParser2.py
|  |  |  |- telemetryStorer.py
|  |  |  ... 
|  |- CANTranslator
|  |  |- config
|  |  |  |- CANBusData(saved201022)Modified.xlsm
|  |  ...
|  ...
|- start-telem.sh 
```
### Telemetry2021
[This repo](https://github.com/DUEM/Telemetry2021)
#### LiveTelemetry.py
Entry point for the whole process
#### telemeteryParser2.py
Called by `telemetryStorer.py`. References `CANBusData.xlsm` to decode the CAN 
messages.
#### telemetryStorer.py
Uses `telemetryParser2.py` to decode the can messages and stores it in either
Excel or Influx. Edit this file to configure the influx credentials or the 
output Excel file. 
### CANTranslator
[That repo](https://github.com/DUEM/CANTranslator)
#### CANBusData.xlsm
Contains info for all the CAN messages and how to decode them.
