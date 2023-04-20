import os
import json
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Googleスプレッドシートへの認証
credentials_json = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_KEY'])
credentials = service_account.Credentials.from_service_account_info(credentials_json)
sheets_api = build('sheets', 'v4', credentials=credentials)

# スプレッドシートIDとシート名
spreadsheet_id = '1QFGyqjOCgWKsRrW22IF9XHtGoCs_L70OmkfeqmnYqIA'
sheet_name = 'Sheet1'

# Hasura GraphQLエンドポイントとヘッダー
pro_hasura_url = 'https://graphql.home.athearth.com/v1/graphql'
st_hasura_url = 'https://graphql.staging.home.athearth.com/v1/graphql'
headers = {
    'Content-Type': 'application/json',
    'x-hasura-admin-secret': os.environ['PRO_HASURA_SECRET']
}

# SQLクエリ
sql1 = "SELECT COUNT(*) FROM properties WHERE to_char(created_at, 'yyyy/mm/dd') = to_char(CURRENT_DATE - 1, 'yyyy/mm/dd')"
sql2 = "SELECT COUNT(*) FROM properties p JOIN property_companies pc ON p.property_company_id = pc.id WHERE p.is_open AND NOT p.is_ignore AND (p.is_acceptable_foreign_nationals OR pc.acceptable_foreign_nationals_status = 'ok')"

# GraphQLクエリテンプレート
graphql_query_template = '''
query($sql: String!) {
  result: __run_sql(sql: $sql) {
    rows
  }
}
'''

def run_sql_query(hasura_url, sql):
    transport = RequestsHTTPTransport(url=hasura_url, headers=headers, use_json=True)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query = gql(graphql_query_template)
    result = client.execute(query, variable_values={'sql': sql})
    return result['result']['rows'][0]['count']

# 各エンドポイントでSQLクエリを実行
pro_sql1_result = run_sql_query(pro_hasura_url, sql1)
pro_sql2_result = run_sql_query(pro_hasura_url, sql2)
st_sql1_result = run_sql_query(st_hasura_url, sql1)
st_sql2_result = run_sql_query(st_hasura_url, sql2)

# 現在の日付を取得
today = datetime.datetime.now().strftime('%Y/%m/%d')

# スプレッドシートに書き込むデータ
data = [
    [today, pro_sql1_result, pro_sql2_result, st_sql1_result, st_sql2_result]
]

# スプレッドシートへの書き込み
range_name = f'{sheet_name}!A:A'
result = sheets_api.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
rows = result.get('values', [])
row_number = len(rows) + 1

range_name = f'{sheet_name}!A{row_number}:E{row_number}'
body = {
    'range': range_name,
    'values': data
}
sheets_api.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='RAW', body=body).execute()

