from flask import render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user

from app import db
from app.models import FavoriteSite
from . import favorites # Import the blueprint instance
from app.forms import FavoriteSiteForm
# from app.utils import sanitize_url # If more complex sanitization is needed

@favorites.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Display user's favorite sites and handle adding new ones."""
    form = FavoriteSiteForm()
    if form.validate_on_submit():
        try:
            # Basic sanitization happens in model validation
            # url = sanitize_url(form.url.data) # Use if more complex cleaning needed
            url = form.url.data
            if not url.startswith(('http://', 'https://')):
                 url = 'http://' + url # Ensure scheme is present
                 
            site = FavoriteSite(
                name=form.name.data,
                url=url, # Use sanitized URL
                owner=current_user
            )
            db.session.add(site)
            db.session.commit()
            flash('Favorite site added!', 'success')
            return redirect(url_for('favorites.index')) # Redirect to clear form
        except Exception as e:
            db.session.rollback()
            flash('Error adding favorite site.', 'danger')
            current_app.logger.error(f"Error adding favorite site: {e}")

    sites = current_user.favorite_sites.order_by(FavoriteSite.name).all()
    return render_template('favorites.html', title='Favorite Sites', form=form, sites=sites)

@favorites.route('/delete/<int:site_id>', methods=['POST'])
@login_required
def delete_site(site_id):
    """Delete a favorite site."""
    site = FavoriteSite.query.get_or_404(site_id)
    if site.owner != current_user:
        abort(403)
    try:
        db.session.delete(site)
        db.session.commit()
        flash('Favorite site deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting favorite site.', 'danger')
        current_app.logger.error(f"Error deleting favorite site {site_id}: {e}")
        
    return redirect(url_for('favorites.index')) 