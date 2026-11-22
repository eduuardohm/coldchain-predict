# Teste de bancada dos sensores (roda no ESP32, não no PC).
# Copie para a raiz da placa ou rode via: import tests.hardware_sensors
import time

import config
from core.sensors import SensorManager

sensores = SensorManager()

while True:
    print("Lendo o acelerômetro...")
    d = sensores.ler_acelerometro()
    if d:
        print(f"AcX = {d['ax']:.3f} | AcY = {d['ay']:.3f} | AcZ = {d['az']:.3f} (g)")
        print(f"GyX = {d['gx']:.1f} | GyY = {d['gy']:.1f} | GyZ = {d['gz']:.1f} (°/s)")

    print("Lendo o RTC...")
    print(sensores.ler_timestamp())

    print("Lendo o DHT22")
    temp, hum = sensores.ler_ambiente()
    print(f"Temp: {temp}°C | Umidade: {hum}%")

    print("Lendo o DS18B20")
    print(f"Temp: {sensores.ler_temperatura()}°C")

    time.sleep(5)
