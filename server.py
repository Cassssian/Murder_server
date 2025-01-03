# type: ignore[import]
# pyright: ignore[import]
# pylint: disable=import-error
# ruff: noqa: F401, E402
# mypy: ignore-errors
# flake8: noqa: F401

import subprocess
import os
import pkg_resources
import requests
from packaging import version
import sys

def clv():
        current_version = pkg_resources.get_distribution("itmgr").version
        
        response = requests.get(f"https://pypi.org/pypi/itmgr/json")
        latest_version = response.json()["info"]["version"]
        
        is_latest = version.parse(current_version) >= version.parse(latest_version)

        
        
        return is_latest

def itmgr_dep():
    """
    Install and import necessary dependencies for the project.
    """
    try:
        __import__("itmgr")
        act = clv()
        
        if not clv():
            if (result := input("\x1b[38;5;116mUne mise à jour a été trouvée, souhaitez-vous l'installer ? (y/n) : \x1b[0m")).lower() == 'y':
                subprocess.check_call([sys.executable, "-m", "pip", "install", "itmgr", "--upgrade"])
            else: 
                print("\x1b[38;5;196mLa mise à jour n'a pas été effectuée.\x1b[0m")

    except:
        subprocess.run(["pip", "install", "itmgr"])
    subprocess.run(["itmgr", "add", "Flask", "flask"])
    subprocess.run(["itmgr", "add", "flask_cors", "Flask-CORS"])
    subprocess.run(["itmgr", "add", "flask_socketio", "Flask-SocketIO"])

itmgr_dep()

from itmgr import install_and_import

install_and_import(["Flask", ["Flask", "request", "jsonify"], False, False],
                   ["flask_cors", ["CORS"], False, False],
                   ["flask_socketio", ["SocketIO"], False, False],
                   ["socket", True, False, False],
                   ["random", True, False, False],
                   ["time", True, False, False],
                   ["threading", True, False, False],
                   ["sqlite3", True, False, False],
                   ["json", True, False, False],
                   ["datetime", "datetime", False, False],
                   ["threading", ["Lock"], False, False],
                   ["webbrowser", True, False, False],
                )


import site
folder = site.getsitepackages()[1]

def remove_line_from_file(filepath, line_to_remove):
    # Lire le contenu du fichier
    with open(filepath, 'r') as file:
        lines = file.readlines()
    
    # Filtrer la ligne à supprimer
    modified_lines = [line for line in lines if line_to_remove not in line]
    
    # Réécrire le fichier sans la ligne
    with open(filepath, 'w') as file:
        file.writelines(modified_lines)

# Utilisation
filepath = folder + "/flask_socketio/__init__.py"
line_to_remove = "reason = socketio.Server.reason"
remove_line_from_file(filepath, line_to_remove)

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from flask_socketio import SocketIO
# import socket
# import random
# import time
# import threading
# import sqlite3
# import json
# import datetime


class GameRecord:
    def __init__(self):
        self.db_path = 'game_history.db'
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS games
                    (id INTEGER PRIMARY KEY,
                     timestamp TEXT,
                     duration INTEGER,
                     winner TEXT,
                     players TEXT,
                     roles TEXT,
                     dead_players TEXT,
                     actions TEXT)''')
        conn.commit()
        conn.close()
    
    def get_top_players(self, limit=3):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT player, COUNT(*) as wins
            FROM (
                SELECT json_each.value as player
                FROM games, json_each(players)
                WHERE (winner = 'Innocents' AND json_each.value NOT IN (
                    SELECT value FROM json_each(roles) WHERE value LIKE '%Meurtrier%'
                )) OR (winner = 'Meurtriers' AND json_each.value IN (
                    SELECT value FROM json_each(roles) WHERE value LIKE '%Meurtrier%'
                ))
            )
            GROUP BY player
            ORDER BY wins DESC
            LIMIT ?
        ''', (limit,))
        
        results = c.fetchall()
        conn.close()
        
        return [{'name': name, 'wins': wins} for name, wins in results]

    def get_win_ratio(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT winner, COUNT(*) as count
            FROM games
            GROUP BY winner
        ''')
        
        results = dict(c.fetchall())
        conn.close()
        
        return {
            'innocent': results.get('Innocents', 0),
            'murderer': results.get('Meurtriers', 0)
        }

    def get_recent_games(self, limit=5):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, timestamp, duration, winner
            FROM games
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        results = c.fetchall()
        conn.close()
        
        return [{
            'id': id,
            'timestamp': timestamp,
            'duration': duration,
            'winner': winner
        } for id, timestamp, duration, winner in results]

    def get_game_details(self, game_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT timestamp, duration, winner, players, roles, dead_players, actions
            FROM games
            WHERE id = ?
        ''', (game_id,))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            timestamp, duration, winner, players, roles, dead, actions = result
            return {
                'timestamp': timestamp,
                'duration': duration,
                'winner': winner,
                'players': json.loads(players),
                'roles': json.loads(roles),
                'dead_players': json.loads(dead),
                'actions': json.loads(actions)
            }
        return None



    def save_game(self, winner, duration, players_data, actions):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO games 
                    (timestamp, duration, winner, players, roles, dead_players, actions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (datetime.now().isoformat(),
                     duration,
                     winner,
                     json.dumps(players_data['players']),
                     json.dumps(players_data['roles']),
                     json.dumps(players_data['dead']),
                     json.dumps(actions)))
        conn.commit()
        conn.close()

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)
socketio = SocketIO(app)



