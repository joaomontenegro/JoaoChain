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
            return []

        msgType, msg = self.Receive()
        if msgType == 'Mempool' and msg and len(msg) >= 4:
            pos = 4
            numTx = utils.BytesToInt(msg[:pos])
            if len(msg) != 4 + numTx * transaction.MSG_LEN:
                return []
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

    def SyncBlocks(self, height):
        # Send msg
        if self.Send('SyncBlocks', utils.IntToBytes(height)): # TODO: server._SyncBlocks()
            return None

        # Receive response
        msgType, msg = self.Receive()
        msgLen = len(msg)
        if msgType == "Blocks" and msg and msgLen < 4:
            return None
        
        # Get peer height
        peerHeight = utils.BytesToInt(msg[:4])
        if peerHeight <= height or msgLen < 8:
            return

        # Get number of hashes
        numHashes = utils.BytesToInt(msg[4:8])
        if msgLen != 8 + 32 * numHashes:
            return None

        # Get hashes
        hashes = []
        for i in range(8, msgLen, 32):
            hashes.append(msg[i:i + 32])
        
        return peerHeight, hashes

    def Close(self):
        serverAddr = b''
        if self.controller.server:
            serverPort = self.controller.server.port
            serverAddr = ("%s:%d" % (network.GetHostname(), serverPort)).encode()

        self.Send('Close', serverAddr)
        super().Close()
s