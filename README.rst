Battleships (game)
==================

Synopsis
--------

Battleships is a quick implementation of the classic two player
game. I wrote the program to play the game with my daughter, and I
wanted to have a functional version coded within one day. (It became
two...)

How to play
-----------

The game is played between two (real) players. For practical reasons
each player should have access to her/his own laptop/pc, and both
computers should be networked and be able to reach each other.

The architecture of the game is that two clients fire at each others
ships in turns, where the communication between the clients is handled
by a dedicated server. I used for this zmq/asyncio to implement a
server that can handle the REQ-REP pattern of multiple clients
concurrently. To find out how that works was my personal aim of this
little project.

The UserInterface of the clients, is admittedly, fairly basic, and
there lots of approaches to make it more fancy. Fancy or not, it does
not matter; we had fun playing it anyway.

How to install
--------------

I suggest installing the package with pip. From the top directory of
the source code:

`pip install --user .`

This should take care of any dependencies.

Let's try it!
-------------

One of the players will be tasked with starting the server. The
current implementation can handle two players. If more players try to
connect, they are politely refused. The first player to login
(connect) starts the game.

But first things first, start the server:

`$ battleships_server`

A server instance is now started that listens to port 9002. If this
port is already taken you can change it in the source code
(battleships/battleships_data.py). Make a note of the hostname or IP
address of the machine on which the server is started.

The client programs can now be started as

`$ battleships`

or

`$ battleships some_host_name`

In the first case, the client will connect to the server running on
localhost; in the second case, a connection will be made to the host
supplied as first argument. Instead of a hostname, you can also use IP
numbers.

Setting up ships
----------------
First action to take is to set up your ships. The game knows about  5
ships:

+---+-------------+
| 1 | 2 positions |
+---+-------------+
| 2 | 3 positions |
+---+-------------+
| 3 | 3 positions |
+---+-------------+
| 4 | 4 positions |
+---+-------------+
| 5 | 5 positions |
+---+-------------+

and they are to be set up in this order. Two empty fields are shown,
one is the "sea" where the player's ships are (going to be placed) and
the other is where the enemy player's ships will be. The
client-program asks the player for coordinates (such as "A 4") after
stating the size of the ship. Then, the player needs to type the
direction, represented by one of the following characters:

+---+------------------+
| R | horizontal right |
+---+------------------+
| L | horizontal left  |
+---+------------------+
| D | vertical down    |
+---+------------------+
| U | vertical up      |
+---+------------------+

The location of the ships is indicated with symbols.

The process is repeated until all 5 ships are placed. It is not
possible to place a ship that is (partially) out the domain or
overlaps with another ship.

When both players have setup their ships, the player how logged in
first gets to shoot first. She or he will be asked to enter
coordinates. The result of the attempt is shown in the "enemy" sea, as
well as in hers/his "sea" at the opponents end. Then, the other player
gets a chance to shoot, and roles are switched until one player has
managed to sink all the ships. Both players are logged out, and can
start again a new session.
