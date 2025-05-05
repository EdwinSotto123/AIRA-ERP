import requests
import os
import json
import re
from datetime import datetime

# Configuración para IBM Cloud
# Es recomendable usar variables de entorno en producción
APIKEY = ""
PROJECT_ID = ""
MODEL_ID = "ibm/granite-3-8b-instruct" # Cambio al modelo de código que es mejor para generar JSON
API_VERSION = "2023-05-29"
URL_BASE = "https://us-south.ml.cloud.ibm.com"



PREGUNTAS = [
    {
        "id": "nombre_empresa",
        "texto": "¿Cuál es el nombre completo de tu empresa o negocio?",
        "descripcion": "Incluye la razón social si aplica (Ej: Juguetes Julia SAC)"
    },
    {
        "id": "sector",
        "texto": "¿A qué sector pertenece tu negocio?",
        "descripcion": "Ejemplo: comercio minorista, servicios, manufactura, distribución, etc."
    },
    {
        "id": "productos_servicios",
        "texto": "¿Qué productos o servicios ofreces?",
        "descripcion": "Describe brevemente los principales productos o servicios."
    },
    {
        "id": "procesos_clave",
        "texto": "¿Cuáles son los procesos más importantes que gestionas? (Ej: ventas, compras, inventario, atención al cliente, producción)",
        "descripcion": "Enumera los procesos clave de tu operación."
    },
    {
        "id": "control_clientes",
        "texto": "¿Necesitas registrar información de clientes? ¿Qué datos son importantes?",
        "descripcion": "Ejemplo: nombre, contacto, historial de compras, deudas, etc."
    },
    {
        "id": "control_proveedores",
        "texto": "¿Gestionas proveedores? ¿Qué información y procesos necesitas controlar?",
        "descripcion": "Ejemplo: compras, pagos, contacto, historial, etc."
    },
    {
        "id": "control_inventario",
        "texto": "¿Llevas control de inventario? ¿Cómo lo haces actualmente?",
        "descripcion": "Describe si usas conteo manual, Excel, sistema, etc."
    },
    {
        "id": "metodos_pago",
        "texto": "¿Qué métodos de pago aceptas y/o usas para pagar a proveedores?",
        "descripcion": "Ejemplo: efectivo, tarjeta, transferencia, crédito, etc."
    },
    {
        "id": "necesidades_adicionales",
        "texto": "¿Hay alguna necesidad o proceso especial que quieras que tu ERP maneje? (Ej: control de deudas, promociones, reportes, facturación electrónica)",
        "descripcion": "Describe cualquier requerimiento adicional importante."
    }
]

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
        exit(1)

def realizar_entrevista():
    """Realiza una entrevista al usuario sobre su negocio retail."""
    print("\n" + "="*80)
    print("  GENERADOR DE ESTRUCTURA ERP PARA RETAIL - POWERED BY IBM GRANITE")
    print("="*80)
    print("\nVamos a crear una estructura de base de datos para un sistema ERP adaptado")
    print("específicamente a las necesidades de tu negocio retail.")
    print("\nPor favor, responde las siguientes preguntas con el mayor detalle posible.\n")
    
    respuestas = {}
    
    for pregunta in PREGUNTAS:
        print(f"\n{pregunta['texto']}")
        print(f"({pregunta['descripcion']})")
        respuesta = input("> ")
        
        # Validación básica para respuestas vacías
        while not respuesta.strip():
            print("Por favor, ingresa una respuesta válida.")
            respuesta = input("> ")
            
        respuestas[pregunta['id']] = respuesta
        
        # Si es la primera pregunta (nombre de empresa), usar para personalizar
        if pregunta['id'] == 'nombre_empresa':
            print(f"\n¡Gracias! Vamos a diseñar un ERP para {respuesta}.")
    
    print("\n¡Gracias por tu información! Ahora generaremos una estructura ERP personalizada.")
    return respuestas

