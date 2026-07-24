


def es_continuacion_valida(generado, candidato, opciones):
    extendido = generado + candidato
    for opcion in opciones:
        if opcion.startswith(extendido):
            return True
    return False

def esta_completo(generado, opciones):
    return generado in opciones




if generado.count(".") > 1:
    return False
else:
    return True

if generado.index("-") == 0:
    return True
else
    refurn False