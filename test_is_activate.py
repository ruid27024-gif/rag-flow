import pymysql

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
        # 1. 先查看将要设置为非激活的人数
        count_inactive_sql = """
        SELECT COUNT(*)
        FROM `user` u
        INNER JOIN sync_person sp
            ON u.email = sp.phone
        WHERE sp.phone IS NOT NULL
          AND sp.phone <> ''
          AND u.is_active <> '0'
          AND (
                sp.organize IS NULL
                OR TRIM(sp.organize) <> '数字化管理中心'
              )
        """

        cursor.execute(count_inactive_sql)
        inactive_count = cursor.fetchone()[0]

        print(f"将要设置为非激活的用户数量：{inactive_count}")

        # 2. 非数字化管理中心的人设置为非激活
        inactive_sql = """
        UPDATE `user` u
        INNER JOIN sync_person sp
            ON u.email = sp.phone
        SET u.is_active = '0'
        WHERE sp.phone IS NOT NULL
          AND sp.phone <> ''
          AND u.is_active <> '0'
          AND (
                sp.organize IS NULL
                OR TRIM(sp.organize) <> '数字化管理中心'
              )
        """

        cursor.execute(inactive_sql)
        inactive_updated = cursor.rowcount

        # 3. 数字化管理中心的人保持/设置为激活
        active_sql = """
        UPDATE `user` u
        INNER JOIN sync_person sp
            ON u.email = sp.phone
        SET u.is_active = '1'
        WHERE sp.phone IS NOT NULL
          AND sp.phone <> ''
          AND TRIM(sp.organize) = '数字化管理中心'
          AND u.is_active <> '1'
        """

        cursor.execute(active_sql)
        active_updated = cursor.rowcount

        conn.commit()

        print(f"已设置非激活用户数量：{inactive_updated}")
        print(f"已保持/设置激活用户数量：{active_updated}")

except Exception as e:
    conn.rollback()
    print("更新失败，已回滚：", e)

finally:
    conn.close()