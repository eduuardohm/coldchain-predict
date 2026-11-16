# Detecção de impacto, queda e tombamento

O módulo [`core/impact.py`](../core/impact.py) analisa as leituras do acelerômetro (MPU-6050) e detecta quedas, batidas e tombamento da caixa.

> [!IMPORTANT]
> **Os valores padrão são apenas uma referência e todos devem ser calibrados com a caixa real.**
> Parte deles vem dos ensaios da OMS para caixas de vacina e da literatura. O restante foi definido pelo grupo. Os valores que vêm da OMS só fazem sentido para caixas pré-qualificadas pela OMS (categoria PQS E004).

## Eventos

| Evento | Quando ocorre | Severidade |
|---|---|---|
| `QUEDA` | queda livre, com ou sem impacto no final | `LEVE` (< 0,305 m), `MODERADA` (até 1 m) ou `GRAVE` (≥ 1 m) |
| `LIMITE_QUEDAS` | o número de quedas de pelo menos 0,305 m passou de 22 | `GRAVE` |
| `IMPACTO` | batida sem queda livre (empilhadeira, outra carga) | `MODERADA` (≥ 3 g) ou `GRAVE` (≥ 10 g ou sensor saturado) |
| `TOMBAMENTO` | caixa inclinada mais de 60° por pelo menos 2 s | `GRAVE` |

Todo evento tem o campo `alerta`, que é `True` só quando a severidade é `GRAVE`. Nesse caso o aparelho envia o alerta pelo 4G na hora. Os outros eventos ficam no log local. Um alerta indica que a caixa **precisa ser inspecionada**, e não que ela foi danificada.

## Parâmetros

Todos são argumentos do construtor `ImpactDetector(...)`.

**Gerais**

| Parâmetro | O que é | Padrão | Origem |
|---|---|---|---|
| `sample_interval_ms` | Intervalo entre duas leituras do acelerômetro. Precisa ser igual à taxa real de leitura, porque o detector mede o tempo contando amostras | 10 ms (100 Hz) | **Grupo:** erro de cerca de ±4 cm na altura estimada perto de 1 m |
| `accel_range_g` | Fundo de escala configurado no sensor. Leituras perto desse valor são marcadas como `saturado` | 16 g | **Hardware:** máximo do MPU-6050. O driver precisa configurar ±16 g, porque o padrão do chip é ±2 g |

**Queda**

| Parâmetro | O que é | Padrão | Origem |
|---|---|---|---|
| `freefall_threshold_g` | Abaixo dessa aceleração total, a caixa é considerada em queda livre | 0,35 g | **Grupo** |
| `freefall_min_ms` | Duração mínima da queda livre para contar como queda. Evita confundir ruído com queda | 80 ms (≈ 3 cm) | **Grupo** |
| `fall_impact_window_ms` | Tempo máximo entre o fim da queda livre e o impacto para os dois serem tratados como um único evento `QUEDA` | 300 ms | **Grupo** |
| `altura_moderada_m` | A partir dessa altura, a queda é `MODERADA` e entra na contagem de quedas | 0,305 m | **Literatura:** menor queda ensaiada por Bus-Jacobs et al. (2024), que aplicou quedas de 30,5 e 61 cm sem dano à vacina |
| `altura_grave_m` | A partir dessa altura, a queda é `GRAVE` e gera alerta | 1,0 m | **OMS:** os protocolos PQS E004 qualificam a caixa com quedas de 1 m sobre concreto |
| `max_quedas` | Número de quedas (de pelo menos `altura_moderada_m`) acima do qual é emitido `LIMITE_QUEDAS` | 22 | **OMS:** número de quedas do ensaio nos protocolos CB05 e VC02 (o CB01 usa 26) |

**Impacto**

