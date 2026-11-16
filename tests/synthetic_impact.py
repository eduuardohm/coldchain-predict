import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import math
import random

from core.impact import ImpactDetector, G

random.seed(42)

DT_MS = 10        # 100 Hz
FUNDO_ESCALA = 16  # MPU-6050 configurado em ±16 g


def ruido(a):
    return random.uniform(-a, a)


def satura(v):
    return max(-FUNDO_ESCALA, min(FUNDO_ESCALA, v))


class Cenario:
    """Gera amostras (fase, ax, ay, az) em g a 100 Hz."""

    def __init__(self):
        self.amostras = []

    def add(self, fase, ax, ay, az):
        self.amostras.append((fase, satura(ax), satura(ay), satura(az)))

    def parado(self, seg, fase="Parado"):
        for _ in range(int(seg * 1000 / DT_MS)):
            self.add(fase, ruido(0.02), ruido(0.02), 1.0 + ruido(0.02))

    def estrada(self, seg):
        for _ in range(int(seg * 1000 / DT_MS)):
            self.add("Estrada", ruido(0.15), ruido(0.15), 1.0 + ruido(0.3))

    def queda(self, altura_m, pulso_z, fase):
        # t = sqrt(2h/g)
        n = int(round(math.sqrt(2 * altura_m / G) * 1000 / DT_MS))
        for _ in range(n):
            self.add(fase, ruido(0.05), ruido(0.05), ruido(0.05))
        for v in pulso_z:
            self.add(fase, ruido(0.3), ruido(0.3), v)

    def batida_x(self, pulso_x, fase):
        for v in pulso_x:
            self.add(fase, v, ruido(0.2), 1.0 + ruido(0.2))

    def tombar(self):
        passos = 100
        for i in range(passos):
            ang = (math.pi / 2) * (i + 1) / passos
            self.add("Tombando", math.sin(ang) + ruido(0.02), ruido(0.02),
                     math.cos(ang) + ruido(0.02))
        for _ in range(300):
            self.add("Deitada", 1.0 + ruido(0.02), ruido(0.02), ruido(0.02))


def cenario_transporte():
    c = Cenario()
    c.parado(2)
    c.estrada(3)
    for v in (1.3, 1.8, 1.5, 0.7, 0.9):                       # buraco: < 3 g
        c.add("Buraco", ruido(0.1), ruido(0.1), v)
    c.parado(1)
    c.queda(0.15, (1.8, 2.5, 1.4, 0.9), "Queda 15 cm")       # abaixo do estudo
    c.parado(2)
    c.queda(0.50, (4.0, 7.5, 5.0, 2.0, 0.6, 1.3), "Queda 50 cm")
    c.parado(2)
    c.queda(1.20, (9.0, 20.0, 18.0, 11.0, 3.5, 1.2), "Queda 1,2 m")  # carroceria
    c.parado(2)
    c.batida_x((2.5, 4.2, 3.6, 1.5), "Batida leve")
    c.parado(2)
    c.batida_x((8.0, 22.0, 17.0, 6.0, 1.5), "Batida forte")  # satura o sensor
    c.parado(2)
    c.tombar()
    esperados = [
        ("QUEDA", "LEVE", False),
        ("QUEDA", "MODERADA", False),
        ("QUEDA", "GRAVE", True),
        ("IMPACTO", "MODERADA", False),
        ("IMPACTO", "GRAVE", True),
        ("TOMBAMENTO", "GRAVE", True),
    ]
    return c.amostras, esperados


def cenario_quedas_acumuladas():
    # 23 quedas de 50 cm: passa do número de quedas do ensaio da OMS (22)
    c = Cenario()
    c.parado(1)
    for i in range(23):
        c.queda(0.50, (4.0, 7.5, 5.0, 2.0, 0.6, 1.3), "Queda {}".format(i + 1))
        c.parado(1)
    esperados = [("QUEDA", "MODERADA", False)] * 23 + [("LIMITE_QUEDAS", "GRAVE", True)]
    return c.amostras, esperados


def detalhes(e):
    if e["tipo"] == "QUEDA":
        return "altura≈{} m, pico={} g{}, nº {}".format(
            e["altura_estimada_m"], e["pico_g"],
            " (saturado)" if e["saturado"] else "", e["contador_quedas"])
    if e["tipo"] == "IMPACTO":
        return "pico={} g{}, duração={} ms".format(
            e["pico_g"], " (saturado)" if e["saturado"] else "", e["duracao_ms"])
    if e["tipo"] == "TOMBAMENTO":
        return "ângulo={}°".format(e["angulo_graus"])
    if e["tipo"] == "LIMITE_QUEDAS":
        return "{} quedas > limite PQS de {}".format(e["contador_quedas"], e["limite"])
    return str(e)


def rodar(titulo, amostras, esperados, imprimir_todos=True):
    detector = ImpactDetector(sample_interval_ms=DT_MS, accel_range_g=FUNDO_ESCALA)

    print("=" * 95)
    print(titulo)
    print("=" * 95)
    print("{:<7} | {:<13} | {:<13} | {:<8} | {:<7} | {}".format(
        "t (ms)", "Fase", "Evento", "Sev.", "4G?", "Detalhes"))
    print("-" * 95)

    obtidos = []
    for fase, ax, ay, az in amostras:
        for e in detector.adicionar_amostra(ax, ay, az):
            obtidos.append((e["tipo"], e["severidade"], e["alerta"]))
            if imprimir_todos or e["alerta"]:
                print("{:<7} | {:<13} | {:<13} | {:<8} | {:<7} | {}".format(
                    detector.t_ms, fase, e["tipo"], e["severidade"],
                    "SIM" if e["alerta"] else "Não", detalhes(e)))

    ok = obtidos == esperados
    print("-" * 95)
    print("Eventos: {} obtidos / {} esperados".format(len(obtidos), len(esperados)))
    if not ok:
        print("Esperado: {}".format(esperados))
        print("Obtido:   {}".format(obtidos))
    print("RESULTADO: {}\n".format("OK" if ok else "FALHOU"))
    return ok


if __name__ == "__main__":
    ok1 = rodar("SIMULAÇÃO 1: Transporte com quedas, batidas e tombamento (100 Hz, ±16 g)",
                *cenario_transporte())
    ok2 = rodar("SIMULAÇÃO 2: Quedas acumuladas (23 × 50 cm, limite PQS = 22) — só alertas",
                *cenario_quedas_acumuladas(), imprimir_todos=False)
    sys.exit(0 if ok1 and ok2 else 1)
