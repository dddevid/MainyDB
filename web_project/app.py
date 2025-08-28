from flask import Flask, render_template, request, redirect, url_for
from MainyDB import MainyDB
import os

app = Flask(__name__)
DATABASE_FILE = os.path.join(app.root_path, 'data.mdb')
db = MainyDB(DATABASE_FILE)

@app.route('/')
def index():
    items = db.get_all()
    return render_template('index.html', items=items)

@app.route('/add', methods=['POST'])
def add_item():
    key = request.form['key']
    value = request.form['value']
    db.set(key, value)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
