# Monitoramento de Cadeia de Frios com Previsão de Violação na Borda

Cargas termolábeis, como vacinas, insulina, produtos biológicos e carnes para exportação, perdem valor quando a temperatura sai da faixa especificada, às vezes por poucas horas. Quando isso acontece, a carga é descartada ou rejeitada, e o prejuízo financeiro pode ser alto. O problema se agrava no transporte rodoviário, em que o caminhão atravessa trechos sem cobertura Wi-Fi e o operador só descobre a violação ao chegar ao destino.




# Estrutura do projeto

```
coldchain-predict/
│
├── boot.py                 # Configurações iniciais de boot (desativar debug, etc.)
├── main.py                 # Orquestrador: Máquina de estados e loop principal
├── config.py               # Constantes: pinos (GPIO), limites de temp (min/max), tamanho da janela
│
├── lib/                    # Drivers de hardware (MicroPython)
│   ├── ds18b20.py          # Temperatura da carga (1-Wire)
│   ├── ds3231.py           # RTC (I2C 0x68)
│   └── mpu6050.py          # Acelerômetro/giroscópio (I2C 0x69)
│
├── core/
│   ├── sensors.py          # Fachada que inicializa e lê todos os sensores de forma limpa
│   ├── predictor.py        # Classe da janela deslizante + Regressão Linear
│   ├── impact.py           # Detecção de impacto, queda e tombamento (acelerômetro MPU-6050)
│   ├── storage.py          # Logger local (salva CSV ou JSON na memória Flash do ESP32)
│   └── modem_4g.py         # Controle do módulo 4G via comandos AT (UART) e envio do payload
│
├── docs/
│   └── deteccao_impacto.md # Critérios de impacto/queda e justificativa (OMS/PQS)
│
└── tests/
    ├── hardware_sensors.py # Teste de bancada dos sensores (roda no ESP32)
    ├── synthetic_sensor.py # Simulação da predição de temperatura (roda no PC)
    └── synthetic_impact.py # Simulação de queda, batida e tombamento (roda no PC)
```

# Pinagem (ESP32-C3)

| Sensor | Pino / barramento |
|---|---|
| DS18B20 | GPIO 2 (1-Wire, pull-up 4,7 kΩ) |
| DHT22 | GPIO 4 |
| I2C 0 (compartilhado) | SDA = GPIO 5, SCL = GPIO 6, 400 kHz |
| DS3231 | I2C, 0x68 |
| MPU-6050 | I2C, 0x69 (AD0 em nível alto) |

Tudo definido em [`config.py`](config.py).

# Detecção de impacto

O módulo [`core/impact.py`](core/impact.py) detecta **quedas**, **impactos** e **tombamento** com o MPU-6050. A severidade das quedas vem da altura estimada pelo tempo de queda livre, comparada com os ensaios de qualificação da OMS para caixas de vacina (WHO/PQS/E004: quedas de 1 m, 22 repetições). Critérios, fontes e limitações estão em [`docs/deteccao_impacto.md`](docs/deteccao_impacto.md).

> **Os valores padrão são só uma referência:** parte vem da OMS (válidos para caixas PQS E004) e da literatura, o resto foi definido pelo grupo. Todos devem ser calibrados com a caixa real.

```
py tests/synthetic_impact.py
```
