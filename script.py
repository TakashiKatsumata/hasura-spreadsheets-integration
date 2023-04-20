import os
import json
import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Google API クレデンシャルの設定
scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds_json = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_KEY'])
creds = Credentials.from_service_account_info(creds_json, scopes)

# スプレッドシート情報
SPREADSHEET_ID = "1QFGyqjOCgWKsRrW22IF9XHtGoCs_L70OmkfeqmnYqIA"
SHEET_NAME = "シート1"

# Hasura クエリ
QUERY_TEMPLATE = """
query
{{
  properties_aggregate(
    where: {{
      _and: [
        {{ created_at: {{ _gte: "{date_start}" }} }},
        {{ created_at: {{ _lt: "{date_end}" }} }}
      ]
    }}
  ) {{
    aggregate {{
      count
    }}
  }}
}}
"""

# Hasura クライアントの作成
def create_hasura_client(endpoint, secret):
    transport = RequestsHTTPTransport(
        url=endpoint,
        headers={"x-hasura-admin-secret": secret},
        use_json=True
    )
    return Client(transport=transport, fetch_schema_from_transport=True)

# 日付範囲を取得
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

date_start = yesterday.strftime("%Y-%m-%d")
date_end = today.strftime("%Y-%m-%d")

# SQL クエリを実行
pro_hasura_client = create_hasura_client("https://graphql.home.athearth.com/v1/graphql", os.environ["PRO_HASURA_SECRET"])
st_hasura_client = create_hasura_client("https://graphql.staging.home.athearth.com/v1/graphql", os.environ["ST_HASURA_SECRET"])

query1 = gql(QUERY_TEMPLATE.format(date_start=date_start, date_end=date_end))
pro_result1 = pro_hasura_client.execute(query1)["properties_aggregate"]["aggregate"]["count"]
st_result1 = st_hasura_client.execute(query1)["properties_aggregate"]["aggregate"]["count"]

# SQL2 クエリ
query2 = gql("""
{
  properties_aggregate(
    where: {
      is_open: { _eq: true },
      is_ignore: { _eq: false },
      _or: [
        { is_acceptable_foreign_nationals: { _eq: true } },
        { property_company: { acceptable_foreign_nationals_status: { _eq: "ok" } } }
      ]
    }
  ) {
    aggregate {
      count
    }
  }
}
""")

pro_result2 = pro_hasura_client.execute(query2)["properties_aggregate"]["aggregate"]["count"]
st_result2 = st_hasura_client.execute(query2)["properties_aggregate"]["aggregate"]["count"]

# スプレッドシートにデータを追加
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

data = [
    yesterday.strftime("%Y/%m/%d"),
    pro_result1,
    pro_result2,
    st_result1,
    st_result2
]

append_request = sheet.values().append(
    spreadsheetId=SPREADSHEET_ID,
    range=SHEET_NAME,
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={
        "values": [data]
    }
)
append_request.execute()
