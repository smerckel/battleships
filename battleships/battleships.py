import argparse
import os
import sys

import numpy as np
import zmq
from termcolor import cprint

from battleships_data import *

import logging
logger = logging.getLogger(__name__)

A=0
B=1
C=2
D=3
E=4
F=5
G=6
H=7
I=8
J=9

class ZMQClient(object):

    def __init__(self, server, port):
        self.context = zmq.Context()
        logger.info(f"Connecting to server ({server}:{port})...")
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect (f"tcp://{server}:{port}")

    def _enc(self, message):
        return [i.encode() for i in message]

    def _dec(self, message):
        return [i.decode() for i in message]
    
    def send(self, message):
        message = self._enc(message)
        self.socket.send_multipart(message)

    def receive(self):
        message = self.socket.recv_multipart()
        message = self._dec(message)
        return message


class Player():
    def __init__(self, mine_field, enemy_field):
        self.whoami = os.environ['USER']
        self.fields = [mine_field, enemy_field]
        self.zmq = None
        self.player_id = None

    def login(self, server='localhost', port=9002):
        self.zmq = ZMQClient(server, port)
        self.zmq.send([LOGIN, self.whoami])
        response = self.zmq.receive()
        assert response[0] == LOGIN
        if response[1] == LOGIN_ERROR:
            logger.error("Failed to login. Too many users.")
            raise ValueError("Failed to login. Too many users.")
        self.player_id = response[2]
        logger.info(f"Logged in as user {self.player_id}")

    def logout(self):
        self.zmq.send([LOGOUT, self.whoami])
        response = self.zmq.receive()
        assert response[0] == LOGOUT and response[1] == LOGOUT_OK
        logger.info(f"Logged out.")
        
    def draw(self):
        # draw header
        print("  ", end="")
        for i in range(Field.SIZE):
            print(f" {i} ", end="")
        print("      ", end="")
        for i in range(Field.SIZE):
            print(f" {i} ", end="")
        print()
        for i in range(Field.SIZE):
            self.fields[1].draw(i)
            print("    ", end='')
            self.fields[0].draw(i)
            print()
        print()


    def _convert_to_indices(self, xs, ys):
        ix = ord(xs) - 65
        iy = int(ys)
        return ix, iy

    
    def enter_coordinates(self):
        while True:
            ans = input("Coordinates, please: ")
            try:
                x,y = ans.split()
            except ValueError:
                print("Coordinates not understood.")
            else:
                try:
                    x = x.upper()
                    ix, iy = self._convert_to_indices(x, y)
                except (ValueError, TypeError):
                    print("Not a valid coordinate. Try again.")
                else:
                    if ix<0 or ix>=Field.SIZE or iy<0 or iy>=Field.SIZE:
                        print("Not a valid coordinate. Try again.")
                    else:
                        break # valid coorindates
        return x, y, ix, iy
        
    def attack(self, x=None, y=None):
        if  x is None and y is None:
            x, y, ix, iy = self.enter_coordinates()
        else:
            ix, iy = self._convert_to_indices(x, y)
        message = [ATTACK, x, y]
        self.zmq.send(message)
        message = self.zmq.receive()
        assert message[0] == ATTACK
        # now ask for the result
        message = [ATTACK_REQ_RESULT]
        self.zmq.send(message)
        response = self.zmq.receive()
        assert response[0] == ATTACK_REQ_RESULT
        result = int(response[1])
        if result==0:
            print("You missed.")
        elif result==1:
            cprint("You hit a ship!", "yellow", "on_blue")
        elif result==2:
            cprint("You sank the ship!", "yellow", "on_red")
        elif result==3:
            cprint("You sank the ship and won the battle.", "yellow", "on_red")
        elif result==-1:
            cprint("You shot at a coordinate you tried alreayd...", "yellow", "on_blue")
        self.fields[1].process_result(result, ix, iy)
        self.draw()
        return result

    def defend(self):
        message = [DEFEND]
        self.zmq.send(message)
        response = self.zmq.receive()
        assert response[0] == DEFEND
        x, y = response[1:]
        ix, iy = self._convert_to_indices(x, y)
        result = self.fields[0].check_attacked_coordinates(ix, iy)
        message = [DEFEND_REQ_RESULT, "%d" %(result)]
        self.zmq.send(message)
        response = self.zmq.receive()
        if result==0:
            print("Opponent missed.")
        elif result==1:
            print("Opponent hit your ship.")
        elif result==2:
            print("Opponent sank your ship.")
        elif result==3:
            print("Opponent sank your ship and won the battle.")
        elif result==-1:
            print("Opponent missed.")

        self.fields[0].process_result(result, ix, iy)
        self.draw()
        return result

    
        
