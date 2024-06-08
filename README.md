
# MQTT Publisher and Analyser

* * *
Author: Zihan Ai
* * *


## Introduction
This project consists of two Python scripts: `publisher.py` and `Analyser.py`. These scripts work together to create a system using MQTT (Message Queuing Telemetry Transport) protocol. The `publisher.py` script handles the publishing of messages, while the `Analyser.py` script is responsible for receiving and analyzing these messages.

## Requirements
- Python 3.6 or higher
- `paho-mqtt` library
- `multiprocessing` library (part of Python standard library)
- `statistics` library (part of Python standard library)
- `threading` library (part of Python standard library)

Install the required libraries using:
```bash
pip install paho-mqtt
```

## Publisher (publisher.py)
The `Publisher` class in `publisher.py` creates multiple MQTT publishers that can send messages to an MQTT broker.


**Usage:**
To run the publisher script:
```bash
python publisher.py
```

## Analyser (Analyser.py)
The `Analyser` class in `Analyser.py` receives messages from the publishers, logs system information, and analyzes the performance metrics of the messages.


## Configuration
- **Broker Address and Port**: Both scripts default to using `localhost` and port `1883`. These can be changed by modifying the respective `broker` and `port` parameters in the script.
- **QoS and Delay**: The publisher script allows dynamic adjustment of QoS and delay through MQTT messages.

## Logging and Analysis
- **System Information**: Logged to `sys_info.log`.
- **Performance Metrics**: Logged to `analysis_results.txt`.
- **Termination Messages**: Handled to ensure proper shutdown and synchronization.

## Running the Scripts
1. First, run the `publisher.py` script:
    ```bash
    python publisher.py
    ```
2. Then, run the `Analyser.py` script:
    ```bash
    python Analyser.py
    ```
   
## Additional Information
When using the MQTT protocol for message transmission, the following steps are taken to ensure orderly communication:
1. The `request/start` command is sent initially to prevent the publishers from starting prematurely. This ensures that all publishers begin transmitting at the same time.
2. At the end of the transmission, a termination message is sent to signal the end of the message exchange. This helps in preventing any confusion or overlap of messages.
---

## Credits
Developed at ANU.