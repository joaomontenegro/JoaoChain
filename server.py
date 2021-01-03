import utils
import network

VERSION = 1

class Server(network.Server):
    def __init__(self, port, controller):
        super().__init__(port)
        self.controller = controller

    def _Version(self, clientSock, clientAddress, msgType, msg):
        peerVersion = utils.BytesToInt(msg)
        if self.controller.ValidateVersion(peerVersion):
            clientSock.Send('VersionOK', utils.IntToBytes(VERSION))
        else:
            clientSock.Send('VersionNO')

    def _GetAddrs(self, clientSock, clientAddress, msgType, msg):
            addrsBytes = self.__GetAddrsBytes(clientSock)
            clientSock.Send('Addrs', addrsBytes) 
            if msg:
                (hostname, port) = msg.decode().split(':')
                port = int(port)
                self.controller.AddPeer(hostname, port)

    def _Close(self, clientSock, clientAddress, msgType, msg):
            clientSock.Close()

    def _Stop(self, clientSock, clientAddress, msgType, msg):
            clientSock.Send('Bye!')
            clientSock.Close()
            self.Stop()

    def __GetAddrsBytes(self, clientSock):
        addrs = self.controller.GetPeerAddrs()
        addrsBytes = b''
        for addr in addrs:
            if (addrsBytes) : addrsBytes += b';'
            addrsBytes += ('%s:%d' % addr).encode()
        return addrsBytes
