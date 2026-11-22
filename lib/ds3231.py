class DS3231:
    def __init__(self, i2c, addr=0x68):
        """i2c: objeto machine.I2C já inicializado (compartilhado com o MPU-6050)."""
        self.i2c = i2c
        self.addr = addr
        self.buf = bytearray(7)

    # --- Conversões BCD (Binário Codificado em Decimal) ---
    def _bcd_to_dec(self, bcd):
        return (bcd // 16) * 10 + (bcd % 16)

    def _dec_to_bcd(self, dec):
        return (dec // 10) * 16 + (dec % 10)

    # --- Configurar a Hora ---
    def set_time(self, year, month, day, weekday, hour, minute, second):
        """Define a data e hora. weekday: 1=Segunda, 7=Domingo."""
        data = bytearray([
            self._dec_to_bcd(second),
            self._dec_to_bcd(minute),
            self._dec_to_bcd(hour),
            self._dec_to_bcd(weekday),
            self._dec_to_bcd(day),
            self._dec_to_bcd(month),
            self._dec_to_bcd(year % 100),  # DS3231 usa apenas 2 dígitos para o ano
        ])
        self.i2c.writeto_mem(self.addr, 0x00, data)

    # --- Ler a Hora ---
    def get_time(self):
        """Retorna um dicionário com a data e hora atual."""
        self.i2c.readfrom_mem_into(self.addr, 0x00, self.buf)
        return {
            'year': self._bcd_to_dec(self.buf[6]) + 2000,
            'month': self._bcd_to_dec(self.buf[5] & 0x1F),  # Remove bit de século
            'day': self._bcd_to_dec(self.buf[4]),
            'weekday': self._bcd_to_dec(self.buf[3]),
            'hour': self._bcd_to_dec(self.buf[2] & 0x3F),   # Formato 24h
            'minute': self._bcd_to_dec(self.buf[1]),
            'second': self._bcd_to_dec(self.buf[0] & 0x7F),
        }

    def get_time_str(self):
        """Retorna a hora formatada (YYYY-MM-DD HH:MM:SS)."""
        t = self.get_time()
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t['year'], t['month'], t['day'],
            t['hour'], t['minute'], t['second']
        )
