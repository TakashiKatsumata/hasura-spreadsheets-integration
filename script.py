import os
import json
import datetime
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

creds_json = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"])
creds = service_account.Credentials.from_service_account_info(creds_json)

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

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
service = build("sheets", "v4", credentials=creds)

spreadsheet_id = "1QFGyqjOCgWKsRrW22IF9XHtGoCs_L70OmkfeqmnYqIA"
sheet_name = "物件取り込み数"

today = datetime.datetime.now().strftime("%Y/%m/%d")

pro_result1 = pro_hasura_client.execute(query1)["properties_aggregate"]["aggregate"]["count"]
st_result1 = st_hasura_client.execute(query1)["properties_aggregate"]["aggregate"]["count"]
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
    spreadsheetId=spreadsheet_id,
    range=sheet_name,
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={
        "values": [data]
    }
)
append_request.execute()
