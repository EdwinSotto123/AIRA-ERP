import json
from flask import Flask, render_template, request, jsonify
import mysql.connector
import os

app = Flask(__name__)

# Configuración de conexión
ip = 'localhost'
port = '3306'
user = 'root'
password = 'pass'

db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'pass'
}

def get_db_connection():
    """Crear y devolver la conexión a la base de datos."""
    print("Conectando a la base de datos...")
    conn = mysql.connector.connect(**db_config)
    print("Conexión exitosa.")
    return conn

def create_tables_without_foreign_keys(cursor, data):
    """Crear las tablas sin claves foráneas."""
    try:
        for module in data["modules"]:
            for table in module["tables"]:
                columns = []
                primary_keys = []
                for column in table["columns"]:
                    column_name = column['column_name']
                    data_type = column['data_type']
                    column_def = f"`{column_name}` {data_type}"
                    
                    if column.get("primary_key"):
                        primary_keys.append(f"`{column_name}`")
                    
                    columns.append(column_def)
                
                if primary_keys:
                    primary_key_def = f"PRIMARY KEY ({', '.join(primary_keys)})"
                    columns.append(primary_key_def)
                
                columns_sql = ",\n  ".join(columns)
                
                create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table['table_name']}` (\n  {columns_sql}\n) ENGINE=InnoDB;\n"
                print(f"Ejecutando SQL:\n{create_table_sql}")
                cursor.execute(create_table_sql)
                print(f"✅ Tabla '{table['table_name']}' creada sin claves foráneas.")
    except mysql.connector.Error as err:
        print(f"❌ Error al crear las tablas: {err}")
        raise

def add_foreign_keys(cursor, data):
    """Agregar claves foráneas después de crear las tablas."""
    try:
        for module in data["modules"]:
            for table in module["tables"]:
                for column in table["columns"]:
                    if "foreign_key" in column:
                        fk_table, fk_column = column['foreign_key'].strip().split('(')
                        fk_column = fk_column.rstrip(')')
                        alter_table_sql = (
                            f"ALTER TABLE `{table['table_name']}` "
                            f"ADD CONSTRAINT `fk_{table['table_name']}_{column['column_name']}` "
                            f"FOREIGN KEY (`{column['column_name']}`) REFERENCES `{fk_table}`(`{fk_column}`) "
                            f"ON DELETE CASCADE ON UPDATE CASCADE;"
                        )
                        try:
                            print(f"Ejecutando FK SQL:\n{alter_table_sql}")
                            cursor.execute(alter_table_sql)
                            print(f"✅ Clave foránea añadida en '{table['table_name']}' para '{column['column_name']}'.")
                        except mysql.connector.Error as err:
                            print(f"⚠️ Error al añadir clave foránea en '{table['table_name']}': {err}")
    except Exception as e:
        print(f"❌ Error global en add_foreign_keys: {e}")
        raise

def create_database_and_tables(datos_negocio):
    """Crear la base de datos y sus tablas."""
    try:
        nombre_empresa = "AIRA-ERP"
        print(f"🚀 Iniciando creación de base de datos '{nombre_empresa}'...")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{nombre_empresa}`")
        print(f"📁 Base de datos '{nombre_empresa}' creada (o ya existía).")
        
        cursor.execute(f"USE `{nombre_empresa}`")
        print(f"🗂️ Usando base de datos '{nombre_empresa}'...")

        create_tables_without_foreign_keys(cursor, datos_negocio)
        add_foreign_keys(cursor, datos_negocio)

        conn.commit()
        print("💾 Cambios guardados en la base de datos.")

    except Exception as e:
        print(f"❌ Error en create_database_and_tables: {e}")
    
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        print("🔚 Conexión cerrada.")

