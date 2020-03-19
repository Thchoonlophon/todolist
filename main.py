import os
import sqlite3
import sys
import time

import pymysql
import pandas as pd
import numpy as np

host = None
# host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
db_name = os.getenv("MYSQL_DB")
user = os.getenv("MYSQL_USER")
pwd = os.getenv("MYSQL_PWD")
table = os.getenv("TODO_TABLE") if host else "todo_list"
path = os.path.abspath(__file__)
db_url = (("/".join(path.split("/")[:-1]) + "/") if "/" in path else (
        "\\".join(path.split("\\")[:-1]) + "\\")) + "script_db.sqlite"


def get_db():
    db = pymysql.connect(host, user, pwd, db_name) if host else sqlite3.connect(db_url)
    return db


class MyCursor:
    def __init__(self, connection):
        self._conn = connection
        self._cur = self._conn.cursor()

    def get_one(self, sql, **kwargs):
        self._cur.execute(sql, kwargs)
        data = self._cur.fetchone()
        return data

    def get_df(self, sql, index=None, **kwargs):
        self._cur.execute(sql, kwargs)
        cols = [i[0] for i in self._cur.description]
        rows = self._cur.fetchall()
        table = pd.DataFrame([[j for j in i] for i in rows], columns=cols)
        return table if not index else table.set_index(index)

    def execute_sql(self, sql, params=None, **kwargs):
        self._cur.execute(sql, kwargs) if not params else self._cur.executemany(sql, params)
        self._conn.commit()

    def close(self):
        self._cur.close()


def get_status(x):
    status = "✔" if x == 1 else "✘"
    return status


def history(dbo, date):
    sql = f"""select content from {table} where status=0 and imp_date<'{date}' order by imp_time"""
    df = dbo.get_df(sql)
    sql = f"""select max(id) maid from {table} where imp_date='{date}'"""
    row = dbo.get_one(sql)
    li = row[0] if row else None
    max_id = int(li) if li else -1
    df["rows"] = [i for i in range(1, len(df) + 1)]
    df["id"] = df[["rows"]].applymap(lambda x: x + max_id)
    df["id"] = df[["id"]].applymap(lambda x: "0" + str(x) if len(str(x)) == 1 else x)
    df["imp_date"] = [date for _ in range(len(df))]
    df["imp_time"] = [time.strftime("%Y-%m-%d %H:%M:%S") for _ in range(len(df))]
    df.drop("rows", axis=1, inplace=True)
    data = np.array(df).tolist()
    sql = f"""insert into {table}(content,id,imp_date,imp_time) values(:1,:2,:3,:4)"""
    dbo.execute_sql(sql, params=data)
    # for i in data:
    #     sql = f"""insert into {table}(content,id,imp_date,imp_time) values('{i[0]}','{i[1]}','{i[2]}','{i[-1]}')"""
    #     dbo.query(sql)
    sql = f"""delete from {table} where status=0 and imp_date<'{date}'"""
    dbo.execute_sql(sql)


