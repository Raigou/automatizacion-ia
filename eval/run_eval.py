import json
from pathlib import Path

from agent.builder import clasificar_ticket, construir_agente


def evaluar() -> None:
    ruta = Path(__file__).parent / "dataset.json"
    casos = json.loads(ruta.read_text(encoding="utf-8"))
    agente = construir_agente()

    aciertos_urgencia = 0
    aciertos_categoria = 0
    errores = 0

    for i, caso in enumerate(casos, start=1):
        try:
            pred = clasificar_ticket(agente, caso["texto"])
        except Exception as e:
            errores += 1
            print(f"{i:>2}. ERROR: {e}")
            continue

        ok_urgencia = pred.urgente == caso["urgente"]
        ok_categoria = pred.categoria == caso["categoria"]
        aciertos_urgencia += ok_urgencia
        aciertos_categoria += ok_categoria

        print(
            f"{i:>2}. urgencia {'OK ' if ok_urgencia else 'MAL'} "
            f"(esperado {caso['urgente']}, obtuvo {pred.urgente}) | "
            f"categoría {'OK ' if ok_categoria else 'MAL'} "
            f"(esperado {caso['categoria']}, obtuvo {pred.categoria})"
        )

    total = len(casos)
    print("-" * 40)
    print(f"Urgencia:  {aciertos_urgencia}/{total} ({aciertos_urgencia / total:.0%})")
    print(f"Categoría: {aciertos_categoria}/{total} ({aciertos_categoria / total:.0%})")
    print(f"Errores:   {errores}")


if __name__ == "__main__":
    evaluar()