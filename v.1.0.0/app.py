from flask import Flask, request, jsonify, render_template
import json
import math
from math import ceil
from bisect import bisect_left

app = Flask(__name__)

# Cargar la base de conocimiento
with open("peisa_advisor_knowledge_base.json", "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)

# Contexto de la conversación
conversations = {}

# Base de datos de modelos de radiadores
RADIATOR_MODELS = {
    "TROPICAL 350": {
        "type": "principal",
        "installation": ["superficie"],
        "style": "clasico",
        "colors": ["blanco"],
        "coeficiente": 0.75,
        "potencia": 185,
        "description": "Radiador de aluminio inyectado, ideal para calefacción principal"
    },
    "TROPICAL 500": {
        "type": "principal",
        "installation": ["superficie"],
        "style": "clasico",
        "colors": ["blanco"],
        "coeficiente": 1.0,
        "potencia": 185,
        "description": "Radiador de aluminio inyectado, alto rendimiento"
    },
    "TROPICAL 600": {
        "type": "principal",
        "installation": ["superficie"],
        "style": "clasico",
        "colors": ["blanco"],
        "coeficiente": 1.16,
        "potencia": 185,
        "description": "Radiador de aluminio inyectado, máxima potencia"
    },
    "BROEN 350": {
        "type": ["principal", "complementaria"],
        "installation": ["superficie"],
        "style": "moderno",
        "colors": ["blanco", "negro"],
        "coeficiente": 0.75,
        "potencia": 185,
        "description": "Diseño discreto y moderno, disponible en dos colores"
    },
    "BROEN 500": {
        "type": ["principal", "complementaria"],
        "installation": ["superficie"],
        "style": "moderno",
        "colors": ["blanco", "negro"],
        "coeficiente": 1.0,
        "potencia": 185,
        "description": "Versión intermedia de la línea Broen"
    },
    "BROEN 600": {
        "type": ["principal", "complementaria"],
        "installation": ["superficie"],
        "style": "moderno",
        "colors": ["blanco", "negro"],
        "coeficiente": 1.16,
        "potencia": 185,
        "description": "Máxima potencia en la línea Broen clásica"
    },
    "BROEN PLUS 700": {
        "type": ["principal", "complementaria"],
        "installation": ["empotrada", "superficie"],
        "style": "moderno",
        "colors": ["blanco"],
        "coeficiente": 1.27,
        "potencia": 185,
        "description": "Emisores mixtos con gran versatilidad de instalación"
    },
    "BROEN PLUS 800": {
        "type": ["principal", "complementaria"],
        "installation": ["empotrada", "superficie"],
        "style": "moderno",
        "colors": ["blanco"],
        "coeficiente": 1.4,
        "potencia": 185,
        "description": "Alto rendimiento con diseño de líneas modernas"
    },
    "BROEN PLUS 1000": {
        "type": ["principal", "complementaria"],
        "installation": ["empotrada", "superficie"],
        "style": "moderno",
        "colors": ["blanco"],
        "coeficiente": 1.65,
        "potencia": 185,
        "description": "Máxima potencia en la línea Broen Plus"
    },
    "GAMMA 500": {
        "type": "complementaria",
        "installation": ["superficie"],
        "style": "moderno",
        "colors": ["blanco"],
        "coeficiente": 0.93,
        "potencia": 185,
        "description": "Radiador de aluminio con alma de acero, resistente a la corrosión"
    },
    "TOALLERO SCALA": {
        "type": "toallero",
        "installation": ["superficie"],
        "style": "moderno",
        "colors": ["blanco", "cromo"],
        "potencia": 632,
        "description": "Especial para baños, mantiene toallas secas y calientes"
    }
}

def get_node_by_id(node_id):
    for node in knowledge_base:
        if node["id"] == node_id:
            return node
    return None

def replace_variables(text, context):
    if not isinstance(text, str):
        return text
        
    for key, val in context.items():
        if isinstance(val, (int, float, str)):
            text = text.replace("{{"+key+"}}", str(val))
    
    try:
        from jinja2 import Template
        template = Template(text)
        return template.render(**context)
    except:
        return text

def filter_radiators(radiator_type, installation, style, color, heat_load):
    """Filtra radiadores según las preferencias del usuario"""
    recommended = []
    
    for name, model in RADIATOR_MODELS.items():
        # Filtrar por tipo de radiador (aceptar si coincide o si está en la lista)
        if isinstance(model.get('type'), str):
            if model.get('type') != radiator_type:
                continue
        else:
            if radiator_type not in model.get('type', []):
                continue
                
        # Filtrar por tipo de instalación
        if installation != 'cualquiera':
            if isinstance(model['installation'], str):
                if model['installation'] != installation:
                    continue
            elif installation not in model['installation']:
                continue
                
        # Filtrar por estilo
        if style != 'cualquiera' and model['style'] != style:
            continue
            
        # Filtrar por color
        if color != 'cualquiera' and color not in model['colors']:
            continue
            
        recommended.append({
            'name': name,
            'description': model['description'],
            'coeficiente': model.get('coeficiente', 1.0),
            'potencia': model['potencia'],
            'colors': model['colors']
        })
    
    # Ordenar por mejor ajuste a la carga térmica
    recommended.sort(key=lambda x: abs(x['potencia'] * x['coeficiente'] - heat_load))
    
    return recommended[:3]  # Top 3 recomendaciones

def format_radiator_recommendations(models, heat_load):
    """Formatea las recomendaciones para mostrarlas al usuario"""
    if not models or not isinstance(models, list):
        return "No encontramos modelos que coincidan con tus requisitos. Por favor intenta con diferentes parámetros."
    
    result = []
    for i, model in enumerate(models, 1):
        try:
            potencia_efectiva = model.get('potencia', 0) * model.get('coeficiente', 1)
            modulos_estimados = ceil(heat_load / potencia_efectiva) if potencia_efectiva > 0 else 0
            
            model_info = [
                f"{i}. {model.get('name', 'Modelo desconocido')}",
                f"   - Potencia efectiva: {potencia_efectiva:.0f} kcal/h",
                f"   - Módulos estimados: {modulos_estimados}",
                f"   - Descripción: {model.get('description', 'Sin descripción disponible')}"
            ]
            
            if 'colors' in model:
                model_info.append(f"   - Colores disponibles: {', '.join(model['colors'])}")
                
            result.append("\n".join(model_info))
        except Exception as e:
            print(f"Error formateando modelo {model}: {e}")
            continue
    
    return "\n\n".join(result) if result else "No se pudieron generar recomendaciones."

def perform_calculation(node, context):
    params = node.get("parametros", {})
    for key, val in params.items():
        context[key] = val

    for action in node.get("acciones", []):
        exec_expression(action, context)

def exec_expression(expr, context):
    try:
        # Agregar funciones especiales al contexto
        local_context = {
            'filter_radiators': filter_radiators,
            'format_radiator_recommendations': format_radiator_recommendations,
            'ceil': ceil,
            'context': context  # Pasamos el contexto completo
        }
        
        # Dividir la expresión en variable y valor
        var, val_expr = [x.strip() for x in expr.split("=", 1)]
        
        # Reemplazar context['variable'] por simplemente variable
        val_expr = val_expr.replace("context['", "").replace("']", "")
        
        # Evaluar la expresión con las variables del contexto
        val = eval(val_expr, {"__builtins__": None}, {**context, **local_context})
        context[var] = val
    except Exception as e:
        print(f"Error evaluando expresión '{expr}': {e}")
        raise

@app.route('/')
def home():
    return render_template('chat.html')

@app.route('/start', methods=['POST'])
def start_conversation():
    conversation_id = request.json.get('conversation_id', 'default')
    conversations[conversation_id] = {
        'current_node': 'inicio',
        'context': {}
    }
    return get_next_message(conversation_id)

@app.route('/reply', methods=['POST'])
def handle_reply():
    conversation_id = request.json.get('conversation_id', 'default')
    option_index = request.json.get('option_index')
    input_values = request.json.get('input_values', {})
    
    if conversation_id not in conversations:
        return jsonify({'error': 'Conversación no encontrada'}), 404
    
    conv = conversations[conversation_id]
    node = get_node_by_id(conv['current_node'])
    
    if not node:
        return jsonify({'error': 'Nodo no encontrado'}), 404
    
    # Procesar la respuesta del usuario
    if node.get('tipo') == 'entrada_usuario':
        try:
            if 'variable' in node:
                value = input_values.get('value', '').replace(',', '.')
                conv['context'][node['variable']] = float(value)
            elif 'variables' in node:
                for var in node['variables']:
                    value = input_values.get(var, '').replace(',', '.')
                    conv['context'][var] = float(value)
            conv['current_node'] = node['siguiente']
        except ValueError:
            return jsonify({
                'error': 'Por favor ingrese valores numéricos válidos (ej: 4.5, 3.75)',
                'node_id': node['id'],
                'type': 'input_error',
                'text': node['pregunta']
            })
    
    elif 'opciones' in node:
        if option_index is not None and 0 <= option_index < len(node['opciones']):
            selected = node['opciones'][option_index]
            # Guardar el valor usando el ID del nodo como clave
            conv['context'][node['id']] = selected.get('valor', selected['texto'])
            # Guardar también el texto para mostrar
            conv['context'][f"{node['id']}_texto"] = selected['texto']
            conv['current_node'] = selected['siguiente']
    
    # Debug: Mostrar el contexto completo
    print("Contexto completo:", conv['context'])
    
    return get_next_message(conversation_id)

def get_next_message(conversation_id):
    conv = conversations[conversation_id]
    node = get_node_by_id(conv['current_node'])
    
    if not node:
        return jsonify({'error': 'Nodo no encontrado'}), 404
    
    response = {
        'conversation_id': conversation_id,
        'node_id': node['id']
    }
    
    # Procesar según el tipo de nodo
    if node.get('tipo') == 'calculo':
        perform_calculation(node, conv['context'])
        conv['current_node'] = node['siguiente']
        return get_next_message(conversation_id)
    elif 'pregunta' in node:
        response['type'] = 'question'
        response['text'] = replace_variables(node['pregunta'], conv['context'])
        
        if 'opciones' in node:
            response['options'] = [opt['texto'] for opt in node['opciones']]
        elif node.get('tipo') == 'entrada_usuario':
            if 'variable' in node:
                response['input_type'] = 'number'
                response['input_label'] = 'Ingrese el valor'
            elif 'variables' in node:
                response['input_type'] = 'multiple'
                response['inputs'] = [
                    {'name': var, 'label': f'Ingrese {var} (metros)', 'type': 'number'}
                    for var in node['variables']
                ]
    elif node.get('tipo') == 'respuesta':
        response['type'] = 'response'
        response['text'] = replace_variables(node['texto'], conv['context'])
        
        if 'opciones' in node:
            response['options'] = [opt['texto'] for opt in node['opciones']]
        else:
            response['is_final'] = True
    elif node.get('tipo') == 'opciones_dinamicas':
        # Manejar opciones dinámicas basadas en modelos recomendados
        if 'modelos_recomendados' in conv['context']:
            models = conv['context']['modelos_recomendados']
            response['type'] = 'question'
            response['text'] = node['pregunta']
            response['options'] = [
                {
                    'texto': f"{model['name']} (Potencia: {model['potencia']*model['coeficiente']:.0f} kcal/h)",
                    'valor': model['name'],
                    'coeficiente': model['coeficiente'],
                    'potencia': model['potencia'],
                    'siguiente': node['siguiente']
                } for model in models
            ]
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)