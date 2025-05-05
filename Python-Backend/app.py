from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
import json
import os
import requests
import re
from datetime import datetime
from  generate_database import create_database_and_tables
import pymysql
import mysql.connector
import csv
from werkzeug.utils import secure_filename

# Es recomendable usar variables de entorno en producción
APIKEY = ""
PROJECT_ID = ""
MODEL_ID = "ibm/granite-3-8b-instruct" # Cambio al modelo de código que es mejor para generar JSON
API_VERSION = "2023-05-29"
URL_BASE = "https://us-south.ml.cloud.ibm.com"

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

def generar_json_erp(datos_negocio):
    """Genera un JSON de estructura ERP basado en los datos del negocio usando IBM Granite."""
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
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
    
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
            
        result = response.json()
        print(f"Tokens generados: {result['results'][0].get('generated_token_count', 0) if 'results' in result and len(result['results']) > 0 else 0}")
        print(f"Tiempo de respuesta: {result['results'][0].get('generation_time', 0) if 'results' in result and len(result['results']) > 0 else 0} ms")
        print("contenido de la respuesta y output:")
        print(result)
        generated_text = ""
        if "results" in result and len(result["results"]) > 0:
            generated_text = result["results"][0].get("generated_text", "")
            if not generated_text:
                print("⚠️ Respuesta vacía del modelo")
                return generar_json_predeterminado(datos_negocio)
        else:
            print("No se generó texto en la respuesta.")
            return generar_json_predeterminado(datos_negocio)
        
        try:
            cleaned_text = generated_text.strip()
            
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
                
            cleaned_text = cleaned_text.strip()
            
            json_data = json.loads(cleaned_text)
            print("✓ JSON válido generado por el modelo")
            
            if "Name_empresa" in json_data:
                json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
            
            return json_data
            
        except json.JSONDecodeError as e:
            print(f"✗ Error al parsear JSON: {e}")
            print("Intentando extraer JSON usando expresiones regulares...")
            
            json_pattern = r'(\{[\s\S]*\})'
            matches = re.search(json_pattern, generated_text, re.DOTALL)
            
            if matches:
                potential_json = matches.group(0)
                try:
                    json_data = json.loads(potential_json)
                    print("✓ JSON válido extraído mediante regex")
                    
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
    
    try:
        cleaned_text = generated_text.strip()
        
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
            
        cleaned_text = cleaned_text.strip()
        
        try:
            json_data = json.loads(cleaned_text)
            print("✓ JSON válido encontrado en la respuesta del modelo Granite.")
            
            if "Name_empresa" in json_data:
                json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
                print("✓ Se usó el modelo Granite para generar el JSON ERP.")
            else:
                print("✗ El modelo Granite no generó el campo Name_empresa.")
            
            return json_data
            
        except json.JSONDecodeError as e:
            print(f"✗ Error al parsear JSON completo: {e}")
            print("Intentando extraer JSON usando expresiones regulares...")
            
            json_pattern = r'(\{[\s\S]*\})'
            matches = re.search(json_pattern, generated_text, re.DOTALL)
            
            if matches:
                potential_json = matches.group(0)
                try:
                    json_data = json.loads(potential_json)
                    print("✓ JSON válido extraído mediante regex de la respuesta del modelo Granite.")
                    
                    if "Name_empresa" in json_data:
                        json_data["Name_empresa"] = datos_negocio["nombre_empresa"]
                        print("✓ Se usó el modelo Granite (regex) para generar el JSON ERP.")
                    else:
                        print("✗ El modelo Granite (regex) no generó el campo Name_empresa.")
                        
                    return json_data
                except json.JSONDecodeError:
                    print("✗ El JSON extraído por regex tampoco es válido")
            
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
    """Guarda el JSON generado como 'static/erp.json'."""
    carpeta = 'static'
    os.makedirs(carpeta, exist_ok=True)  # Crea la carpeta si no existe
    filename = os.path.join(carpeta, 'erp.json')

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
            
            primary_keys = [col.get("column_name") for col in columns if col.get("primary_key")]
            
            foreign_keys = []
            for col in columns:
                if col.get("foreign_key"):
                    foreign_keys.append(f"{col.get('column_name')} -> {col.get('foreign_key')}")


def main(datos_negocio):
    """Función principal que ejecuta el flujo completo."""
    try:
        json_data = generar_json_erp(datos_negocio)
        create_database_and_tables(json_data)

        if json_data:
            filename = guardar_json(json_data, datos_negocio["nombre_empresa"])
            mostrar_resumen_estructura(json_data)
            
            print("\n" + "="*80)
            print(f"  PROCESO COMPLETADO EXITOSAMENTE")
            print("="*80)
            print(f"\nLa estructura de su ERP ha sido generada y guardada en: {filename}")
            print("\nPuede utilizar este archivo para crear su base de datos MySQL.")
            print("Recuerde que este es solo el primer paso para implementar su sistema ERP.")

            
            
        else:
            print("\n✗ No se pudo generar la estructura ERP. Por favor, intente nuevamente más tarde.")
    
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
    finally:
        print("\n¡Gracias por usar el Generador de Estructura ERP para Retail!")

@app.route('/api/generar-erp', methods=['POST'])
def generar_erp():
    data = request.json
    print("=== DATOS RECIBIDOS DEL CHATBOT ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    respuestas = data.get('respuestas')
    if not respuestas or not respuestas.get('nombre_empresa'):
        return jsonify({'error': 'Información insuficiente para generar el ERP'}), 400
    
    main(respuestas)
    print("=== JSON GENERADO POR IBM GRANITE ===")
    print(json.dumps(respuestas, indent=2, ensure_ascii=False))
    return jsonify({'estructura': respuestas})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)