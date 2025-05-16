from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session , get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from geopy.geocoders import Nominatim
import pymysql
from flask_migrate import Migrate

pymysql.install_as_MySQLdb()

app = Flask(__name__)

def to_celsius(temp):
    return round(float(temp) - 273.15, 2)
                    
def to_fahrenheit(temp):
    return round((float(temp) - 273.15) * 9/5 + 32, 2)

def to_mph(speed):
    return round(float(speed) * 2.237, 2)

def to_hg(pressure):
    return round(float(pressure) * 0.02953, 2)

app.config['SECRET_KEY'] = '86b8f64c32ca404a8e5dd422adaa4d60d9419037d2f02323269cb4f405306313'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:anshu2005@localhost/weather_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

migrate = Migrate(app, db)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    favorites = db.Column(db.String(255), default="")

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        flash('You are already registered and logged in!', 'info')
        return redirect(url_for('weather'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email) |
            (User.mobile == mobile)
        ).first()

        if existing_user:
            flash('Username, email, or mobile number already exists!', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    

    return render_template('register.html')

def get_city_from_latlon(lat, lon):
    geolocator = Nominatim(user_agent="weather_app")
    location = geolocator.reverse((lat, lon), exactly_one=True)
    return location.raw.get("address", {}).get("city", "Your Location")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        flash('You are already logged in!', 'info')
        return redirect(url_for('weather'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter((User.username == username) | (User.email == username)).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['username'] = user.username
            session.modified = True
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(url_for('weather'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    session.pop('username', None)
    logout_user()
    session.pop('_flashes',None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    data = request.get_json()
    city = data.get("city", "").strip().capitalize()

    if not city:
        return jsonify({"success": False, "message": "Invalid city"})

    user = User.query.get(current_user.id)
    favorite_list = user.favorites.split(",") if user.favorites else []

    if city in favorite_list:
        return jsonify({"success": False, "message": "City already in favorites"})
    elif len(favorite_list) >= 5:
        return jsonify({"success": False, "message": "You can only save up to 5 favorite cities"})

    favorite_list.append(city)
    user.favorites = ",".join(favorite_list)
    db.session.commit()

    return jsonify({"success": True, "message": "City added successfully"})

@app.route('/remove_favorite/<city>', methods=['GET'])
@login_required
def remove_favorite(city):
    user = User.query.get(current_user.id)
    favorite_list = user.favorites.split(",") if user.favorites else []

    if city in favorite_list:
        favorite_list.remove(city)
        user.favorites = ",".join(favorite_list)
        db.session.commit()
        flash(f"{city} removed from favorites!", "info")

    return redirect(url_for("weather"))

@app.route('/', methods=['GET', 'POST'])
@login_required
def weather():
    username = session.get('username')
    api_key = '04c14d81f665a82641413f3c7e58584c'

    # Prioritize POST data over URL params
    if request.method == 'POST':
        city = request.form.get('city')
        lat = request.form.get('lat')
        lon = request.form.get('lon')
    else:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        city = None

    if not city and not (lat and lon):
        city = 'NADAUN'

    if lat and lon:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}"
    else:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}"

    try:
        response = urllib.request.urlopen(weather_url)
        list_of_data = json.loads(response.read())

        response_forecast = urllib.request.urlopen(forecast_url)
        forecast_data = json.loads(response_forecast.read())
    except Exception as e:
        if request.method == 'POST':
            return jsonify({"success": False, "message": "Could not fetch weather data"})
        flash("Could not fetch weather data. Please try again.", "weather_error")
        return redirect(url_for("weather"))

    timezone_offset = list_of_data.get('timezone', 0)
    local_timezone = timezone(timedelta(seconds=timezone_offset))

    cityname = list_of_data.get("name", "").strip()
    if not cityname and lat and lon:
        cityname = get_city_from_latlon(float(lat), float(lon))

    data = {
        "cityname": cityname,
        "country_code": list_of_data['sys']['country'],
        "coordinate": f"{list_of_data['coord']['lon']} {list_of_data['coord']['lat']}",
        "temp_cel": to_celsius(list_of_data['main']['temp']),
        "temp_fah": to_fahrenheit(list_of_data['main']['temp']),
        "pressure_hpa": list_of_data['main']['pressure'],
        "pressure_hg": to_hg(list_of_data['main']['pressure']),
        "humidity": list_of_data['main']['humidity'],
        "wind_speed_mps": list_of_data['wind']['speed'],
        "wind_speed_mph": to_mph(list_of_data['wind']['speed']),
        "visibility": list_of_data.get('visibility', 'N/A'),
        "sunrise": datetime.fromtimestamp(list_of_data['sys']['sunrise'], local_timezone).strftime('%H:%M:%S'),
        "sunset": datetime.fromtimestamp(list_of_data['sys']['sunset'], local_timezone).strftime('%H:%M:%S'),
        "weather_desc": list_of_data['weather'][0]['description'].capitalize(),
    }

    forecast_dict = {}
    hourly_forecast = []
    for entry in forecast_data['list']:
        date = entry['dt_txt'].split(' ')[0]
        time = entry['dt_txt'].split(' ')[1][:5]
        
        if date not in forecast_dict:
            forecast_dict[date] = {
                "temp_cel": [],
                "temp_fah": [],
                "weather": entry['weather'][0]['description']
            }
        forecast_dict[date]["temp_cel"].append(to_celsius(entry['main']['temp']))
        forecast_dict[date]["temp_fah"].append(to_fahrenheit(entry['main']['temp']))

    for entry in forecast_data['list'][:24]:
        time = entry['dt_txt'].split(' ')[1][:5]
        hourly_forecast.append({
            "time": time,
            "temp_cel": to_celsius(entry['main']['temp']),
            "temp_fah": to_fahrenheit(entry['main']['temp']),
            "weather": " ".join(word.capitalize() for word in entry['weather'][0]['description'].split())
        })

    forecast_list = []
    for date, values in forecast_dict.items():
        avg_temp_cel = round(sum(values["temp_cel"]) / len(values["temp_cel"]), 2)
        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%y")
        # Capitalize each word in the weather description
        weather_desc = " ".join(word.capitalize() for word in values["weather"].split())
        forecast_list.append({
            "date": formatted_date,
            "temp_cel": avg_temp_cel,
            "weather":weather_desc
        })

    if request.method == 'POST':
        return jsonify({
            "success": True,
            "data": data,
            "hourly_forecast": hourly_forecast,
            "forecast": forecast_list
        })
    return render_template('index.html', username=username, data=data, forecast=forecast_list, hourly_forecast=hourly_forecast, user=current_user)

@app.route('/about', methods=['GET', 'POST'])
def about():
    if request.method == 'POST':
        # Handle feedback/suggestion form submission
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        feedback = request.form.get('feedback').strip()

        if name and email and feedback:
            new_feedback = Feedback(name=name, email=email, feedback=feedback)
            db.session.add(new_feedback)
            db.session.commit()
            flash('Thank you for your feedback!', 'success_feedback')
            return redirect(url_for('about'))
        else:
            flash('Please fill in all fields.', 'danger_feedback')

    return render_template('about.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)