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
                elif lib == "Flask-CORS":
                    try:
                        __import__("flask_cors")
                    except ImportError:
                        print(f"Installation de la bibliothèque {lib}...")
                        subprocess.check_call(["pip", "install", lib])
                elif lib == "Flask-SocketIO":
                    try:
                        __import__("flask_socketio")
                    except ImportError:
                        print(f"Installation de la bibliothèque {lib}...")
                        subprocess.check_call(["pip", "install", lib])
                else:
                    try:
                        __import__(lib)
                    except ImportError:
                        print(f"Installation de la bibliothèque {lib}...")
                        subprocess.check_call(["pip", "install", lib])
                    
# Liste des bibliothèques à installer si elles ne sont pas déjà installées
bibliotheques_a_installer = ["Flask", "Flask-CORS", "Flask-SocketIO", "socket"]

gest_io(bibliotheques_a_installer)


# -----------------------------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import socket
import random
import time




app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)
socketio = SocketIO(app)




# Variables globales pour gérer l'état du jeu
players = []
ready_players = []
roles = {}
dead_players = []
death_codes = {}  # Pour stocker les codes de mort {code: player_name}
scanned_dead_players = []  # Liste des joueurs morts confirmés
game_in_progress = False  # État du jeu
couple_messages = {}
couple_pairs = {}





@app.route('/get_couple_partner', methods=['POST'])
def get_couple_partner():
    data = request.get_json()
    player_name = data.get('name')
    
    # Trouver le partenaire du couple
    couple_members = [p for p, r in roles.items() if r == "Couple"]
    partner = next((p for p in couple_members if p != player_name), None)
    
    return jsonify({'partner': partner})


@app.route('/send_couple_message', methods=['POST'])
def send_couple_message():
    data = request.get_json()
    sender = data.get('sender')
    message = data.get('message')
    
    # Trouver le partenaire
    couple_members = [p for p, r in roles.items() if r == "Couple"]
    partner = next((p for p in couple_members if p != sender), None)
    
    if partner:
        if partner not in couple_messages:
            couple_messages[partner] = []
        couple_messages[partner].append({
            'sender': sender,
            'message': message
        })
    
    return jsonify({'status': 'success'})


@app.route('/get_couple_messages', methods=['POST'])
def get_couple_messages():
    data = request.get_json()
    player_name = data.get('name')
    
    messages = couple_messages.get(player_name, [])
    # Effacer les messages après les avoir récupérés
    couple_messages[player_name] = []
    
    return jsonify({'messages': messages})


@app.route('/check_couple_partner_alive', methods=['POST'])
def check_couple_partner_alive():
    data = request.get_json()
    player_name = data.get('name')
    
    # Trouver le partenaire du couple
    couple_members = [p for p, r in roles.items() if r == "Couple"]
    partner = next((p for p in couple_members if p != player_name), None)
    
    is_partner_alive = partner and partner not in dead_players
    
    return jsonify({
        'partner': partner, 
        'is_partner_alive': is_partner_alive
    })


@app.route('/')
def home():
    return app.send_static_file('index.html')


@app.route('/game_state', methods=['GET'])
def game_state():
    return jsonify({'game_in_progress': game_in_progress})


@app.route('/join', methods=['POST'])
def join():
    global game_in_progress
    data = request.get_json()
    player_name = data.get('name')
    
    if game_in_progress:
        return jsonify({'success': False, 'message': 'Une partie est déjà en cours.'})
    
    if player_name not in players:
        players.append(player_name)
        return jsonify({'success': True, 'players': players})
    return jsonify({'success': True, 'players': players})


@app.route('/ready', methods=['POST'])
def ready():
    data = request.get_json()
    player_name = data.get('name')
    if player_name not in ready_players:
        ready_players.append(player_name)
    return jsonify({
        'ready_players': ready_players,
        'all_ready': len(ready_players) == len(players)
    })