| Parâmetro | O que é | Padrão | Origem |
|---|---|---|---|
| `impact_threshold_g` | A partir dessa aceleração, a leitura é considerada um choque. Abaixo dela, é vibração normal | 3 g | **Grupo:** acima dos solavancos de estrada |
| `impact_grave_g` | Pico a partir do qual um impacto sem queda é `GRAVE` | 10 g | **Grupo** |
| `refractory_ms` | Depois de um evento, choques nesse intervalo são ignorados, para que o repique da caixa não conte como um novo evento | 500 ms | **Grupo** |

**Tombamento**

| Parâmetro | O que é | Padrão | Origem |
|---|---|---|---|
| `tilt_threshold_deg` | Inclinação, em relação à posição calibrada, a partir da qual a caixa é considerada tombada | 60° | **Grupo:** a OMS não trata de orientação |
| `tilt_hysteresis_deg` | Margem para considerar que a caixa voltou à posição: ela precisa ficar abaixo de `tilt_threshold_deg` menos esse valor. Evita alertas repetidos quando a caixa fica perto do limite | 10° | **Grupo** |
| `tilt_min_ms` | Tempo mínimo inclinada para gerar `TOMBAMENTO`. Evita alertas quando a caixa só balança | 2 s | **Grupo** |
| `gravity_alpha` | Peso de cada leitura nova no filtro que estima a direção da gravidade. Quanto menor, mais suave e mais lento | 0,1 | **Grupo** |

A vibração de estrada não gera alerta. Os protocolos da OMS a tratam como uma condição que a caixa precisa suportar, e o estudo de Bus-Jacobs não encontrou efeito dela sobre a vacina.

## Exemplo de uso

O detector recebe uma leitura (ax, ay, az) em g por vez e devolve uma lista de eventos, que normalmente vem vazia. A primeira leitura define a posição "em pé" da caixa.

```python
from core.impact import ImpactDetector

det = ImpactDetector()  # valores padrão, 100 Hz

# 1 s com a caixa parada, em pé (calibra a orientação)
for _ in range(100):
    det.adicionar_amostra(0.0, 0.0, 1.0)

# Queda de ~1,2 m: 490 ms em queda livre (≈ 0 g)
for _ in range(49):
    det.adicionar_amostra(0.0, 0.0, 0.02)

# Impacto no chão (o sensor satura em 16 g) e repouso
eventos = []
for az in (9.0, 16.0, 16.0, 11.0, 1.0):
    eventos += det.adicionar_amostra(0.0, 0.0, az)

for e in eventos:
    print(e)
```

Saída:

```
{'tipo': 'QUEDA', 'severidade': 'GRAVE', 'alerta': True, 't_ms': 1010, 'queda_livre_ms': 490, 'altura_estimada_m': 1.18, 'pico_g': 16.0, 'saturado': True, 'contador_quedas': 1}
```

A queda de cerca de 1,2 m foi estimada em 1,18 m. Como passa de 1 m, ela é `GRAVE` e gera alerta. O pico ficou limitado a 16 g (`saturado: True`), mas isso não afeta a classificação, que usa a altura.

## Teste com cenário sintético

O script [`tests/synthetic_impact.py`](../tests/synthetic_impact.py) simula um transporte completo a 100 Hz e confere se cada evento foi detectado com a severidade certa:

```
py tests/synthetic_impact.py
```

Saída (resumida):

