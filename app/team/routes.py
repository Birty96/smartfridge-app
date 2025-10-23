from flask import render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from app import db
from app.models import Team, TeamMember, TeamEvent, EventRSVP, TeamDocument, TeamMessage, ApplicationPermission
from . import team
from app.utils import check_permission

# --- Team Management Routes ---

@team.route('/teams')
@login_required
@check_permission('team_management', 'read')
def list_teams():
    """List all teams the user has access to."""
    user_teams = TeamMember.query.filter_by(user_id=current_user.id, is_active=True).all()
    return render_template('team/list_teams.html', teams=user_teams)

@team.route('/team/new', methods=['GET', 'POST'])
@login_required
@check_permission('team_management', 'write')
def create_team():
    """Create a new team."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Team name is required.', 'danger')
            return redirect(url_for('team.create_team'))
            
        team = Team(name=name, description=description, created_by=current_user.id)
        db.session.add(team)
        
        # Add creator as team admin
        member = TeamMember(team=team, user_id=current_user.id, role='admin')
        db.session.add(member)
        
        try:
            db.session.commit()
            flash('Team created successfully!', 'success')
            return redirect(url_for('team.view_team', team_id=team.id))
        except Exception as e:
            db.session.rollback()
            flash('Error creating team.', 'danger')
            current_app.logger.error(f"Error creating team: {e}")
            
    return render_template('team/create_team.html')

@team.route('/team/<int:team_id>')
@login_required
@check_permission('team_management', 'read')
def view_team(team_id):
    """View team details."""
    team = Team.query.get_or_404(team_id)
    member = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    events = team.events.order_by(TeamEvent.start_time.desc()).limit(5).all()
    messages = team.messages.order_by(TeamMessage.created_at.desc()).limit(10).all()
    documents = team.documents.order_by(TeamDocument.uploaded_at.desc()).limit(5).all()
    
    return render_template('team/view_team.html', 
                         team=team, 
                         member=member,
                         events=events,
                         messages=messages,
                         documents=documents)

@team.route('/team/<int:team_id>/members')
@login_required
@check_permission('team_management', 'read')
def list_members(team_id):
    """List team members."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    members = team.members.all()
    return render_template('team/list_members.html', team=team, members=members)

@team.route('/team/<int:team_id>/member/add', methods=['POST'])
@login_required
@check_permission('team_management', 'write')
def add_member(team_id):
    """Add a new team member."""
    team = Team.query.get_or_404(team_id)
    member = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    if member.role != 'admin':
        abort(403)
        
    user_id = request.form.get('user_id')
    role = request.form.get('role')
    
    if not user_id or not role:
        flash('User ID and role are required.', 'danger')
        return redirect(url_for('team.list_members', team_id=team_id))
        
    if role not in ['admin', 'coach', 'player']:
        flash('Invalid role.', 'danger')
        return redirect(url_for('team.list_members', team_id=team_id))
        
    new_member = TeamMember(team_id=team_id, user_id=user_id, role=role)
    db.session.add(new_member)
    
    try:
        db.session.commit()
        flash('Member added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding member.', 'danger')
        current_app.logger.error(f"Error adding team member: {e}")
        
    return redirect(url_for('team.list_members', team_id=team_id))

# --- Event Management Routes ---

@team.route('/team/<int:team_id>/events')
@login_required
@check_permission('team_management', 'read')
def list_events(team_id):
    """List team events."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    events = team.events.order_by(TeamEvent.start_time).all()
    return render_template('team/list_events.html', team=team, events=events)

@team.route('/team/<int:team_id>/event/new', methods=['GET', 'POST'])
@login_required
@check_permission('team_management', 'write')
def create_event(team_id):
    """Create a new team event."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        event_type = request.form.get('event_type')
        start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        location = request.form.get('location')
        
        if not all([title, event_type, start_time, end_time]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('team.create_event', team_id=team_id))
            
        event = TeamEvent(
            team_id=team_id,
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            created_by=current_user.id
        )
        db.session.add(event)
        
        try:
            db.session.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('team.list_events', team_id=team_id))
        except Exception as e:
            db.session.rollback()
            flash('Error creating event.', 'danger')
            current_app.logger.error(f"Error creating event: {e}")
            
    return render_template('team/create_event.html', team=team)

