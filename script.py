import os
import json
import datetime
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

# Hasuraエンドポイントとシークレットキーの設定
pro_hasura_url = "https://graphql.home.athearth.com/v1/graphql"
st_hasura_url = "https://graphql.staging.home.athearth.com/v1/graphql"

pro_hasura_headers = {
    "Content-Type": "application/json",
    "x-hasura-admin-secret": os.environ["PRO_HASURA_SECRET"]
}

st_hasura_headers = {
    "Content-Type": "application/json",
    "x-hasura-admin-secret": os.environ["ST_HASURA_SECRET"]
}

pro_hasura_transport = RequestsHTTPTransport(url=pro_hasura_url, headers=pro_hasura_headers)
st_hasura_transport = RequestsHTTPTransport(url=st_hasura_url, headers=st_hasura_headers)

pro_hasura_client = Client(transport=pro_hasura_transport, fetch_schema_from_transport=False)
st_hasura_client = Client(transport=st_hasura_transport, fetch_schema_from_transport=False)

# 既存のコードはここから続きます
query1 = gql("""
    query {
        properties_aggregate(where: {
            created_at: {
                _eq: "yesterday"
            }
        }) {
            aggregate {
                count
            }
        }
    }
""")

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
