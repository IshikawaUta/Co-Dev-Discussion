from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Message, User
from forms.forms import MessageForm
from datetime import datetime
from bson.objectid import ObjectId
from flask_socketio import join_room, leave_room, emit # Import emit, join_room, leave_room

# Fungsi ini akan mengembalikan instance Blueprint, menerima socketio sebagai argumen
def create_messages_blueprint(socketio_instance):
    messages_bp = Blueprint('messages', __name__)

    @messages_bp.route('/messages')
    @login_required
    def list_conversations():
        """Route to list all conversations for the current user."""
        conversations = Message.get_conversations(current_user._id)
        return render_template('messages.html', conversations=conversations)

    @messages_bp.route('/messages/<string:other_user_id>', methods=['GET', 'POST'])
    @login_required
    def conversation_detail(other_user_id):
        """Route to display a conversation with a specific user and allow sending messages."""
        try:
            other_user_obj_id = ObjectId(other_user_id)
            other_user = User.find_by_id(other_user_id)
            if not other_user:
                flash('User tidak ditemukan.', 'danger')
                return redirect(url_for('messages.list_conversations'))
        except Exception:
            flash('ID pengguna tidak valid.', 'danger')
            return redirect(url_for('messages.list_conversations'))

        messages = Message.get_messages_between_users(current_user._id, other_user_obj_id)
        
        # Tandai pesan yang diterima oleh current_user dari other_user sebagai sudah dibaca
        Message.mark_messages_as_read(other_user_obj_id, current_user._id)

        form = MessageForm()

        if form.validate_on_submit():
            content = form.content.data
            sender_id = current_user._id
            receiver_id = other_user_obj_id
            
            u_ids = sorted([str(sender_id), str(receiver_id)])
            conversation_id = f"{u_ids[0]}-{u_ids[1]}"

            new_message = Message(sender_id, receiver_id, content, conversation_id)
            saved_message = new_message.save() # Call save method

            if saved_message: # Check if save was successful
                message_data = {
                    'message_id': str(saved_message._id),
                    'sender_id': str(saved_message.sender_id),
                    'receiver_id': str(saved_message.receiver_id),
                    'content': saved_message.content,
                    'created_at': saved_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'sender_username': current_user.username
                }
                
                socketio_instance.emit('new_message', message_data, room=str(current_user._id))
                socketio_instance.emit('new_message', message_data, room=str(other_user_obj_id))

                flash('Pesan Anda telah dikirim!', 'success') # Add success flash message
                form.content.data = '' 
                return redirect(url_for('messages.conversation_detail', other_user_id=other_user_id))
            else:
                flash('Gagal mengirim pesan. Silakan coba lagi. Periksa log server untuk detailnya.', 'danger') # Add error flash message
                # If save failed, it's good to redirect to refresh the page and show the error.
                return redirect(url_for('messages.conversation_detail', other_user_id=other_user_id))
        
        return render_template('conversation.html', 
                               other_user=other_user, 
                               messages=messages, 
                               form=form)

    # SocketIO event handlers. Dekorator ini harus menggunakan socketio_instance.
    @socketio_instance.on('connect')
    def handle_connect():
        """Handles new client connections."""
        if current_user.is_authenticated:
            join_room(str(current_user._id))
            print(f"User {current_user.username} (ID: {current_user._id}) connected and joined room {current_user._id}")
        else:
            print("Anonymous user connected")

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handles client disconnections."""
        if current_user.is_authenticated:
            leave_room(str(current_user._id))
            print(f"User {current_user.username} (ID: {current_user._id}) disconnected and left room {current_user._id}")

    return messages_bp
