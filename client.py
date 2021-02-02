import block
import transaction

import utils
import network

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

    ### Message Methods ###

    def Version(self):
        version = self.controller.GetVersion()
        if not self.Send('Version', utils.IntToBytes(version)):
            return None
        msgType, msg = self.Receive()
        if  msgType == 'VersionOK':
            return utils.BytesToInt(msg)
        return None

    def GetAddrs(self):
        addrs = []

        if not self.Send('GetAddrs', self.__GetServerAddrMsg()):
            return addrs
        
        msgType, msg = self.Receive()
        if msgType == 'Addrs' and msg:
            addrsStr = msg.decode().split(';')
            for addrStr in addrsStr:
                (hostname, port) = tuple(addrStr.split(':'))
                port = int(port)
                addrs.append((hostname, port))

        return addrs

    def GetMempool(self):
        mempool = []
        
        if not self.Send('GetMempool'):
            return mempool

        msgType, msg = self.Receive()
        if msgType == 'Mempool' and msg:
            pos = 4
            numTx = utils.BytesToInt(msg[:pos])
            for _i in range(numTx):
                nextPos = pos + transaction.MSG_LEN
                tx = transaction.DecodeTx(msg[pos:nextPos])
                mempool.append(tx)
                pos = nextPos

        return mempool

    def AddBlock(self, bl):
        blBytes = block.EncodeBlock(bl)
        if not blBytes:
            return False

        if not self.Send('AddBlock', blBytes):
            return False

        return True

    def Close(self):
        self.Send('Close', self.__GetServerAddrMsg())
        super().Close()

    #######################

    def __GetServerAddrMsg(self):
        if self.controller.server:
            serverPort = self.controller.server.port
            return ("%s:%d" % (network.GetHostname(), serverPort)).encode()
        return b''
