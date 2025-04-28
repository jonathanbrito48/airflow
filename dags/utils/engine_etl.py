import datetime as dt
from datetime import datetime
import psycopg2
from psycopg2 import OperationalError
import pandas as pd
import os

today = datetime.date(datetime.today())

class DatabaseConnection:
    def __init__(self, db_name, db_user, db_password, db_host, db_port):
        self.connection_params = {
            'database': db_name,
            'user': db_user,
            'password': db_password,
            'host': db_host,
            'port': db_port
        }
        self.connection = None
    
    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            print(f"Conexão com o PostgreSQL bem-sucedida - {dt.datetime.now()}")
            return self.connection
        except OperationalError as e:
            print(f"O erro '{e}' ocorreu - {dt.datetime.now()}")
            return None
    
    def close(self):
        if self.connection:
            self.connection.close()


# repositories.py - Operações com o banco de dados
class SalesRepository:
    def __init__(self, connection):
        self.connection = connection
    
    def get_sales_data(self):
        query = f"""
        SELECT 
            id_venda_item, id_venda, data_venda, data_envio,
            tipo_envio, id_cliente, nome_cliente, segmento, 
            pais, cidade, estado, codigo_postal, regiao, 
            id_produto, descricao_produto, categoria_produto, 
            subcategoria_produto, valor_venda, quantidade_vendida, 
            desconto, margem,created_at,empresa_id
        FROM public.api_integration
        WHERE created_at > '{today} 00:00:00.000';
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        
        return data, columns
    


