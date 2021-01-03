import blockchain
import network
import utils

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
        self.clients      = []
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
            self.server = PeerServer(serverPort, self)
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
        for client in self.clients:
            if client:
                addrs.append((client.hostname, client.port))
        return addrs

    def AddPeer(self, hostname, port):
        #todo protect threading
        if not self._HasClient(hostname, port) and not self._IsMe(hostname, port):
            client = PeerClient(hostname, port, self)
            if client.Connect():
                # Validate version
                peerVersion = client.Version()
                if peerVersion and self.ValidateVersion(peerVersion):
                    self.clients.append(client)
                    return True
                else:
                    client.Close()
                    Log("Invalid peer version:%d" % peerVersion)
        return False

    def RemovePeer(self, hostname, port):
        self.clients = [c for c in self.clients if not (c.hostname == hostname and c.port == port)]

    def _HasClient(self, hostname, port):
        for client in self.clients:
            if client.hostname == hostname and client.port == port:
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
        newClients = []
        
        for client in self.clients:
            if not client.IsConnected():
                if not client.Connect() and client.failedAttempts > 3:
                    Log("Dropping peer: %s" % client)
                    continue
            newClients.append(client)

        self.clients = newClients

    def _UpdatePeers(self):
        self._SanitizePeers()
        
        if not self.clients:
            Log("No peers: adding initial peers.")
            self._AddInitialPeers()

        if len(self.clients) >= NUM_PEERS:
            return

        for client in self.clients:
            addrs = client.GetAddrs()
            for addr in addrs:
                hostname, port = addr
                self.AddPeer(hostname, port)
                if len(self.clients) >= NUM_PEERS:
                    return


class PeerClient(network.Client):
    def __init__(self, hostname, port, controller):
        super().__init__(hostname, port)
        self.failedAttempts = 0
        self.controller = controller

    def Connect(self):
        success = super().Connect()
        if not success:
            self.failedAttempts += 1
        else:
            self.failedAttempts = 0
        return success

    def Version(self):
        if not self.Send('Version', utils.IntToBytes(VERSION)):
            return None
        msgType, msg = self.Receive()
        if  msgType == 'VersionOK':
            return utils.BytesToInt(msg)
        return None

    def GetAddrs(self):
        addrs = []

        # Get the server address
        if self.controller.server:
            serverPort = self.controller.server.port
            outMsg = ("%s:%d" % (network.GetHostname(), serverPort)).encode()
        else:
            outMsg = b''

        if not self.Send('GetAddrs', outMsg):
            return addrs        
        
        msgType, msg = self.Receive()
        if  msgType == 'Addrs' and msg:
            addrsStr = msg.decode().split(';')
            for addrStr in addrsStr:
                (hostname, port) = tuple(addrStr.split(':'))
                port = int(port)
                addrs.append((hostname, port))

        return addrs

    def Close(self):
        self.Send('Close')
        super().Close()


class PeerServer(network.Server):
    def __init__(self, port, controller):
        super().__init__(port)
        self.controller = controller

    def ProcessMessage(self, msgType, msg, clientSock):
        if msgType == 'Version':
            peerVersion = utils.BytesToInt(msg)
            if self.controller.ValidateVersion(peerVersion):
                clientSock.Send('VersionOK', utils.IntToBytes(VERSION))
            else:
                clientSock.Send('VersionNO')

        elif msgType == 'GetAddrs':
            addrsBytes = self._GetAddrsBytes(clientSock)
            clientSock.Send('Addrs', addrsBytes) 
            if msg:
                (hostname, port) = msg.decode().split(':')
                port = int(port)
                self.controller.AddPeer(hostname, port)

        if msgType == 'Close':
            clientSock.Close()

        elif msgType == 'Stop':
            clientSock.Send('Bye!')
            clientSock.Close()
            self.Stop()

    def _GetAddrsBytes(self, clientSock):
        addrs = self.controller.GetPeerAddrs()
        addrsBytes = b''
        for addr in addrs:
            if (addrsBytes) : addrsBytes += b';'
            addrsBytes += ('%s:%d' % addr).encode()
        return addrsBytes


if __name__ == '__main__':
    import sys

    c = Controller()

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        c.Start(True, 5001)
        
    else:    
        #port = int(sys.argv[1])
        c.Start(True, 5002)
    
