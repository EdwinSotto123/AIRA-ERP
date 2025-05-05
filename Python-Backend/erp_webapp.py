import json
import requests
import os
from flask import Flask, render_template, request, jsonify
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes
from ibm_watson_machine_learning.foundation_models.extensions.langchain import WatsonxLLM
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuración para IBM Cloud
APIKEY = ""
PROJECT_ID = ""
MODEL_ID = "ibm/granite-3-8b-instruct"
API_VERSION = "2023-05-29"
URL_BASE = "https://us-south.ml.cloud.ibm.com"

# Configuración de conexión MySQL
mysql_username = 'root'
mysql_password = 'pass'
mysql_host = 'localhost'
mysql_port = '3306'
database_name = 'AIRA-ERP'
mysql_uri = f'mysql+mysqlconnector://{mysql_username}:{mysql_password}@{mysql_host}:{mysql_port}/{database_name}'

# Inicializa Granite LLM y SQLDatabase
parameters = {
    GenParams.MAX_NEW_TOKENS: 256,
    GenParams.TEMPERATURE: 0.5,
}
credentials = {
    "url": URL_BASE,
    "apikey": APIKEY
}
model = ModelInference(
    model_id=MODEL_ID,
    params=parameters,
    credentials=credentials,
    project_id=PROJECT_ID
)
granite_llm = WatsonxLLM(model=model)
db = SQLDatabase.from_uri(mysql_uri)
agent_executor = create_sql_agent(llm=granite_llm, db=db, verbose=True)

def obtener_token():
    """Obtiene un token de acceso de IBM Cloud."""
    token_url = "https://iam.cloud.ibm.com/identity/token"
    token_data = {
        "apikey": APIKEY,
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey"
    }
    token_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    try:
        token_response = requests.post(token_url, data=token_data, headers=token_headers)
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        print("✓ Token obtenido correctamente")
        return access_token
    except Exception as e:
        print(f"✗ Error al obtener el token: {e}")
        if 'token_response' in locals():
            print(f"Respuesta: {token_response.text}")
        return None

def generar_esquema(json_path='static/erp.json'):
    """
    Lee el archivo JSON y genera una descripción textual del esquema de la base de datos.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        erp_data = json.load(f)
    
    esquema = f"### Esquema de la Base de Datos de {erp_data['Name_empresa']}:\n"
    
    for module in erp_data['modules']:
        for table in module['tables']:
            esquema += f"- **{table['table_name'].lower()}**:\n"
            for column in table['columns']:
                columna = f"    - {column['column_name'].lower()} ({column['data_type']})"
                if column.get('primary_key'):
                    columna += " - PRIMARY KEY"
                if 'foreign_key' in column:
                    columna += f" - FOREIGN KEY REFERENCES {column['foreign_key'].lower()}"
                esquema += columna + "\n"
    
    return esquema, erp_data['Name_empresa']

def generar_sql_con_granite(consulta_usuario, esquema):
    """Genera una consulta SQL basada en lenguaje natural usando IBM Granite."""
    # Obtener token de acceso
    access_token = obtener_token()
    if not access_token:
        return None
    
    # Preparar headers y URL
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    url = f"{URL_BASE}/ml/v1/text/generation?version={API_VERSION}"
    
    # Crear prompt para generar SQL
    prompt = f"""
Eres un experto en SQL y bases de datos en español. Traduce la siguiente pregunta en lenguaje natural a una consulta SQL válida en MySQL.

Información importante:
- La base de datos está en español.
- Los nombres de tablas y columnas pueden contener términos como "clientes", "productos", "ventas", etc.
- Genera SOLO la consulta SQL, sin explicaciones adicionales ni comentarios.

Esquema de la base de datos:
{esquema}

Ejemplos de conversión:
1. Pregunta: "¿Cuántos clientes tengo?"
   SQL: SELECT COUNT(*) AS total_clientes FROM clientes;

2. Pregunta: "Muéstrame las ventas de hoy"
   SQL: SELECT * FROM ventas WHERE DATE(fecha) = CURDATE();

