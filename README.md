# umon

umon is a system monitoring script.  
It provides a lightweight way to monitor system metrics and display them in one single png file.  

It is meant for proofs of concept and troubleshooting.

## Output
![alt text](https://github.com/nmotte/umon/blob/master/screenshot/example.png)

## Pre-requisites
* Install gnuplot on the server running umon
```bash
# Ubuntu
> sudo apt-get install gnuplot

# Fedora/CentOS/RedHat
> sudo yum install gnuplot
```

* Install iostat on the servers to monitor
```bash
# Ubuntu
> sudo apt-get install sysstat

# Fedora/CentOS/RedHat
> yum install sysstat
```

* Install dstat on the servers to monitor
```bash
# Ubuntu
> sudo apt-get install dstat

# Fedora/CentOS/RedHat
> yum install dstat
```

* Setup SSH keys to connect to all the servers without password

## Configuration file
```bash
{
    "servers":[
        {
            "hostname": string,
            "devices": [string],
            "interfaces": [string]
        }
    ]
}
```

* __hostname__

    Type: String  
    Hostname of a server to monitor

* __devices__

    Type: Array of strings  
    List of devices to monitor, e.g "sda", "sdb", "nvme0n1"

* __interfaces__

    Type: Array of strings  
    List of interfaces to monitor, e.g. "eth0", "eth1"

## Run 
```bash
> python umon.py --help
Usage: umon.py [options] arg

Options:
  -h, --help            show this help message and exit
  -u USER, --user=USER  User used for SSH and scp
  -r TIME, --runtime=TIME
                        Monitoring time (in seconds), default=-1 (stops on
                        user input)
  -c CONF, --conf=CONF  Path to a configuration file
  -s SAMPLING, --sampling=SAMPLING
                        Sampling time (time between two dots, in seconds),
                        default=5
  -t TIMEOUT, --timeout=TIMEOUT
                        SSH connection timeout (in seconds), default=60
  -d, --debug           Enable debug logs

> python umon.py -r 5 -s 1 -t 10 -c umon.json -u root
INFO    # Umon UID: 3637a7b6-2cb0-4762-a099-07d2535d8ad3
INFO    # Starting dstat and iostat on ns6737901.ip-164-132-166.eu
INFO    # Umon started at 13:08:38 GMT, it will stop in 5 seconds...
INFO    # Stopping dstat and iostat on ns6737901.ip-164-132-166.eu
INFO    # Retrieving and merging stats from ns6737901.ip-164-132-166.eu
INFO    # Generating gnuplot configuration file
INFO    # Dumping graphs in output.png

> python umon.py -s 1 -t 10 -c umon.json -u root
INFO    # Umon UID: 4ab75362-8594-41dc-b78b-5081968b3e4a
INFO    # Starting dstat and iostat on ns6737901.ip-164-132-166.eu
INFO    # Umon started at 13:08:38 GMT... Enter 'stop' to stop:
> stop
INFO    # Stopping dstat and iostat on ns6737901.ip-164-132-166.eu
INFO    # Retrieving and merging stats from ns6737901.ip-164-132-166.eu
INFO    # Generating gnuplot configuration file
INFO    # Dumping graphs in output.png
```
