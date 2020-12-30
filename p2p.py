# Setup Server
   # Version
   # Addresses
# Find Peers
# Create Clients for peers
# Shake hands with version
# Ask for other peer addresses known to them
# Create Clients for those peers too

import network

INITIAL_ADDRS = ["127.0.0.1:5001", "127.0.0.1:5002"]

class PeerClient(network.Client):
    def __init__(self, hostname, port):
        super().__init__(hostname, port)

        self.version = 1
        pass

    def Version(self):
        self.sock.Send('Version', network.IntToBytes(self.version))
        msgType, msg = self.sock.Receive()
        if  msgType == 'VersionOK':
            return network.BytesToInt(msg)
        return None

    def GetAddrs(self):
        self.sock.Send('GetAddrs')
        msgType, msg = self.sock.Receive()
        if  msgType == 'Addrs':
            return msg.decode().split(';')
        return None

    def Close(self):
        self.sock.Send('Close')
        super().Close()

    def Stop(self):
        self.sock.Send('Stop')
        msgType, _msg = self.sock.Receive()
        return msgType == 'Bye!'


class PeerServer(network.Server):
    def __init__(self, port, peerManager):
        super().__init__(port)

        self.version = 1
        self.peerManager = peerManager

    def ProcessMessage(self, msgType, msg, clientSock):
        if msgType == 'Version':
            if network.BytesToInt(msg) == self.version:
                clientSock.Send('VersionOK', network.IntToBytes(self.version))
            else:
                clientSock.Send('VersionNO')

        elif msgType == 'GetAddrs':
            peerAddrs = self.peerManager.GetPeerAddrs()
            addrsBytes = ';'.join(peerAddrs).encode()
            clientSock.Send('Addrs', addrsBytes) 

        if msgType == 'Close':
            clientSock.Close()

        elif msgType == 'Stop':
            clientSock.Send('Bye!')
            clientSock.Close()
            self.Stop()
    

class PeerManager:
    def __init__(self):
        self.peerAddrs = list(INITIAL_ADDRS)

    def GetPeerAddrs(self):
        return list(self.peerAddrs)


if __name__ == '__main__':
    import sys

    ok = False

    if len(sys.argv) > 1:
        if sys.argv[1] == 'server':
            ok = True
            peerManager = PeerManager()
            server = PeerServer(5001, peerManager)
            server.Start()

        elif sys.argv[1] == 'client':
            ok = True
            client = PeerClient(network.GetHostname(), 5001)
            client.Connect()
            print ('Version:',  client.Version())
            print ('GetAddrs: ', client.GetAddrs())
            client.Close()

        elif sys.argv[1] == 'stop':
            ok = True
            client = PeerClient(network.GetHostname(), 5001)
            client.Connect()
            client.Stop()

    if not ok:
        print("Usage: %s [server|client|stop]" % sys.argv[0])

