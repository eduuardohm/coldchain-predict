# --- PINAGEM DO ESP32-C3-MINI ---
# Valores iguais aos validados em bancada na montagem de hardware.
PIN_ONEWIRE_DS18B20 = 2   # Pino de dados do sensor de temperatura DS18B20 (pull-up 4.7k externo)
PIN_DHT22 = 4             # Pino de dados do DHT22 (temperatura/umidade ambiente)

# Barramento I2C compartilhado: MPU-6050 e DS3231 usam os mesmos pinos
I2C_ID = 0
PIN_I2C_SDA = 5           # Pino SDA do barramento I2C
PIN_I2C_SCL = 6           # Pino SCL do barramento I2C
I2C_FREQ = 400000         # 400 kHz (suportado por MPU-6050 e DS3231)

I2C_ADDR_RTC = 0x68       # DS3231 (endereço fixo)
I2C_ADDR_MPU = 0x69       # MPU-6050 com AD0 em nível alto (0x68 colidiria com o RTC)
MPU_ACCEL_RANGE_G = 16    # Fundo de escala do acelerômetro (deve bater com ImpactDetector.accel_range_g)

# --- PARÂMETROS DA CARGA E DO MODELO ---
TEMP_MIN = 2.0            # Limite inferior (°C)
TEMP_MAX = 8.0            # Limite superior (°C)
WINDOW_SIZE = 10          # Quantidade de leituras na janela deslizante
ALERT_HORIZON_MIN = 15.0  # Antecedência do alerta (TTV em minutos)

# --- TEMPORIZAÇÃO ---
# DICA DE TESTE DE BANCADA: Usar 10 segundos para testar rápido no ESP32 vendo no terminal!
# Na apresentação/operação real, mudar para 60 (1 minuto).
SAMPLE_INTERVAL_SEC = 10
SAMPLE_INTERVAL_MIN = SAMPLE_INTERVAL_SEC / 60.0

LOG_FILENAME = "log_cadeia_frio.csv"