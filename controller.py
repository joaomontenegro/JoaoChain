import blockchain
import network
import utils

import threading
import time

VERSION = 1
INITIAL_ADDRS = [("PORTO", 5001)]
DEFAULT_SERVER_PORT = 5002
MAIN_LOOP_SLEEP = 0.1
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

    def Start(self, startClients, startServer=True, serverPort=DEFAULT_SERVER_PORT):
        if self.isRunning:
            return
        
        self.isRunning = True

        if startServer:
            Log("Starting server")
            self.server = PeerServer(serverPort, self)
            self.serverThread = threading.Thread(name='Server', target=self.server.Start)
            self.serverThread.start()

        try:
            # Main Loop
            while True:
                if startClients:
                    self._MainLoopStep()
                time.sleep(MAIN_LOOP_SLEEP)
        except:
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

    def _MainLoopStep(self):
        Log("Step...")
        
        if not self.isRunning:
            return

        # TODO less frequent?
        self._UpdatePeers()

        #todo: ask for blocks / send new blocks?

        return True

    def _HasClient(self, hostname, port):
        for client in self.clients:
            if client.hostname == hostname and client.port == port:
                return True
        return False

    def _AddPeer(self, hostname, port):
        #todo protect threading
        Log("Adding:%s:%d" % (hostname, port))
        if not self._HasClient(hostname, port):
            client = PeerClient(hostname, port)
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

    def _AddInitialPeers(self):
        for addr in INITIAL_ADDRS:
            hostname, port = addr
            self._AddPeer(hostname, port)

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
                self._AddPeer(hostname, port)
                if len(self.clients) >= NUM_PEERS:
                    return


class PeerClient(network.Client):
    def __init__(self, hostname, port):
        super().__init__(hostname, port)
        self.failedAttempts = 0

    def Connect(self):
        success = super().Connect()
        if not success:
            self.failedAttempts += 1
        else:
            self.failedAttempts = 0
        return success

    def Version(self):
        self.sock.Send('Version', utils.IntToBytes(VERSION))
        msgType, msg = self.sock.Receive()
        if  msgType == 'VersionOK':
            return utils.BytesToInt(msg)
        return None

    def GetAddrs(self):
        self.sock.Send('GetAddrs')
        msgType, msg = self.sock.Receive()
        addrs = []
        if  msgType == 'Addrs' and msg:
            addrsStr = msg.decode().split(';')
            for addrStr in addrsStr:
                (hostname, port) = tuple(addrStr.split(':'))
                port = int(port)
                addrs.append((hostname, port))

        return addrs

    def Close(self):
        self.sock.Send('Close')
        super().Close()

    def Stop(self):
        self.sock.Send('Stop')
        msgType, _msg = self.sock.Receive()
        return msgType == 'Bye!'


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
            self._GetAddrs(clientSock)

        if msgType == 'Close':
            clientSock.Close()

        elif msgType == 'Stop':
            clientSock.Send('Bye!')
            clientSock.Close()
            self.Stop()

    def _GetAddrs(self, clientSock):
        addrs = self.controller.GetPeerAddrs()
        addrsBytes = b''
        for addr in addrs:
            if (addrsBytes) : addrsBytes += b';'
            addrsBytes += ('%s:%d' % addr).encode()

        clientSock.Send('Addrs', addrsBytes) 



if __name__ == '__main__':
    import sys

    c = Controller()

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        c.Start(False, True, 5001)
    else:    
        #port = int(sys.argv[1])
        c.Start(True, False)
    
