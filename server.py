import utils
import network

class Server(network.Server):
    def __init__(self, port, controller):
        super().__init__(port)
        self.controller = controller

    ### Message Methods ###

    def _Version(self, clientSock, clientAddress, msgType, msg):
        peerVersion = utils.BytesToInt(msg)
        if self.controller.ValidateVersion(peerVersion):
            version = self.controller.GetVersion()
            clientSock.Send('VersionOK', utils.IntToBytes(version))
        else:
            clientSock.Send('VersionNO')

    def _GetAddrs(self, clientSock, clientAddress, msgType, msg):
            addrsBytes = self.__GetAddrsBytes()
            clientSock.Send('Addrs', addrsBytes) 
            if msg:
                (hostname, port) = self.__GetServerAddrFromMsg(msg)
                self.controller.AddPeer(hostname, port)

    def _Close(self, clientSock, clientAddress, msgType, msg):
        
        if msg :
            (hostname, port) = self.__GetServerAddrFromMsg(msg)
            self.controller.RemovePeer(hostname, port)
        clientSock.Close()

    def _Stop(self, clientSock, clientAddress, msgType, msg):
            clientSock.Send('Bye!')
            clientSock.Close()
            self.Stop()

    #######################

    def __GetAddrsBytes(self):
        addrs = self.controller.GetPeerAddrs()
        addrsBytes = b''
        for addr in addrs:
            if (addrsBytes) : addrsBytes += b';'
            addrsBytes += ('%s:%d' % addr).encode()
        return addrsBytes

    def __GetServerAddrFromMsg(self, msg):
        (hostname, port) = msg.decode().split(':')
        return (hostname, int(port))
