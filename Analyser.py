import statistics
import threading
import paho.mqtt.client as mqtt
import time


class Analyser:
    def __init__(self, broker='localhost', port=1883):
        self.broker_qos = 0
        self.messages = {}
        self.message_times = {}
        self.sys_info = []
        self.termination_status = {}
        self.termination_lock = threading.Lock()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(broker, port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        if rc == 0:
            print("Connection successful")
            self.subscribe_topics(self.broker_qos)
        else:
            print("Failed to connect, check the connection parameters and broker status")
        client.subscribe("$SYS/#")

    def subscribe_topics(self, qos):
        """Unsubscribe and resubscribe to the topics with the new QoS level."""
        self.client.unsubscribe("counter/#")
        self.client.subscribe("counter/#", qos=qos)
        print(f"Subscribed to 'counter/#' with QoS {qos}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        current_time = time.perf_counter()
        if topic.startswith("$SYS/"):
            sys_info_entry = f"{topic}: {payload}"
            self.sys_info.append(sys_info_entry)
            with open('sys_info.log', 'a') as f:
                f.write(f"{sys_info_entry}\n")
        else:
            if topic.startswith("counter/") and "/terminate" in topic:
                with self.termination_lock:
                    self.termination_status[topic] = True
                print(f"Received termination message for {topic}")
            elif topic.startswith("counter/"):
                if topic not in self.messages:
                    self.messages[topic] = []
                    self.message_times[topic] = []
                self.messages[topic].append(int(payload))
                self.message_times[topic].append(current_time)

    def control_publishers(self):
        p2b_qos = [0, 1, 2]
        delays = [0, 1, 2, 4]
        instance_counts = [1, 2, 3, 4, 5]
        b2a_qos = [0, 1, 2]

        com = 1

        for analyser_qos in b2a_qos:
            self.subscribe_topics(analyser_qos)
            for qos in p2b_qos:
                for delay in delays:
                    for instance_count in instance_counts:
                        self.client.publish("request/qos", qos)
                        self.client.publish("request/delay", delay)
                        self.client.publish("request/instance_count", instance_count)
                        time.sleep(2)
                        self.client.publish("request/start", "start")
                        with open("analysis_results.txt", "a") as file:
                            title = f"{com}. Combination of instance_count = {instance_count}, delay = {delay}, publisher to broker QoS = {qos}, broker to analyser QoS = {analyser_qos} "
                            file.write(title + "\n")
                        com += 1
                        time.sleep(70)  # 等待数据收集
                        self.wait_for_termination(instance_count)
                        self.analyze_performance()
                        self.log_sys_info(com)
                        self.reset_data()

    def wait_for_termination(self, instance_count):
        start_wait = time.time()
        while len(self.termination_status) < instance_count:
            if time.time() - start_wait > 60:
                print("Timeout waiting for termination messages.")
                break
            time.sleep(1)

    def analyze_performance(self):
        with open("analysis_results.txt", "a") as file:
            for topic, msgs in self.messages.items():
                if topic not in self.message_times or len(self.message_times[topic]) < 2:
                    print(f"Warning: No sufficient start time recorded for {topic}. Skipping analysis for this topic.")
                    continue

                # 计算总时间
                total_time = self.message_times[topic][-1] - self.message_times[topic][0]
                message_rate = len(msgs) / total_time if total_time > 0 else 0
                if msgs:
                    max_received_msg = max(msgs)
                    min_received_msg = min(msgs)
                    expected_msgs = max_received_msg - min_received_msg + 1
                    received_msgs = len(set(msgs))
                    # duplicate_rate = (1 - received_msgs / len(msgs)) * 100 if len(msgs) > 0 else 0
                    loss_rate = (1 - received_msgs / expected_msgs) * 100 if expected_msgs > 0 else 0
                    misorders = sum(1 for i in range(1, len(msgs)) if msgs[i] < msgs[i - 1])
                    misorder_rate = misorders / len(msgs) * 100 if msgs else 0
                    gaps = [(j - i) * 1000 for i, j in
                            zip(self.message_times[topic][:-1], self.message_times[topic][1:])]
                    median_gap = statistics.median(gaps) if gaps else None
                else:
                    loss_rate = 100
                    # duplicate_rate = 0
                    misorder_rate = 0
                    median_gap = None

                results = (f"Topic: {topic} (Broker to Analyser QoS = {self.broker_qos})\n"
                           f"  Average Message Rate: {message_rate:.6f} messages/second\n"
                           f"  Message Loss Rate: {loss_rate:.6f}%\n"
                           f"  Misorder Rate: {misorder_rate:.6f}%\n"
                           # f"  Duplicate Rate = {duplicate_rate:.6f}%\n"
                           f"  Median Inter-message Gap: {median_gap:.6f} ms")
                file.write(results + "\n\n")

    def log_sys_info(self, combination_number):
        with open('sys_info.log', 'a') as f:
            f.write(f"Combination {combination_number} System Information:\n")
            for sys_info_entry in self.sys_info:
                f.write(f"{sys_info_entry}\n")
            f.write("\n")

    def reset_data(self):
        self.messages.clear()
        self.message_times.clear()
        self.termination_status.clear()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


if __name__ == "__main__":
    analyser = Analyser()
    try:
        analyser.control_publishers()
    finally:
        analyser.stop()
