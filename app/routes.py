import secrets
import os
from PIL import Image
from flask import render_template, request, redirect, flash, request, url_for, abort
from app import app, db, bcrypt
from app.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, CommentForm
from app.models import User, Post, Comment
from flask_login import login_user, current_user, logout_user, login_required

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/posts', methods=['GET', 'POST'])
def posts():
    all_posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('posts.html', posts=all_posts)

@app.route('/posts/user/<int:user_id>', methods=['GET', 'POST'])
def user_posts(user_id):
    user = User.query.get_or_404(user_id).order_by(Post.date_posted.desc())
    user_posts = user.posts
    return render_template('posts.html', posts=user_posts)

@app.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('posts'))
    return render_template('create_post.html', title='Nowy Post', form=form, legend='Nowy Post')

@app.route('/posts/<int:post_id>/comment', methods=['GET', 'POST'])
@login_required
def add_comment(post_id, comment_id=-1):
    form = CommentForm()
    if form.validate_on_submit():
        comment= Comment(content=form.content.data, commentator=current_user, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been created!', 'success')
        return redirect(url_for('post', post_id=post_id))
    return render_template('add_comment.html', form=form, legend='Nowy Komentarz', post_id=post_id, comment_id=comment_id)

@app.route('/posts/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    all_comments = post.comments

    return render_template('post.html', title=post.title, post=post, comments=all_comments)

@app.route('/posts/<int:post_id>/delete')
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    comments = post.comments
    if post.author != current_user:
        abort(403)
    for comment in comments:
        db.session.delete(comment)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect('/posts')

@app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been edited!', 'success')
        return redirect(url_for('post', post_id=post_id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Edytuj Post', form=form, legend='Edytuj Post')

@app.route('/posts/<int:post_id>/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(post_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.commentator != current_user:
        abort(403)
    form = CommentForm()
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        flash('Your comment has been edited!', 'success')
        return redirect(url_for('post', post_id=post_id))
    elif request.method == 'GET':
        form.content.data = comment.content
    return render_template('add_comment.html', title='Edytuj Komentarz', form=form, legend='Edytuj Komentarz', comment_id=comment_id, post_id=post_id)

@app.route('/posts/<int:post_id>/<int:comment_id>/edit/delete')
@login_required
def delete_comment(comment_id, post_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.commentator != current_user:
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', 'success')
    return redirect(url_for('post',post_id=post_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! Ypu are now able to log in', 'success')
        return redirect('/login')
    return render_template('register.html', title='Zarejestruj się', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login Unsuccesful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex+f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route('/account',methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/'+current_user.image_file)
    return render_template('account.html', title='Twoje Konto', image_file=image_file, form=form)

@app.route(('/review'))
def review():
    return render_template('review.html')