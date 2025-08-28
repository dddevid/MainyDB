from flask import Flask, render_template, request, redirect, url_for
from MainyDB import MainyDB
import os

app = Flask(__name__)
DATABASE_FILE = os.path.join(app.root_path, 'data.mdb')
db = MainyDB(DATABASE_FILE)

@app.route('/')
def index():
    items = db.get_database("my_database").get_collection("items").find().to_list()
    return render_template('index.html', items=items)

@app.route('/add', methods=['POST'])
def add_item():
    item_name = request.form.get('item_name')
    if item_name:
        db.get_database("my_database").get_collection("items").insert_one({'name': item_name})
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
