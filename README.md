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
└── core/
    ├── sensors.py          # Fachada que inicializa e lê todos os sensores de forma limpa
    ├── predictor.py        # Classe da janela deslizante + Regressão Linear
    ├── storage.py          # Logger local (salva CSV ou JSON na memória Flash do ESP32)
    └── modem_4g.py         # Controle do módulo 4G via comandos AT (UART) e envio do payload
```
