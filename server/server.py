from flask import Flask
from database.database import init_db

app = Flask('J4U-Server')



@app.teardown_appcontext
def shutdown_session(exception=None):
  db_session.remove()

if __name__ == "__main__":
  init_db()
  app.run()