```
SIMULAÇÃO 1: Transporte com quedas, batidas e tombamento (100 Hz, ±16 g)
t (ms)  | Fase          | Evento        | Sev.     | 4G?     | Detalhes
6540    | Parado        | QUEDA         | LEVE     | Não     | altura≈0.14 m, pico=None g, nº 0
8620    | Queda 50 cm   | QUEDA         | MODERADA | Não     | altura≈0.5 m, pico=7.51 g, nº 1
11190   | Queda 1,2 m   | QUEDA         | GRAVE    | SIM     | altura≈1.18 m, pico=16.0 g (saturado), nº 2
13230   | Batida leve   | IMPACTO       | MODERADA | Não     | pico=4.33 g, duração=20 ms
15280   | Batida forte  | IMPACTO       | GRAVE    | SIM     | pico=16.03 g (saturado), duração=40 ms
20040   | Deitada       | TOMBAMENTO    | GRAVE    | SIM     | ângulo=89.8°
Eventos: 6 obtidos / 6 esperados
RESULTADO: OK

SIMULAÇÃO 2: Quedas acumuladas (23 × 50 cm, limite PQS = 22) — só alertas
t (ms)  | Fase          | Evento        | Sev.     | 4G?     | Detalhes
31720   | Queda 23      | LIMITE_QUEDAS | GRAVE    | SIM     | 23 quedas > limite PQS de 22
Eventos: 24 obtidos / 24 esperados
RESULTADO: OK
```

A simulação 1 também passa por 3 s de vibração de estrada e por um buraco de 1,8 g. Nenhum dos dois gerou evento, como esperado. A queda de 15 cm aparece sem pico (`pico=None`) porque o impacto dela ficou abaixo de 3 g.

## Por que as quedas são medidas em altura, e não em g

As fontes definem as quedas pela **altura**, não por aceleração. Nenhuma delas traz valores em g. Além disso, o pico de aceleração muda muito conforme a superfície e o lado da caixa que bate, e pode passar do limite de ±16 g do sensor.

A altura é estimada pelo tempo em que o acelerômetro fica em queda livre (perto de 0 g), com $h = \tfrac{1}{2} g t^2$. Uma queda de 1 m dura cerca de 452 ms. Assim dá para comparar a queda diretamente com os ensaios, e a medida continua certa mesmo quando o sensor satura.

## Calibração

1. Montar o aparelho na caixa real, carregada com uma carga simulada.
2. Soltar a caixa de alturas conhecidas (por exemplo 0,3 m, 0,6 m e 1 m), caindo sobre face, aresta e canto.
3. Comparar a `altura_estimada_m` com a altura real e ajustar `freefall_threshold_g`, se necessário.
4. Usar o pico em g medido nas quedas de 1 m como referência para `impact_grave_g`.
5. Se a caixa não for qualificada pela OMS, definir `altura_grave_m` e `max_quedas` a partir desses ensaios.

## Limitações

- **Rotação:** se a caixa girar durante a queda e o sensor estiver longe do centro, a queda livre pode não ser detectada. O sensor deve ficar perto do centro da caixa.
- **Margem de erro:** com ±4 cm de erro, uma queda real de 1,0 m pode ser estimada abaixo de 1 m e não gerar alerta.
- **Limite do ensaio da OMS:** a OMS ensaia uma única caixa nova de cada modelo, em condições controladas. Uma caixa desgastada pode falhar com menos.
- **Validação:** até agora o módulo só foi testado com dados sintéticos ([`tests/synthetic_impact.py`](../tests/synthetic_impact.py)).

## Referências

1. Bus-Jacobs, L. et al. (2024). Effects of Shock and Vibration on Product Quality during Last-Mile Transportation of Ebola Vaccine under Refrigerated Conditions. *Emerging Infectious Diseases*, 30(4), 757–760. https://doi.org/10.3201/eid3004.231060. Alturas de queda: [Appendix Table 2](https://wwwnc.cdc.gov/eid/article/30/4/23-1060-app1.pdf).
2. WHO/PQS/E004/CB05-VP.4 (2024). *Vaccine cold box with freeze-prevention technology.* https://extranet.who.int/prequal/sites/default/files/document_files/WHO_PQS_E004_CB05_VP.4.pdf
3. WHO/PQS/E004/VC02-VP.1 (2018). *Vaccine carrier with freeze-prevention technology.*
4. WHO/PQS/E004/CB01-VP.3 (2018). *Vaccine cold box.*
5. WHO. *E004: Cold boxes and vaccine carriers.* https://extranet.who.int/prequal/immunization-devices/e004-cold-boxes-and-vaccine-carriers
