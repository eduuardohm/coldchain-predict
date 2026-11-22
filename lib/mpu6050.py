import time

# Fundo de escala do acelerômetro: g -> (valor do registrador 0x1C, LSB/g)
_ACCEL_RANGES = {
    2: (0x00, 16384.0),
    4: (0x08, 8192.0),
    8: (0x10, 4096.0),
    16: (0x18, 2048.0),
}


class MPU6050:
    def __init__(self, i2c, addr=0x69, accel_range_g=2):
        """
        i2c: objeto machine.I2C já inicializado (compartilhado com o DS3231).
        accel_range_g: 2, 4, 8 ou 16. Para o ImpactDetector use 16.
        """
        self.i2c = i2c
        self.addr = addr
        reg, self.accel_lsb = _ACCEL_RANGES[accel_range_g]
        self.wake_up()
        self.i2c.writeto_mem(self.addr, 0x1C, bytes([reg]))

    def wake_up(self):
        self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')
        time.sleep_ms(100)

    def read_all(self):
        """
        Lê os 14 bytes a partir do registrador 0x3B.
        Retorna dict (ax/ay/az em g, gx/gy/gz em °/s, temp em °C)
        ou None se a leitura I2C falhar.
        """
        try:
            buf = self.i2c.readfrom_mem(self.addr, 0x3B, 14)
        except Exception as e:
            print("Erro ao ler MPU6050: {}".format(e))
            # None (e não zeros): ax=ay=az=0 seria lido como queda livre
            return None

        def parse_16bit(offset):
            val = buf[offset] * 256 + buf[offset + 1]
            if val > 32767:
                val -= 65536
            return val

        return {
            'ax': parse_16bit(0) / self.accel_lsb,
            'ay': parse_16bit(2) / self.accel_lsb,
            'az': parse_16bit(4) / self.accel_lsb,
            'temp': parse_16bit(6) / 340.0 + 36.53,
            'gx': parse_16bit(8) / 131.0,
            'gy': parse_16bit(10) / 131.0,
            'gz': parse_16bit(12) / 131.0,
        }
