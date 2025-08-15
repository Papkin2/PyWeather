from flask import Flask, render_template, request, redirect, url_for, session
from weather import main as get_weather
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        addr = request.form['address']
        session['data'] = get_weather(addr) 
        return redirect(url_for('index'))   
     
    data = session.pop('data', None)  
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)