players = []
ready_players = []
roles = {}
dead_players = []
death_codes = {}
scanned_dead_players = []
game_in_progress = False
couple_messages = {}
couple_pairs = {}
cameraman_resurrections = {}
cameraman_pending_resurrection = None
game_actions = []
game_start_time = None
saved = False
assign = False
pending_resurrections = set()

state_lock = Lock()

def record_action(action_type, player, target=None, description=None):
        global game_actions
        game_actions.append({
            'time': int(time.time() - game_start_time),
            'type': action_type,
            'player': player,
            'target': target,
            'description': description
        })

@app.route('/get_stats')
def get_stats():
    game_records = GameRecord()
    top_players = game_records.get_top_players(3)
    win_ratio = game_records.get_win_ratio()
    recent_games = game_records.get_recent_games(5)
    
    return jsonify({
        'topPlayers': top_players,
        'winRatio': win_ratio,
        'recentGames': recent_games
    })

@app.route('/game_details/<int:game_id>')
def game_details(game_id):
    game_records = GameRecord()
    game_data = game_records.get_game_details(game_id)
    return jsonify(game_data)



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
        global couple_messages
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
        global couple_messages
        data = request.get_json()
        player_name = data.get('name')
        
        messages = couple_messages.get(player_name, [])
        # Effacer les messages après les avoir récupérés
        couple_messages[player_name] = []
        
        return jsonify({'messages': messages})


@app.route('/check_couple_partner_alive', methods=['POST'])
def check_couple_partner_alive():
        global roles, dead_players
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
        global players, game_in_progress
        data = request.get_json()
        player_name = data.get('name')
        
        if game_in_progress:
            return jsonify({'success': False, 'message': 'Une partie est déjà en cours.'})
        
        if player_name in players:
            return jsonify({'success': False, 'error': 'duplicate_name'})

        players.append(player_name)
        couple_messages = {}
        return jsonify({'success': True, 'players': players})


@app.route('/ready', methods=['POST'])
def ready():
        global ready_players, players
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
        global game_in_progress, roles, ready_players, players, game_start_time, actions
        data = request.get_json()
        player_name = data.get('name')

        if len(ready_players) != len(players):
            return jsonify({'success': False, 'message': 'Tous les joueurs ne sont pas prêts.'})

        if not player_name in roles.keys() and not game_in_progress:
            game_in_progress = True
            roles = assign_roles(players)
            game_start_time = time.time()
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            open_admin_page(local_ip)
            return jsonify({'success': True, 'roles': roles})
        
        elif player_name in roles.keys():
            game_in_progress = True
            return jsonify({'success': True, 'roles': roles})

        
        return jsonify({'success': False, 'message': 'Une partie est déjà en cours.'})

    

@app.route('/get_players', methods=['GET'])
def get_players():
        global players, ready_players, dead_players, scanned_dead_players
        return jsonify({
            'players': players,
            'ready_players': ready_players,
            'dead_players': scanned_dead_players,
            'all_ready': len(ready_players) == len(players)
        })


