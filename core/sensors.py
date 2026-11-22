import dht
from machine import I2C, Pin

import config
from lib.ds18b20 import DS18B20Manager
from lib.ds3231 import DS3231
from lib.mpu6050 import MPU6050


class SensorManager:
    """Inicializa e lê todos os sensores do nó."""
    def __init__(self):
        # Um único I2C compartilhado entre RTC (0x68) e MPU-6050 (0x69)
        self.i2c = I2C(config.I2C_ID,
                       sda=Pin(config.PIN_I2C_SDA),
                       scl=Pin(config.PIN_I2C_SCL),
                       freq=config.I2C_FREQ)
        self.rtc = DS3231(self.i2c, addr=config.I2C_ADDR_RTC)
        self.mpu = MPU6050(self.i2c, addr=config.I2C_ADDR_MPU,
                           accel_range_g=config.MPU_ACCEL_RANGE_G)
        self.ds18b20 = DS18B20Manager(config.PIN_ONEWIRE_DS18B20)
        self.dht = dht.DHT22(Pin(config.PIN_DHT22))

    def ler_timestamp(self):
        """'YYYY-MM-DD HH:MM:SS' do RTC, ou None se falhar."""
        try:
            return self.rtc.get_time_str()
        except Exception as e:
            print("Erro ao ler RTC: {}".format(e))
            return None

    def ler_temperatura(self):
        """Temperatura da carga (°C) pelo DS18B20, ou None se falhar."""
        return self.ds18b20.read_temperature()

    def ler_ambiente(self):
        """(temperatura °C, umidade %) do DHT22, ou (None, None) se falhar."""
        try:
            self.dht.measure()
            return self.dht.temperature(), self.dht.humidity()
        except Exception as e:
            print("Erro ao ler DHT22: {}".format(e))
            return None, None

    def ler_acelerometro(self):
        """Dict com ax/ay/az (g), gx/gy/gz (°/s) e temp, ou None se falhar."""
        return self.mpu.read_all()