3. Pregunta: "¿Cuál es el cliente que más compró?"
   SQL: SELECT c.nombre, SUM(v.total) AS total_compras FROM clientes c JOIN ventas v ON c.id = v.cliente_id GROUP BY c.id ORDER BY total_compras DESC LIMIT 1;

Pregunta: {consulta_usuario}

SQL:
"""
    
    # Preparar cuerpo de la petición
    body = {
        "project_id": PROJECT_ID,
        "model_id": MODEL_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 256,
            "temperature": 0.1,
            "top_p": 0.95
        }
    }
    
    try:
        # Enviar petición a IBM Granite
        print("Enviando consulta a IBM Granite...")
        response = requests.post(url, headers=headers, json=body)
        print(f"Estado de respuesta: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error en la API: {response.text}")
            return None
        
        # Procesar respuesta
        result = response.json()
        if "results" in result and len(result["results"]) > 0:
            generated_text = result["results"][0].get("generated_text", "")
            
            # Limpiar la respuesta para extraer solo el SQL
            import re
            sql_match = re.search(r'SELECT.*?;', generated_text, re.IGNORECASE | re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(0)
            else:
                sql_query = generated_text.strip()
            
            print(f"SQL generado: {sql_query}")
            return sql_query
        else:
            print("No se generó texto en la respuesta")
            return None
    
    except Exception as e:
        print(f"Error al generar SQL: {e}")
        return None

def run_query(query, database_name):
    """Ejecuta una consulta SQL y devuelve los resultados."""
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='pass',  # Reemplaza con tu contraseña real
            database=database_name
        )
        cursor = connection.cursor(dictionary=True)
        print(f"Ejecutando query: {query}")
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result
    except mysql.connector.Error as err:
        print(f"Error MySQL: {err}")
        return str(err)
    except Exception as e:
        print(f"Error general: {e}")
        return str(e)

def get_latest_erp_json():
    """Busca el archivo JSON de ERP más reciente en la carpeta static."""
    archivos = [f for f in os.listdir('static') if f.endswith('.json')]
    if not archivos:
        return None, None
    archivos.sort(key=lambda x: os.path.getmtime(os.path.join('static', x)), reverse=True)
    json_path = os.path.join('static', archivos[0])
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            erp_data = json.load(f)
        return erp_data, json_path
    except Exception as e:
        print(f"Error al leer el JSON: {e}")
        return None, None

@app.route('/')
def index():
    erp_data, _ = get_latest_erp_json()
    if not erp_data:
        return "No hay estructura ERP generada aún.", 404
    return render_template('index.html', modules=erp_data.get('modules', []), erp_data=erp_data)

@app.route('/get_modules')
def get_modules():
    erp_data, _ = get_latest_erp_json()
    if not erp_data:
        return jsonify([])
    return jsonify(erp_data.get('modules', []))

@app.route('/module/<module_name>')
def module(module_name):
    erp_data, _ = get_latest_erp_json()
    if not erp_data:
        return "No hay estructura ERP generada aún.", 404
    modules = erp_data.get('modules', [])
    module = next((mod for mod in modules if mod.get('module_name', '').lower() == module_name.lower()), None)
    if not module:
        return "Módulo no encontrado", 404
    return render_template('index.html', modules=modules, selected_module=module, erp_data=erp_data)

@app.route('/table/<module_name>/<table_name>')
def table(module_name, table_name):
    erp_data, _ = get_latest_erp_json()
    if not erp_data:
        return "No hay estructura ERP generada aún.", 404
    modules = erp_data.get('modules', [])
    module = next((mod for mod in modules if mod.get('module_name', '').lower() == module_name.lower()), None)
    if not module:
        return "Módulo no encontrado", 404
    table_json = next((tbl for tbl in module.get('tables', []) if tbl.get('table_name', '').lower() == table_name.lower()), None)
    if not table_json:
        return "Tabla no encontrada", 404

    # Obtener datos reales de la tabla en MySQL
    try:
        # Ajusta los datos de conexión según tu configuración
        import mysql.connector
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='pass',
            database='AIRA-ERP'  # Cambia esto al nombre de tu base de datos
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table_name}")
        table_rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        table_rows = []
        print(f"Error al consultar la tabla {table_name}: {e}")

    return render_template(
        'index.html',
        modules=modules,
        selected_module=module,
        selected_table=table_json,
        table_rows=table_rows,
        erp_data=erp_data
    )

@app.route('/chat_sql', methods=['POST'])
def chat_sql():
    """
    Endpoint para preguntas en lenguaje natural sobre la base de datos ERP usando Granite + LangChain.
    Espera un JSON: {"question": "¿Cuántos clientes hay registrados?"}
    """
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({'error': 'No se proporcionó ninguna pregunta.'}), 400
    
    try:
        # Usar una pregunta más específica añadiendo contexto SQL
        contextualized_question = f"{question}"
        
        # Ejecuta la pregunta usando el agente Granite+LangChain+SQL
        print(f"Procesando consulta: {question}")
        result = agent_executor.invoke(contextualized_question)
        print(f"Resultado obtenido: {result}")
        
        # Extraer solo la parte relevante de la respuesta
        if isinstance(result, dict) and 'output' in result:
            return jsonify({'response': result['output']})
        else:
            return jsonify({'response': str(result)})
    except Exception as e:
        print(f"Error en chat_sql: {str(e)}")
        return jsonify({'response': f"Lo siento, no pude procesar tu consulta. Error: {str(e)}"}), 200  # Return 200 to show error in chat

@app.route('/chat')
def chat_interface():
    """Ruta para la interfaz de chat con consultas en lenguaje natural."""
    return render_template('chat.html')

@app.route('/consulta', methods=['POST'])
def consulta():
    """Endpoint para consultas en lenguaje natural."""
    try:
        # Obtener consulta del usuario
        input_usuario = request.json.get('question')
        if not input_usuario:
            return jsonify({'response': 'Por favor, ingresa una pregunta'}), 400
        
        print(f"Consulta recibida: {input_usuario}")
        
        # Obtener esquema de la base de datos
        try:
            esquema, nombre_empresa = generar_esquema()
            database_name = nombre_empresa
            print(f"Usando base de datos: {database_name}")
        except Exception as e:
            print(f"Error al obtener esquema: {e}")
            return jsonify({'response': f'Error al leer el esquema: {str(e)}'}), 500
        
        # Generar SQL con IBM Granite
        sql_query = generar_sql_con_granite(input_usuario, esquema)
        if not sql_query:
            return jsonify({'response': 'No se pudo generar una consulta SQL válida'}), 500
        
        # Ejecutar consulta SQL
        resultados = run_query(sql_query, database_name)
        
        # Formatear respuesta
        if isinstance(resultados, list):
            if len(resultados) == 0:
                response = "No se encontraron resultados."
            elif len(resultados) == 1 and len(resultados[0]) == 1:
                # Si es un único valor (como un COUNT)
                key = list(resultados[0].keys())[0]
                value = resultados[0][key]
                
                # Formatear respuesta según tipo de consulta
                if "count" in key.lower() or input_usuario.lower().startswith("cuant"):
                    if str(value) == "1":
                        response = f"Se encontró 1 registro."
                    else:
                        response = f"Se encontraron {value} registros."
                else:
                    response = f"El resultado es: {value}"
            else:
                # Formatear múltiples resultados
                response = f"Se encontraron {len(resultados)} registros. "
                response += "Primeros resultados:\n\n"
                
                # Mostrar hasta 3 resultados
                for i, row in enumerate(resultados[:3]):
                    response += f"Registro {i+1}: "
                    for key, value in row.items():
                        response += f"{key}: {value}, "
                    response = response[:-2] + "\n"  # Quitar última coma
                
                if len(resultados) > 3:
                    response += f"\n(Mostrando 3 de {len(resultados)} resultados)"
        else:
            # Si no es una lista, probablemente sea un mensaje de error
            response = f"Error en la consulta: {resultados}"
        
        return jsonify({
            'response': response,
            'sql': sql_query
        })
    
    except Exception as e:
        print(f"Error general: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'response': f'Error al procesar la consulta: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)