#import statements
from flask import Flask, render_template, url_for, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from flask_ngrok import run_with_ngrok
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import secrets


secret_key = secrets.token_hex(16)  #generate a random secret key

app = Flask(__name__) # Construct an instance of Flask class for our webapp

app.secret_key = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db' #the database URI that should be used for the connection
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    #Relationship with other tables
    books = db.relationship('Book', backref='user') #one to many relationship with Book table
    transactions = db.relationship('Transaction', backref='user') #one to many relationship with Transaction table
    ratings = db.relationship('Rating', backref='user') #one to many relationship with Rating table
    book_complaints = db.relationship('Book_Complaints', backref='user') #one to many relationship with Rating table

class Book(UserMixin, db.Model):
    __tablename__ = "book"
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(1000))
    isbn = db.Column(db.String(1000))
    price = db.Column(db.Integer)
    pages = db.Column(db.Integer)
    condition = db.Column(db.String(1000))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    book_transactions = db.relationship('User', backref='book') 
    book_complaints = db.relationship('Book_Complaints', backref='book', cascade="all, delete-orphan")

class Transaction(UserMixin, db.Model):
    __tablename__ = "transaction"
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(1000))
    isbn = db.Column(db.String(1000))
    price = db.Column(db.Integer)
    pages = db.Column(db.Integer)
    condition = db.Column(db.String(1000))
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, nullable=False)
    amt_sold_for = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Rating(UserMixin, db.Model):
    __tablename__ = "rating"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    issues = db.Column(db.String(1000))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Book_Complaints(UserMixin, db.Model):
    __tablename__ = "book_complaints"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    comment = db.Column(db.String(1000))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Contact_Detail(UserMixin, db.Model):
    __tablename__ = "contact_detail"
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    name = db.Column(db.String(1000))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(1000))
    user_queries = db.Column(db.String(1000))
    

# login required decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap


db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

list_book = []

@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)

@app.route('/') #URL '/' to be handled by main() route handler
def index():
    return render_template('index.html')

@app.route('/user')
@login_required
def user():
    return render_template('user.html', name=current_user.name)

@app.route('/admin')
def admin():
    return render_template('admin.html', name=current_user.name)

#Admin's dashboard
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():  
    books_sell = (db.session.query(Transaction.title, Transaction.isbn, Transaction.price, Transaction.pages, Transaction.condition, Transaction.date_added, User.name).join(User, User.id==Transaction.seller_id)).order_by(Transaction.date_added).all()
    books_more = (db.session.query(Book.title, Book.isbn, Book.price, Book.pages, Book.condition, Book.date_added, User.name).join(User, User.id==Book.seller_id)).order_by(Book.date_added).all()

    books_bought = (db.session.query(Transaction.title, Transaction.isbn, Transaction.amt_sold_for, Transaction.order_date, User.name).join(User)).order_by(Transaction.date_added).all()

    ratings = (db.session.query(Rating.id, Rating.rating, Rating.issues, User.name).join(User)).order_by(Rating.timestamp).all()
    queries = Contact_Detail.query.all()
    complaints = (db.session.query(Book_Complaints.book_id, Book_Complaints.comment, User.name, User.email).join(User)).order_by(Book_Complaints.timestamp).all()
   
    return render_template('admin_dashboard.html', books_sold=books_sell, books_more=books_more,books_bought=books_bought, queries=queries, complaints = complaints, ratings=ratings, name=current_user.name)

#For displaying the dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    books_sold = Transaction.query.filter_by(seller_id=current_user.id).all()
    book_new = Book.query.filter_by(seller_id=current_user.id).order_by(Book.date_added).all()
    if book_new:
        for book in book_new:
            books_sold.append(book)
        
    books_bought = Transaction.query.filter_by(buyer_id=current_user.id).all()
    
    return render_template('dashboard.html', name=current_user.name,  books=books_sold, transactions=books_bought)

#For logging in users
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = True if request.form['remember'] else False

        user = User.query.filter_by(email=email).first()

        #If user is not registered
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))

        #If admin logs into the system
        if request.form['email'] == 'admin@admin' or request.form['password'] == 'admin':
            session['logged_in'] = True
            flash("You are logged in")
            login_user(user, remember=remember)
            return redirect(url_for('admin'))
            
        else:
            session['logged_in'] = True
            flash("You are logged in")
            login_user(user, remember=remember)
            return redirect(url_for('user'))

    return render_template('login.html', error=error)

