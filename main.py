from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
import requests
import json
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
Bootstrap5(app)

# create the extension
db = SQLAlchemy()
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
# initialize the app with the extension
db.init_app(app)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    year = db.Column(db.SmallInteger(), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    ranking = db.Column(db.SmallInteger, nullable=True)
    review = db.Column(db.String(200), nullable=True)
    img_url = db.Column(db.String(250), nullable=False)


class EditMovieForm(FlaskForm):
    rating = FloatField('Your rating out of 10', validators=[DataRequired()])
    review = StringField('Your review')
    submit = SubmitField('Done')


class AddMovieForm(FlaskForm):
    title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


def get_movie_details(movie_id: int):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TOKEN')}"
    }

    response = requests.get(url, headers=headers).text
    return json.loads(response)


def get_movies(movie_title: str):
    url = f"https://api.themoviedb.org/3/search/movie?query={movie_title}&include_adult=false&language=en-US&page=1"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TOKEN')}"
    }

    response = requests.get(url, headers=headers).text

    return json.loads(response)["results"]


def update_rankings():
    all_movies = db.session.execute(
        db.select(Movie).order_by(-Movie.rating)).scalars()
    for index, movie in enumerate(all_movies, start=1):
        movie.ranking = index


@app.route("/")
def home():
    with app.app_context():
        all_movies = list(db.session.execute(
            db.select(Movie).order_by(Movie.ranking)).scalars())
    return render_template("index.html", movies=all_movies)


@app.route('/edit', methods=["POST", "GET"])
def edit_movie():
    form = EditMovieForm()
    if form.validate_on_submit():
        with app.app_context():
            movie_to_update = db.get_or_404(
                Movie, request.args.get('movie_id'))
            movie_to_update.rating = request.form.get('rating')
            movie_to_update.review = request.form.get('review', '')
            update_rankings()
            db.session.commit()
            return redirect(url_for('home'))
    return render_template('edit.html', edit_form=form)


@app.route('/select', methods=["POST", "GET"])
def select_movie():
    form = AddMovieForm()
    if form.validate_on_submit():
        movies = get_movies(request.form.get('title'))
        return render_template('select.html', all_movies=movies)
    return render_template('add.html', add_form=form)


@app.route('/add', methods=["POST", "GET"])
def add_movie():
    movie = get_movie_details(request.args.get('movie_api_id'))
    with app.app_context():
        new_movie = Movie(
            title=movie["original_title"],
            year=movie["release_date"].split("-")[0],
            description=movie["overview"],
            img_url=f'https://image.tmdb.org/t/p/w500{movie["poster_path"]}'
        )
        db.session.add(new_movie)
        update_rankings()
        db.session.commit()
        return redirect(url_for('edit_movie', movie_id=new_movie.id))


@app.route('/book', methods=['POST', 'GET'])
def delete_book():
    with app.app_context():
        book_to_delete = db.get_or_404(Movie, request.args.get('movie_id'))
        db.session.delete(book_to_delete)
        update_rankings()
        db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
