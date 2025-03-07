import os
import time  # Import the time module
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import event, and_, or_, func

app = Flask(__name__)
app.secret_key = '502c168d124a023746c182b987b22f42'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader callback
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_photo = db.Column(db.String(500), nullable=True)  # New field for profile photo
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)  # Add this line
    is_online = db.Column(db.Boolean, default=False)  # Add this line
    
    # Add cascade relationships
    sent_messages = db.relationship('Message', 
                                  foreign_keys='Message.sender',
                                  backref='sender_user',
                                  cascade='all, delete-orphan',
                                  primaryjoin='User.username == Message.sender')
                                  
    received_messages = db.relationship('Message',
                                      foreign_keys='Message.recipient',
                                      backref='recipient_user',
                                      cascade='all, delete-orphan',
                                      primaryjoin='User.username == Message.recipient')
                                      
    group_messages = db.relationship('GroupMessage',
                                   backref=db.backref('sender', lazy='joined'),  # Changed from 'user' to 'sender'
                                   cascade='all, delete-orphan')

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    recipient = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    file_url = db.Column(db.String(200))
    file_name = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    reply_to = db.relationship('Message', remote_side=[id], backref='replies')
    is_read = db.Column(db.Boolean, default=False)  # Add this line

    def __repr__(self):
        return f'<Message {self.sender} to {self.recipient}: {self.content}>'

from datetime import datetime

group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(200))  # This column is missing in the database
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships remain the same
    creator = db.relationship('User', foreign_keys=[creator_id])
    members = db.relationship('User', secondary=group_members, 
                            backref=db.backref('groups', lazy='dynamic'))
    messages = db.relationship('GroupMessage', backref='group', lazy='dynamic')

class GroupMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_groupmessage_user'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id', name='fk_groupmessage_group'), nullable=False)
    file_url = db.Column(db.String(200))
    file_name = db.Column(db.String(100))
    reply_to = db.Column(db.Integer, db.ForeignKey('group_message.id', name='fk_groupmessage_reply'), nullable=True)
    
    replied_message = db.relationship('GroupMessage', remote_side=[id], backref='replies')

@app.route('/')
@login_required
def index():
    users = User.query.all()
    # Get groups where user is either creator or member
    groups = Group.query.filter(
        (Group.creator_id == current_user.id) | 
        (Group.members.any(id=current_user.id))
    ).all()
    
    return render_template('index.html', 
                         users=users, 
                         groups=groups,
                         session=session)

@app.route("/chat/<recipient>", methods=['GET', 'POST'])
@login_required
def chat(recipient):
    if request.method == 'POST':
        message_content = request.form.get('message')
        file = request.files.get('file')
        file_url = None
        file_name = None
        reply_to_id = request.form.get('reply_to')
        reply_to_message = None

        print(f"Request data: message_content={message_content}, file={file}, reply_to_id={reply_to_id}")

        if reply_to_id:
            reply_to_message = Message.query.get(reply_to_id)
            print(f"Replying to message: {reply_to_message}")

        if file and file.filename != '':
            if file.mimetype.startswith('image/') or file.mimetype.startswith('audio/') or file.mimetype.startswith('video/') or file.mimetype.startswith('application/'):
                if file.content_length <= 20 * 1024 * 1024:  # Check file size is under 20 MB
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    file_url = url_for('static', filename=f'uploads/{filename}')
                    file_name = file.filename
                    print(f"File saved: url={file_url}, name={file_name}")

        new_message = Message(
            sender=session['username'],
            recipient=recipient,
            content=message_content if message_content else '',
            image_url=file_url if file and file.mimetype.startswith('image/') else None,
            file_url=file_url if file and not file.mimetype.startswith('image/') else None,
            file_name=file_name,
            reply_to=reply_to_message
        )

        print(f"New message created: {new_message}")

        db.session.add(new_message)
        db.session.commit()

        print("Database commit successful")

        return jsonify({
            'success': True,
            'message': {
                'id': new_message.id,
                'sender': new_message.sender,
                'content': new_message.content,
                'image_url': new_message.image_url,
                'file_url': new_message.file_url,
                'file_name': new_message.file_name,
                'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'reply_to': {
                    'id': reply_to_message.id,
                    'content': reply_to_message.content
                } if reply_to_message else None
            }
        })
    else:  # GET request
        # Get search query parameter
        search_query = request.args.get('search', '').lower()
        
        if search_query:
            # Get all users except current user
            all_users = User.query.filter(User.username != current_user.username).all()
            
            # Split users into exact matches, partial matches, and others
            exact_matches = []
            partial_matches = []
            other_users = []
            
            for user in all_users:
                username_lower = user.username.lower()
                if username_lower == search_query:
                    exact_matches.append(user)
                elif search_query in username_lower:
                    partial_matches.append(user)
                else:
                    other_users.append(user)
            
            # Combine lists in priority order: exact matches first, then partial matches, then others
            users = exact_matches + partial_matches + other_users
        else:
            # If no search query, get all users except current user
            users = User.query.filter(User.username != current_user.username).all()
        
        # Get messages between current user and recipient
        messages = Message.query.filter(
            or_(
                and_(Message.sender == current_user.username, Message.recipient == recipient),
                and_(Message.sender == recipient, Message.recipient == current_user.username)
            )
        ).order_by(Message.timestamp).all()
        
        recipient_user = User.query.filter_by(username=recipient).first_or_404()
        
        # Get unread count for each user
        for user in users:
            user.unread_count = Message.query.filter_by(
                sender=user.username,
                recipient=current_user.username,
                is_read=False
            ).count()
        
        return render_template('chat.html', 
                             recipient=recipient,
                             recipient_user=recipient_user,
                             messages=messages, 
                             users=users,
                             search_query=search_query)