#For signing up new users
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_email = request.form['email']
        user_name = request.form['name']
        user_password = request.form['password']

        user = User.query.filter_by(email=user_email).first() #Check if user exists

        if user:
            flash('Email address already exists')
            return redirect(url_for('signup'))
        
        #Store details of the new user into User table
        new_user = User(email=user_email, password=generate_password_hash(user_password, method='sha256'), name=user_name)

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return 'There was an issue adding your account'
        
    return render_template('signup.html')

#For contacting the admin
@app.route('/contact', methods=['POST', 'GET'])
def contact_us():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        subject = request.form['subject']

        #Store necessary details into Contact_Detail table
        new_query = Contact_Detail(name=name, email=email, phone=phone, user_queries=subject)

        try:
            db.session.add(new_query)
            db.session.commit()
            if current_user.is_authenticated:   #If user is logged in
                flash("Thank you for contacting us") 
                return redirect(url_for('user'))
            else:
                flash("Thank you for contacting us")
                return redirect(url_for('index'))
        except:
            return 'Thank you for using our website'

    return render_template('contact.html')

#When user wants to log out
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You are logged out")
    logout_user()
    return redirect(url_for('index'))

@app.route('/buy')
@login_required
def buy():
    books = Book.query.order_by(Book.date_added).all()
    return render_template('buy.html', books=books)

#For buying books
@app.route('/buying/<int:id>')
@login_required
def buying(id):
    book_to_buy = Book.query.get_or_404(id) # Retrieve a book by it ID
    new_transaction = Transaction(buyer_id=current_user.id, price=book_to_buy.price, book_id = book_to_buy.id, seller_id=book_to_buy.seller_id, title=book_to_buy.title, isbn=book_to_buy.isbn, pages=book_to_buy.pages, condition=book_to_buy.condition, date_added=book_to_buy.date_added, amt_sold_for=book_to_buy.price )

    try:
        db.session.add(new_transaction) #Store transaction information into Transaction table
        db.session.delete(book_to_buy)
        db.session.commit()
        flash("Your purchase was successful")
        return redirect(url_for('user'))
    except:
        return 'There was an issue buying your book'

#For selling books
@app.route('/sell', methods = ['POST', 'GET'])
@login_required
def sell():
    if request.method == 'POST':
        title = request.form['book']
        isbn = request.form['book_id']
        price = request.form['price']
        pages = request.form['pages']
        condition = request.form['condition']
        #store all book related information into Book table
        new_book = Book(seller_id=current_user.id, title=title, isbn=isbn, price=price, pages=pages, condition=condition)

        try:
            db.session.add(new_book) #Add the book to the Book table
            db.session.commit()
            flash("Your book has been added")
            return redirect(url_for('user'))
        except:
            return 'There was an issue adding your book'

    return render_template('sell.html')

#Store the ratings in Rating 
@app.route('/rating/<int:id>', methods = ['POST', 'GET'])
@login_required
def rating(id):
    book_to_rate = Book.query.get_or_404(id)
    if request.method == 'POST':
        rating = request.form['rating'] #retrieve the rating given by user 
        issues = request.form['queries'] #retrieve the issues written by user 

        book_rating = Rating(user_id=current_user.id, rating = rating, issues = issues )
        new_complaint = Book_Complaints(user_id = current_user.id, comment = issues, book_id = id)

        try:
            db.session.add(book_rating) #add to Rating table
            db.session.add(new_complaint)
            db.session.commit()
            db.session.commit()
            flash('Thank you for rating the book')
            return redirect(url_for('buy'))

        except:
            return 'Thank you'

    else:
        return render_template('rating.html', book = book_to_rate)

#Delete a rating
@app.route('/delete_rating/<int:id>')
@login_required
def delete_rating(id):
    rating_to_delete = Rating.query.get_or_404(id) #retreive the query to delete

    try:
        db.session.delete(rating_to_delete)
        db.session.commit()
        flash('Rating has been deleted') #Display a message to the user
        return redirect(url_for('admin_dashboard')) #Redirect to admin dashboard

    except:
        return 'There was a problem deleting the rating'

#Delete a query
@app.route('/delete_query/<int:id>') 
@login_required
def delete_query(id):
    query_to_delete = Contact_Detail.query.get_or_404(id) #retreive the query to delete

    try:
        db.session.delete(query_to_delete)
        db.session.commit()
        flash('Query has been solved') #Display a message to the user
        return redirect(url_for('admin_dashboard')) #Redirect to admin dashboard

    except:
        return 'There was a problem deleting the query'

if __name__ == "__main__":
    app.run(debug=True)