class Field():
    SIZE=10
    SYMBOLS = dict(water='≈',ship='⊡',hit='⊛',sunk='◌', missed='⊙')
    FGCOLORS = dict(water='grey', ship='white', hit='red', sunk='green', missed='yellow')
    BGCOLORS = dict(water='on_blue', ship='on_blue', hit='on_yellow', sunk='on_yellow', missed='on_blue')
    
    SHIPS = (2, 3, 3, 4, 5)
    #SHIPS = (2,)
    def __init__(self):
        self.F = np.zeros((Field.SIZE, Field.SIZE), int)
        self.ships = []
        self.hits = [0 for i in Field.SHIPS]
        
    def add(self, X,Y, ship, direction):
        x=X-1
        y=Y-1
        if ship in self.ships:
            raise ValueError('Ship already placed')
        size = Field.SHIPS[ship]
        dm = dict(R=(1,0), D=(0,1), L=(-1,0), U=(0,-1))
        d, r= dm[direction]
        s = []
        for i in range(size):
            ix, iy  = x + r*i, y +d * i
            if ix<0 or ix==Field.SIZE or iy<0 or iy==Field.SIZE:
                raise ValueError('Ship out of domain')
            if self.F[ix, iy]:
                raise ValueError('Overlapping ships')
            s.append((ix,iy))
        for ix, iy in s:
            self.F[ix, iy] = ship + 1
        self.ships.append(ship)
        
    def mark(self, X,Y, value):
        self.F[X,Y] = value
        
    def draw(self, row):
        print(f"{chr(65+row)} ", end='')
        for i in range(Field.SIZE):
            s = self.F[row,i]
            if s==0:
                symbol = "water"
            elif s>0:
                symbol = "ship"
            elif s==-1:
                symbol = "missed"
            elif s==-2:
                symbol = "hit"
            elif s==-3:
                symbol = "sunk"
            c = Field.SYMBOLS[symbol]
            fg = Field.FGCOLORS[symbol]
            bg = Field.BGCOLORS[symbol]
            cprint(" ", fg, "on_blue", end='')
            cprint(c, fg, bg, end='')
            cprint(" ", fg, bg, end='')
            
    def check_attacked_coordinates(self, ix, iy):
        cell = self.F[ix, iy]
        if cell == -1 or cell == -2:
            r = -1 # already hit: tell them they missed.
        elif cell ==0:
            r = 0 # missed
        else: #
            ship = cell -1 # 0 is empty 1 is ship0, 2 is ship1 etc.
            self.hits[ship]+=1
            if self.hits[ship] == Field.SHIPS[ship]:
                r=2 # ship sunk
            else:
                r=1 # ship hit
            if all([self.hits[i]==S for i, S in enumerate(Field.SHIPS)]):
                r=3 # all ships hit
        return r

    def process_result(self, result, ix, iy):
        if result==0:
            self.mark(ix, iy,-1)
        elif result==1:
            self.mark(ix, iy,-2)
        elif result==2:
            self.mark(ix, iy,-2)
        elif result==3:
            self.mark(ix, iy,-3)


class UI:

    def __init__(self, player, mine):
        self.player = player
        self.mine = mine

    def add_ships(self):
        print("You are about to place your ships.")
        print("I will tell you the length of the ship.")
        print("You choose a start coordinate, for example 'D 3'.")
        print("And then the direction you want to place it:")
        print("R : to the right")
        print("L : to the left")
        print("U : up")
        print("D : down")
        print("")
        print("Good luck")
        print()
        input("Hit enter to continue...")
        
        for ship, length in enumerate(self.mine.SHIPS):
            self.player.draw()
            print(f"Place a ship of length {length}")
            while True:
                r = self._add_ship(ship)
                if r==0:
                    break
        print("You're done! Let the battle begin!")
        
    def _add_ship(self, ship):
        x,y, ix, iy = self.player.enter_coordinates()
        while True:
            ans = input("Orientation: ")
            direction = ans.strip().upper()
            if direction in "R L U D".split():
                break
            else:
                print("Entry not understood.")
        try:
            self.mine.add(ix+1, iy+1, ship, direction)
        except ValueError:
            print("Could not place ship. Out of domain or on top of another ship.")
            return -1
        else:
            return 0

    def play(self):
        self.player.draw()
        if self.player.player_id == '0':
            role = ATTACKER
        else:
            role = DEFENDER

        while True:
            if role == ATTACKER:
                end_of_game = self.player.attack()
                role = DEFENDER
            else:
                end_of_game = self.player.defend()
                role = ATTACKER
            if end_of_game==3:
                break
        self.player.logout()


def main():
    description='''
Battleships client

    A client program to play the classic game Battleships.

'''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('HOSTNAME', nargs='?', default=HOST, help=f'Hostname or IP address of the Battleships server. Defaults to "{HOST}".')
    parser.add_argument('--debug', action='store_true')
    
    args = parser.parse_args()
    host = args.HOSTNAME

    if args.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    fmt = "[%(levelname)6s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=fmt)
    logger.setLevel(loglevel)

    mine = Field()
    enemy = Field()

    player = Player(mine, enemy)
    try:
        player.login(host, PORT)
    except ValueError:
        pass
    else:
        ui = UI(player, mine)
        ui.add_ships()
        ui.play()

