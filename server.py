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
                    
# Liste des bibliothèques à installer si elles ne sont pas déjà installées
bibliotheques_a_installer = ["Flask", "Flask-CORS"]

gest_io(bibliotheques_a_installer)


# -----------------------------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import time

app = Flask(__name__)
CORS(app)

# Variables globales pour gérer l'état du jeu
players = []
ready_players = []
roles = {}
dead_players = []
game_started = False

@app.route('/join', methods=['POST'])
def join():
    data = request.get_json()
    player_name = data.get('name')
    if player_name not in players:
        players.append(player_name)
    return jsonify({'players': players})

@app.route('/ready', methods=['POST'])
def ready():
    data = request.get_json()
    player_name = data.get('name')
    if player_name not in ready_players:
        ready_players.append(player_name)
    return jsonify({'ready_players': ready_players})

@app.route('/start_game', methods=['POST'])
def start_game():
    global game_started, roles
    if not game_started:
        game_started = True
        # Assigner les rôles
        roles = assign_roles(players)
    return jsonify(roles)

@app.route('/set_dead', methods=['POST'])
def set_dead():
    data = request.get_json()
    player_name = data.get('name')
    if player_name not in dead_players:
        dead_players.append(player_name)
    return jsonify({'dead_players': dead_players})

@app.route('/end_game', methods=['POST'])
def end_game():
    global game_started, players, ready_players, roles, dead_players
    result = check_winner()
    # Réinitialiser le jeu
    game_started = False
    players = []
    ready_players = []
    roles = {}
    dead_players = []
    return jsonify({'message': result})

def assign_roles(players):
    roles = {}
    # Copier la liste des joueurs
    available_players = players.copy()
    
    # Assigner le meurtrier (1 joueur)
    murderer = random.choice(available_players)
    roles[murderer] = "Meurtrier"
    available_players.remove(murderer)
    
    # Assigner le détective (1 joueur)
    if available_players:
        detective = random.choice(available_players)
        roles[detective] = "Détective"
        available_players.remove(detective)
    
    # Le reste des joueurs sont des civils
    for player in available_players:
        roles[player] = "Civil"
    
    return roles

def check_winner():
    murderer_alive = False
    civilians_alive = False
    
    for player in players:
        if player not in dead_players:
            if roles.get(player) == "Meurtrier":
                murderer_alive = True
            elif roles.get(player) in ["Civil", "Détective"]:
                civilians_alive = True
    
    if not murderer_alive:
        return "Les civils et le détective ont gagné!"
    elif not civilians_alive:
        return "Le meurtrier a gagné!"
    else:
        return "Le jeu continue..."

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
