import base64
import json
import threading
from uuid import uuid4
from flask import render_template, redirect, url_for, make_response, Response, stream_with_context
import os
import pyotp
import pyrebase
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re
import io
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg')
from langchain.document_loaders import UnstructuredFileLoader

import chat_helper, scrape_helper

# Flask and Redis setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Redis configuration
redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)

# Firebase configuration
config = {
  'apiKey': "AIzaSyAGQDaamCqI4URitEBD_PBAuR-cRtPCq70",
  'authDomain': "sunflower-928b3.firebaseapp.com",
   'databaseURL': "https://sunflower-928b3-default-rtdb.asia-southeast1.firebasedatabase.app",
   'projectId': "sunflower-928b3",
  'storageBucket': "sunflower-928b3.appspot.com",
  'messagingSenderId': "405620669957",
  'appId': "1:405620669957:web:022c0dd4a1628db80b266c",
  'measurementId': "G-EHW2R4H6FL",
'serviceAccount': './sunflower-928b3-firebase-adminsdk-8o750-26fefdf5b1.json'
}

# Initialize Firebase
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()


# basedir = os.path.abspath(os.path.dirname(__file__))
# app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "chat.db")}'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'  # Use your preferred database
db = SQLAlchemy(app)

class User(db.Model):
    uid = db.Column(db.String(28), primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    session_id = db.Column(db.String(36), nullable=False)  # UUID for each session
    chat_name = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.Text, nullable=False)
    file_content = db.Column(db.Text, nullable=True)
    images = db.Column(db.Text, nullable=True)
    sender = db.Column(db.Text, nullable=False)  # 'user' or 'assistant'


# Email 2FA Function
def send_otp(email, otp):
    sender_email = "thirdeye.official.contact@gmail.com"  # Replace with your email
    sender_password = "hofn mlgf uljc moxm"    # Replace with your App Password
    receiver_email = email

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your OTP Code"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"Your OTP code is {otp}"
    message.attach(MIMEText(text, "plain"))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        cookies = request.cookies
        email = cookies.get('email').lower()
        # email = redis_client.get('current_email')
        otp_key = f"{email}_otp"
        stored_otp = redis_client.get(otp_key)

        if stored_otp == user_otp:
            auth_key = f"{email}_auth"
            password = redis_client.get(auth_key)
            name = redis_client.get(f"{email}_username")

            try:
                auth.create_user_with_email_and_password(email, password)
            except:
                pass
            user = auth.sign_in_with_email_and_password(email, password)

            res = make_response(redirect(url_for('index')))
            res.set_cookie('uid', user["localId"])
            try:
                name = User.query.filter_by(uid=user["localId"]).first().name
                # db.session.add(user)
                # db.session.commit()
                # res.set_cookie('username', name)
            except:
                user = User(uid=user["localId"], name=name, email=email.lower())
                db.session.add(user)
                db.session.commit()

            # res.set_cookie('username', user["username"])
            # Cleanup Redis keys
            res.delete_cookie('email')
            redis_client.delete(otp_key)
            redis_client.delete(auth_key)
            redis_client.delete(f"{email}_username")

            return res
        else:
            error = "Invalid OTP! Please try again."
            res = make_response(render_template("login.html", error=error))
            res.delete_cookie('email')
            redis_client.delete(otp_key)
            redis_client.delete(f"{email}_auth")
            redis_client.delete(f"{email}_username")

            return res
    else:
        return render_template('verify_otp.html')

@app.route("/login")
def login():
    return render_template("login.html")

# Sign up
@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route('/signup_post', methods=['POST', 'GET'])
def signup_post():
    if request.method == "POST":
        result = request.form
        email = result["email"].lower()
        password = result["password"]
        confirm_password = result['confirm_password']
        username = result["name"]#.lower()

        if password != confirm_password:
            error = "Passwords don't match! Please correct the password"
            return render_template("signup.html", error=error)

        try:
            totp = pyotp.TOTP(pyotp.random_base32())
            otp = totp.now()
            if send_otp(email, otp):
                otp_key = f"{email}_otp"
                auth_key = f"{email}_auth"
                # auth_email = f"{email}_current_email"
                auth_username = f"{email}_username"

                redis_client.setex(otp_key, 120, otp)  # OTP valid for 5 minutes
                redis_client.setex(auth_key, 120, password)
                redis_client.setex(auth_username, 120,username)

                res = make_response(redirect(url_for('verify_otp')))
                res.set_cookie('email', email)

                return res
            else:
                return "Failed to send OTP."

        except Exception as e:
            if 'WEAK_PASSWORD' in str(e):
                error = 'Weak Password! Password should be at least 6 characters'
            else:
                print(e)
                error = 'Account already exists! Login Instead'
            return render_template("signup.html", error=e)

    else:
        return render_template("signup.html")

