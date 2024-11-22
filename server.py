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
import os
import threading




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

    if not player_name in roles.keys() and not game_in_progress:
        game_in_progress = True
        roles = assign_roles(players)
        return jsonify({'success': True, 'roles': roles})
    
    elif player_name in roles.keys():
        game_in_progress = True
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

        # Vérifiez si le joueur mort est le Caméraman
        if roles.get(player_name) == "Caméraman":
            handle_cameraman_death(player_name)  # Appeler la nouvelle fonction
        

    return jsonify({'success': True})


@app.route('/resurrect', methods=['POST'])
def resurrect():
    data = request.get_json()
    camerman_name = data.get('camerman_name')
    target_name = data.get('target_name')

    if target_name in dead_players:
        dead_players.remove(target_name)
        socketio.emit('update_dead_players', {'dead_players': dead_players})  # Mettre à jour la liste des morts
        # Vérifiez si le Caméraman devient démoniaque
        if roles.get(target_name) == "Meurtrier":
            roles[camerman_name] = "Caméraman (Démoniaque)"
        return jsonify({'success': True})

    return jsonify({'success': False})


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
    
    # # Assigner les meurtriers (2 joueurs si possible)
    # murderer_count = min(2, len(players) // 4)

    # for _ in range(murderer_count):
    #     murderer = random.choice(available_players)
    #     roles[murderer] = "Meurtrier"
    #     available_players.remove(murderer)
    
    # # Assigner le couple
    # if len(available_players) >= 2:
    #     couple_member1 = random.choice(available_players)
    #     available_players.remove(couple_member1)
    #     couple_member2 = random.choice(available_players)
    #     available_players.remove(couple_member2)
    #     roles[couple_member1] = "Couple"
    #     roles[couple_member2] = "Couple"
    
    # # Assigner le détective
    # if available_players:
    #     detective = random.choice(available_players)
    #     roles[detective] = "Détective"
    #     available_players.remove(detective)
    
    # # Assigner le médecin
    # if available_players:
    #     medic = random.choice(available_players)
    #     roles[medic] = "Médecin"
    #     available_players.remove(medic)
    
    # Assigner le caméraman
    if available_players:
        cameraman = random.choice(available_players)
        roles[cameraman] = "Caméraman"
        available_players.remove(cameraman)
    
    # Le reste des joueurs sont des civils
    for player in available_players:
        roles[player] = "Civil"
    return roles


def handle_cameraman_death(cameraman_name):
    # Attendre 20 secondes avant d'envoyer la notification
    threading.Timer(20, notify_cameraman_death, [cameraman_name]).start()


def notify_cameraman_death(cameraman_name):
    # Émettre un événement pour notifier tous les joueurs
    socketio.emit('cameraman_death_notification', {'name': cameraman_name})


def check_winner():
    murderers = [p for p in players if roles.get(p) == "Meurtrier"]
    murderers_alive = [p for p in murderers if p not in dead_players]
    
    innocents = [p for p in players if roles.get(p) in ["Civil", "Détective", "Médecin", "Caméraman", "Couple"]]
    innocents_alive = [p for p in innocents if p not in dead_players]

    time_elapsed = time.time() > 600
    
    if not murderers_alive and all(code in scanned_dead_players for code in death_codes.keys()):
        return "Les innocents ont gagné en éliminant tous les meurtriers!"
    
    if not innocents_alive and all(code in scanned_dead_players for code in death_codes.keys()):
        return "Les meurtriers ont gagné en éliminant tous les innocents!"
    
    elif time_elapsed:
        return f"Le temps est écoulé! Les {random.choice(['innocents', 'meurtriers'])} ont gagné!"
    
    return "Le jeu continue..."


@app.route('/reset_game', methods=['POST'])
def reset_game():
    global players, ready_players, roles, dead_players, death_codes, scanned_dead_players, game_in_progress
    
    # Réinitialiser toutes les variables du jeu
    game_in_progress = False
    players = []
    ready_players = []
    roles = {}
    dead_players = []
    death_codes = {}
    scanned_dead_players = []
    
    return jsonify({'status': 'success'})


def ngrok():
    subprocess.Popen(['./ngrok.exe'], stdout=subprocess.PIPE)
    time.sleep(1)
    if not os.path.exists(os.path.join(os.path.expanduser("~"), 'AppData', 'Local' , 'ngrok', 'ngrok.yml')):
        subprocess.Popen(['ngrok', 'config', 'add-authtoken', '2pCUFvSe9CHgq5dZk11ajfy5Tql_3J3B2sqieZMeisMQ4HoBs'], stdout=subprocess.PIPE)
    subprocess.Popen(['ngrok', 'http', f'http://{local_ip}:5000', '--url=jawfish-correct-weekly.ngrok-free.app'])




if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)


    print(f"Local IP: http://{local_ip}:5000")
    # ngrok_access = threading.Thread(target=ngrok)
    # ngrok_access.start()

    socketio.run(app, '0.0.0.0')
