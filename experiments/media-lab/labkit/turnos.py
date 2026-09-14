"""
Turnos de la ventana desatendida: cuándo le toca correr cada `cada_horas` horas.

Todo el cálculo vive en UTC a propósito. `ancla` es un instante concreto (una
fecha ISO con su zona); sumarle horas mueve ese instante, no una hora de reloj
local, así que un cambio de hora (DST) no altera el intervalo real entre
turnos. La zona Europe/Madrid solo entra al mostrar el resultado, nunca al
calcularlo.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

# Un disparo real puede llegar unos segundos o minutos antes de la marca exacta (el reloj de la
# máquina, el arranque de la tarea programada…). Sin este margen esos segundos de adelanto caen
# en el turno ANTERIOR (ya fuera de su tolerancia) y la ventana se lo salta entero hasta el
# siguiente. Se calcula qué turno toca como si ya hubieran pasado estos minutos, pero
# `minutos_desde_inicio` se sigue midiendo desde el `ahora` real, así que puede salir ligeramente
# negativo dentro de este margen.
MARGEN_ADELANTO_MIN = 2


def turno_actual(ahora: datetime, ancla: datetime, cada_horas: int, tolerancia_min: int,
                  ultimo_atendido: str | None) -> dict:
    """turno_inicio = ancla + k·cada_horas, con k el mayor entero tal que turno_inicio <=
    ahora + MARGEN_ADELANTO_MIN (si ahora < ancla, k es negativo: el turno es el anterior al
    ancla). `toca` exige estar entre -MARGEN_ADELANTO_MIN y la tolerancia desde el inicio del
    turno Y que ese turno no sea ya el atendido."""
    if ahora.tzinfo is None or ancla.tzinfo is None:
        raise ValueError("ahora y ancla necesitan zona horaria")
    if cada_horas <= 0:
        raise ValueError("cada_horas debe ser positivo")
    if tolerancia_min <= 0:
        raise ValueError("tolerancia_min debe ser positivo")

    ahora_utc = ahora.astimezone(timezone.utc)
    ancla_utc = ancla.astimezone(timezone.utc)
    paso = timedelta(hours=cada_horas)
    margen = timedelta(minutes=MARGEN_ADELANTO_MIN)
    k = math.floor((ahora_utc + margen - ancla_utc) / paso)
    turno_inicio = ancla_utc + k * paso
    siguiente = turno_inicio + paso
    minutos_desde_inicio = (ahora_utc - turno_inicio).total_seconds() / 60
    turno_inicio_iso = turno_inicio.isoformat(timespec="seconds")

    if turno_inicio_iso == ultimo_atendido:
        motivo, toca = "turno ya atendido", False
    elif not (-MARGEN_ADELANTO_MIN <= minutos_desde_inicio < tolerancia_min):
        motivo, toca = "fuera del turno", False
    else:
        motivo, toca = "toca", True

    return {
        "toca": toca,
        "motivo": motivo,
        "turno_inicio": turno_inicio,
        "siguiente": siguiente,
        "minutos_desde_inicio": minutos_desde_inicio,
        "ahora": ahora_utc,
    }
