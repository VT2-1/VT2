import os

os.chdir(r"C:\Users\Trash\Documents\VarTexter2")

import sqlite3

db = sqlite3.connect(".ft")
cur = db.cursor()

print(cur.execute("""SELECT * FROM files""").fetchall())
print(cur.execute("""SELECT * FROM tags""").fetchall())
print(cur.execute("""SELECT * FROM file_tags""").fetchall())
