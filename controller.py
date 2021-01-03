import utils
import network
import blockchain
import server
import client

import threading
import time

VERSION = 1
INITIAL_ADDRS = [("PORTO", 5001)]
DEFAULT_SERVER_PORT = 5001
MAIN_LOOP_TIME = 0.1
UPDATE_PEERS_TIME = 1.0
NUM_PEERS = 5

doLog = True
def Log(msg):
    if doLog:
        print(msg)

class Controller:
    def __init__(self):
        self.isRunning    = False
        self.blockchain   = blockchain.Blockchain()
        self.peers      = []
        self.server       = None
        self.serverThread = None

    def Start(self, startServer=True, serverPort=DEFAULT_SERVER_PORT):
        if self.isRunning:
            return
        
        self.isRunning = True
        timerMainLoop = utils.Timer(MAIN_LOOP_TIME)
        timerUpdatePeers = utils.Timer(UPDATE_PEERS_TIME)

        if startServer:
            Log("Starting server")
            self.server = server.Server(serverPort, self)
            self.serverThread = threading.Thread(name='Server', target=self.server.Start)
            self.serverThread.start()

        try:
            # Main Loop
            while True:
                if timerUpdatePeers.IsDone():
                    self._UpdatePeers()
                    timerUpdatePeers.Reset()
                    Log("My Peers: " + str(self.GetPeerAddrs()))
                
                # Sleep until main loop time has passed
                timerMainLoop.SleepUntilDone()
                timerMainLoop.Reset()
        except:
            if startServer:
                self.server.Stop()
                self.serverThread.join()
            raise

    def ValidateVersion(self, version):
        return version == VERSION

    def GetPeerAddrs(self):
        # todo protect from threadding?
        addrs = []
        for peer in self.peers:
            if peer:
                addrs.append((peer.hostname, peer.port))
        return addrs

    def AddPeer(self, hostname, port):
        #todo protect threading
        if not self._HasPeer(hostname, port) and not self._IsMe(hostname, port):
            peer = client.Client(hostname, port, self)
            if peer.Connect():
                # Validate version
                peerVersion = peer.Version()
                if peerVersion and self.ValidateVersion(peerVersion):
                    self.peers.append(peer)
                    return True
                else:
                    peer.Close()
                    Log("Invalid peer version:%d" % peerVersion)
        return False

    def RemovePeer(self, hostname, port):
        print("Removing peer: %s:%d" % (hostname, port))
        self.peers = [c for c in self.peers if not (c.hostname == hostname and c.port == port)]

    def _HasPeer(self, hostname, port):
        for peer in self.peers:
            if peer.hostname == hostname and peer.port == port:
                return True
        return False

    def _IsMe(self, hostname, port):
        return (self.server and
                    hostname in (network.GetHostname(), 'localhost', '127.0.0.1') and
                    port == self.server.port)
            

    def _AddInitialPeers(self):
        for addr in INITIAL_ADDRS:
            hostname, port = addr
            self.AddPeer(hostname, port)

    def _SanitizePeers(self):
        newPeers = []
        
        for peer in self.peers:
            if not peer.IsConnected():
                if not peer.Connect() and peer.failedAttempts > 3:
                    Log("Dropping peer: %s" % peer)
                    continue
            newPeers.append(peer)

        self.peers = newPeers

    def _UpdatePeers(self):
        self._SanitizePeers()
        
        if not self.peers:
            Log("No peers: adding initial peers.")
            self._AddInitialPeers()

        if len(self.peers) >= NUM_PEERS:
            return

        for peer in self.peers:
            addrs = peer.GetAddrs()
            for addr in addrs:
                hostname, port = addr
                self.AddPeer(hostname, port)
                if len(self.peers) >= NUM_PEERS:
                    return

if __name__ == '__main__':
    import sys

    c = Controller()

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        c.Start(True, 5001)
        
    else:    
        #port = int(sys.argv[1])
        c.Start(True, 5002)
    
