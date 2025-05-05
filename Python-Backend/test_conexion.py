import json
from flask import Flask, render_template, request, jsonify
import mysql.connector
import os


db_config = {
    'host': '127.0.0.1',
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

get_db_connection()