import os
import time
import threading
import pyautogui
import numpy as np
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from scipy.signal import butter, lfilter
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

class MqttClient():
    def __init__(self, broker, port, timeout, topics, filter):
        self.client = mqtt.Client()

        self._broker = broker
        self.port = port
        self.timeout = timeout
        self.topics = topics

        self.DataC1 = []
        self.DataC2 = []
        self.DataFilteredC1 = []
        self.DataFilteredC2 = []
        self.fs = 120
        self.fc = 3
        self.filterOrder = 3


    def connect_to_broker(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self._broker, self.port, self.timeout)
        

        mqtt_thread = threading.Thread(target=self.client.loop_forever)
        mqtt_thread.start()


    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8')

        payloadChannel1 = payload.split(" ")[0].split(";")[:-1]
        payloadChannel2 = payload.split(" ")[1].split(";")[:-1]

        self.DataC1 = [int(dataConvert) for dataConvert in payloadChannel1]
        self.DataC2 = [int(dataConvert) for dataConvert in payloadChannel2]  

        self.DataC1 = np.interp(self.DataC1, (0, 4095), (0, 3.3))
        self.DataC2 = np.interp(self.DataC2, (0, 4095), (0, 3.3))




        self.nyquist = 0.5 * self.fs
        self.normalCutoff = self.fc / self.nyquist
        self.b, self.a = butter(self.filterOrder, self.normalCutoff, btype='low', analog=False)
        
        self.DataFilteredC1 = lfilter(self.b, self.a, self.DataC1)
        self.DataFilteredC2 = lfilter(self.b, self.a, self.DataC2)


    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(self.topics)


class plotGraphycs():
    def __init__(self, client):
        self.mqtt = client
        self.mqtt.DataFilteredC1
        self.mqtt.DataFilteredC2
        self.mqtt.DataC1
        self.mqtt.DataC2
        self.data_c1 = []
        self.data_c2 = []

        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 6))  # Subplots com 2 linhas e 1 coluna
        plt.subplots_adjust(hspace=0.8, wspace = 0.8)

        self.line_c1, = self.ax1.plot([], [], lw=2)
        self.line_c2, = self.ax2.plot([], [], lw=2)

        self.ax1.set_xlim(0, 2000)
        self.ax1.set_ylim(0, 3.3)
        self.ax2.set_xlim(0, 2000)
        self.ax2.set_ylim(0, 3.3)

        self.ax1.set_title('EOG - Canal 1')
        self.ax1.set_xlabel('Tempo (s)')
        self.ax1.set_ylabel('Tensão (V)')

        self.ax2.set_title('EOG - Canal 2')
        self.ax2.set_xlabel('Tempo (s)')
        self.ax2.set_ylabel('Tensão (V)')

        self.save_button_ax = plt.axes([0.5, 0, 0.1, 0.05])  # [left, bottom, width, height]
        self.save_button = Button(self.save_button_ax, 'Avançar')
        
        thread_atualizacao = threading.Thread(target=self.clear_data)
        self.close_event = threading.Event()
        self.save_button.on_clicked(self.start_thread)
        self.ani = FuncAnimation(self.fig, self.update, init_func=self.init, interval=1/120, save_count=200)  # Intervalo em milissegundos

    def init(self):
        self.line_c1.set_data([], [])
        self.line_c2.set_data([], [])
        return self.line_c1, self.line_c2

    def update(self, frame):
        self.data_c1.extend(self.mqtt.DataC1)
        self.data_c2.extend(self.mqtt.DataC2)

        if len(self.data_c1) >= 2000:
            self.data_c1 = self.data_c1[-2000:]
        if len(self.data_c2) >= 2000:
            self.data_c2 = self.data_c2[-2000:]

        self.line_c1.set_xdata(range(len(self.data_c1)))
        self.line_c1.set_ydata(self.data_c1)

        self.line_c2.set_xdata(range(len(self.data_c2)))
        self.line_c2.set_ydata(self.data_c2)

        self.ax1.relim()
        self.ax1.autoscale_view()

        self.ax2.relim()
        self.ax2.autoscale_view()

        time.sleep(1/(120/20))

    def clear_data(self):
        while(1):
            largura_monitor, altura_monitor = pyautogui.size()
            normalizedData = [(d - 0) / (3.3 - 0) for d in self.mqtt.DataC1]
            
            if sum(self.mqtt.DataC1) / len(self.mqtt.DataC1) >= 2 or sum(self.mqtt.DataC1) / len(self.mqtt.DataC1) <= 1:
                x_tela = int((sum(normalizedData) / len(normalizedData)) * largura_monitor)
                x_cursor, y_cursor = pyautogui.position()
                if x_tela != x_cursor:
                    pyautogui.moveTo(x_tela, y_cursor)
            time.sleep(1/(120/20))

    def start_thread(self, event):
        plt.close()
        self.thread_atualizacao = threading.Thread(target=self.clear_data)
        self.thread_atualizacao.start()

if __name__ == "__main__":
    load_dotenv()

    #filter = filterData()

    client = MqttClient(
        str(os.environ.get('HOST_IP')),
        int(os.environ.get('PORT')),
        int(os.environ.get('TIMEOUT')),
        str(os.environ.get('TOPIC')), 
        filter
    )

    client.connect_to_broker()

    graph = plotGraphycs(client)

    plt.show()
