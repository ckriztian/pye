from flask import Flask, request, jsonify, render_template
import json
import math
from math import ceil

app = Flask(__name__)

# Cargar la base de conocimiento
with open("peisa_advisor_knowledge_base.json", "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)

# Contexto de la conversación
conversations = {}

def get_node_by_id(node_id):
    for node in knowledge_base:
        if node["id"] == node_id:
            return node
    return None

def replace_variables(text, context):
    if not isinstance(text, str):
        return text
        
    # Reemplazo básico para compatibilidad
    for key, val in context.items():
        if isinstance(val, (int, float, str)):
            text = text.replace("{{"+key+"}}", str(val))
    
    # Usar Jinja2 para manejo más avanzado
    try:
        from jinja2 import Template
        template = Template(text)
        return template.render(**context)
    except:
        return text

def perform_calculation(node, context):
    params = node.get("parametros", {})
    for key, val in params.items():
        context[key] = val

    for action in node.get("acciones", []):
        exec_expression(action, context)

def exec_expression(expr, context):
    try:
        var, val_expr = [x.strip() for x in expr.split("=", 1)]
        val = eval(val_expr, {"__builtins__": None, "ceil": ceil}, context)
        context[var] = val
    except Exception as e:
        print(f"Error evaluando expresión '{expr}': {e}")

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
            if 'valor' in selected:
                conv['context'][node['id']] = selected['valor']
            elif node['id'] == 'seleccion_modelo':
                conv['context']['modelo_seleccionado'] = selected['texto']
            conv['current_node'] = selected['siguiente']
    
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
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)