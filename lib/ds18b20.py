import time

import ds18x20
import onewire
from machine import Pin


def _rom_hex(rom):
    return ''.join(['%02x' % b for b in rom])


class DS18B20Manager:
    def __init__(self, pin_id):
        """Inicializa o barramento 1-Wire e escaneia os sensores conectados."""
        # O pull-up interno ajuda, mas não substitui o resistor externo de 4.7k
        self.pin = Pin(pin_id, Pin.IN, Pin.PULL_UP)
        self.ow = onewire.OneWire(self.pin)
        self.sensor = ds18x20.DS18X20(self.ow)

        self.roms = self.sensor.scan()

        if self.roms:
            print("[OK] {} sensor(es) DS18B20 encontrado(s).".format(len(self.roms)))
            for rom in self.roms:
                print("    -> ROM: {}".format(_rom_hex(rom)))
        else:
            print("[ERRO] Nenhum sensor DS18B20 detectado no GPIO {}!".format(pin_id))

    def read_all_temperatures(self):
        """
        Dispara a conversão e lê todos os sensores do barramento.
        Retorna {rom_hex: temperatura_celsius}, ou {"error": "NO_SENSOR"}.
        """
        if not self.roms:
            return {"error": "NO_SENSOR"}

        self.sensor.convert_temp()
        # 750 ms para resolução de 12 bits (padrão)
        time.sleep_ms(750)

        temps = {}
        for rom in self.roms:
            rom_str = _rom_hex(rom)
            try:
                temps[rom_str] = round(self.sensor.read_temp(rom), 2)
            except Exception as e:
                # Erro de CRC ou falha de comunicação no fio
                temps[rom_str] = "READ_ERROR: {}".format(e)
        return temps

    def read_temperature(self):
        """Temperatura (°C) do primeiro sensor, ou None se não houver/falhar."""
        temps = self.read_all_temperatures()
        for valor in temps.values():
            if isinstance(valor, float):
                return valor
        return None