def generar_json_erp(datos_negocio):
    """Genera un JSON de estructura ERP basado en los datos del negocio usando IBM Granite."""
    # Obtener token directamente como en el ejemplo proporcionado
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
    except Exception as e:
        print(f"✗ Error al obtener el token: {e}")
        if 'token_response' in locals():
            print(f"Respuesta: {token_response.text}")
        return None
    
    # Preparar headers para la API
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    # URL para la generación de texto
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
    # Primero, prepara los datos
    prompt = f"""
Eres un experto en sistemas ERP para pymes. Analiza la siguiente información del negocio y genera SOLO el objeto JSON de la estructura mínima de módulos y tablas que necesita este negocio para operar eficientemente. 
- El resultado debe ser solo un JSON plano, sin saltos de línea innecesarios, sin comentarios, sin explicaciones, sin encabezados o texto adicional antes o después del JSON.
- Incluye solo los módulos estrictamente necesarios para el funcionamiento del negocio según su sector, productos/servicios y procesos clave.
- Cada módulo debe incluir las tablas necesarias y sus columnas con tipo de dato, indicando claves primarias y claves foráneas cuando sea necesario.
- Omite campos genéricos o irrelevantes. El diseño debe ser práctico y funcional.

Información del negocio:
- Nombre: "{datos_negocio['nombre_empresa']}"
- Sector: "{datos_negocio['sector']}"
- Productos/Servicios: "{datos_negocio['productos_servicios']}"
- Procesos clave: "{datos_negocio['procesos_clave']}"
- Clientes: "{datos_negocio['control_clientes']}"
- Proveedores: "{datos_negocio['control_proveedores']}"
- Inventario: "{datos_negocio['control_inventario']}"
- Métodos de pago: "{datos_negocio['metodos_pago']}"
- Necesidades adicionales: "{datos_negocio['necesidades_adicionales']}"

Ejemplo de formato esperado:
{{
    "Name_empresa": "Juguetes Julia SAC",
    "modules": [
        {{
            "module_name": "Clientes",
            "tables": [
                {{
                    "table_name": "clientes",
                    "columns": [
                        {{"column_name": "cliente_id", "data_type": "INT AUTO_INCREMENT", "primary_key": true}},
                        {{"column_name": "nombre", "data_type": "VARCHAR(100)", "primary_key": false}},
                        {{"column_name": "telefono", "data_type": "VARCHAR(15)", "primary_key": false}}
                    ]
                }}
            ]
        }},
        {{
            "module_name": "Ventas",
            "tables": [
                {{
                    "table_name": "ventas",
                    "columns": [
                        {{"column_name": "venta_id", "data_type": "INT AUTO_INCREMENT", "primary_key": true}},
                        {{"column_name": "cliente_id", "data_type": "INT", "primary_key": false, "foreign_key": "clientes(cliente_id)"}},
                        {{"column_name": "fecha_venta", "data_type": "DATETIME", "primary_key": false}}
                    ]
                }}
            ]
        }}
    ]
}}
Recuerda: SOLO el JSON, sin saltos de línea ni texto adicional.
"""

    print("\nGenerando estructura ERP personalizada con IBM Granite...")
    
    # Parámetros ajustados exactamente como en el ejemplo que funciona
    body = {
        "project_id": PROJECT_ID,
        "model_id": MODEL_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 4096,
            "temperature": 0.5,
            "top_p": 0.95
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        print(f"Estado de la respuesta: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return generar_json_predeterminado(datos_negocio)
            
        # Procesamiento similar al ejemplo proporcionado
        result = response.json()
        print(f"Tokens generados: {result['results'][0].get('generated_token_count', 0) if 'results' in result and len(result['results']) > 0 else 0}")
        print(f"Tiempo de respuesta: {result['results'][0].get('generation_time', 0) if 'results' in result and len(result['results']) > 0 else 0} ms")
        print("contenido de la respuesta y output:")
        print(result)
        # Obtener el texto generado
        generated_text = ""
        if "results" in result and len(result["results"]) > 0:
            generated_text = result["results"][0].get("generated_text", "")
            if not generated_text:
                print("⚠️ Respuesta vacía del modelo")
                return generar_json_predeterminado(datos_negocio)
        else:
            print("No se generó texto en la respuesta.")
            return generar_json_predeterminado(datos_negocio)
        
        # Validación de JSON directa como en el ejemplo
        try:
            # Limpiar texto
            cleaned_text = generated_text.strip()
            
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
                
            cleaned_text = cleaned_text.strip()
            
            # Intentar cargar como JSON
            json_data = json.loads(cleaned_text)
            print("✓ JSON válido generado por el modelo")
            
            # Asegurar que el nombre de empresa esté correcto
            if "Name_empresa" in json_data:
                json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
            
            return json_data
            
        except json.JSONDecodeError as e:
            print(f"✗ Error al parsear JSON: {e}")
            print("Intentando extraer JSON usando expresiones regulares...")
            
            # Búsqueda con regex como en el ejemplo
            json_pattern = r'(\{[\s\S]*\})'
            matches = re.search(json_pattern, generated_text, re.DOTALL)
            
            if matches:
                potential_json = matches.group(0)
                try:
                    json_data = json.loads(potential_json)
                    print("✓ JSON válido extraído mediante regex")
                    
                    # Asegurar que el nombre de empresa esté correcto
                    if "Name_empresa" in json_data:
                        json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
                        
                    return json_data
                except json.JSONDecodeError:
                    print("✗ El JSON extraído por regex tampoco es válido")
            
            print("Usando JSON predeterminado por fallo en la generación")
            return generar_json_predeterminado(datos_negocio)
    
    except Exception as e:
        print(f"Error en la petición: {e}")
        if 'response' in locals():
            print(f"Respuesta: {response.text}")
        return generar_json_predeterminado(datos_negocio)

def procesar_respuesta_json(generated_text, datos_negocio):
    """Procesa y valida el texto generado por el modelo, extrayendo y limpiando el JSON."""
    print("\nProcesando respuesta del modelo...")
    
    try:
        # Limpiar texto para extraer solo el JSON
        cleaned_text = generated_text.strip()
        
        # Eliminar marcadores de código markdown si están presentes
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
            
        cleaned_text = cleaned_text.strip()
        
        # Intentar cargar como JSON
        try:
            json_data = json.loads(cleaned_text)
            print("✓ JSON válido encontrado en la respuesta del modelo Granite.")
            
            # Asegurar que el nombre de empresa esté correcto
            if "Name_empresa" in json_data:
                json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
                print("✓ Se usó el modelo Granite para generar el JSON ERP.")
            else:
                print("✗ El modelo Granite no generó el campo Name_empresa.")
            
            return json_data
            
        except json.JSONDecodeError as e:
            print(f"✗ Error al parsear JSON completo: {e}")
            print("Intentando extraer JSON usando expresiones regulares...")
            
            # Buscar estructura JSON completa
            json_pattern = r'(\{[\s\S]*\})'
            matches = re.search(json_pattern, generated_text, re.DOTALL)
            
            if matches:
                potential_json = matches.group(0)
                try:
                    json_data = json.loads(potential_json)
                    print("✓ JSON válido extraído mediante regex de la respuesta del modelo Granite.")
                    
                    # Asegurar que el nombre de empresa esté correcto
                    if "Name_empresa" in json_data:
                        json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
                        print("✓ Se usó el modelo Granite (regex) para generar el JSON ERP.")
                    else:
                        print("✗ El modelo Granite (regex) no generó el campo Name_empresa.")
                        
                    return json_data
                except json.JSONDecodeError:
                    print("✗ El JSON extraído por regex tampoco es válido")
            
            # Si todo falla, crear un JSON básico
            print("Generando JSON básico predeterminado...")
            return generar_json_predeterminado(datos_negocio)
    
    except Exception as e:
        print(f"✗ Error inesperado al procesar la respuesta: {e}")
        print("Usando JSON predeterminado por excepción.")
        return generar_json_predeterminado(datos_negocio)

def generar_json_predeterminado(datos_negocio):
    """Genera un JSON de estructura ERP predeterminado cuando falla la generación."""
    print("⚠️  Usando JSON predeterminado (fallback).")
    
    json_predeterminado = {
        "Name_empresa": datos_negocio["nombre_empresa"],
        "modules": [
            {
                "module_name": "Clientes",
                "tables": [
                    {
                        "table_name": "clientes",
                        "columns": [
                            {
                                "column_name": "cliente_id",
                                "data_type": "INT AUTO_INCREMENT",
                                "primary_key": True
                            },
                            {
                                "column_name": "nombre",
                                "data_type": "VARCHAR(100)",
                                "primary_key": False
                            },
                            {
                                "column_name": "telefono",
                                "data_type": "VARCHAR(15)",
                                "primary_key": False
                            },
                            {
                                "column_name": "email",
                                "data_type": "VARCHAR(100)",
                                "primary_key": False
                            },
                            {
                                "column_name": "direccion",
                                "data_type": "VARCHAR(200)",
                                "primary_key": False
                            },
                            {
                                "column_name": "fecha_registro",
                                "data_type": "DATETIME",
                                "primary_key": False
                            }
                        ]
                    }
                ]
            },
            {
                "module_name": "Productos",
                "tables": [
                    {
                        "table_name": "productos",
                        "columns": [
                            {
                                "column_name": "producto_id",
                                "data_type": "INT AUTO_INCREMENT",
                                "primary_key": True
                            },
                            {
                                "column_name": "nombre",
                                "data_type": "VARCHAR(100)",
                                "primary_key": False
                            },
                            {
                                "column_name": "descripcion",
                                "data_type": "TEXT",
                                "primary_key": False
                            },
                            {
                                "column_name": "precio_venta",
                                "data_type": "DECIMAL(10,2)",
                                "primary_key": False
                            },
                            {
                                "column_name": "precio_compra",
                                "data_type": "DECIMAL(10,2)",
                                "primary_key": False
                            },
                            {
                                "column_name": "stock_actual",
                                "data_type": "INT",
                                "primary_key": False
                            },
                            {
                                "column_name": "stock_minimo",
                                "data_type": "INT",
                                "primary_key": False
                            }
                        ]
                    },
                    {
                        "table_name": "categorias",
                        "columns": [
                            {
                                "column_name": "categoria_id",
                                "data_type": "INT AUTO_INCREMENT",
                                "primary_key": True
                            },
                            {
                                "column_name": "nombre",
                                "data_type": "VARCHAR(50)",
                                "primary_key": False
                            },
                            {
                                "column_name": "descripcion",
                                "data_type": "VARCHAR(200)",
                                "primary_key": False
                            }
                        ]
                    }
                ]
            },
            {
                "module_name": "Ventas",
                "tables": [
                    {
                        "table_name": "ventas",
                        "columns": [
                            {
                                "column_name": "venta_id",
                                "data_type": "INT AUTO_INCREMENT",
                                "primary_key": True
                            },
                            {
                                "column_name": "cliente_id",
                                "data_type": "INT",
                                "primary_key": False,
                                "foreign_key": "clientes(cliente_id)"
                            },
                            {
                                "column_name": "fecha_venta",
                                "data_type": "DATETIME",
                                "primary_key": False
                            },
                            {
                                "column_name": "total",
                                "data_type": "DECIMAL(10,2)",
                                "primary_key": False
                            },
                            {
                                "column_name": "metodo_pago",
                                "data_type": "VARCHAR(50)",
                                "primary_key": False
                            },
                            {
                                "column_name": "estado",
                                "data_type": "VARCHAR(20)",
                                "primary_key": False
                            }
                        ]
                    },
                    {
                        "table_name": "detalle_ventas",
                        "columns": [
                            {
                                "column_name": "detalle_id",
                                "data_type": "INT AUTO_INCREMENT",
                                "primary_key": True
                            },
                            {
                                "column_name": "venta_id",
                                "data_type": "INT",
                                "primary_key": False,
                                "foreign_key": "ventas(venta_id)"
                            },
                            {
                                "column_name": "producto_id",
                                "data_type": "INT",
                                "primary_key": False,
                                "foreign_key": "productos(producto_id)"
                            },
                            {
                                "column_name": "cantidad",
                                "data_type": "INT",
                                "primary_key": False
                            },
                            {
                                "column_name": "precio_unitario",
                                "data_type": "DECIMAL(10,2)",
                                "primary_key": False
                            },
                            {
                                "column_name": "subtotal",
                                "data_type": "DECIMAL(10,2)",
                                "primary_key": False
                            }
                        ]
                    }
                ]
            },
            {
                "module_name": "Inventario",
                "tables": [
                    {
                        "table_name": "movimientos_inventario",
                        "columns": [
                            {
                                "column_name": "movimiento_id",
                                "data_type": "INT AUTO_INCREMENT",
                                "primary_key": True
                            },
                            {
                                "column_name": "producto_id",
                                "data_type": "INT",
                                "primary_key": False,
                                "foreign_key": "productos(producto_id)"
                            },
                            {
                                "column_name": "tipo_movimiento",
                                "data_type": "VARCHAR(20)",
                                "primary_key": False
                            },
                            {
                                "column_name": "cantidad",
                                "data_type": "INT",
                                "primary_key": False
                            },
                            {
                                "column_name": "fecha_movimiento",
                                "data_type": "DATETIME",
                                "primary_key": False
                            },
                            {
                                "column_name": "usuario",
                                "data_type": "VARCHAR(50)",
                                "primary_key": False
                            },
                            {
                                "column_name": "nota",
                                "data_type": "VARCHAR(200)",
                                "primary_key": False
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Añadir módulo de Proveedores si el usuario mencionó ese aspecto
    if "proveedores" in datos_negocio["gestion_proveedores"].lower():
        json_predeterminado["modules"].append({
            "module_name": "Proveedores",
            "tables": [
                {
                    "table_name": "proveedores",
                    "columns": [
                        {
                            "column_name": "proveedor_id",
                            "data_type": "INT AUTO_INCREMENT",
                            "primary_key": True
                        },
                        {
                            "column_name": "nombre",
                            "data_type": "VARCHAR(100)",
                            "primary_key": False
                        },
                        {
                            "column_name": "contacto",
                            "data_type": "VARCHAR(100)",
                            "primary_key": False
                        },
                        {
                            "column_name": "telefono",
                            "data_type": "VARCHAR(15)",
                            "primary_key": False
                        },
                        {
                            "column_name": "email",
                            "data_type": "VARCHAR(100)",
                            "primary_key": False
                        },
                        {
                            "column_name": "direccion",
                            "data_type": "VARCHAR(200)",
                            "primary_key": False
                        }
                    ]
                },
                {
                    "table_name": "compras",
                    "columns": [
                        {
                            "column_name": "compra_id",
                            "data_type": "INT AUTO_INCREMENT",
                            "primary_key": True
                        },
                        {
                            "column_name": "proveedor_id",
                            "data_type": "INT",
                            "primary_key": False,
                            "foreign_key": "proveedores(proveedor_id)"
                        },
                        {
                            "column_name": "fecha_compra",
                            "data_type": "DATETIME",
                            "primary_key": False
                        },
                        {
                            "column_name": "total",
                            "data_type": "DECIMAL(10,2)",
                            "primary_key": False
                        },
                        {
                            "column_name": "estado",
                            "data_type": "VARCHAR(20)",
                            "primary_key": False
                        }
                    ]
                },
                {
                    "table_name": "detalle_compras",
                    "columns": [
                        {
                            "column_name": "detalle_id",
                            "data_type": "INT AUTO_INCREMENT",
                            "primary_key": True
                        },
                        {
                            "column_name": "compra_id",
                            "data_type": "INT",
                            "primary_key": False,
                            "foreign_key": "compras(compra_id)"
                        },
                        {
                            "column_name": "producto_id",
                            "data_type": "INT",
                            "primary_key": False,
                            "foreign_key": "productos(producto_id)"
                        },
                        {
                            "column_name": "cantidad",
                            "data_type": "INT",
                            "primary_key": False
                        },
                        {
                            "column_name": "precio_unitario",
                            "data_type": "DECIMAL(10,2)",
                            "primary_key": False
                        },
                        {
                            "column_name": "subtotal",
                            "data_type": "DECIMAL(10,2)",
                            "primary_key": False
                        }
                    ]
                }
            ]
        })
    
    # Añadir módulo de Cuentas por Cobrar si mencionó crédito o deudas
    if any(keyword in datos_negocio["metodos_pago"].lower() for keyword in ["crédit", "credit", "deuda", "fiado", "pagar después"]) or \
       "deuda" in datos_negocio["necesidades_adicionales"].lower():
        json_predeterminado["modules"].append({
            "module_name": "CuentasPorCobrar",
            "tables": [
                {
                    "table_name": "deudas",
                    "columns": [
                        {
                            "column_name": "deuda_id",
                            "data_type": "INT AUTO_INCREMENT",
                            "primary_key": True
                        },
                        {
                            "column_name": "cliente_id",
                            "data_type": "INT",
                            "primary_key": False,
                            "foreign_key": "clientes(cliente_id)"
                        },
                        {
                            "column_name": "venta_id",
                            "data_type": "INT",
                            "primary_key": False,
                            "foreign_key": "ventas(venta_id)"
                        },
                        {
                            "column_name": "monto_total",
                            "data_type": "DECIMAL(10,2)",
                            "primary_key": False
                        },
                        {
                            "column_name": "monto_pendiente",
                            "data_type": "DECIMAL(10,2)",
                            "primary_key": False
                        },
                        {
                            "column_name": "fecha_inicio",
                            "data_type": "DATETIME",
                            "primary_key": False
                        },
                        {
                            "column_name": "fecha_vencimiento",
                            "data_type": "DATETIME",
                            "primary_key": False
                        },
                        {
                            "column_name": "estado",
                            "data_type": "VARCHAR(20)",
                            "primary_key": False
                        }
                    ]
                },
                {
                    "table_name": "pagos",
                    "columns": [
                        {
                            "column_name": "pago_id",
                            "data_type": "INT AUTO_INCREMENT",
                            "primary_key": True
                        },
                        {
                            "column_name": "deuda_id",
                            "data_type": "INT",
                            "primary_key": False,
                            "foreign_key": "deudas(deuda_id)"
                        },
                        {
                            "column_name": "monto",
                            "data_type": "DECIMAL(10,2)",
                            "primary_key": False
                        },
                        {
                            "column_name": "fecha_pago",
                            "data_type": "DATETIME",
                            "primary_key": False
                        },
                        {
                            "column_name": "metodo_pago",
                            "data_type": "VARCHAR(50)",
                            "primary_key": False
                        },
                        {
                            "column_name": "nota",
                            "data_type": "VARCHAR(200)",
                            "primary_key": False
                        }
                    ]
                }
            ]
        })
    
    return json_predeterminado

def guardar_json(json_data, nombre_empresa):
    """Guarda el JSON generado en un archivo."""
    # Crear un nombre de archivo seguro basado en el nombre de la empresa
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', nombre_empresa)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"erp_{safe_name}_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        print(f"\n✓ Estructura ERP guardada exitosamente en: {filename}")
        return filename
    except Exception as e:
        print(f"\n✗ Error al guardar el archivo JSON: {e}")
        return None

def mostrar_resumen_estructura(json_data):
    """Muestra un resumen de la estructura ERP generada."""
    if not json_data or "modules" not in json_data:
        print("\n✗ No hay datos válidos para mostrar.")
        return

    print("\n" + "="*80)
    print(f"  RESUMEN DE ESTRUCTURA ERP PARA: {json_data.get('Name_empresa', 'EMPRESA')}")
    print("="*80)
    
    modules = json_data.get("modules", [])
    print(f"\n✓ Total de módulos generados: {len(modules)}")
    
    for module in modules:
        module_name = module.get("module_name", "Desconocido")
        tables = module.get("tables", [])
        
        print(f"\n- MÓDULO: {module_name}")
        print(f"  Tablas ({len(tables)}):")
        
        for table in tables:
            table_name = table.get("table_name", "desconocida")
            columns = table.get("columns", [])
            
            # Encontrar clave primaria
            primary_keys = [col.get("column_name") for col in columns if col.get("primary_key")]
            
            # Encontrar claves foráneas
            foreign_keys = []
            for col in columns:
                if col.get("foreign_key"):
                    foreign_keys.append(f"{col.get('column_name')} -> {col.get('foreign_key')}")
            
            print(f"  • {table_name} ({len(columns)} columnas)")
            print(f"    - PK: {', '.join(primary_keys) if primary_keys else 'Ninguna'}")
            if foreign_keys:
                print(f"    - FK: {', '.join(foreign_keys)}")

def main():
    """Función principal que ejecuta el flujo completo."""
    try:
        # Realizar entrevista al usuario
        datos_negocio = realizar_entrevista()
        
        # Generar JSON de estructura ERP
        json_data = generar_json_erp(datos_negocio)
        
        if json_data:
            # Guardar el JSON en un archivo
            filename = guardar_json(json_data, datos_negocio["nombre_empresa"])
            
            # Mostrar resumen de la estructura
            mostrar_resumen_estructura(json_data)
            
            print("\n" + "="*80)
            print(f"  PROCESO COMPLETADO EXITOSAMENTE")
            print("="*80)
            print(f"\nLa estructura de su ERP ha sido generada y guardada en: {filename}")
            print("\nPuede utilizar este archivo para crear su base de datos MySQL.")
            print("Recuerde que este es solo el primer paso para implementar su sistema ERP.")
            
            # Preguntar si desea crear la base de datos ahora
            print("\n¿Desea crear la base de datos MySQL ahora? (sí/no)")
            respuesta = input("> ").strip().lower()
            if respuesta in ["sí", "si", "s", "yes", "y"]:
                print("\nPara crear la base de datos, necesitará:")
                print("1. MySQL instalado en su sistema")
                print("2. Credenciales de acceso (usuario/contraseña)")
                print("\nImplementación de creación de base de datos pendiente...")
                # Aquí se agregaría la lógica para crear la base de datos
            else:
                print("\nPuede crear la base de datos manualmente en otro momento usando el archivo JSON generado.")
        else:
            print("\n✗ No se pudo generar la estructura ERP. Por favor, intente nuevamente más tarde.")
    
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
    finally:
        print("\n¡Gracias por usar el Generador de Estructura ERP para Retail!")

if __name__ == "__main__":
    main()
