class ColdChainPredictor:
    def __init__(self, t_min, t_max, window_size=10, sample_interval_min=1.0, alert_horizon_min=15.0):
        self.t_min = t_min
        self.t_max = t_max
        self.n = window_size
        self.dt = sample_interval_min
        self.horizon = alert_horizon_min
        self.window = []

        self.sum_x = sum(range(self.n))
        self.sum_x2 = sum(x * x for x in range(self.n))
        self.denom = (self.n * self.sum_x2) - (self.sum_x ** 2)

    def configurar_faixa(self, novo_t_min, novo_t_max):
        # Ajusta o intervalo de temperatura do modelo transportado.
        self.t_min = novo_t_min
        self.t_max = novo_t_max

    def adicionar_leitura(self, temp):
        self.window.append(temp)
        if len(self.window) > self.n:
            self.window.pop(0)

    def avaliacao(self):
        if not self.window:
            return {"status": "AGUARDANDO DADOS"}

        temp_atual = self.window[-1]

        # 1. Violação real imediata
        if temp_atual > self.t_max or temp_atual < self.t_min:
            return {
                "alerta": True,
                "tipo": "VIOLACAO_REAL",
                "temp_atual": temp_atual,
                "taxa_variacao_min": None,
                "ttv_min": 0.0
            }

        # Janela mínima não foi preenchida. Coleta de dados em andamento.
        if len(self.window) < self.n:
            return {
                "alerta": False,
                "tipo": "COLETANDO_JANELA",
                "temp_atual": temp_atual
            }

        # 2. Calcula a taxa de variação (inclinação da regressão linear)
        sum_y = sum(self.window)
        sum_xy = sum(i * y for i, y in enumerate(self.window))

        inclinacao_por_amostra = ((self.n * sum_xy) - (self.sum_x * sum_y)) / self.denom
        taxa_por_minuto = inclinacao_por_amostra / self.dt

        # 3. Calcula o Time-to-Violation (TTV) baseado na variação e no intervalo de temperaturado produto.
        ttv = float('inf')
        if taxa_por_minuto > 0:
            ttv = (self.t_max - temp_atual) / taxa_por_minuto
        elif taxa_por_minuto <= 0:
            ttv = (self.t_min - temp_atual) / taxa_por_minuto

        violacao_prevista = ttv <= self.horizon

        return {
            "alerta": violacao_prevista,
            "tipo": "VIOLACAO_PREVISTA" if violacao_prevista else "NORMAL",
            "temp_atual": temp_atual,
            "temp_projetada": round(temp_atual + (taxa_por_minuto * self.horizon), 2),
            "taxa_variacao_min": round(taxa_por_minuto, 3),
            "ttv_min": round(ttv, 1) if ttv != float('inf') else None
        }
