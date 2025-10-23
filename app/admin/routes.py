from flask import render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user

from app import db
from app.models import User, ApplicationPermission
from . import admin # Import the blueprint instance
from .decorators import admin_required # Import the custom decorator

@admin.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard homepage."""
    # Could add some stats here later (e.g., user count)
    user_count = User.query.count()
    return render_template('dashboard.html', title='Admin Dashboard', user_count=user_count)

@admin.route('/users')
@login_required
@admin_required
def manage_users():
    """Display list of users and allow toggling admin status."""
    users = User.query.order_by(User.username).all()
    return render_template('manage_users.html', title='Manage Users', users=users)

@admin.route('/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle the admin status of a user."""
    user_to_modify = User.query.get_or_404(user_id)
    
    # Prevent admin from removing their own admin status via this route
    if user_to_modify == current_user:
        flash('You cannot change your own admin status.', 'warning')
        return redirect(url_for('admin.manage_users'))
        
    try:
        user_to_modify.is_admin = not user_to_modify.is_admin
        db.session.commit()
        status = "granted" if user_to_modify.is_admin else "revoked"
        flash(f'Admin status {status} for user {user_to_modify.username}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error changing admin status.', 'danger')
        current_app.logger.error(f"Error toggling admin status for user {user_id}: {e}")
        
    return redirect(url_for('admin.manage_users'))

@admin.route('/user/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    """Mark a user account as approved."""
    user_to_approve = User.query.get_or_404(user_id)
    
    if user_to_approve.is_approved:
        flash(f'User {user_to_approve.username} is already approved.', 'info')
    else:
        try:
            user_to_approve.is_approved = True
            db.session.commit()
            flash(f'User {user_to_approve.username} approved successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error approving user.', 'danger')
            current_app.logger.error(f"Error approving user {user_id}: {e}")
            
    return redirect(url_for('admin.manage_users'))

@admin.route('/user/<int:user_id>/permissions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_permissions(user_id):
    """Manage application permissions for a user."""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        application = request.form.get('application')
        permission_level = request.form.get('permission_level')
        
        if not all([application, permission_level]):
            flash('Application and permission level are required.', 'danger')
            return redirect(url_for('admin.manage_permissions', user_id=user_id))
            
        if permission_level not in ['read', 'write', 'admin']:
            flash('Invalid permission level.', 'danger')
            return redirect(url_for('admin.manage_permissions', user_id=user_id))
            
        # Check if permission already exists
        permission = ApplicationPermission.query.filter_by(
            user_id=user_id,
            application=application
        ).first()
        
        if permission:
            permission.permission_level = permission_level
            permission.is_active = True
        else:
            permission = ApplicationPermission(
                user_id=user_id,
                application=application,
                permission_level=permission_level,
                granted_by=current_user.id
            )
            db.session.add(permission)
            
        try:
            db.session.commit()
            flash('Permission updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating permission.', 'danger')
            current_app.logger.error(f"Error updating permission: {e}")
            
    # Get current permissions
    permissions = user.application_permissions.all()
    
    # Define available applications
    applications = [
        'team_management',
        'recipe_app',
        # Add other applications here
    ]
    
    return render_template('admin/manage_permissions.html',
                         user=user,
                         permissions=permissions,
                         applications=applications)

@admin.route('/user/<int:user_id>/permission/<int:permission_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_permission(user_id, permission_id):
    """Revoke an application permission."""
    permission = ApplicationPermission.query.get_or_404(permission_id)
    
    if permission.user_id != user_id:
        abort(404)
        
    try:
        permission.is_active = False
        db.session.commit()
        flash('Permission revoked successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error revoking permission.', 'danger')
        current_app.logger.error(f"Error revoking permission: {e}")
        
    return redirect(url_for('admin.manage_permissions', user_id=user_id))

# Optional: Add route to delete users if needed, but be careful!
# @admin.route('/user/<int:user_id>/delete', methods=['POST'])
# @login_required
# @admin_required
# def delete_user(user_id):
#     user_to_delete = User.query.get_or_404(user_id)
#     if user_to_delete == current_user:
#         flash('You cannot delete yourself.', 'danger')
#         return redirect(url_for('admin.manage_users'))
#     try:
#         # Handle related data carefully (e.g., ingredients might be deleted by cascade)
#         flash(f'User {user_to_delete.username} deleted.', 'info')
#         db.session.delete(user_to_delete)
#         db.session.commit()
#     except Exception as e:
#         db.session.rollback()
#         flash('Error deleting user.', 'danger')
#         current_app.logger.error(f"Error deleting user {user_id}: {e}")
#     return redirect(url_for('admin.manage_users')) 