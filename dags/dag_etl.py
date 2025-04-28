from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime,timedelta


class ETLSalesPipelines:
    @staticmethod
    def transform_time_dimension(df):
        import pandas as pd 
        df = df['data_venda'].drop_duplicates().reset_index()
        df['data_venda'] = pd.to_datetime(df['data_venda'])
        df['id_data_venda'] = df['data_venda'].dt.strftime('%Y%m%d')
        df['ano_venda'] = df['data_venda'].dt.year
        df['mes_venda'] = df['data_venda'].dt.month
        df['dia_venda'] = df['data_venda'].dt.day
        return df
    
    @staticmethod
    def transform_timeship_dimension(df):
        import pandas as pd 
        df = df['data_envio'].drop_duplicates().reset_index()
        df['data_envio'] = pd.to_datetime(df['data_envio'])
        df['id_data_entrega'] = df['data_envio'].dt.strftime('%Y%m%d')
        df['ano_entrega'] = df['data_envio'].dt.year
        df['mes_entrega'] = df['data_envio'].dt.month
        df['dia_entrega'] = df['data_envio'].dt.day
        return df

    @staticmethod
    def transform_client_dimension(df):
        import pandas as pd 
        df = df[['id_cliente','nome_cliente','segmento',
                'pais','cidade','estado','codigo_postal',
                'regiao','created_at','empresa_id']]\
                .drop_duplicates(subset=['id_cliente'])\
                .reset_index(drop=True)
        return df
    
    @staticmethod
    def transform_ship_type(df):
        import pandas as pd 
        df = df[['tipo_envio','created_at','empresa_id']]\
                .drop_duplicates(subset=['tipo_envio','empresa_id'])
        df['id_tipo_entrega'] = df['empresa_id'].astype(str) +'-'+ df['tipo_envio'].astype(str)
        return df[['id_tipo_entrega','tipo_envio','created_at','empresa_id']]
    
    def transform_product_dimension(df):
        import pandas as pd 
        df = df[['id_produto','descricao_produto','categoria_produto',
                 'subcategoria_produto','created_at','empresa_id']]\
                .drop_duplicates(subset=['id_produto','empresa_id'])\
                .reset_index(drop=True)
        return df
    
    def transform_sales_fact(df):
        import pandas as pd 
        df_sale = df[['id_venda_item','id_venda','quantidade_vendida','valor_venda',
                'desconto','margem','created_at','empresa_id','id_cliente',
                'id_produto','tipo_envio','data_envio','data_venda']].copy()
        df_sale['data_envio'] = pd.to_datetime(df_sale['data_envio'])
        df_sale['data_venda'] = pd.to_datetime(df_sale['data_venda'])
        df_sale['tipo_entrega_id'] = df_sale['empresa_id'].astype(str) +'-'+ df['tipo_envio'].astype(str)
        df_sale['data_entrega_id'] = df_sale['data_envio'].dt.strftime('%Y%m%d')
        df_sale['data_venda_id'] = df_sale['data_venda'].dt.strftime('%Y%m%d')
        return df_sale[['id_venda_item','id_venda','quantidade_vendida',
                   'valor_venda','desconto','margem','created_at',
                   'empresa_id','id_cliente','data_entrega_id',
                   'data_venda_id','id_produto','tipo_entrega_id']]