@app.route('/set_dead', methods=['POST'])   
def set_dead():
        global dead_players, death_codes, roles
        data = request.get_json()
        player_name = data.get('name')
        death_code = data.get('code')
        if player_name not in dead_players:
            dead_players.append(player_name)
            death_codes[death_code] = player_name
            record_action('death', player_name)

            if roles.get(player_name) == "Caméraman":
                handle_cameraman_death(player_name)

        return jsonify({'success': True})


@app.route('/resurrect', methods=['POST'])
def resurrect():
        global pending_resurerections, roles
        data = request.get_json()
        camerman_name = data.get('camerman_name')
        target_name = data.get('target_name')

        if camerman_name in pending_resurrections:
            pending_resurrections.remove(camerman_name)
            if roles.get(target_name) == "Meurtrier":
                roles[camerman_name] = "Caméraman (Démoniaque)"
                record_action('resurrect_evil', target_name, camerman_name)
            else:
                record_action('resurrect', target_name, camerman_name)
            return jsonify({'success': True})

        return jsonify({'success': False})

@socketio.on('resurrection_declined')
def handle_resurrection_declined(data):
    socketio.emit('show_death_code', {
        'cameraman': data['cameraman']
    })

@socketio.on('resurrection_accepted')
def handle_resurrection_accepted(data):
        global cameraman_resurrections, roles
        cameraman_resurrections[data['cameraman']] = 1
        socketio.emit('player_resurrected', {
            'cameraman': data['cameraman'],
            'reviver': data['reviver'],
            'is_murderer': roles.get(data['reviver']) == "Meurtrier"
        })



@app.route('/verify_dead', methods=['POST'])
def verify_dead():
        global death_codes, scanned_dead_players
        data = request.get_json()
        entered_code = data.get('code')
        scanner = data.get('scanner')
        if entered_code in death_codes:
            dead_player = death_codes[entered_code]
            if dead_player not in scanned_dead_players:
                scanned_dead_players.append(dead_player)
                record_action('scan', scanner, dead_player)
                socketio.emit('update_dead_players', {'dead_players': scanned_dead_players})
                return jsonify({
                    'success': True,
                    'dead_players': scanned_dead_players
                })
        return jsonify({
            'success': False,
            'dead_players': scanned_dead_players
        })

def reset_game_variables():
        global players, ready_players, roles, dead_players, death_codes, scanned_dead_players, game_actions, assign, saved
        players = []
        ready_players = []
        roles = {}
        dead_players = []
        death_codes = {}
        scanned_dead_players = []
        game_actions = []
        assign = False
        saved = False