@app.route('/login_post', methods=['POST', 'GET'])
def login_post():
    if request.method == "POST":
        result = request.form
        email = result["email"].lower()
        password = result["pass"]

        try:
            uid = User.query.filter_by(email=email).first().uid
        except:
            error = 'Account not found! Sign Up Instead'
            return render_template("login.html", error=error)

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            totp = pyotp.TOTP(pyotp.random_base32())
            otp = totp.now()
            if send_otp(user["email"], otp):
                otp_key = f"{email}_otp"
                auth_key = f"{email}_auth"

                redis_client.setex(otp_key, 120, otp)  # OTP valid for 5 minutes
                redis_client.setex(auth_key, 120, password)

                res = make_response(redirect(url_for('verify_otp')))
                res.set_cookie('email', email)

                return res
            else:
                return "Failed to send OTP."

        except Exception as e:
            # print(e)
            if 'EMAIL_NOT_FOUND' in str(e):
                error = 'Account not found! Sign Up Instead'
            else:
                error = 'Incorrect Email or Password!'
            return render_template("login.html", error=error)
    else:
        return render_template("login.html")

@app.route('/')
def index():
    cookies = request.cookies
    user_id = cookies.get('uid') # Get the current user's ID

    if user_id==None:
        return redirect(url_for('login'))
    name = User.query.filter_by(uid=user_id).first().name

    # Retrieve all unique session IDs for the user
    sessions = Chat.query.with_entities(Chat.session_id, Chat.chat_name, db.func.min(Chat.timestamp)).filter_by(user_id=user_id).group_by(Chat.session_id).order_by(db.func.min(Chat.timestamp).desc()).all()

    # Format the sessions for the template
    session_data = [{'session_id': session_id, 'chat_name': chat_name} for session_id, chat_name, _ in sessions]

    return render_template('main_app.html', sessions=session_data, username=name)

# # Start a new chat session
# @app.route('/new_chat', methods=['POST'])
# def new_chat():
#     cookies = request.cookies
#     # user_id = cookies.get('uid')
#     new_session_id = str(uuid4())  # Generate a unique session ID for the new chat
#     # Store the new session ID in the session
#     session['current_session_id'] = new_session_id
#
#     return jsonify({'session_id': new_session_id})



@app.route('/send_message', methods=['POST'])
def send_message():
    if request.content_type != 'application/json':
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.json
    cookies = request.cookies
    user_id = cookies.get('uid')
    user_message = data['message']
    file_content = data['file_content']
    session_id = data['session_id']

    # Fetch or create chat name
    try:
        chat_name = Chat.query.filter_by(session_id=session_id).first().chat_name
    except:
        chat_name = 'New Chat'

    # Store user message
    chat_message = Chat(user_id=user_id, session_id=session_id, chat_name=chat_name, message=user_message,
                        file_content=file_content, sender='user')
    db.session.add(chat_message)
    db.session.commit()

    return jsonify({'status': 'Message received, starting stream...'})

@app.route('/stream_response', methods=['GET'])
def stream_response():
    user_message = request.args.get('message')
    session_id = request.args.get('session_id')
    document = request.args.get('document')
    cookies = request.cookies
    user_id = cookies.get('uid')

    if document=='true':
        response_stream = chat_helper.summarise_document(user_message)
        try:
            chat_name = Chat.query.filter_by(session_id=session_id).first().chat_name
        except:
            chat_name = 'New Chat'
    else:
        try:
            chat_name = Chat.query.filter_by(session_id=session_id).first().chat_name
            chats = Chat.query.filter_by(user_id=user_id, session_id=session_id).order_by(Chat.timestamp).all()
            chat_history = [{'role': chat.sender, 'content': chat.message+'\n *Document Content:\n'+chat.file_content if chat.file_content else chat.message} for chat in chats]

        except:
            chat_name = 'New Chat'
            chat_history = []

        # Get bot response (generator or full string)
        response_stream = generate_assistant_response(user_message, chat_history)

    def generate(response_stream):
        full_response = ""
        images = []

        try:
            # Handle image generation (if images exist)
            if type(response_stream)==dict:
                for chunk in response_stream['response']:
                    full_response += chunk
                    yield f"data: {json.dumps({'response': chunk})}\n\n"

                for img in response_stream['images']:
                    images.append(img)
                    yield f"data: {json.dumps({'image': img})}\n\n"

                chat_response = Chat(user_id=user_id, session_id=session_id, chat_name=chat_name,
                                     message=full_response,
                                     images=json.dumps(images), sender='assistant')
            else:
                for chunk in response_stream:
                    full_response += chunk
                    yield f"data: {json.dumps({'response': chunk})}\n\n"

                chat_response = Chat(user_id=user_id, session_id=session_id, chat_name=chat_name,
                                     message=full_response, sender='assistant')

            yield "data: [DONE]\n\n"  # Indicate the end of the stream

            db.session.add(chat_response)
            db.session.commit()

        except Exception as e:
            # print(e)
            yield f"data: [ERROR] {str(e)}\n\n"

    return Response(stream_with_context(generate(response_stream)), mimetype='text/event-stream')