class SalesService:
    def __init__(self, repository):
        self.repository = repository
    
    def _get_sales_dataframe(self) -> pd.DataFrame:
        """Obtém os dados de vendas como DataFrame."""
        data, columns = self.repository.get_sales_data()
        return pd.DataFrame(data, columns=columns)
    
    def _process_dimension(self, transform_method: str, insert_method: str) -> str:
        """Processa uma dimensão genérica."""
        df = self._get_sales_dataframe()
        transformed_df = getattr(ETLSalesPipelines, transform_method)(df)
        
        chunk_size = 100
        total_registros = len(transformed_df)
        success_count = 0
        
        if total_registros > 100:
            while success_count < total_registros:               
                
                chunk = transformed_df[success_count:success_count + chunk_size]

                getattr(self, insert_method)(chunk)
                success_count += chunk_size
                print(f"Enviados {len(chunk)} registros (total: {success_count} de {total_registros})")
        else:
            getattr(self, insert_method)(transformed_df)
        return f"{transform_method.replace('transform_', '').replace('_', ' ').title()} finalizada {datetime.now()}"
    
    def process_shiptype_dimension(self) -> str:
        return self._process_dimension('transform_ship_type', '_insert_shiptype_dimension')
    
    def process_time_dimension(self) -> str:
        return self._process_dimension('transform_time_dimension', '_insert_time_dimension')
    
    def process_timeship_dimension(self):
        return self._process_dimension('transform_timeship_dimension', '_insert_timeship_dimension')
    
    def process_client_dimension(self):
        return self._process_dimension('transform_client_dimension', '_insert_client_dimension')
        
    def process_product_dimension(self):
        return self._process_dimension('transform_product_dimension', '_insert_product_dimension')
    
    def process_fact_sales(self):
        return self._process_dimension('transform_sales_fact', '_insert_fact_sales')
    
    def _insert_time_dimension(self, df):
        with self.repository.connection.cursor() as cursor:
            for data in df.values:
                query = """
                INSERT INTO dw_vendas.dim_tempo_venda (
                    id_data_venda, data_venda, ano_venda, 
                    mes_venda, dia_venda) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id_data_venda) DO NOTHING;
                """
                cursor.execute(query, (
                    data[2], data[1], data[3], 
                    data[4], data[5]
                ))
            self.repository.connection.commit()

    def _insert_timeship_dimension(self, df):
        with self.repository.connection.cursor() as cursor:
            for data in df.values:
                query = """
                INSERT INTO dw_vendas.dim_tempo_entrega (
                    id_data_entrega, data_entrega, ano_entrega, 
                    mes_entrega, dia_entrega) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id_data_entrega) DO NOTHING;
                """
                cursor.execute(query, (
                    data[2], data[1], data[3], 
                    data[4], data[5]
                ))
            self.repository.connection.commit()

    def _insert_client_dimension(self,df):
        with self.repository.connection.cursor() as cursor:
            for data in df.values:
                query = """
                INSERT INTO dw_vendas.dim_cliente
                    (id_cliente, nome_cliente, segmento, pais, cidade,
                    estado, codigo_postal, regiao, created_at, empresa_id)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id_cliente) DO NOTHING;
                """           

                cursor.execute(query, (
                    data[0],data[1],data[2],
                    data[3],data[4],data[5],
                    data[6],data[7],data[8],
                    data[9]
                ))
            self.repository.connection.commit()

    def _insert_shiptype_dimension(self, df):
        with self.repository.connection.cursor() as cursor:
            for data in df.values:
                query = """
                INSERT INTO dw_vendas.dim_tipo_entrega
                    (id_tipo_entrega, tipo_entrega, created_at, empresa_id)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT (id_tipo_entrega) DO NOTHING;
                """

                cursor.execute(query,(
                    data[0],data[1],
                    data[2],data[3]
                ))
            self.repository.connection.commit()

    def _insert_product_dimension(self, df):
        with self.repository.connection.cursor() as cursor:
            for data in df.values:
                query = """
                INSERT INTO dw_vendas.dim_produto
                    (id_produto, produto, categoria, sub_categoria, created_at, empresa_id)
                VALUES(%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id_produto) DO NOTHING;
                """

                cursor.execute(query, (
                    data[0],data[1],data[2],
                    data[3],data[4],data[5]
                ))

            self.repository.connection.commit()
    
    def _insert_fact_sales(self, df):
        with self.repository.connection.cursor() as cursor:
            for data in df.values:
                query = """
                INSERT INTO dw_vendas.fato_vendas
                    (id_venda_item, venda, quantidade, venda_valor,
                    desconto, margem, created_at, empresa_id, cliente_id,
                    data_entrega_id, data_venda_id, produto_id, tipo_entrega_id)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """

                cursor.execute(query, (
                    data[0],data[1],data[2],data[3],
                    data[4],data[5],data[6],data[7],data[8],
                    data[9],data[10],data[11],data[12]
                ))

            self.repository.connection.commit()  

def create_etl_task(process_method: str):
    """Factory function para criar funções callable dinâmicas"""
    def etl_callable():
        # 2. Mova todos os imports pesados para dentro da função
        import dotenv
        from utils.engine_etl import SalesRepository, DatabaseConnection
        import pandas as pd
        import os
        
        dotenv.load_dotenv()
        
        db = DatabaseConnection(
            os.getenv('DATABASE'), os.getenv('USER_DB'), 
            os.getenv('PASSWORDDB'), os.getenv('HOSTDB'), os.getenv('PORTDB')
        )
        
        connection = db.connect()
        if connection:
            try:
                repository = SalesRepository(connection)
                service = SalesService(repository)
                result = getattr(service, process_method)()
                print(result)
            finally:
                db.close()
    
    return etl_callable


default_args = {
    "owner": "Data Team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    "etl_datawarehouse",
    default_args=default_args,
    start_date=datetime(2025,4,24),
    schedule=None,
    catchup=False,
    tags=['ETL','DW','Sales'],
) as dag:
    clientes = PythonOperator(
        task_id='etl_CLientes',
        python_callable=create_etl_task('process_client_dimension')
    )

    produtos = PythonOperator(
        task_id='etl_Produtos',
        python_callable=create_etl_task('process_product_dimension')

    )

    tempo_venda = PythonOperator(
        task_id = 'etl_tempo_venda',
        python_callable=create_etl_task('process_time_dimension')

    )

    tempo_entrega = PythonOperator(
        task_id = 'etl_tempo_entrega',
        python_callable=create_etl_task('process_timeship_dimension')
       
    )

    tipo_entrega = PythonOperator(
        task_id = 'etl_tipo_Entrega',
        python_callable= create_etl_task('process_shiptype_dimension')

    )

    fato_vendas = PythonOperator(
        task_id = 'etl_fato_vendas',
        python_callable= create_etl_task('process_fact_sales')

    )

    clientes >> produtos >> tempo_venda >> tempo_entrega >> tipo_entrega >> fato_vendas

    


