from app import DB, FLAGS, run


def migrate_and_send_again(path):
    FLAGS["debug"] = True
    DB.execute("create table if not exists users (id text, raw text, note text)")
    return run(path, "again.json", "migration")
