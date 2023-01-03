import asyncio
import random
import zmq
import zmq.asyncio

from battleships_data import *

import logging

logger = logging.getLogger(__name__)


async def client_task(name):
    """Basic request-reply client using REQ socket."""

    # let's wait for some random time.
    t = random.random()*2
    logger.debug(f"Client starts in {t} secs")
    await asyncio.sleep(t)
    logger.debug(f"Going to log in")
    socket = zmq.asyncio.Context().socket(zmq.REQ)
    socket.identity = u"Client-{}".format(name).encode("ascii")
    socket.connect("tcp://%s:%s" % (HOST, PORT))

    # log in and get an id.

    message = Server.enc([LOGIN, name])
    socket.send_multipart(message)
    message = await socket.recv_multipart()
    message = Server.dec(message)
    assert message[0]==LOGIN
    if message[1]==LOGIN_ERROR:
        logger.error(f"Player {name} cannot log in because too many players.")
        return
    
    ident = int(message[2])
    logger.info(f"Client {name} logged in as player {ident}")

    # CLient has been logged in successfully. Now let's play.

    for turn in range(2):
        # Send request, get reply
        if ident == 0:
            message = Server.enc([ATTACK, "A", "5"])
        else:
            message = Server.enc([DEFEND])
        socket.send_multipart(message)
        logger.debug(f"Request ({message})sent by {name}/{ident}")
        reply = await socket.recv_multipart()
        reply = Server.dec(reply)
        if ident == 0:
            assert reply[0] == ATTACK
        else:
            assert reply[0] == DEFEND
        logger.debug(f"Reply received by client {name}/{ident} : {reply}.")
        # Send request, get reply
        if ident == 1:
            message = [ATTACK_REQ_RESULT]
        else:
            result = random.randint(-1, 4)
            message = [DEFEND_REQ_RESULT, "%d" % (result)]
        message = Server.enc(message)
        socket.send_multipart(message)
        logger.debug(f"Request sent by {name}/{ident} : {message}")
        reply = await socket.recv_multipart()
        reply = Server.dec(reply)
        logger.info(f"Client {name} ({ident}) received: {reply[1]}")
        ident +=1
        ident %=2
        
        
class Server():

    def __init__(self):
        self.context = zmq.asyncio.Context.instance()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind("tcp://*:%s" % (PORT))


        # Initialize main loop state
        self.poller = zmq.asyncio.Poller()
        self.poller.register(self.frontend, zmq.POLLIN)
        self.Q_defender = asyncio.Queue()
        self.Q_attacker = asyncio.Queue()
        self.client_attacker = None
        self.client_defender = None
        logger.info("Zeeslag server started...")
        
    @classmethod    
    def enc(cls, message):
        return [i.encode() for i in message]

    @classmethod
    def dec(cls, message):
        return [i.decode() for i in message]



        
    def start_test_clients(self):
        names = ["leonie", "lucas"] #, "luisa"]
        tasks = []
        for i in names:
            tasks.append(asyncio.create_task(client_task(i)))

        
    async def send_coordinates_to_defender(self, request):
        # Wait until defender said she is ready
        logger.debug("Waiting for defender to get ready...")
        cmd, value = await self.Q_attacker.get()
        assert cmd==STATUS and value==READY
        logger.debug("Defender appearst to be ready.")
        x = request[1]
        y = request[2]
        logger.debug(f"Will send the coords {x}, {y} to defender")
        await self.Q_defender.put((COORDS, (x,y)))
        # notify the attacker the coords are sent.
        client = self.client_attacker
        reply = Server.enc([ATTACK, OK])
        logger.debug("Notify attacker coordinates are sent.")
        self.frontend.send_multipart([client, b"", *reply])
        logger.debug("END of send_coordinates")

    async def recv_coordinates_from_attacker(self):
        # Tell attacker we're ready to receive.
        logger.debug("Tell attacker defender is ready")
        await self.Q_attacker.put((STATUS,READY))
        logger.debug("Defender ready, and waiting for coordinates.")
        # Wait for the coordinates:
        cmd, value = await self.Q_defender.get()
        assert cmd == COORDS
        logger.debug(f"Received the coordinates {value}")
        # Send the coordinates to the defender
        client = self.client_defender
        reply = Server.enc([DEFEND, *value])
        logger.debug(f"Reply to defender: {reply}")
        self.frontend.send_multipart([client, b"", *reply])
        logger.debug("END of recv_coordinates")

    async def send_result_to_attacker(self):
        # Tell defender we're ready to receive.
        await self.Q_defender.put((STATUS,READY))
        logger.debug("Defender knows we're ready")
        cmd, value = await self.Q_attacker.get()
        assert cmd==DEFEND_REQ_RESULT
        reply = Server.enc([ATTACK_REQ_RESULT, value])
        client = self.client_attacker
        logger.debug(f"Reply to attacker : {reply}")
        self.frontend.send_multipart([client, b"", *reply])
        logger.debug("END of send_result_to_attacker")
        
    async def recv_result_from_defender(self, request):
        cmd, value = await self.Q_defender.get()
        assert cmd==STATUS and value==READY
        logger.debug(f"Attacker is ready to find out the result, sending {request}")
        await self.Q_attacker.put(request)
        # notify the defender the result is sent
        client = self.client_defender
        reply = Server.enc([DEFEND_REQ_RESULT, OK])
        logger.debug(f"Reply to defender: {reply}")
        self.frontend.send_multipart([client, b"", *reply])
        logger.debug("END of recv_result_from_defender")
        
    async def monitor_frontend(self, test=False):
        if test:
            self.start_test_clients()
        n_players = 0
        
        while True:
            sockets = dict(await self.poller.poll())
            if self.frontend in sockets:
                client, empty, *request = await self.frontend.recv_multipart()
                request = self.dec(request)
                
                if request[0] == LOGIN:
                    if n_players==2:
                        # already two players logged in.
                        reply = [LOGIN, LOGIN_ERROR, ""]
                        reply = self.enc(reply)
                        self.frontend.send_multipart([client, b"", *reply])
                    else:
                        reply = [LOGIN, LOGIN_OK, "%d"%(n_players)]
                        reply = self.enc(reply)
                        self.frontend.send_multipart([client, b"", *reply])
                        n_players+=1
                        logger.info(f"Player {request[1]} logged in.")
                        
                elif request[0] == ATTACK:
                    self.client_attacker = client
                    t = asyncio.create_task(self.send_coordinates_to_defender(request))
                elif request[0] == DEFEND:
                    self.client_defender = client
                    t = asyncio.create_task(self.recv_coordinates_from_attacker())
                elif request[0] == ATTACK_REQ_RESULT:
                    t = asyncio.create_task(self.send_result_to_attacker())
                elif request[0] == DEFEND_REQ_RESULT:
                    t = asyncio.create_task(self.recv_result_from_defender(request))
                elif request[0] == LOGOUT:
                    n_players-=1
                    reply = [LOGOUT, LOGOUT_OK, ""]
                    reply = self.enc(reply)
                    self.frontend.send_multipart([client, b"", *reply])
                    logger.info(f"Player {request[1]} logged out.")
                        
        # Clean up, but we don't get here anyway.
        self.frontend.close()
        self.context.term()


def main():        
    fmt = "[%(levelname)6s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=fmt)
    logger.setLevel(logging.INFO)        
    s = Server()
    asyncio.run(s.monitor_frontend(test=False))