def todo_list(*args):
    args = args[0]
    sql = f"""select count(*) cont from {table} where status=0 and imp_date<'{args["date"]}'"""
    row = args["dbo"].get_one(sql)
    cont = row[0] if row else None
    _ = history(args["dbo"], args["date"]) if cont > 0 else None
    sql = f"""select id,content,status from {table} where imp_date='{args["date"]}' order by id"""
    df = args["dbo"].get_df(sql)
    data = df.to_dict("records")
    content_list = df["content"].tolist() if not df.empty else []
    content_len = [len(i) for i in content_list]
    max_len = max(content_len) if len(content_len) > 0 else 8
    head = """\t    ────────────────────""" + "─" * max_len + "\n" + \
           """\t     status   id    """ + " " * ((max_len - 5) // 2) + "event" + " " * (
                   max_len - ((max_len - 5) // 2 + 5)) + "\n" + \
           """\t    ────────────────────""" + "─" * max_len + "\n"""
    content = [
        f"""\t        {get_status(i["status"])}     {i["id"]}    """ + " " * ((max_len - len(i["content"])) // 2) + i[
            "content"] + "  \n" for i in data]
    footer = head.split("\n")[-2]
    strings = "Nothing To Do!"
    content_str = "".join(content) if content != [] else (("\t    " + " " * ((footer.count("─") - 14) // 2)
                                                           ) + strings + "\n")
    title = "\n\n\t    " + " " * ((footer.count("─") - 9) // 2) + "TODO List\n"
    print(title)
    print(head + content_str + footer + "\n")


def done(*args):
    args = args[0]
    sql = f"""update {table} set status=1 where id='{args["the_id"]}' and imp_date='{args["date"]}'"""
    args["dbo"].execute_sql(sql)
    todo_list(args)


def undo(*args):
    args = args[0]
    sql = f"""update {table} set status=0 where id='{args["the_id"]}' and imp_date='{args["date"]}'"""
    args["dbo"].execute_sql(sql)
    todo_list(args)


def add(*args):
    args = args[0]
    sql = f"""select max(id) maid from {table} where imp_date='{args["date"]}'"""
    row = args["dbo"].get_one(sql)
    get_id = row[0] if row else None
    maid = int(get_id) if get_id else -1
    sql = f"""insert into {table}(id,content,imp_date,imp_time) values('{"0" + str(maid + 1) if
    len(str(maid + 1)) < 2 else str(maid + 1)}','{args["content"]}','{args["date"]}',
    '{time.strftime("%Y-%m-%d %H:%M:%S")}')"""
    args["dbo"].execute_sql(sql)
    todo_list(args)


def delete(*args):
    args = args[0]
    sql = f"""delete from {table} where id='{args["the_id"]}' and imp_date='{args["date"]}'"""
    args["dbo"].execute_sql(sql)
    sql = f"""update {table} set id=(case when id-1<10 then concat('0',id-1) else id-1 end) where 
    id>{int(args["the_id"])} and imp_date='{args["date"]}'""" if host else f"""update {table} set id=(
    case when id-1<10 then '0'||(id-1) else id-1 end) where id>'{args["the_id"]}' and 
    imp_date='{args["date"]}'"""
    args["dbo"].execute_sql(sql)
    todo_list(args)


def modify(*args):
    args = args[0]
    sql = f"""update {table} set content='{args["content"]}' where id='{args["the_id"]}' 
    and imp_date='{args["date"]}'"""
    args["dbo"].execute_sql(sql)
    todo_list(args)


def clean(*args):
    args = args[0]
    sql = f"""delete from {table} where imp_date='{args["date"]}'"""
    args["dbo"].execute_sql(sql)
    todo_list(args)


def get_help(args):
    print("\n\n")
    print("    todo [-h] | [-add | -clean | -delete | -done | -modify | -undo] <the id | content>")
    print('\t-add\t: You can use this param to write a new mission.\n\t\t  for a example: '
          'todo -add "the example"')
    print("\t-clean\t: you can use this param to clear the today's list.\n\t\t  for a example: "
          "todo -clean")
    print("\t-delete\t: You can use this param to delete a mission.\n\t\t  for a example: "
          "todo -delete <the id of the mission \n\t\t  which you want to delete>")
    print("\t-done\t: You can use this param to finish a mission.\n\t\t  for a example: "
          "todo -done <the id of the mission \n\t\t  which you want to finish>")
    print("\t-modify\t: You can use this param to modify the content of one mission.\n\t\t  for "
          "a example: todo -modify <the id of the mission which \n\t\t  you want to modify> <the "
          "content of this mission after modified>")
    print("\t-undo\t: You can use this param to chanag the status from finished to unfinish."
          "\n\t\t  for a example: todo -undo <the id of the mission which you want to \n\t\t  "
          "change the status back to unfinish>")
    print("\t-h\t: You can use this param to get help info\n\t\t  for a example: todo -h")


def main_function(key, **kwargs):
    function = {
        "todo": todo_list,
        "-add": add,
        "-done": done,
        "-undo": undo,
        "-delete": delete,
        "-modify": modify,
        "-clean": clean,
        "-h": get_help
    }
    function[key](kwargs)


if __name__ == '__main__':
    params = sys.argv[2:]
    operate = params[0] if len(params) > 0 else "todo"
    dbo = get_db()
    cur = MyCursor(dbo)
    date = time.strftime("%Y-%m-%d")
    the_id = params[1] if operate not in ("-add", "-h") and len(params) >= 2 else ""
    content = params[1] if operate == "-add" and len(params) >= 2 else params[2] if operate == "-modify" else ""
    main_function(operate, dbo=cur, date=date, the_id=the_id, content=content)
    cur.close()
    dbo.close()
