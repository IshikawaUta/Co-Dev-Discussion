import datetime
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import get_db

class User(UserMixin):
    """
    Model for users who will log in.
    Implements UserMixin for integration with Flask-Login.
    """
    def __init__(self, username, email, password_hash, role='user', _id=None):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # Default role is 'user', can be 'admin'
        self._id = _id if _id else ObjectId()

    def get_id(self):
        """Returns the user's unique ID as a string, required by Flask-Login."""
        return str(self._id)

    def is_admin(self):
        """Checks if the user has the 'admin' role."""
        return self.role == 'admin'

    @staticmethod
    def find_by_username(username):
        """Finds a user by username."""
        user_data = get_db().users.find_one({"username": username})
        if user_data:
            return User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=user_data["password_hash"],
                role=user_data.get("role", 'user'),  # Get role, default 'user'
                _id=user_data["_id"]
            )
        return None

    @staticmethod
    def find_by_email(email):
        """Finds a user by email."""
        user_data = get_db().users.find_one({"email": email})
        if user_data:
            return User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=user_data["password_hash"],
                role=user_data.get("role", 'user'),
                _id=user_data["_id"]
            )
        return None

    @staticmethod
    def find_by_id(user_id):
        """Finds a user by ObjectId."""
        try:
            # Ensure user_id can be converted to ObjectId
            user_data = get_db().users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    role=user_data.get("role", 'user'),  # Get role, default 'user'
                    _id=user_data["_id"]
                )
        except Exception as e:
            print(f"Error finding user by ID {user_id}: {e}")
            return None
        return None

    def save(self):
        """Saves a new user to the database. password_hash is assumed to be hashed."""
        get_db().users.insert_one({
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "created_at": datetime.datetime.utcnow() # Add user creation timestamp
        })

    def check_password(self, password):
        """Checks the entered password against the stored hash."""
        return check_password_hash(self.password_hash, password)


