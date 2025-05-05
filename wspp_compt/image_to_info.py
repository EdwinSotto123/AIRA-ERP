import os
import json
import base64
import mysql.connector
import traceback
import re
from PIL import Image
import io

# Import the IBM WatsonX AI SDK
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

# Configuración para IBM Cloud
APIKEY = "fvo19VD0QVeovpA603v5gd8xZrf4ZBS-m0Ttcnhf-4Ca"
PROJECT_ID = "eed8e832-b305-4a9f-8dfd-124902ca2ea7"
VISION_MODEL_ID = "ibm/granite-vision-3-2-2b"  # Modelo de visión de IBM Granite
INSTRUCT_MODEL_ID = "ibm/granite-3-8b-instruct"   # Modelo para instrucciones
API_VERSION = "2023-05-29"
URL_BASE = "https://us-south.ml.cloud.ibm.com"

# Configuración de MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pass',  # Reemplaza con tu contraseña real
    'database': 'AIRA-ERP'  # Reemplaza con el nombre de tu base de datos
}

def encode_image(image_path):
    """Codifica la imagen en base64."""
    try:
        with Image.open(image_path) as img:
            # Redimensionar si la imagen es muy grande
            if max(img.size) > 2000:
                img.thumbnail((2000, 2000), Image.LANCZOS)
            
            # Convertir a bytes
            buffer = io.BytesIO()
            img.save(buffer, format=img.format or 'JPEG')
            img_bytes = buffer.getvalue()
        
        # Codificar en base64
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error al codificar la imagen: {e}")
        raise

def parse_structured_output(text_content):
    """Intenta extraer datos clave:valor del texto generado por el modelo."""
    extracted_data = {}
    # Busca líneas que se parezcan a "CLAVE: VALOR"
    lines = text_content.strip().split('\n')
    for line in lines:
        match = re.match(r'^\s*([^:]+?)\s*:\s*(.*)$', line)
        if match:
            key = match.group(1).strip().upper().replace(" ", "_") # Normaliza la clave
            value = match.group(2).strip()
            extracted_data[key] = value
        else:
            # Si no hay ':' pero la línea contiene info, guárdala con clave genérica
            if line.strip() and not extracted_data.get(f"INFO_{len(extracted_data)}"):
                 extracted_data[f"INFO_{len(extracted_data)}"] = line.strip()

    # Si no se encontró formato clave:valor, intenta un parseo más básico
    if not extracted_data:
        # Simple parsing: section headers become keys, content becomes values
        current_section = "GENERAL"
        current_content = []
        
        for line in lines:
            if line.strip().isupper() and line.strip().endswith(':'):
                # This looks like a section header
                if current_content:
                    extracted_data[current_section] = "\n".join(current_content)
                    current_content = []
                current_section = line.strip().rstrip(':')
            elif line.strip():
                current_content.append(line.strip())
        
        # Add the last section
        if current_content:
            extracted_data[current_section] = "\n".join(current_content)

    return extracted_data

def analizar_imagen(image_path):
    """Analiza una imagen usando IBM Granite Vision y devuelve texto plano organizado."""
    if not os.path.exists(image_path):
        print(f"Error: La imagen no existe: {image_path}")
        return None
    
    try:
        # 1. Configurar credenciales
        print("Configurando credenciales...")
        credentials = Credentials(
            url=URL_BASE,
            api_key=APIKEY
        )
        
        # 2. Codificar la imagen
        print(f"Codificando imagen: {image_path}...")
        encoded_image = encode_image(image_path)
        
        # 3. Crear el prompt y la estructura de mensajes
        user_query = """
Analiza esta imagen y describe detalladamente su contenido en texto plano.

Debes identificar y organizar la información con el siguiente formato:

TIPO: [Producto/Factura/Inventario/Otro]

INFORMACIÓN PRINCIPAL:
- Título: [título o nombre principal]
- Fecha: [fecha si existe]
- ID/Referencia: [número o código de referencia]

DETALLES:
- [Lista detallada de elementos importantes]
- [Incluir precios, cantidades, descripciones]

RESUMEN:
[Breve resumen de lo que muestra la imagen]

Responde ÚNICAMENTE con el formato solicitado.
"""
        
        # Estructura de mensajes para model.chat()
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_query
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ]
        
        # 4. Instanciar el modelo
        print(f"Instanciando modelo de visión: {VISION_MODEL_ID}...")
        params = {
            "max_tokens": 1024,
            "temperature": 0.2,
        }
        model = ModelInference(
            model_id=VISION_MODEL_ID,
            params=params,
            credentials=credentials,
            project_id=PROJECT_ID,
        )
        
        # 5. Hacer la petición
        print("Enviando imagen para análisis...")
        response = model.chat(messages=messages)
        
        # 6. Procesar la respuesta
        if response and 'choices' in response and len(response['choices']) > 0:
            message_content = response['choices'][0].get('message', {}).get('content', "")
            if message_content:
                print("✓ Información extraída correctamente")
                print(f"Texto generado: {message_content}")
                return message_content
        
        print("No se pudo extraer información de la imagen")
        return None
        
    except Exception as e:
        print(f"Error al analizar la imagen: {e}")
        traceback.print_exc()
        return None

