from flask import Blueprint, render_template, current_app


main_bp = Blueprint('main', __name__)


@main_bp.get('/')
def index():
    return render_template('index.html', mapbox_token=current_app.config['MAPBOX_TOKEN'])


@main_bp.get('/dashboard')
def dashboard():
    return render_template('dashboard.html', mapbox_token=current_app.config['MAPBOX_TOKEN'])