@app.route('/messages/<recipient>', methods=['GET'])
def get_messages(recipient):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Mark messages as read when the recipient views them
    unread_messages = Message.query.filter(
        Message.sender == recipient,
        Message.recipient == session['username'],
        Message.is_read == False
    ).all()
    
    for message in unread_messages:
        message.is_read = True
    
    db.session.commit()

    # Get all messages ordered by unread first, then timestamp
    messages = Message.query.filter(
        ((Message.sender == session['username']) & (Message.recipient == recipient)) |
        ((Message.sender == recipient) & (Message.recipient == session['username']))
    ).order_by(
        Message.is_read.asc(),  # Unread messages first
        Message.timestamp.desc()  # Then by timestamp descending
    ).all()

    return jsonify([{
        'id': message.id,
        'sender': message.sender,
        'content': message.content,
        'image_url': message.image_url,
        'file_url': message.file_url,
        'file_name': message.file_name,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': message.is_read,
        'reply_to': {
            'id': message.reply_to.id,
            'content': message.reply_to.content
        } if message.reply_to else None
    } for message in messages])

@app.route('/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    message = Message.query.get(message_id)
    user = User.query.filter_by(username=session['username']).first()
    if message and (message.sender == session['username'] or user.is_admin):
        db.session.delete(message)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_messages', methods=['POST'])
def delete_messages():
    if 'username' not in session:
        return jsonify({'success': False}), 403
    data = request.get_json()
    message_ids = data.get('message_ids', [])
    for message_id in message_ids:
        message = Message.query.get(message_id)
        if message and (message.sender == session['username'] or session['username'] == 'OMKARKUMBHAR'):
            db.session.delete(message)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/ban_user/<int:user_id>', methods=['POST'])
def ban_user(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    if user.is_admin:
        user_to_ban = User.query.get(user_id)
        if user_to_ban:
            db.session.delete(user_to_ban)
            db.session.commit()
    return jsonify({'success': True})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        profile_photo = request.files.get('profile_photo')
        profile_photo_url = None
        if profile_photo:
            filename = secure_filename(profile_photo.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            profile_photo_url = url_for('static', filename=f'uploads/{unique_filename}')
        if User.query.filter_by(username=username).first():
            return 'Username already exists!'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, profile_photo=profile_photo_url)
        if username == 'OMKARKUMBHAR':
            new_user.is_admin = True
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('signup.html')

# Update the login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)  # Use Flask-Login's login_user function
            session['username'] = username  # Keep this for compatibility with existing code
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

# Update the logout route
@app.route('/logout')
@login_required
def logout():
    current_user.is_online = False
    db.session.commit()
    logout_user()
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/manage_user', methods=['POST'])
def manage_user():
    if 'username' not in session:
        return redirect(url_for('login'))
    data = request.form
    new_username = data.get('username')
    new_password = data.get('password')
    profile_photo = request.files.get('profile_photo')
    profile_photo_url = None
    if profile_photo:
        filename = secure_filename(profile_photo.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        profile_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        profile_photo_url = url_for('static', filename=f'uploads/{unique_filename}')
    user = User.query.filter_by(username=session['username']).first()
    if user:
        user.username = new_username
        user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        if profile_photo_url:
            user.profile_photo = profile_photo_url
        db.session.commit()
        session['username'] = new_username
        return redirect(url_for('chat', recipient=new_username))
    return jsonify({'success': False})

@app.route('/user_selector')
def user_selector():
    if 'username' not in session:
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('user_selector.html', users=users)

@app.route('/notify_close', methods=['POST'])
def notify_close():
    if 'username' in session:
        username = session['username']
        # Handle the notification logic here, e.g., update user status in the database
        print(f"User {username} has closed the browser.")
        return jsonify({'success': True})
    return jsonify({'success': False}), 403

# Create group
@app.route("/group/create", methods=["POST"])
@login_required
def create_group():
    group_name = request.form.get("group_name")
    if not group_name:
        flash("Group name is required", "error")
        return redirect(url_for("manage_groups"))
    
    new_group = Group(
        name=group_name,
        creator_id=current_user.id
    )
    new_group.members.append(current_user)
    db.session.add(new_group)
    db.session.commit()
    
    flash("Group created successfully!", "success")
    return redirect(url_for("manage_groups"))

# Manage groups page
@app.route("/groups")
@login_required
def manage_groups():
    my_groups = Group.query.filter_by(creator_id=current_user.id).all()
    member_groups = Group.query.filter(
        Group.members.any(id=current_user.id),
        Group.creator_id != current_user.id
    ).all()
    return render_template("manage_groups.html", my_groups=my_groups, member_groups=member_groups)

# Group chat page
@app.route("/group/<int:group_id>/chat")
@login_required
def group_chat(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user not in group.members:
        flash("You don't have access to this group", "error")
        return redirect(url_for("manage_groups"))
    
    messages = GroupMessage.query.filter_by(group_id=group_id).order_by(GroupMessage.timestamp).all()
    return render_template("group_chat.html", group=group, messages=messages)

# Add member to group
@app.route("/group/<int:group_id>/add_member", methods=["POST"])
@login_required
def add_member(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user.id != group.creator_id:
        flash("Only group creator can add members", "error")
        return redirect(url_for("group_chat", group_id=group_id))
    
    username = request.form.get("username")
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash(f"User {username} not found", "error")
    elif user in group.members:
        flash(f"User {username} is already in the group", "warning")
    else:
        group.members.append(user)
        db.session.commit()
        flash(f"User {username} added to the group", "success")
    
    return redirect(url_for("group_chat", group_id=group_id))

# Remove member from group
@app.route("/group/<int:group_id>/remove_member/<int:member_id>", methods=["POST"])
@login_required
def remove_member(group_id, member_id):
    group = Group.query.get_or_404(group_id)
    if current_user.id != group.creator_id:
        flash("Only group creator can remove members", "error")
        return redirect(url_for("group_chat", group_id=group_id))
    
    member = User.query.get_or_404(member_id)
    if member.id == group.creator_id:
        flash("Cannot remove group creator", "error")
    else:
        group.members.remove(member)
        db.session.commit()
        flash(f"User {member.username} removed from the group", "success")
    
    return redirect(url_for("group_chat", group_id=group_id))

# Send message in group chat
@app.route('/send_group_message/<int:group_id>', methods=['POST'])
@login_required
def send_group_message(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user not in group.members:
        flash("You don't have access to this group", "error")
        return redirect(url_for('manage_groups'))

    try:
        message_content = request.form.get('message', '').strip()
        reply_to = request.form.get('reply_to')
        file = request.files.get('file')

        # Handle file upload if present
        file_url = None
        file_name = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            file_url = url_for('static', filename=f'uploads/{filename}')
            file_name = filename

        # Create message
        message = GroupMessage(
            content=message_content,
            user_id=current_user.id,
            group_id=group_id,
            file_url=file_url,
            file_name=file_name,
            reply_to=int(reply_to) if reply_to and reply_to.isdigit() else None,
            timestamp=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()

        flash("Message sent successfully!", "success")
        return redirect(url_for('group_chat', group_id=group_id))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('group_chat', group_id=group_id))

@app.route('/delete_group/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Check if the current user is the group creator
    if group.creator_id != current_user.id:
        flash('You do not have permission to delete this group.', 'error')
        return redirect(url_for('manage_groups'))
    
    try:
        # Delete group photo if it exists
        if group.photo_url:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], group.photo_url)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        
        # Delete all messages in the group
        GroupMessage.query.filter_by(group_id=group_id).delete()
        
        # Remove all members from the group
        group.members.clear()
        
        # Delete the group
        db.session.delete(group)
        db.session.commit()
        
        flash('Group deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the group.', 'error')
        
    return redirect(url_for('manage_groups'))

@app.route('/leave_group/<int:group_id>', methods=['POST'])
@login_required
def leave_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    # Check if user is in the group
    if current_user not in group.members:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('manage_groups'))
    
    # Prevent group creator from leaving
    if group.creator_id == current_user.id:
        flash('Group creator cannot leave the group. Delete the group instead.', 'error')
        return redirect(url_for('manage_groups'))
    
    try:
        # Remove user from group members
        group.members.remove(current_user)
        db.session.commit()
        flash('Successfully left the group.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while leaving the group.', 'error')
    
    return redirect(url_for('manage_groups'))

@app.route('/group/<int:group_id>/get_messages')
@login_required
def get_group_messages(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user not in group.members:
        return jsonify({'error': 'You are not a member of this group'}), 403

    last_message_id = request.args.get('last_message_id', default=0, type=int)

    # Query for new messages
    messages = GroupMessage.query.filter(GroupMessage.group_id == group_id, GroupMessage.id > last_message_id).order_by(GroupMessage.timestamp).all()

    # If there are no new messages, hold the connection open (long polling)
    if not messages:
        # Wait for a maximum of 20 seconds for new messages
        for i in range(20):
            db.session.commit()  # Release the database connection
            time.sleep(1)  # Wait for 1 second

            messages = GroupMessage.query.filter(GroupMessage.group_id == group_id, GroupMessage.id > last_message_id).order_by(GroupMessage.timestamp).all()

            if messages:
                break  # Exit the loop if new messages are found
        else:
            return jsonify([])  # Return an empty list if no messages are found after waiting

    # Serialize messages
    messages_list = []
    for message in messages:
        message_data = {
            'id': message.id,
            'content': message.content,
            'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': message.user_id,
            'group_id': message.group_id,
            'file_url': message.file_url,
            'file_name': message.file_name,
            'reply_to': message.reply_to,
            'user': {
                'id': message.user.id,
                'username': message.user.username
            }
        }
        messages_list.append(message_data)

    response = jsonify(messages_list)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/api/search_users")
@login_required
def search_users():
    search_query = request.args.get('q', '').lower()
    
    if search_query:
        users = User.query.filter(
            and_(
                User.username != current_user.username,
                User.username.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        users = User.query.filter(User.username != current_user.username).all()
    
    return jsonify([{
        'username': user.username,
        'profile_photo': user.profile_photo or 'default_avatar.png'
    } for user in users])

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session['username'] != 'OMKARKUMBHAR':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/ban_user', methods=['POST'])
@admin_required
def admin_ban_user():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'success': False, 'message': 'Username required'}), 400
        
    try:
        # Get the user to ban
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Delete all messages sent by the user
        Message.query.filter_by(sender=username).delete()
        
        # Delete all messages received by the user
        Message.query.filter_by(recipient=username).delete()
        
        # Remove user from all groups they're a member of
        for group in user.groups:
            if group.creator_id == user.id:
                # If user is group creator, delete the entire group
                GroupMessage.query.filter_by(group_id=group.id).delete()
                group.members.clear()
                db.session.delete(group)
            else:
                # If user is just a member, remove them from group
                group.members.remove(user)
                
        # Delete all group messages sent by the user
        GroupMessage.query.filter_by(user_id=user.id).delete()
        
        # Finally, delete the user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'User {username} has been banned and all their data has been removed'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error banning user: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/block_user', methods=['POST'])
@admin_required
def admin_block_user():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'success': False, 'message': 'Username required'}), 400
        
    try:
        # Add your database logic here to block the user
        # For example:
        # user = User.query.filter_by(username=username).first()
        # user.is_blocked = True
        # db.session.commit()
        
        return jsonify({'success': True, 'message': f'User {username} has been blocked'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/update_online_status', methods=['POST'])
@login_required
def update_online_status():
    current_user.last_seen = datetime.utcnow()
    current_user.is_online = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/get_user_status/<username>')
@login_required
def get_user_status(username):
    user = User.query.filter_by(username=username).first_or_404()
    now = datetime.utcnow()
    is_online = user.is_online and (now - user.last_seen).total_seconds() < 300  # 5 minutes threshold
    
    return jsonify({
        'is_online': is_online,
        'last_seen': user.last_seen.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/mark_message_read', methods=['POST'])
@login_required
def mark_message_read():
    data = request.get_json()
    message_id = data.get('message_id')
    
    message = Message.query.get_or_404(message_id)
    if message.recipient == current_user.username and not message.is_read:
        message.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message_id
        })
    
    return jsonify({'success': False}), 400

if __name__ == '__main__':
    with app.app_context():  # WARNING: This will delete all data
        db.create_all()
    app.run(debug=True)