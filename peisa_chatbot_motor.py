
import json
import math

with open("peisa_advisor_knowledge_base.json", "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)

context = {}

def get_node_by_id(node_id):
    for node in knowledge_base:
        if node["id"] == node_id:
            return node
    return None

def replace_variables(text):
    for key, val in context.items():
        text = text.replace("{{"+key+"}}", str(val))
    return text

def ask_question(node):
    print("\n" + node["pregunta"])
    if "opciones" in node:
        for i, option in enumerate(node["opciones"], 1):
            print(f"{i}. {option['texto']}")
        while True:
            choice = input("Elige una opción: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(node["opciones"]):
                selected = node["opciones"][int(choice)-1]
                if "valor" in selected:
                    context[node["id"]] = selected["valor"]
                else:
                    # Por defecto guardamos el texto como identificador del modelo
                    context["modelo_seleccionado"] = selected["texto"]
                return selected
            else:
                print("Opción inválida.")
    elif "tipo" in node and node["tipo"] == "entrada_usuario":
        if "variable" in node:
            val = input("Respuesta: ").strip()
            context[node["variable"]] = try_parse_number(val)
            return None
        elif "variables" in node:
            for var in node["variables"]:
                val = input(f"Ingrese {var}: ").strip()
                context[var] = try_parse_number(val)
            return None

def try_parse_number(value):
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except:
        return value

def perform_calculation(node):
    params = node.get("parametros", {})
    for key, val in params.items():
        context[key] = val

    for action in node.get("acciones", []):
        exec_expression(action, context)

def exec_expression(expr, context):
    try:
        var, val_expr = [x.strip() for x in expr.split("=", 1)]
        from math import ceil
        val = eval(val_expr, {"__builtins__": None, "ceil": ceil}, context)
        context[var] = val
    except Exception as e:
        print(f"Error evaluando expresión '{expr}': {e}")

def run_chatbot():
    current_node_id = "inicio"
    while True:
        node = get_node_by_id(current_node_id)
        if node is None:
            print("Nodo no encontrado:", current_node_id)
            break

        node_type = node.get("tipo", "")
        if node_type == "question" or "pregunta" in node:
            response = ask_question(node)
            if response is None:
                current_node_id = node.get("siguiente")
            else:
                current_node_id = response["siguiente"]

        elif node_type == "calculo":
            perform_calculation(node)
            current_node_id = node.get("siguiente")

        elif node_type == "respuesta":
            print("\n" + replace_variables(node["texto"]))
            if "opciones" in node:
                for i, option in enumerate(node["opciones"], 1):
                    print(f"{i}. {option['texto']}")
                while True:
                    choice = input("Elige una opción: ").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(node["opciones"]):
                        current_node_id = node["opciones"][int(choice)-1]["siguiente"]
                        break
                    else:
                        print("Opción inválida.")
            else:
                break
        else:
            print("Tipo de nodo desconocido:", node_type)
            break

if __name__ == "__main__":
    print("Bienvenido al sistema experto PEISA Advisor")
    run_chatbot()