def generar_esquema():
    """
    Lee el archivo JSON y genera una descripción textual del esquema de la base de datos.
    """
    try:
        # Buscar el archivo JSON más reciente
        json_dir = 'static'
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        if not json_files:
            print("No se encontraron archivos JSON")
            return None, None
        
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(json_dir, x)), reverse=True)
        json_path = os.path.join(json_dir, json_files[0])
        
        with open(json_path, 'r', encoding='utf-8') as f:
            erp_data = json.load(f)
        
        esquema = f"### Esquema de la Base de Datos de {erp_data.get('Name_empresa', 'ERP')}:\n"
        
        for module in erp_data.get('modules', []):
            for table in module.get('tables', []):
                esquema += f"- **{table.get('table_name', '').lower()}**:\n"
                for column in table.get('columns', []):
                    columna = f"    - {column.get('column_name', '').lower()} ({column.get('data_type', '')})"
                    if column.get('primary_key'):
                        columna += " - PRIMARY KEY"
                    if 'foreign_key' in column:
                        columna += f" - FOREIGN KEY REFERENCES {column.get('foreign_key', '').lower()}"
                    esquema += columna + "\n"
        
        return esquema, erp_data.get('Name_empresa', 'ERP')
    except Exception as e:
        print(f"Error al generar esquema: {e}")
        return None, None

def generar_consulta_sql(info_extraida, esquema):
    """Genera una consulta SQL basada en la información extraída en texto plano."""
    try:
        # Configurar credenciales
        print("Configurando credenciales para generar SQL...")
        credentials = Credentials(
            url=URL_BASE,
            api_key=APIKEY
        )
        
        # Crear prompt para generar SQL mejorado y específico para MySQL
        prompt = f"""
Eres un experto en MySQL 8.0. Genera una consulta SQL válida basada en esta información extraída de una imagen.

Esquema de la base de datos:
{esquema}

Información extraída de la imagen:
{info_extraida}

REGLAS OBLIGATORIAS PARA MYSQL 8.0:
1. Usa comillas invertidas (`tabla`) para TODOS los nombres de tablas y columnas
2. Termina SIEMPRE la consulta con punto y coma (;)
3. Para INSERT INTO, especifica siempre los nombres de columnas entre comillas invertidas:
   INSERT INTO `tabla` (`columna1`, `columna2`) VALUES ('valor1', 'valor2');
4. Para SELECT, especifica cada columna explícitamente:
   SELECT `columna1`, `columna2` FROM `tabla` WHERE `condicion` = 'valor';
5. Usa comillas simples (') para valores de texto, no comillas dobles
6. Usa el formato correcto para fechas: 'YYYY-MM-DD'
7. Escribe la consulta completa, sin abreviaturas ni parámetros
8. No uses funciones, operadores o sintaxis que no sean estándar en MySQL 8.0

Genera UNA SOLA consulta SQL simple y funcional que sea exactamente ejecutable sin modificaciones.
Sin comentarios, sin explicaciones, solo la consulta SQL válida.
"""
        
        # Instanciar el modelo
        print(f"Instanciando modelo de texto: {INSTRUCT_MODEL_ID}...")
        params = {
            "max_tokens": 512,
            "temperature": 0.1,
        }
        model = ModelInference(
            model_id=INSTRUCT_MODEL_ID,
            params=params,
            credentials=credentials,
            project_id=PROJECT_ID,
        )
        
        # Hacer la petición
        print("Generando consulta SQL...")
        response = model.generate(prompt=prompt)
        
        # Procesar la respuesta para extraer SQL válido
        if response and 'results' in response and len(response['results']) > 0:
            generated_text = response['results'][0].get('generated_text', "").strip()
            
            # Extraer SQL válido
            import re
            
            # Intentar extraer SQL entre backticks o marcadores de código
            code_patterns = [
                r'```sql\s*([\s\S]*?)\s*```',  # Markdown SQL code block
                r'```\s*([\s\S]*?)\s*```',      # Any code block
                r'`([\s\S]*?)`',                # Inline code
            ]
            
            for pattern in code_patterns:
                matches = re.search(pattern, generated_text, re.DOTALL)
                if matches:
                    sql_query = matches.group(1).strip()
                    break
            else:
                # Si no hay bloques de código, buscar patrones de consulta SQL
                sql_pattern = r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|SHOW|USE)[\s\S]*?;'
                matches = re.search(sql_pattern, generated_text, re.IGNORECASE | re.DOTALL)
                
                if matches:
                    sql_query = matches.group(0).strip()
                else:
                    # Si todo falla, usar todo el texto generado
                    sql_query = generated_text
            
            # Asegurar que la consulta termina con punto y coma
            if not sql_query.endswith(';'):
                sql_query += ';'
                
            # Verificar que la consulta parece completa
            if len(sql_query.strip()) > 10 and any(kw in sql_query.upper() for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                print(f"SQL generado: {sql_query}")
                return sql_query
            else:
                print(f"SQL incompleto o inválido: {sql_query}")
                return "SELECT 1;  -- Consulta de fallback porque no se pudo generar SQL válido"
        
        print("No se generó texto en la respuesta")
        return "SELECT 1;  -- Consulta de fallback porque no se generó respuesta"
        
    except Exception as e:
        print(f"Error al generar SQL: {e}")
        traceback.print_exc()
        return "SELECT 1;  -- Consulta de fallback debido a error: " + str(e)

def ejecutar_consulta(sql_query, database_name):
    """Ejecuta una consulta SQL en la base de datos."""
    try:
        # Configurar conexión a la base de datos
        config = DB_CONFIG.copy()
        config['database'] = database_name
        
        # Conectar a la base de datos
        print(f"Conectando a la base de datos: {config['database']}...")
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)
        
        # Ejecutar consulta
        print(f"Ejecutando SQL: {sql_query}")
        cursor.execute(sql_query)
        
        # Si es una consulta SELECT, obtener resultados
        if sql_query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
        else:
            # Si es INSERT, UPDATE o DELETE, obtener recuento de filas afectadas
            conn.commit()
            result = {"affected_rows": cursor.rowcount}
        
        # Cerrar conexión
        cursor.close()
        conn.close()
        
        print("Consulta ejecutada correctamente")
        return result
    
    except mysql.connector.Error as e:
        print(f"Error de MySQL: {e}")
        return {"error": str(e)}
    
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return {"error": str(e)}

