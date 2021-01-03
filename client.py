import utils
import network

VERSION = 1

class Client(network.Client):
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