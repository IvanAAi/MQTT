import multiprocessing
import paho.mqtt.client as mqtt
import time


def accurate_delay(delay):
    _ = time.perf_counter() + delay / 1000
    while time.perf_counter() < _:
        pass


class Publisher(multiprocessing.Process):
    def __init__(self, client_id, instance_number, broker='localhost', port=1883):
        super().__init__()
        self.client_id = client_id
        self.instance_number = instance_number
        self.broker = broker
        self.port = port
        self.qos = multiprocessing.Value('i', 0)
        self.delay = multiprocessing.Value('i', 1000)  # ms
        self.running = multiprocessing.Event()
        self.start_event = multiprocessing.Event()
        self.counter = multiprocessing.Value('i', 0)

    def on_connect(self, client, userdata, flags, rc):
        print(f"{self.client_id} connected with result code {rc}")

        self.client.subscribe("request/#")
        self.client.subscribe("request/start")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic == "request/start" and payload == "start":
            self.start_event.set()
        elif topic == "request/qos":
            with self.qos.get_lock():
                self.qos.value = int(payload)
        elif topic == "request/delay":
            with self.delay.get_lock():
                self.delay.value = int(payload)
        elif topic == "request/instance_count":

            active_count = int(payload)
            if self.instance_number <= active_count:
                if not self.running.is_set():
                    self.running.set()
                    self.start_event.set()
            else:
                self.running.clear()

    def run(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

        try:
            while True:
                self.start_event.wait()
                if not self.running.is_set():
                    continue

                start_time = time.time()
                topic = f"counter/{self.instance_number}/{self.qos.value}/{self.delay.value}"
                while self.running.is_set() and (time.time() - start_time < 60):  # 发送持续5秒
                    message = str(self.counter.value)
                    self.client.publish(topic, message, qos=self.qos.value)
                    with self.counter.get_lock():
                        self.counter.value += 1
                    accurate_delay(self.delay.value)

                terminate_topic = f"counter/{self.instance_number}/{self.qos.value}/{self.delay.value}/terminate"
                self.client.publish(terminate_topic, "terminate", qos=self.qos.value)
                self.running.clear()
                self.start_event.clear()
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def stop(self):
        self.running.clear()
        self.start_event.set()


if __name__ == "__main__":
    publishers = []
    for i in range(1, 6):
        pub_id = f"pub-{i}"
        pub = Publisher(pub_id, i)
        publishers.append(pub)
        pub.start()

    try:
        # Keep the main thread running to maintain active subscriptions
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for pub in publishers:
            pub.stop()
        for pub in publishers:
            pub.join()
