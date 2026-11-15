import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random

from core.predictor import ColdChainPredictor

random.seed(42)

def gerar_cenario_sintetico():
    leituras = []

    # Fase 1: 12 min estável em ~4.0°C (com ruído leve de sensor DS18B20)
    for _ in range(12):
        leituras.append(round(4.0 + random.uniform(-0.05, 0.05), 2))

    # Fase 2 e 3: Aquecimento gradual (+0.35°C por minuto) até passar de 8.0°C
    temp = leituras[-1]
    for _ in range(14):
        temp += 0.35 + random.uniform(-0.03, 0.03)
        leituras.append(round(temp, 2))

    return leituras

def rodar_simulacao():
    # Produto 1: Vacinas/Medicamentos (2°C a 8°C)
    predictor = ColdChainPredictor(
        t_min=2.0, 
        t_max=8.0, 
        window_size=10, 
        sample_interval_min=1.0, 
        alert_horizon_min=15.0
    )

    print("=" * 85)
    print("SIMULAÇÃO 1: Carga Refrigerada (Faixa: 2.0°C a 8.0°C | Horizonte Alerta: 15 min)")
    print("=" * 85)
    print(f"{'Min':<4} | {'Temp (°C)':<10} | {'Status':<18} | {'Taxa (°C/min)':<14} | {'Temp Proj.':<11} | {'TTV (min)':<9} | {'4G?'}")
    print("-" * 85)

    dados = gerar_cenario_sintetico()

    for minuto, temp in enumerate(dados, start=1):
        predictor.adicionar_leitura(temp)
        res = predictor.avaliacao()

        taxa = f"{res.get('taxa_variacao_min'):+.3f}" if res.get('taxa_variacao_min') is not None else "---"
        proj = f"{res.get('temp_projetada')}°C" if res.get('temp_projetada') is not None else "---"
        ttv = f"{res.get('ttv_min')} min" if res.get('ttv_min') is not None else "Estável"
        acionar_4g = "SIM [ALERTA]" if res.get("alerta") else "Não (Sleep)"

        print(f"{minuto:<4} | {temp:<10.2f} | {res['tipo']:<18} | {taxa:<14} | {proj:<11} | {ttv:<9} | {acionar_4g}")

if __name__ == "__main__":
    rodar_simulacao()
