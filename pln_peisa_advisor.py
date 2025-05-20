
import re

def interpretar_texto(texto):
    resultado = {}

    # Buscar dimensiones (ej. 4x5x2.4 o 4 x 5 x 2.4)
    m = re.search(r'(\d+(\.\d+)?)\s*(x|por|×)\s*(\d+(\.\d+)?)\s*(x|por|×)?\s*(\d+(\.\d+)?)?', texto.lower())
    if m:
        resultado['largo'] = float(m.group(1))
        resultado['ancho'] = float(m.group(4))
        if m.group(7):
            resultado['alto'] = float(m.group(7))
        else:
            resultado['alto'] = 2.4  # valor por defecto

    # Buscar superficie (ej. "40 m2", "40 metros cuadrados")
    m2 = re.search(r'(\d+(\.\d+)?)\s*(m2|metros cuadrados|mts2)', texto.lower())
    if m2:
        resultado['superficie'] = float(m2.group(1))

    # Buscar tipo de sistema
    if "radiador" in texto.lower():
        resultado['tipo_producto'] = 'radiador'
    elif "piso radiante" in texto.lower() or "piso" in texto.lower():
        resultado['tipo_producto'] = 'piso radiante'

    # Buscar ubicación para zona
    if any(x in texto.lower() for x in ["sur", "patagonia", "chubut", "santa cruz", "bariloche", "ushuaia"]):
        resultado['zona_geografica'] = 'sur'
    elif any(x in texto.lower() for x in ["norte", "cordoba", "tucuman", "salta", "santiago del estero"]):
        resultado['zona_geografica'] = 'norte'

    return resultado

# Ejemplo de prueba
if __name__ == "__main__":
    consulta = input("Escribí tu consulta: ")
    vars_extraidas = interpretar_texto(consulta)
    print("\nVariables detectadas:")
    for k, v in vars_extraidas.items():
        print(f"  {k}: {v}")