@app.route('/start_game', methods=['POST'])
def start_game():
    global game_in_progress, roles
    data = request.get_json()
    player_name = data.get('name')

    # if not game_in_progress:
    game_in_progress = True
    if not roles:
        roles = assign_roles(players)
        return jsonify({'success': True, 'roles': roles})
    return jsonify({'success': False, 'message': 'Une partie est déjà en cours.'})


@app.route('/get_players', methods=['GET'])
def get_players():
    return jsonify({
        'players': players,
        'ready_players': ready_players,
        'dead_players': scanned_dead_players,  # Uniquement les morts confirmés
        'all_ready': len(ready_players) == len(players)
    })


@app.route('/set_dead', methods=['POST'])
def set_dead():
    data = request.get_json()
    player_name = data.get('name')
    death_code = data.get('code')
    if player_name not in dead_players:
        dead_players.append(player_name)
        death_codes[death_code] = player_name
    return jsonify({'success': True})


@app.route('/verify_dead', methods=['POST'])
def verify_dead():
    data = request.get_json()
    entered_code = data.get('code')
    if entered_code in death_codes:
        dead_player = death_codes[entered_code]
        if dead_player not in scanned_dead_players:
            scanned_dead_players.append(dead_player)
            # Émettre un événement pour informer tous les joueurs
            socketio.emit('update_dead_players', {'dead_players': scanned_dead_players})  # Émettre l'événement
            return jsonify({
                'success': True,
                'dead_players': scanned_dead_players
            })
    return jsonify({
        'success': False,
        'dead_players': scanned_dead_players
    })


@app.route('/end_game', methods=['POST'])
def end_game():
    global game_in_progress, players, ready_players, roles, dead_players, death_codes, scanned_dead_players
    
    result = check_winner()
    
    # Réinitialiser toutes les variables du jeu
    game_in_progress = False
    players = []
    ready_players = []
    roles = {}
    dead_players = []
    death_codes = {}
    scanned_dead_players = []
    
    return jsonify({'message': result})


def assign_roles(players):
    roles = {}
    # Copier la liste des joueurs
    available_players = players.copy()
    
    # Assigner les meurtriers (2 joueurs si possible)
    murderer_count = min(2, len(players) // 4)

    for _ in range(murderer_count):
        murderer = random.choice(available_players)
        roles[murderer] = "Meurtrier"
        available_players.remove(murderer)
    
    # Assigner le couple
    if len(available_players) >= 2:
        couple_member1 = random.choice(available_players)
        available_players.remove(couple_member1)
        couple_member2 = random.choice(available_players)
        available_players.remove(couple_member2)
        roles[couple_member1] = "Couple"
        roles[couple_member2] = "Couple"
    
    # Assigner le détective
    if available_players:
        detective = random.choice(available_players)
        roles[detective] = "Détective"
        available_players.remove(detective)
    
    # Assigner le médecin
    if available_players:
        medic = random.choice(available_players)
        roles[medic] = "Médecin"
        available_players.remove(medic)
    
    # Assigner le caméraman
    if available_players:
        cameraman = random.choice(available_players)
        roles[cameraman] = "Caméraman"
        available_players.remove(cameraman)
    
    # Le reste des joueurs sont des civils
    for player in available_players:
        roles[player] = "Civil"
    print(roles)
    return roles


def check_winner():
    murderers = [p for p in players if roles.get(p) == "Meurtrier"]
    murderers_alive = [p for p in murderers if p not in dead_players]
    
    innocents = [p for p in players if roles.get(p) in ["Civil", "Détective", "Médecin", "Caméraman", "Couple"]]
    innocents_alive = [p for p in innocents if p not in dead_players]

    time_elapsed = time.time() > 600
    
    if not murderers_alive:
        return "Les innocents ont gagné en éliminant tous les meurtriers!"
    elif not innocents_alive:
        return "Les meurtriers ont gagné en éliminant tous les innocents!"
    elif time_elapsed:
        return f"Le temps est écoulé! Les {random.choice(['innocents', 'meurtriers'])} ont gagné!"
    else:
        return "Le jeu continue..."




if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print(f"Le serveur est en cours d'exécution sur : http://{local_ip}:{5000}")

    socketio.run(app, '0.0.0.0', 5000, debug=True)
