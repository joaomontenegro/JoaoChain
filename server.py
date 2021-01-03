import utils
import network

VERSION = 1

class Server(network.Server):
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
