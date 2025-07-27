from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gallery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(80))
    model = db.Column(db.String(80))
    year = db.Column(db.Integer)
    engine_cc = db.Column(db.Integer)
    cylinders = db.Column(db.Integer)
    transmission = db.Column(db.String(50))
    fuel_type = db.Column(db.String(50))
    body_type = db.Column(db.String(50))
    mileage = db.Column(db.Integer)
    color = db.Column(db.String(50))
    plate = db.Column(db.String(20))
    paint_status = db.Column(db.String(200))
    purchase_price = db.Column(db.Float)
    sold = db.Column(db.Boolean, default=False)
    sale_price = db.Column(db.Float)
    sale_date = db.Column(db.Date)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'))
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    car = db.relationship('Car', backref=db.backref('expenses', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    db.create_all()
    if not User.query.first():
        admin = User(username='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

with app.app_context():
    init_db()

@app.route('/')
@login_required
def index():
    cars = Car.query.all()
    return render_template('index.html', cars=cars)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/cars/new', methods=['GET', 'POST'])
@login_required
def new_car():
    if request.method == 'POST':
        car = Car(
            brand=request.form['brand'],
            model=request.form['model'],
            year=request.form['year'],
            engine_cc=request.form['engine_cc'],
            cylinders=request.form['cylinders'],
            transmission=request.form['transmission'],
            fuel_type=request.form['fuel_type'],
            body_type=request.form['body_type'],
            mileage=request.form['mileage'],
            color=request.form['color'],
            plate=request.form['plate'],
            paint_status=request.form['paint_status'],
            purchase_price=request.form['purchase_price'],
        )
        db.session.add(car)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_car.html')

@app.route('/cars/<int:car_id>')
@login_required
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    total_expenses = sum(e.amount for e in car.expenses)
    cost = (car.purchase_price or 0) + total_expenses
    profit = None
    if car.sold and car.sale_price:
        profit = car.sale_price - cost
    return render_template('car_detail.html', car=car, cost=cost, profit=profit)

@app.route('/cars/<int:car_id>/expense', methods=['POST'])
@login_required
def add_expense(car_id):
    car = Car.query.get_or_404(car_id)
    description = request.form['description']
    amount = float(request.form['amount'])
    expense = Expense(car=car, description=description, amount=amount)
    db.session.add(expense)
    db.session.commit()
    return redirect(url_for('car_detail', car_id=car_id))

@app.route('/cars/<int:car_id>/sell', methods=['POST'])
@login_required
def sell_car(car_id):
    car = Car.query.get_or_404(car_id)
    car.sale_price = float(request.form['sale_price'])
    car.sale_date = datetime.strptime(request.form['sale_date'], '%Y-%m-%d').date()
    car.sold = True
    db.session.commit()
    return redirect(url_for('car_detail', car_id=car_id))

@app.route('/reports')
@login_required
def reports():
    cars = Car.query.all()
    total_purchase = sum(c.purchase_price or 0 for c in cars)
    total_expense = sum(e.amount for c in cars for e in c.expenses)
    total_sales = sum(c.sale_price or 0 for c in cars if c.sold)
    profit = total_sales - (total_purchase + total_expense)
    sold_count = len([c for c in cars if c.sold])
    stock_count = len([c for c in cars if not c.sold])
    return render_template('reports.html', **locals())

if __name__ == '__main__':
    app.run(debug=True)