class Topic:
    """Model for discussion topics."""
    def __init__(self, title, content, author_id, author_username, created_at=None, updated_at=None, _id=None):
        self.title = title
        self.content = content
        self.author_id = ObjectId(author_id) # Store author_id as ObjectId
        self.author_username = author_username
        self.created_at = created_at if created_at else datetime.datetime.utcnow()
        self.updated_at = updated_at if updated_at else datetime.datetime.utcnow()
        self._id = _id if _id else ObjectId()

    def save(self):
        """Saves a new topic or updates an existing one."""
        if self._id and get_db().topics.count_documents({"_id": self._id}) > 0:
            # Update existing topic
            get_db().topics.update_one(
                {"_id": self._id},
                {"$set": {
                    "title": self.title,
                    "content": self.content,
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
        else:
            # Insert new topic
            result = get_db().topics.insert_one({
                "title": self.title,
                "content": self.content,
                "author_id": self.author_id,
                "author_username": self.author_username,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            })
            self._id = result.inserted_id
        return self._id

    def update(self):
        """Updates an existing topic (alias method for save with update)."""
        self.save()

    def delete(self):
        """Deletes a topic and all associated posts."""
        get_db().topics.delete_one({"_id": self._id})
        # Important: Ensure topic_id in the posts collection is also stored as ObjectId
        get_db().posts.delete_many({"topic_id": self._id})

    @staticmethod
    def get_paginated_topics(page, per_page):
        """Retrieves topics with pagination."""
        skip = (page - 1) * per_page
        topics_data = list(get_db().topics.find().sort("created_at", -1).skip(skip).limit(per_page))
        total_topics = get_db().topics.count_documents({})
        
        # Convert raw data from DB to Topic objects
        topics = [Topic(
            title=t["title"],
            content=t["content"],
            author_id=t["author_id"],
            author_username=t["author_username"],
            created_at=t["created_at"],
            updated_at=t.get("updated_at", t["created_at"]), # Get updated_at if available
            _id=t["_id"]
        ) for t in topics_data]
        
        return topics, total_topics

    @staticmethod
    def find_by_id(topic_id):
        """Finds a topic by ObjectId."""
        try:
            topic_data = get_db().topics.find_one({"_id": ObjectId(topic_id)})
            if topic_data:
                return Topic(
                    title=topic_data["title"],
                    content=topic_data["content"],
                    author_id=topic_data["author_id"],
                    author_username=topic_data["author_username"],
                    created_at=topic_data["created_at"],
                    updated_at=topic_data.get("updated_at", topic_data["created_at"]),
                    _id=topic_data["_id"]
                )
        except Exception as e:
            print(f"Error finding topic by ID {topic_id}: {e}")
            return None
        return None
    
    @staticmethod
    def search_topics(query_text, page, per_page):
        """Searches for topics by text using Atlas Search with pagination."""
        skip = (page - 1) * per_page

        # Aggregation pipeline for Atlas Search
        # 'topic_text_index' is the name of the Atlas Search index you created in Atlas
        pipeline = [
            {
                '$search': {
                    'index': 'topic_text_index', 
                    'text': {
                        'query': query_text,
                        'path': ['title', 'content'] # Search in title and content fields
                    }
                }
            },
            {'$sort': {'created_at': -1}}, # Sort by newest date
            {
                '$facet': {
                    'totalData': [{'$skip': skip}, {'$limit': per_page}],
                    'totalCount': [{'$count': 'count'}]
                }
            }
        ]

        # Execute pipeline
        result = list(get_db().topics.aggregate(pipeline))

        # Extract results
        # Handle cases where there are no results or empty documents from $facet
        topics_data = result[0]['totalData'] if result and 'totalData' in result[0] else []
        total_results = result[0]['totalCount'][0]['count'] if result and 'totalCount' in result[0] and result[0]['totalCount'] else 0

        # Convert raw data from DB to Topic objects
        topics = [Topic(
            title=t["title"],
            content=t["content"],
            author_id=t["author_id"],
            author_username=t["author_username"],
            created_at=t["created_at"],
            updated_at=t.get("updated_at", t["created_at"]),
            _id=t["_id"]
        ) for t in topics_data]

        return topics, total_results


class Post:
    """Model for posts (replies) within a topic."""
    def __init__(self, topic_id, content, author_id, author_username, created_at=None, updated_at=None, _id=None):
        self.topic_id = ObjectId(topic_id) # Store topic_id as ObjectId
        self.content = content
        self.author_id = ObjectId(author_id) # Store author_id as ObjectId
        self.author_username = author_username
        self.created_at = created_at if created_at else datetime.datetime.utcnow()
        self.updated_at = updated_at if updated_at else datetime.datetime.utcnow()
        self._id = _id if _id else ObjectId()

    def save(self):
        """Saves a new post or updates an existing one."""
        if self._id and get_db().posts.count_documents({"_id": self._id}) > 0:
            # Update existing post
            get_db().posts.update_one(
                {"_id": self._id},
                {"$set": {
                    "content": self.content,
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
        else:
            # Insert new post
            result = get_db().posts.insert_one({
                "topic_id": self.topic_id,
                "content": self.content,
                "author_id": self.author_id,
                "author_username": self.author_username,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            })
            self._id = result.inserted_id
        return self._id

    def update(self):
        """Updates an existing post (alias method for save with update)."""
        self.save()

    def delete(self):
        """Deletes a post."""
        get_db().posts.delete_one({"_id": self._id})

    @staticmethod
    def find_by_id(post_id):
        """Finds a post by ObjectId."""
        try:
            post_data = get_db().posts.find_one({"_id": ObjectId(post_id)})
            if post_data:
                return Post(
                    topic_id=post_data["topic_id"],
                    content=post_data["content"],
                    author_id=post_data["author_id"],
                    author_username=post_data["author_username"],
                    created_at=post_data["created_at"],
                    updated_at=post_data.get("updated_at", post_data["created_at"]),
                    _id=post_data["_id"]
                )
        except Exception as e:
            print(f"Error finding post by ID {post_id}: {e}")
            return None
        return None

    @staticmethod
    def get_posts_for_topic(topic_id, page, per_page):
        """Retrieves posts by topic with pagination."""
        skip = (page - 1) * per_page
        # Ensure query uses ObjectId for topic_id
        posts_data = list(get_db().posts.find({"topic_id": ObjectId(topic_id)}).sort("created_at", 1).skip(skip).limit(per_page))
        total_posts = get_db().posts.count_documents({"topic_id": ObjectId(topic_id)})
        
        # Convert raw data from DB to Post objects
        posts = [Post(
            topic_id=p["topic_id"],
            content=p["content"],
            author_id=p["author_id"],
            author_username=p["author_username"],
            created_at=p["created_at"],
            updated_at=p.get("updated_at", p["created_at"]),
            _id=p["_id"]
        ) for p in posts_data]

        return posts, total_posts


class Message:
    """Model for private messages."""
    def __init__(self, sender_id, receiver_id, content, conversation_id, created_at=None, read=False, _id=None):
        # Pastikan sender_id dan receiver_id selalu menjadi ObjectId
        self.sender_id = ObjectId(sender_id) 
        self.receiver_id = ObjectId(receiver_id) 
        self.content = content
        self.conversation_id = conversation_id 
        self.created_at = created_at if created_at is not None else datetime.datetime.utcnow()
        self.read = read
        self._id = _id if _id else ObjectId()

    def save(self):
        """Saves a new message to the database."""
        db = get_db()
        message_data = {
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "read": self.read
        }
        try:
            # For messages, we typically only insert, not update existing ones by _id
            # The count_documents check for _id is less relevant here for new messages
            # but harmless for existing ones (which wouldn't be 'new' in this context).
            if self._id and db.messages.count_documents({"_id": self._id}) > 0:
                print(f"Attempting to update existing message with _id: {self._id}. This is unusual for messages.")
                db.messages.update_one({"_id": self._id}, {"$set": message_data})
                print(f"Message updated: {self._id}")
            else:
                result = db.messages.insert_one(message_data)
                self._id = result.inserted_id
                print(f"New message inserted with _id: {self._id}") # Debug print
            return self
        except Exception as e:
            print(f"Error saving message: {e}") # Debug print
            # Optionally log more details about the error
            return None # Indicate failure

    @staticmethod
    def get_messages_between_users(user1_id, user2_id):
        """Retrieves messages between two specific users."""
        db = get_db()
        # Create a consistent conversation_id by sorting and joining user IDs
        u_ids = sorted([str(user1_id), str(user2_id)])
        conv_id = f"{u_ids[0]}-{u_ids[1]}"

        messages_data = list(db.messages.find({
            "conversation_id": conv_id
        }).sort("created_at", 1)) # Sort by timestamp ascending

        messages = []
        for msg_data in messages_data:
            # Ensure sender_id and receiver_id are handled as ObjectId before passing to Message constructor
            sender_obj = ObjectId(msg_data["sender_id"]) if not isinstance(msg_data["sender_id"], ObjectId) else msg_data["sender_id"]
            receiver_obj = ObjectId(msg_data["receiver_id"]) if not isinstance(msg_data["receiver_id"], ObjectId) else msg_data["receiver_id"]

            messages.append(Message(
                sender_id=sender_obj,
                receiver_id=receiver_obj,
                content=msg_data["content"],
                conversation_id=msg_data["conversation_id"],
                created_at=msg_data["created_at"],
                read=msg_data.get("read", False),
                _id=msg_data["_id"]
            ))
        return messages

    @staticmethod
    def get_conversations(user_id):
        """Retrieves a list of conversations for a given user, with the last message and unread count."""
        db = get_db()
        
        # Aggregate pipeline to get a list of unique interlocutors and their last message
        pipeline = [
            # Stage 1: Find all messages involving the current user (sender or receiver)
            {"$match": {"$or": [{"sender_id": ObjectId(user_id)}, {"receiver_id": ObjectId(user_id)}]}},
            
            # Stage 2: Sort by created_at descending to easily get the last message per conversation
            {"$sort": {"created_at": -1}}, 
            
            # Stage 3: Group messages by their conversation_id to find the last message
            {"$group": {
                "_id": "$conversation_id", # Group by the generated conversation ID
                "last_message_id": {"$first": "$_id"},
                "last_message_content": {"$first": "$content"},
                "last_message_sender_id": {"$first": "$sender_id"},
                "last_message_receiver_id": {"$first": "$receiver_id"},
                "last_message_timestamp": {"$first": "$created_at"}
            }},
            
            # Stage 4: Lookup the actual message document for its content and read status
            {"$lookup": {
                "from": "messages",
                "localField": "last_message_id",
                "foreignField": "_id",
                "as": "last_message_info"
            }},
            {"$unwind": "$last_message_info"}, # Deconstruct the array
            
            # Stage 5: Determine the 'other_user_id' in each conversation
            {"$addFields": {
                "other_user_id": {
                    "$cond": {
                        "if": {"$eq": ["$last_message_sender_id", ObjectId(user_id)]},
                        "then": "$last_message_receiver_id",
                        "else": "$last_message_sender_id"
                    }
                }
            }},
            
            # Stage 6: Lookup the other user's information (username)
            {"$lookup": {
                "from": "users",
                "localField": "other_user_id",
                "foreignField": "_id",
                "as": "other_user_info"
            }},
            {"$unwind": "$other_user_info"},
            
            # Stage 7: Calculate unread count for the current user in this conversation
            {"$lookup": {
                "from": "messages",
                "let": {"convId": "$_id"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$conversation_id", "$$convId"]},
                                {"$eq": ["$receiver_id", ObjectId(user_id)]},
                                {"$eq": ["$read", False]}
                            ]
                        }
                    }},
                    {"$count": "unread_count"}
                ],
                "as": "unread_messages_count"
            }},
            {"$addFields": {
                "unread_count": {"$ifNull": [{"$arrayElemAt": ["$unread_messages_count.unread_count", 0]}, 0]}
            }},

            # Stage 8: Project the final desired fields
            {"$project": {
                "_id": 0, # Exclude the _id from the group stage
                "conversation_id": "$_id", # Rename group _id to conversation_id
                "other_user_id": "$other_user_info._id",
                "other_username": "$other_user_info.username",
                "last_message_content": "$last_message_info.content",
                "last_message_timestamp": "$last_message_info.created_at",
                "unread_count": 1
            }},
            
            # Stage 9: Sort the conversations by the timestamp of their last message
            {"$sort": {"last_message_timestamp": -1}}
        ]
        
        conversations = list(db.messages.aggregate(pipeline))
        return conversations


    @staticmethod
    def mark_messages_as_read(sender_id, receiver_id):
        """Marks messages sent from sender_id to receiver_id as read."""
        db = get_db()
        db.messages.update_many(
            {"sender_id": sender_id, "receiver_id": receiver_id, "read": False},
            {"$set": {"read": True}}
        )
