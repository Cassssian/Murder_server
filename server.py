import subprocess


def gest_io(bibliotheques : list[str]):
    """
    Vérifie si les bibliothèques sont installées et les installe si nécessaire.
    bibliotheques: Liste des bibliothèques à installer
    """
    for lib in bibliotheques:
                if lib == "Flask":
                    try:
                        __import__("flask")
                    except ImportError:
                        print(f"Installation de la bibliothèque {lib}...")
                        subprocess.check_call(["pip", "install", lib])
                elif lib == "Flask-SocketIO":
                    try:
                        __import__("flask_socketio")
                    except ImportError:
                        print(f"Installation de la bibliothèque {lib}...")
                        subprocess.check_call(["pip", "install", lib])
                    
# Liste des bibliothèques à installer si elles ne sont pas déjà installées
bibliotheques_a_installer = ["Flask", "Flask-SocketIO"]

gest_io(bibliotheques_a_installer)


# -----------------------------------------------

import random
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Timer

app = Flask(__name__)
socketio = SocketIO(app)

participants = {}
timer_started = False
roles_assigned = False

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join')
def handle_join(data):
    global participants
    username = data['username']
    participants[username] = False
    emit('update_participants', participants, broadcast=True)

@socketio.on('ready')
def handle_ready(data):
    global participants, timer_started, roles_assigned
    username = data['username']
    participants[username] = True

    if all(participants.values()) and not roles_assigned:
        # Attente de 10 secondes pour vérifier que personne d'autre ne rejoint
        Timer(10, assign_roles).start()

    emit('update_participants', participants, broadcast=True)

def assign_roles():
    global roles_assigned
    roles_assigned = True
    
    # Définir les rôles en fonction du nombre de participants
    usernames = list(participants.keys())
    random.shuffle(usernames)
    
    roles = ["murder", "murder", "sheriff", "cameraman", "doctor"]
    if len(usernames) > 10:
        roles.append("sheriff")
        roles.append("doctor")
    roles.append("couple")  # Le couple aura deux rôles

    # Attribution des rôles
    assigned_roles = {}
    for role in roles:
        if role == "couple":
            assigned_roles[usernames.pop()] = "couple"
            assigned_roles[usernames.pop()] = "couple"
        else:
            assigned_roles[usernames.pop()] = role

    for user in usernames:
        assigned_roles[user] = "innocent"

    # Envoyer les rôles à chaque utilisateur
    for user, role in assigned_roles.items():
        emit('assign_role', {'role': role}, room=user)

@socketio.on('start_game')
def handle_start_game():
    global timer_started
    if not timer_started:
        timer_started = True
        start_timer()

def start_timer():
    emit('start_timer', broadcast=True)
    Timer(600, timer_end).start()

def timer_end():
    global timer_started
    timer_started = False
    emit('timer_ended', broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    # Nettoyage lorsque les participants se déconnectent
    username = None
    for user, ready in participants.items():
        if ready is False:
            username = user
            break
    if username:
        del participants[username]
    emit('update_participants', participants, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
