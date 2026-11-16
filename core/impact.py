import math

G = 9.80665  # m/s²

# ----------------------------------------------------------------------
# Valores padrão de referência. Todos os parâmetros devem ser calibrados
# com a caixa real (ver docs/deteccao_impacto.md).
# ----------------------------------------------------------------------
# WHO/PQS/E004 (CB01-VP.3, CB05-VP.4, VC02-VP.1): caixas térmicas e vaccine
# carriers são qualificados com quedas livres de 1 m sobre concreto.
ALTURA_QUEDA_PQS_M = 1.0

# WHO/PQS/E004/CB05-VP.4 e VC02-VP.1: 22 quedas no ensaio (CB01-VP.3 usa 26).
QUEDAS_ENSAIO_PQS = 22

# Bus-Jacobs et al. (2024), Appendix Table 2: 8 quedas de 30,5 cm + 1 de 61 cm
# (embalagem de 31,8–68 kg, perfil ISTA 4AB) sem alteração relevante na
# qualidade da vacina. Abaixo de 30,5 cm não há ensaio de referência.
ALTURA_MIN_ESTUDO_M = 0.305

LEVE = "LEVE"
MODERADA = "MODERADA"
GRAVE = "GRAVE"


class ImpactDetector:
    """
    Detecção de eventos mecânicos a partir do acelerômetro (MPU-6050).

    Lógica pura: recebe amostras (ax, ay, az) em g, sem depender do hardware.
    Amostras devem chegar em intervalo fixo (sample_interval_ms).

    Eventos (todos com "tipo", "severidade", "alerta" e "t_ms"):
      - QUEDA:          queda livre (+ impacto opcional). Severidade pela
                        altura estimada, comparada com os ensaios da OMS.
      - LIMITE_QUEDAS:  número de quedas relevantes passou do número de
                        quedas do ensaio de qualificação da OMS.
      - IMPACTO:        choque sem queda livre (batida, empilhadeira).
      - TOMBAMENTO:     caixa inclinada além do limiar por tempo prolongado.

    Política: "alerta" é True somente para severidade GRAVE. Esse campo
    indica que é preciso transmitir na hora (4G); os demais eventos são
    apenas registrados no log local.
    """

    def __init__(self,
                 sample_interval_ms=10,
                 accel_range_g=16,
                 # Queda
                 freefall_threshold_g=0.35,
                 freefall_min_ms=80,
                 fall_impact_window_ms=300,
                 altura_moderada_m=ALTURA_MIN_ESTUDO_M,
                 altura_grave_m=ALTURA_QUEDA_PQS_M,
                 max_quedas=QUEDAS_ENSAIO_PQS,
                 # Impacto sem queda livre
                 impact_threshold_g=3.0,
                 impact_grave_g=10.0,
                 refractory_ms=500,
                 # Tombamento
                 tilt_threshold_deg=60.0,
                 tilt_hysteresis_deg=10.0,
                 tilt_min_ms=2000,
                 gravity_alpha=0.1):
        self.dt = sample_interval_ms
        self.sat_g = accel_range_g * 0.98

        self.ff_thr = freefall_threshold_g
        self.ff_min_ms = freefall_min_ms
        self.fall_window_ms = fall_impact_window_ms
        self.altura_moderada = altura_moderada_m
        self.altura_grave = altura_grave_m
        self.max_quedas = max_quedas

        self.impact_thr = impact_threshold_g
        self.impact_grave = impact_grave_g
        self.refractory_ms = refractory_ms

        self.tilt_thr = tilt_threshold_deg
        self.tilt_hyst = tilt_hysteresis_deg
        self.tilt_min_ms = tilt_min_ms
        self.alpha = gravity_alpha
        self.resetar()

    def resetar(self):
        self.t_ms = 0
        self.ref = None          # orientação de referência (vetor unitário)
        self.grav = None         # gravidade estimada (filtro passa-baixa)
        self.angulo = 0.0

        # Queda livre
        self.ff_inicio = None
        self.queda_ms = 0
        self.queda_fim = None
        self.contador_quedas = 0
        self.limite_emitido = False

        # Choque
        self.em_choque = False
        self.choque_inicio = 0
        self.pico = 0.0
        self.saturado = False
        self.ultimo_evento = -10 ** 9

        # Inclinação
        self.tilt_inicio = None
        self.tombado = False

    def calibrar(self, ax, ay, az):
        """Define a orientação atual como 'em pé'. Chamar com a caixa parada."""
        mag = math.sqrt(ax * ax + ay * ay + az * az)
        if mag == 0:
            return
        self.ref = (ax / mag, ay / mag, az / mag)
        self.grav = [ax, ay, az]
        self.tilt_inicio = None
        self.tombado = False

    def adicionar_amostra(self, ax, ay, az):
        """Processa uma amostra. Retorna lista de eventos (normalmente vazia)."""
        self.t_ms += self.dt
        mag = math.sqrt(ax * ax + ay * ay + az * az)

        if self.ref is None:
            self.calibrar(ax, ay, az)
            return []

        eixo_max = max(abs(ax), abs(ay), abs(az))
        eventos = self._verificar_queda_impacto(mag, eixo_max)
        e = self._verificar_inclinacao(ax, ay, az, mag)
        if e:
            eventos.append(e)
        return eventos

    # ------------------------------------------------------------------
    # Queda e impacto
    # ------------------------------------------------------------------

    def _verificar_queda_impacto(self, mag, eixo_max):
        t = self.t_ms

        # Queda livre terminou sem impacto forte (ex.: caiu em superfície macia)
        if (self.queda_fim is not None and not self.em_choque
                and t - self.queda_fim > self.fall_window_ms):
            eventos = self._registrar_queda(pico=None, saturado=False)
            self.queda_fim = None
            return eventos

        # 1. Queda livre: magnitude próxima de 0 g
        if mag < self.ff_thr:
            if self.ff_inicio is None:
                self.ff_inicio = t
            return []

        if self.ff_inicio is not None:
            duracao = t - self.ff_inicio
            self.ff_inicio = None
            if duracao >= self.ff_min_ms:
                self.queda_ms = duracao
                self.queda_fim = t

        # 2. Choque: acumula o pico enquanto estiver acima do limiar
        if mag >= self.impact_thr:
            if not self.em_choque:
                self.em_choque = True
                self.choque_inicio = t
                self.pico = mag
                self.saturado = False
            elif mag > self.pico:
                self.pico = mag
            if eixo_max >= self.sat_g:
                self.saturado = True
            return []

        # 3. Choque terminou: emite o evento
        if self.em_choque:
            self.em_choque = False
            if t - self.ultimo_evento < self.refractory_ms:
                # Repique logo após um evento: não conta como nova queda/impacto
                self.queda_fim = None
                return []
            self.ultimo_evento = t

            if (self.queda_fim is not None
                    and self.choque_inicio - self.queda_fim <= self.fall_window_ms):
                eventos = self._registrar_queda(self.pico, self.saturado)
            else:
                eventos = [self._evento_impacto(t)]
            self.queda_fim = None
            return eventos

        return []

    def _classificar_altura(self, h):
        if h >= self.altura_grave:
            return GRAVE      # acima da altura de qualificação da OMS
        if h >= self.altura_moderada:
            return MODERADA   # faixa ensaiada (Bus-Jacobs) e coberta pela OMS
        return LEVE

    def _registrar_queda(self, pico, saturado):
        t_s = self.queda_ms / 1000.0
        h = 0.5 * G * t_s * t_s
        sev = self._classificar_altura(h)

        if h >= self.altura_moderada:
            self.contador_quedas += 1

        eventos = [{
            "tipo": "QUEDA",
            "severidade": sev,
            "alerta": sev == GRAVE,
            "t_ms": self.queda_fim - self.queda_ms,
            "queda_livre_ms": self.queda_ms,
            "altura_estimada_m": round(h, 2),
            "pico_g": round(pico, 2) if pico is not None else None,
            "saturado": saturado,
            "contador_quedas": self.contador_quedas,
        }]

        if self.contador_quedas > self.max_quedas and not self.limite_emitido:
            self.limite_emitido = True
            eventos.append({
                "tipo": "LIMITE_QUEDAS",
                "severidade": GRAVE,
                "alerta": True,
                "t_ms": self.t_ms,
                "contador_quedas": self.contador_quedas,
                "limite": self.max_quedas,
            })
        return eventos

    def _evento_impacto(self, t):
        # Sem queda livre não há altura; usa o pico. Se o sensor saturou,
        # o pico real é desconhecido (>= fundo de escala) e trata-se como grave.
        grave = self.saturado or self.pico >= self.impact_grave
        return {
            "tipo": "IMPACTO",
            "severidade": GRAVE if grave else MODERADA,
            "alerta": grave,
            "t_ms": self.choque_inicio,
            "pico_g": round(self.pico, 2),
            "saturado": self.saturado,
            "duracao_ms": t - self.choque_inicio,
        }

    # ------------------------------------------------------------------
    # Tombamento
    # ------------------------------------------------------------------

    def _verificar_inclinacao(self, ax, ay, az, mag):
        # Só atualiza a gravidade estimada quando a caixa está quase estática
        if 0.8 < mag < 1.2:
            a = self.alpha
            g = self.grav
            g[0] += a * (ax - g[0])
            g[1] += a * (ay - g[1])
            g[2] += a * (az - g[2])

        g = self.grav
        gmag = math.sqrt(g[0] * g[0] + g[1] * g[1] + g[2] * g[2])
        if gmag == 0:
            return None

        r = self.ref
        cos_ang = (g[0] * r[0] + g[1] * r[1] + g[2] * r[2]) / gmag
        cos_ang = max(-1.0, min(1.0, cos_ang))
        self.angulo = math.acos(cos_ang) * 180.0 / math.pi

        if self.angulo > self.tilt_thr:
            if self.tilt_inicio is None:
                self.tilt_inicio = self.t_ms
            if not self.tombado and self.t_ms - self.tilt_inicio >= self.tilt_min_ms:
                self.tombado = True
                return {
                    "tipo": "TOMBAMENTO",
                    "severidade": GRAVE,
                    "alerta": True,
                    "t_ms": self.tilt_inicio,
                    "angulo_graus": round(self.angulo, 1),
                }
        elif self.angulo < self.tilt_thr - self.tilt_hyst:
            self.tilt_inicio = None
            self.tombado = False

        return None
