import gc
import time

import config
from core.predictor import ColdChainPredictor
from core.sensors import SensorManager
from core.storage import LocalStorage

# def acionar_modem_4g_stub(timestamp, resultado):
#     """Stub provisório até integrarmos o módulo 4G via UART."""
#     print("\n" + "!" * 60)
#     print(f"[GATILHO 4G ATIVADO] {timestamp} -> Motivo: {resultado['tipo']}")
#     print(f"Payload p/ envio: Temp={resultado['temp_atual']}°C | "
#           f"Taxa={resultado.get('taxa_variacao_min')}°C/min | "
#           f"TTV={resultado.get('ttv_min')} min")
#     print("!" * 60 + "\n")

def main():
    print("Iniciando Nó Sensor de Cadeia de Frio (ESP32-C3)...")
    sensores = SensorManager()
    storage = LocalStorage()
    predictor = ColdChainPredictor(
        t_min=config.TEMP_MIN,
        t_max=config.TEMP_MAX,
        window_size=config.WINDOW_SIZE,
        sample_interval_min=config.SAMPLE_INTERVAL_MIN,
        alert_horizon_min=config.ALERT_HORIZON_MIN
    )

    intervalo_ms = config.SAMPLE_INTERVAL_SEC * 1000
    proximo = time.ticks_ms()  # instante em que o ciclo atual deve começar

    ciclo = 0
    while True:
        inicio = time.ticks_ms()
        ciclo += 1
        ts = sensores.ler_timestamp()
        temp = sensores.ler_temperatura()
        acc = sensores.ler_acelerometro()
        temp_amb, umid = sensores.ler_ambiente()

        # Debug temperatura DHT22
        if temp_amb is not None:
            print(f"[{ciclo:03d}] DHT22: Temp={temp_amb:.1f}°C | Umidade={umid:.1f}%")
        else:
            print(f"[{ciclo:03d}] Falha na leitura do DHT22.")

        # Debug acelerômetro
        if acc is not None:
            print(f"[{ciclo:03d}] Acel (g): X={acc['ax']:.3f} Y={acc['ay']:.3f} Z={acc['az']:.3f} | "
                  f"Giro (°/s): X={acc['gx']:.1f} Y={acc['gy']:.1f} Z={acc['gz']:.1f}")
        else:
            print(f"[{ciclo:03d}] Falha na leitura do acelerômetro.")

        # Predição temperatura DS18B20
        if temp is not None:
            predictor.adicionar_leitura(temp)
            res = predictor.avaliacao()

            # Salva no CSV local dentro da Flash do ESP32
            try:
                storage.registrar(ts, res)
            except OSError as e:
                print(f"[{ciclo:03d}] Falha ao gravar no CSV: {e}")

            print(f"[{ciclo:03d}] {ts} | Temp: {temp:.2f}°C | "
                  f"Status: {res['tipo']} | Taxa: {res.get('taxa_variacao_min')} | "
                  f"TTV: {res.get('ttv_min')} | Proj({config.ALERT_HORIZON_MIN:.0f}min): "
                  f"{res.get('temp_projetada')} | Janela: {len(predictor.window)}/{config.WINDOW_SIZE}")

            # Regra de negócio: só liga o 4G se houver violação prevista ou real
            # if res.get("alerta"):
            #     acionar_modem_4g_stub(ts, res)
        else:
            print(f"[{ciclo:03d}] {ts} | Falha na leitura da temperatura. Tentando no próximo ciclo...")

        gc.collect()  # Limpa memória RAM do microcontrolador

        # Período fixo: dorme só o que sobra do intervalo, sem acumular deriva
        proximo = time.ticks_add(proximo, intervalo_ms)
        restante = time.ticks_diff(proximo, time.ticks_ms())
        duracao = time.ticks_diff(time.ticks_ms(), inicio)
        if restante > 0:
            print(f"[{ciclo:03d}] Ciclo levou {duracao} ms, dormindo {restante} ms")
            time.sleep_ms(restante)
        else:
            # Ciclo passou do intervalo: não tenta "recuperar", reinicia a referência
            print(f"[{ciclo:03d}] AVISO: ciclo levou {duracao} ms (> {intervalo_ms} ms)")
            proximo = time.ticks_ms()

if __name__ == "__main__":
    main()