def procesar_imagen_a_database(image_path):
    """
    Procesa una imagen, extrae información, genera una consulta SQL y la ejecuta.
    Devuelve resultados en texto plano estructurado.
    """
    try:
        # Verificar que la imagen existe
        if not os.path.exists(image_path):
            return "ERROR: La imagen no existe: " + image_path
        
        # Paso 1: Analizar la imagen con Granite Vision
        print(f"Analizando imagen: {image_path}")
        info_extraida = analizar_imagen(image_path)
        if not info_extraida:
            return "ERROR: No se pudo extraer información de la imagen"
        
        # Paso 2: Obtener esquema de la base de datos
        esquema, nombre_empresa = generar_esquema()
        if not esquema or not nombre_empresa:
            return "ERROR: No se pudo obtener el esquema de la base de datos"
        
        # Paso 3: Generar consulta SQL con Granite Instruct
        sql_query = generar_consulta_sql(info_extraida, esquema)
        if not sql_query:
            return "ERROR: No se pudo generar una consulta SQL"
        
        # Paso 4: Ejecutar la consulta SQL
        resultado_sql = ejecutar_consulta(sql_query, nombre_empresa)
        
        # Paso 5: Formatear los resultados en texto plano organizado
        resultado_texto = f"""
====================================================
RESULTADOS DEL ANÁLISIS DE IMAGEN
====================================================

INFORMACIÓN EXTRAÍDA:
{info_extraida}

----------------------------------------------------
CONSULTA SQL GENERADA:
{sql_query}

----------------------------------------------------
RESULTADO DE LA CONSULTA:
"""
        
        # Formatear el resultado SQL como texto
        if isinstance(resultado_sql, list):
            if len(resultado_sql) == 0:
                resultado_texto += "No se encontraron resultados."
            else:
                resultado_texto += f"Se encontraron {len(resultado_sql)} registros:\n\n"
                for i, row in enumerate(resultado_sql):
                    resultado_texto += f"Registro {i+1}:\n"
                    for key, value in row.items():
                        resultado_texto += f"- {key}: {value}\n"
                    resultado_texto += "\n"
        elif isinstance(resultado_sql, dict):
            if "error" in resultado_sql:
                resultado_texto += f"Error: {resultado_sql['error']}\n"
            elif "affected_rows" in resultado_sql:
                resultado_texto += f"Operación exitosa. Filas afectadas: {resultado_sql['affected_rows']}\n"
            else:
                for key, value in resultado_sql.items():
                    resultado_texto += f"- {key}: {value}\n"
        else:
            resultado_texto += str(resultado_sql)
        
        return resultado_texto
    
    except Exception as e:
        print(f"Error en el procesamiento: {e}")
        traceback.print_exc()
        return f"ERROR GENERAL: {str(e)}"

# Ejemplo de uso
if __name__ == "__main__":
    # Ruta a la imagen a procesar
    imagen = input("Ingresa la ruta a la imagen: ")
    
    # Procesar imagen
    resultado = procesar_imagen_a_database(imagen)
    
    # Mostrar resultados
    print(resultado)