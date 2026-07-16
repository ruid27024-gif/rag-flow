import pymysql

new_api_key = "你的新API_KEY"

conn = pymysql.connect(
    host="localhost",
    port=5455,
    user="root",
    password="infini_rag_flow",
    database="rag_flow",
    charset="utf8mb4"
)

try:
    with conn.cursor() as cursor:
        sql = """
        UPDATE tenant_llm
        SET api_key = %s
        """
        cursor.execute(sql, ('sk-ws-H.EDIHPRL.RRr3.MEQCHybUX2NyotJScLSrKWV6lAA5niqfAv-I7n8GlL6NrSQCIQCFJieAnNLTw1yKk50U4PKdQ70Dr0qkNTczLQufruFwNQ',))
        conn.commit()

        print(f"已更新 {cursor.rowcount} 行")

finally:
    conn.close()