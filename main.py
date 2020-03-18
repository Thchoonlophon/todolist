import os
import sys
import time

import records
import numpy as np

host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
db_name = os.getenv("MYSQL_DB")
user = os.getenv("MYSQL_USER")
pwd = os.getenv("MYSQL_PWD")


def get_db():
    db_url = f"mysql://{user}:{pwd}@{host}:{port}/{db_name}"
    db = records.Database(db_url)
    return db


def get_status(x):
    status = "✔" if x == 1 else "✘"
    return status


def history(dbo, date):
    sql = f"""select content from todo_list where status=0 and imp_date<'{date}' order by imp_time"""
    rows = dbo.query(sql)
    df = rows.export("df")
    sql = f"""select max(id) maid from todo_list where imp_date='{date}'"""
    rows = dbo.query(sql)
    li = rows.all()[0]["maid"]
    max_id = int(li) if li else -1
    df["rows"] = [i for i in range(1, len(df) + 1)]
    df["id"] = df[["rows"]].applymap(lambda x: x + max_id)
    df["id"] = df[["id"]].applymap(lambda x: "0" + str(x) if len(str(x)) == 1 else x)
    df["imp_date"] = [date for _ in range(len(df))]
    df["imp_time"] = [time.strftime("%Y-%m-%d %H:%M:%S") for _ in range(len(df))]
    df.drop("rows", axis=1, inplace=True)
    data = np.array(df).tolist()
    for i in data:
        sql = f"""insert into todo_list(content,id,imp_date,imp_time) values('{i[0]}','{i[1]}','{i[2]}','{i[-1]}')"""
        dbo.query(sql)
    sql = f"""delete from todo_list where status=0 and imp_date<'{date}'"""
    dbo.query(sql)


def todo_list(*args):
    args = args[0]
    sql = f"""select count(*) cont from todo_list where status=0 and imp_date<'{args["date"]}'"""
    rows = args["dbo"].query(sql)
    cont = rows.all()[0]["cont"]
    _ = history(args["dbo"], args["date"]) if cont > 0 else None
    sql = f"""select id,content,status from todo_list where imp_date='{args["date"]}' order by id"""
    rows = args["dbo"].query(sql)
    df = rows.export("df")
    data = df.to_dict("records")
    content_list = df["content"].tolist() if not df.empty else []
    content_len = [len(i) for i in content_list]
    max_len = max(content_len) if len(content_len) > 0 else 8
    head = """\t\t\t────────────────────""" + "─" * max_len + "\n" + \
           """\t\t\t status   id    """ + " " * ((max_len - 5) // 2) + "event" + " " * (
                   max_len - ((max_len - 5) // 2 + 5)) + "\n" + \
           """\t\t\t────────────────────""" + "─" * max_len + "\n"""
    content = [
        f"""\t\t\t    {get_status(i["status"])}     {i["id"]}    """ + " " * ((max_len - len(i["content"])) // 2) + i[
            "content"] + "  \n" for i in data]
    footer = head.split("\n")[-2]
    strings = "Nothing To Do!"
    content_str = "".join(content) if content != [] else (("\t\t\t" + " " * ((footer.count("─") - 14) // 2)
                                                           ) + strings + "\n")
    title = "\n\n\t\t\t" + " " * ((footer.count("─") - 9) // 2) + "TODO List\n"
    print(title)
    print(head + content_str + footer + "\n\n")


def done(*args):
    args = args[0]
    sql = f"""update todo_list set status=1 where id='{args["the_id"]}' and imp_date='{args["date"]}'"""
    args["dbo"].query(sql)
    todo_list(args)


def undo(*args):
    args = args[0]
    sql = f"""update todo_list set status=0 where id='{args["the_id"]}' and imp_date='{args["date"]}'"""
    args["dbo"].query(sql)
    todo_list(args)


def add(*args):
    args = args[0]
    sql = f"""select max(id) maid from todo_list where imp_date='{args["date"]}'"""
    rows = args["dbo"].query(sql)
    get_id = rows.all()[0]["maid"]
    maid = int(get_id) if get_id else -1
    sql = f"""insert into todo_list(id,content,imp_date,imp_time) values('{"0" + str(maid + 1) if
    len(str(maid + 1)) < 2 else str(maid + 1)}','{args["content"]}','{args["date"]}',
    '{time.strftime("%Y-%m-%d %H:%M:%S")}')"""
    args["dbo"].query(sql)
    todo_list(args)


def delete(*args):
    args = args[0]
    sql = f"""delete from todo_list where id='{args["the_id"]}' and imp_date='{args["date"]}'"""
    args["dbo"].query(sql)
    sql = f"""update todo_list set id=(case when id-1<10 then concat('0',id-1) else 'new' end) where 
    id>{int(args["the_id"])} and imp_date='{args["date"]}'"""
    args["dbo"].query(sql)
    todo_list(args)


def modify(*args):
    args = args[0]
    sql = f"""update todo_list set content='{args["content"]}' where id='{args["the_id"]}' 
    and imp_date='{args["date"]}'"""
    args["dbo"].query(sql)
    todo_list(args)


def clean(*args):
    args = args[0]
    sql = f"""delete from todo_list where imp_date='{args["date"]}'"""
    args["dbo"].query(sql)
    todo_list(args)


def main_function(key, **kwargs):
    function = {
        "todo": todo_list,
        "add": add,
        "done": done,
        "undo": undo,
        "delete": delete,
        "modify": modify,
        "clean": clean
    }
    function[key](kwargs)


if __name__ == '__main__':
    params = sys.argv[1:]
    operate = params[0].split("\\")[-1].replace(".bat", "")
    dbo = get_db()
    date = time.strftime("%Y-%m-%d")
    the_id = params[1] if operate != "add" and len(params) >= 2 else ""
    content = params[1] if operate == "add" and len(params) >= 2 else params[2] if operate == "modify" else ""
    main_function(operate, dbo=dbo, date=date, the_id=the_id, content=content)
    dbo.close()
