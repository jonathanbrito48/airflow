from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

file_temp='integration.json'

def prepara_arquivo_request():
    import pandas as pd
    df = pd.read_csv('/home/jonathan-brito/Documentos/archive/Sample - Superstore.csv',
                     sep=',',
                     encoding='latin1')
    
    df = df[['Order ID', 'Order Date', 'Ship Date', 'Ship Mode',
       'Customer ID', 'Customer Name', 'Segment', 'Country', 'City', 'State',
       'Postal Code', 'Region', 'Product ID', 'Category', 'Sub-Category',
       'Product Name', 'Sales', 'Quantity', 'Discount', 'Profit']]
    
    df.rename(columns={
        'Order ID':'id_venda',
        'Order Date':'data_venda',
        'Ship Date':'data_envio',
        'Ship Mode':'tipo_envio',
        'Customer ID':'id_cliente',
        'Customer Name':'nome_cliente',
        'Segment':'segmento',
        'Country':'pais',
        'City':'cidade',
        'State':'estado',
        'Postal Code':'codigo_postal',
        'Region':'regiao',
        'Product ID':'id_produto',
        'Category':'categoria_produto',
        'Sub-Category':'subcategoria_produto',
        'Product Name':'descricao_produto',
        'Sales':'valor_venda',
        'Quantity':'quantidade_vendida',
        'Discount':'desconto',
        'Profit':'margem'
    }, inplace=True)

    df['data_venda'] = pd.to_datetime(df['data_venda'],format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
    df['data_envio'] = pd.to_datetime(df['data_envio'],format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
    df['quantidade_vendida'] = df['quantidade_vendida'].astype('float')


    df.to_json(file_temp,indent=1,orient='records')

    return print(f"dados de integração prontos - {datetime.now()}")

def integra_api():
    import requests
    import json
    import os

    url='http://localhost:8000/integration/'

    with open(file_temp,'r') as file:
        all_data = json.load(file)

    headers = {
        'Authorization': 'Token 4940c39cca654751110b9ada1fcdade5',
        'Content_Type': 'application/json'
    }

    chunk_size = 100
    total_registros = len(all_data)
    success_count = 0

    while success_count < total_registros:
        chunk = all_data[success_count:success_count + chunk_size]
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=chunk  # Usa json= em vez de data= para auto-serialização
            )
            response.raise_for_status()  # Verifica erros HTTP
            success_count += chunk_size
            print(f"Enviados {len(chunk)} registros (total: {success_count} de {total_registros})")
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {str(e)}")
            raise

    os.remove(file_temp)

    return print(f"{response.text,'-', datetime.now()}")

    
default_args= {
    "owner": "data_team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2)
}

with DAG(
    "integracao_api",
    default_args=default_args,
    start_date=datetime(2024,1,1),
    schedule_interval=None,
    catchup=False,
) as dag:
    preparar = PythonOperator(task_id="preparar_dados",
                              python_callable=prepara_arquivo_request
                              )
    integra = PythonOperator(
        task_id="integracao_api",
        python_callable=integra_api
        )

    trigger_filha = TriggerDagRunOperator(
        task_id = "trigger_etl_dw",
        trigger_dag_id="etl_datawarehouse",
        execution_date= '{{ ds }}'
    )    
    preparar >> integra >> trigger_filha


    