def assign_roles(players):
        global roles, assign
        if assign:
            return roles
    
        assign = True
        roles = {}
        available_players = players.copy()

        # Assign murderers first
        murderer_count = max(2, len(players) // 4)
        for _ in range(murderer_count):
            if available_players:
                murderer = random.choice(available_players)
                roles[murderer] = "Meurtrier"
                available_players.remove(murderer)

        # Assign couple if enough players
        if len(available_players) >= 2:
            couple_member1 = random.choice(available_players)
            available_players.remove(couple_member1)
            couple_member2 = random.choice(available_players)
            available_players.remove(couple_member2)
            roles[couple_member1] = "Couple"
            roles[couple_member2] = "Couple"
        # Assign special roles to remaining players
        while available_players:
            player = available_players.pop()
            role = random.choice(["Détective", "Médecin", "Caméraman", "Civil", "Civil", "Civil"])
            roles[player] = role

        return roles



@app.route('/handle_cameraman_death', methods=['POST'])
def handle_cameraman_death():
        global cameraman_resurrections
        data = request.get_json()
        cameraman_name = data['name']
        
        if cameraman_name not in cameraman_resurrections:
            cameraman_resurrections[cameraman_name] = 0
        
        if cameraman_resurrections[cameraman_name] >= 1:
            return jsonify({'can_resurrect': False})
            
        return jsonify({'can_resurrect': True})

@socketio.on('player_selected')
def handle_player_selection(data):
    socketio.emit('show_resurrection_choice', {
        'cameraman': data['cameraman'],
        'selectedPlayer': data['selectedPlayer']
    })

@app.route('/initiate_resurrection', methods=['POST'])
def initiate_resurrection():
        global cameraman_pending_resurrection
        data = request.get_json()
        cameraman_name = data['cameraman']
        initiator = data['initiator']
        
        cameraman_pending_resurrection = {
            'cameraman': cameraman_name,
            'initiator': initiator
        }
        
        return jsonify({'success': True})


def save_game_result(winner):
        global saved
        if saved:
            return

        else:
            saved = True
            game_records = GameRecord()
            game_records.save_game(
                winner=winner,
                duration=int(time.time() - game_start_time),
                players_data={
                    'players': players,
                    'roles': roles,
                    'dead': dead_players
                },
                actions=game_actions
            )

def open_admin_page(url):
    webbrowser.open(f'http://{url}:5000/admin')

@app.route('/admin')
def admin():
    return app.send_static_file('admin.html')

@app.route('/check_victory', methods=['POST'])
def check_victory():
        global players, roles, dead_players, scanned_dead_players, game_actions
        if check_time_limit():
            return jsonify({
                'valid': True,
                'message': "Le temps est écoulé! Les {winner} ont gagné!"
            })


        data = request.get_json()
        winner = data.get('winner')
        
        murderers = [p for p in players if roles.get(p) in ["Meurtrier", "Caméraman (Démoniaque)"]]
        innocents = [p for p in players if roles.get(p) not in ["Meurtrier", "Caméraman (Démoniaque)"]]
        
        all_dead_confirmed = all(p in scanned_dead_players for p in dead_players)
        
        if winner == "Meurtriers":
            valid = all(p in dead_players for p in innocents) and all_dead_confirmed
        else:
            valid = all(p in dead_players for p in murderers) and all_dead_confirmed
            
        if valid:
            save_game_result(winner)
            return jsonify({
                'valid': True,
                'message': f"Les {winner} ont gagné !!"
            })
            
        return jsonify({
            'valid': False,
            'message': "Verification failed"
        })

@socketio.on('restart_game')
def handle_restart_game():
    socketio.emit('game_restart')

def check_time_limit():
    global game_start_time, saved
    if time.time() > game_start_time + 600 and not saved:  # 10 minutes
        winner = random.choice(['Innocents', 'Meurtriers'])
        save_game_result(winner)
        socketio.emit('game_end', {'winner': winner})
        return True
    return False


@app.route('/reset_game', methods=['POST'])
def reset_game():
    global players, ready_players, roles, dead_players, scanned_dead_players, game_actions, game_start_time, saved, assign, game_in_progress, couple_messages, couple_pairs, cameraman_resurrections, cameraman_pending_resurrection, game_actions, game_start_time, saved, assign
    players = []
    ready_players = []
    roles = {}
    dead_players = []
    death_codes = {}
    scanned_dead_players = []
    game_in_progress = False
    couple_messages = {}
    couple_pairs = {}
    cameraman_resurrections = {}
    cameraman_pending_resurrection = None
    game_actions = []
    game_start_time = None
    saved = False
    assign = False

    
    return jsonify({'status': 'success'})



def ngrok():

    # ngrok config add-authtoken 2p2PH2tcX0kRsxLmFQAbNOBRFah_DtKFfxa3sSotYbb5sB24 -> burro-golden-bird.ngrok-free.app
    # ngrok config add-authtoken 2pCUFvSe9CHgq5dZk11ajfy5Tql_3J3B2sqieZMeisMQ4HoBs -> jawfish-correct-weekly.ngrok-free.app

    # Supprimer le fichier ngrok.yml s'il existe lorsqu'on change d'url
    
    subprocess.Popen(['./ngrok.exe'], stdout=subprocess.PIPE)
    time.sleep(1)
    if not os.path.exists(os.path.join(os.path.expanduser("~"), 'AppData', 'Local' , 'ngrok', 'ngrok.yml')):
        subprocess.Popen(['ngrok', 'config', 'add-authtoken', '2p2PH2tcX0kRsxLmFQAbNOBRFah_DtKFfxa3sSotYbb5sB24'], stdout=subprocess.PIPE)
    subprocess.Popen(['ngrok', 'http', f'http://{local_ip}:5000', '--url=burro-golden-bird.ngrok-free.app'])




if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)


    print(f"Local IP: http://{local_ip}:5000")
    ngrok_access = threading.Thread(target=ngrok)
    ngrok_access.start()

    socketio.run(app, '0.0.0.0')