@team.route('/event/<int:event_id>/rsvp', methods=['POST'])
@login_required
@check_permission('team_management', 'write')
def rsvp_event(event_id):
    """RSVP to a team event."""
    event = TeamEvent.query.get_or_404(event_id)
    TeamMember.query.filter_by(team_id=event.team_id, user_id=current_user.id).first_or_404()
    
    status = request.form.get('status')
    notes = request.form.get('notes')
    
    if not status or status not in ['attending', 'not_attending', 'maybe']:
        flash('Invalid RSVP status.', 'danger')
        return redirect(url_for('team.list_events', team_id=event.team_id))
        
    rsvp = EventRSVP.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    
    if rsvp:
        rsvp.status = status
        rsvp.notes = notes
        rsvp.responded_at = datetime.utcnow()
    else:
        rsvp = EventRSVP(
            event_id=event_id,
            user_id=current_user.id,
            status=status,
            notes=notes
        )
        db.session.add(rsvp)
        
    try:
        db.session.commit()
        flash('RSVP updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating RSVP.', 'danger')
        current_app.logger.error(f"Error updating RSVP: {e}")
        
    return redirect(url_for('team.list_events', team_id=event.team_id))

# --- Document Management Routes ---

@team.route('/team/<int:team_id>/documents')
@login_required
@check_permission('team_management', 'read')
def list_documents(team_id):
    """List team documents."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    documents = team.documents.order_by(TeamDocument.uploaded_at.desc()).all()
    return render_template('team/list_documents.html', team=team, documents=documents)

@team.route('/team/<int:team_id>/document/upload', methods=['POST'])
@login_required
@check_permission('team_management', 'write')
def upload_document(team_id):
    """Upload a team document."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    if 'document' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('team.list_documents', team_id=team_id))
        
    file = request.files['document']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('team.list_documents', team_id=team_id))
        
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'team_documents', str(team_id))
        os.makedirs(file_path, exist_ok=True)
        
        file_path = os.path.join(file_path, filename)
        file.save(file_path)
        
        document = TeamDocument(
            team_id=team_id,
            title=request.form.get('title', filename),
            description=request.form.get('description'),
            file_path=file_path,
            file_type=file.content_type,
            uploaded_by=current_user.id
        )
        db.session.add(document)
        
        try:
            db.session.commit()
            flash('Document uploaded successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error uploading document.', 'danger')
            current_app.logger.error(f"Error uploading document: {e}")
            
    return redirect(url_for('team.list_documents', team_id=team_id))

# --- Message Management Routes ---

@team.route('/team/<int:team_id>/messages')
@login_required
@check_permission('team_management', 'read')
def list_messages(team_id):
    """List team messages."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    messages = team.messages.order_by(TeamMessage.created_at.desc()).all()
    return render_template('team/list_messages.html', team=team, messages=messages)

@team.route('/team/<int:team_id>/message/new', methods=['POST'])
@login_required
@check_permission('team_management', 'write')
def create_message(team_id):
    """Create a new team message."""
    team = Team.query.get_or_404(team_id)
    TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first_or_404()
    
    content = request.form.get('content')
    is_announcement = request.form.get('is_announcement') == 'true'
    
    if not content:
        flash('Message content is required.', 'danger')
        return redirect(url_for('team.list_messages', team_id=team_id))
        
    message = TeamMessage(
        team_id=team_id,
        user_id=current_user.id,
        content=content,
        is_announcement=is_announcement
    )
    db.session.add(message)
    
    try:
        db.session.commit()
        flash('Message posted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error posting message.', 'danger')
        current_app.logger.error(f"Error posting message: {e}")
        
    return redirect(url_for('team.list_messages', team_id=team_id)) 