def generate_assistant_response(query, chat_history):
    query = query.lower()
    keywords = ['chart', 'graph', 'plot', 'diagram', 'visualization']

    if any(word in query for word in keywords):
        # Non-streaming response, likely to involve an image
        return process_image_response(query, chat_history)
    else:
        # Streaming response for text
        return stream_response(query, chat_history)

def stream_response(query, chat_history):
    response = chat_helper.query(query, stream=True, chat_history=chat_history)
    return response


def process_image_response(query, chat_history):
    response = chat_helper.query(query, stream=False, chat_history=chat_history)
    history_text, images = resolve_response(response)

    # Store the final text response (history_text) along with images
    return {'response': history_text, 'images': images}


def save_fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_base64

def llm_correct_code(code, error_message):
    response = chat_helper.query_code_model(code, error_message)
    return response

def resolve_response(response):
    history_text = ''
    images = []

    if "```" in response:
        pattern = r"```python(.*?)```"
        code_block = re.search(pattern, response, re.DOTALL)

        if code_block:
            code = code_block.group(1).strip()
            response = response.replace(f"```python\n{code}\n```", "")

            try:
                exec(code)  # Execute the extracted code

                # Convert all figures to base64-encoded strings
                for i in plt.get_fignums():
                    fig = plt.figure(i)
                    img_base64 = save_fig_to_base64(fig)
                    images.append(img_base64)

            except Exception as e:
                corrected_code = llm_correct_code(code, str(e))
                exec(corrected_code)

                for i in plt.get_fignums():
                    fig = plt.figure(i)
                    img_base64 = save_fig_to_base64(fig)
                    images.append(img_base64)

    history_text += response  # Append remaining non-code text
    return history_text, images


# Retrieve chat history
@app.route('/chat_history', methods=['GET'])
def chat_history():
    cookies = request.cookies
    user_id = cookies.get('uid')  # Get current user's ID
    session_id = request.args.get('session_id')  # Get the session ID from the request

    chats = Chat.query.filter_by(user_id=user_id, session_id=session_id).order_by(Chat.timestamp).all()
    history = [{'sender': chat.sender, 'message': chat.message, 'images': json.loads(chat.images) if chat.images else None, 'timestamp': chat.timestamp} for chat in chats]

    return jsonify(history)

@app.route('/create_session', methods=['POST'])
def create_session():
    # cookies = request.cookies
    # user_id = cookies.get('uid')  # Get current user's ID
    new_session = str(uuid4())
    session['current_session_id'] = new_session

    return jsonify({'session_id': new_session})

@app.route('/load_chat/<int:session_id>', methods=['GET'])
def load_chat(session_id):
    cookies = request.cookies
    user_id = cookies.get('uid')  # Get current user's ID
    chats = Chat.query.filter_by(user_id=user_id, session_id=session_id).all()
    messages = [{'sender': chat.sender, 'text': chat.message} for chat in chats]
    return jsonify({'messages': messages})

@app.route('/rename_chat', methods=['POST'])
def rename_chat():
    data = request.json
    session_id = data['session_id']
    new_name = data['new_name']

    # Update the chat name in your database
    session = Chat.query.filter_by(session_id=session_id).all()
    if session:
        for s in session: s.chat_name = new_name
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/delete_chat', methods=['DELETE'])
def delete_chat():
    data = request.json
    session_id = data['session_id']

    # Delete the chat from your database
    session = Chat.query.filter_by(session_id=session_id).all()

    if session:
        [db.session.delete(s) for s in session]
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404


# Upload a file for scraping
@app.route('/upload_file', methods=['POST'])
def upload_file():

    if 'file' in request.files:
        file = request.files['file']
        file_path = os.path.join("uploads", file.filename)
        file.save(file_path)

        # Use LangChain UnstructuredLoader to extract file content
        loader = UnstructuredFileLoader(file_path)
        documents = loader.load()

        complete_document_content = ''
        for content in documents:
            complete_document_content += content.page_content
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            scrape_helper.save_content_to_db(content.page_content, file.filename, timestamp)

        return jsonify({"content": complete_document_content,"message": "File content extracted"})


    else:
        return jsonify({"error": "No file uploaded"}), 400

# Scrape a URL for content
@app.route('/scrape_link', methods=['POST'])
def scrape_link():
    url = request.json.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    content = scrape_helper.scrape_data(url)

    return jsonify({"content": content, "message": "URL content extracted"})


def start_scraper_loop():
    scraper_thread = threading.Thread(target=scrape_helper.main_scraping_loop)
    scraper_thread.daemon = True  # Daemon thread will stop when the main Flask app stops
    scraper_thread.start()



if __name__ == '__main__':
    with app.app_context():
        scraper_thread = threading.Thread(target=scrape_helper.main_scraping_loop)
        scraper_thread.daemon = True  # Daemon thread will stop when the main Flask app stops
        scraper_thread.start()
        db.create_all()
        app.run(debug=True)

