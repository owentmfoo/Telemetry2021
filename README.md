#Telemetry Operation Guide


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