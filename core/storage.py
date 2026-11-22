import os

import config

CABECALHO = "timestamp,tipo,alerta,temp_atual,temp_projetada,taxa_variacao_min,ttv_min\n"


def _campo(valor):
    return "" if valor is None else str(valor)


class LocalStorage:
    """Logger CSV na Flash do ESP32. Uma linha por avaliação do predictor."""
    def __init__(self, filename=None):
        self.filename = filename or config.LOG_FILENAME
        try:
            os.stat(self.filename)
        except OSError:
            with open(self.filename, "w") as f:
                f.write(CABECALHO)

    def registrar(self, timestamp, res):
        """Acrescenta uma linha ao CSV. Campos ausentes ficam vazios."""
        linha = ",".join([
            _campo(timestamp),
            _campo(res.get("tipo", res.get("status"))),
            _campo(res.get("alerta", False)),
            _campo(res.get("temp_atual")),
            _campo(res.get("temp_projetada")),
            _campo(res.get("taxa_variacao_min")),
            _campo(res.get("ttv_min")),
        ]) + "\n"
        with open(self.filename, "a") as f:
            f.write(linha)
