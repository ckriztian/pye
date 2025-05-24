from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import math
from math import ceil
from bisect import bisect_left

app = FastAPI(title="PEISA - SOLDASUR S.A", description="Asistente para cálculos de calefacción")

# Modelos Pydantic para request/response
class StartConversationRequest(BaseModel):
    conversation_id: str

class ReplyRequest(BaseModel):
    conversation_id: str
    option_index: Optional[int] = None
    input_values: Optional[Dict[str, Any]] = {}

class ConversationResponse(BaseModel):
    conversation_id: str
    node_id: str
    type: Optional[str] = None
    text: Optional[str] = None
    options: Optional[List[str]] = None
    input_type: Optional[str] = None
    input_label: Optional[str] = None
    inputs: Optional[List[Dict[str, Any]]] = None
    is_final: Optional[bool] = None
    error: Optional[str] = None

# Cargar la base de conocimiento
try:
    with open("peisa_advisor_knowledge_base.json", "r", encoding="utf-8") as f:
        knowledge_base = json.load(f)
except FileNotFoundError:
    print("Advertencia: No se encontró el archivo peisa_advisor_knowledge_base.json")
    knowledge_base = []

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

def get_node_by_id(node_id: str) -> Optional[Dict[str, Any]]:
    """Busca un nodo por su ID en la base de conocimiento"""
    for node in knowledge_base:
        if node["id"] == node_id:
            return node
    return None

def replace_variables(text: str, context: Dict[str, Any]) -> str:
    """Reemplaza variables en el texto usando el contexto"""
    if not isinstance(text, str):
        return text
        
    for key, val in context.items():
        if isinstance(val, (int, float, str)):
            text = text.replace("{{"+key+"}}", str(val))
    
    try:
        from jinja2 import Template
        template = Template(text)
        return template.render(**context)
    except Exception as e:
        print(f"Error en template Jinja2: {e}")
        return text

def filter_radiators(radiator_type: str, installation: str, style: str, color: str, heat_load: float) -> List[Dict[str, Any]]:
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

def format_radiator_recommendations(models: List[Dict[str, Any]], heat_load: float) -> str:
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

def perform_calculation(node: Dict[str, Any], context: Dict[str, Any]) -> None:
    """Ejecuta los cálculos definidos en un nodo"""
    params = node.get("parametros", {})
    for key, val in params.items():
        context[key] = val

    for action in node.get("acciones", []):
        exec_expression(action, context)

def exec_expression(expr: str, context: Dict[str, Any]) -> None:
    """Ejecuta una expresión matemática y guarda el resultado en el contexto"""
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

# Servir archivos estáticos (CSS, JS, imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Sirve la página principal del chat"""
    try:
        with open("chat.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo chat.html no encontrado")

@app.post("/start", response_model=ConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """Inicia una nueva conversación"""
    conversation_id = request.conversation_id
    conversations[conversation_id] = {
        'current_node': 'inicio',
        'context': {}
    }
    return await get_next_message(conversation_id)

@app.post("/reply", response_model=ConversationResponse)
async def handle_reply(request: ReplyRequest):
    """Maneja las respuestas del usuario"""
    conversation_id = request.conversation_id
    option_index = request.option_index
    input_values = request.input_values or {}
    
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conv = conversations[conversation_id]
    node = get_node_by_id(conv['current_node'])
    
    if not node:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    
    # Procesar la respuesta del usuario
    if node.get('tipo') == 'entrada_usuario':
        try:
            if 'variable' in node:
                value = str(input_values.get('value', '')).replace(',', '.')
                conv['context'][node['variable']] = float(value)
            elif 'variables' in node:
                for var in node['variables']:
                    value = str(input_values.get(var, '')).replace(',', '.')
                    conv['context'][var] = float(value)
            conv['current_node'] = node['siguiente']
        except ValueError:
            return ConversationResponse(
                conversation_id=conversation_id,
                node_id=node['id'],
                error='Por favor ingrese valores numéricos válidos (ej: 4.5, 3.75)',
                type='input_error',
                text=node['pregunta']
            )
    
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
    
    return await get_next_message(conversation_id)

async def get_next_message(conversation_id: str) -> ConversationResponse:
    """Obtiene el siguiente mensaje de la conversación"""
    conv = conversations[conversation_id]
    node = get_node_by_id(conv['current_node'])
    
    if not node:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    
    response = ConversationResponse(
        conversation_id=conversation_id,
        node_id=node['id']
    )
    
    # Procesar según el tipo de nodo
    if node.get('tipo') == 'calculo':
        perform_calculation(node, conv['context'])
        conv['current_node'] = node['siguiente']
        return await get_next_message(conversation_id)
    elif 'pregunta' in node:
        response.type = 'question'
        response.text = replace_variables(node['pregunta'], conv['context'])
        
        if 'opciones' in node:
            response.options = [opt['texto'] for opt in node['opciones']]
        elif node.get('tipo') == 'entrada_usuario':
            if 'variable' in node:
                response.input_type = 'number'
                response.input_label = 'Ingrese el valor'
            elif 'variables' in node:
                response.input_type = 'multiple'
                response.inputs = [
                    {'name': var, 'label': f'Ingrese {var} (metros)', 'type': 'number'}
                    for var in node['variables']
                ]
    elif node.get('tipo') == 'respuesta':
        response.type = 'response'
        response.text = replace_variables(node['texto'], conv['context'])
        
        if 'opciones' in node:
            response.options = [opt['texto'] for opt in node['opciones']]
        else:
            response.is_final = True
    elif node.get('tipo') == 'opciones_dinamicas':
        # Manejar opciones dinámicas basadas en modelos recomendados
        if 'modelos_recomendados' in conv['context']:
            models = conv['context']['modelos_recomendados']
            response.type = 'question'
            response.text = node['pregunta']
            response.options = [
                f"{model['name']} (Potencia: {model['potencia']*model['coeficiente']:.0f} kcal/h)"
                for model in models
            ]
    
    return response

# Endpoint adicional para salud del servicio
@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud del servicio"""
    return {"status": "ok", "service": "PEISA - SOLDASUR S.A"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
