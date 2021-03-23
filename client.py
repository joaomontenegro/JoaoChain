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
        if msgType == 'Mempool' and msg and len(msg) >= utils.INT_BYTE_LEN:
            start = 0
            end = utils.INT_BYTE_LEN
            numTx = utils.BytesToInt(msg[start:end])
            
            start = end
            end += numTx * transaction.MSG_LEN
            if len(msg) != end:
                return []
            
            for i in range(start, end, transaction.MSG_LEN):
                tx = transaction.DecodeTx(msg[i:i+transaction.MSG_LEN])
                mempool.append(tx)

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
        if not self.Send('SyncBlocks', utils.IntToBytes(height)):
            return 0, None

        # Receive response
        msgType, msg = self.Receive()
        if msg:
            msgLen = len(msg)
        else:
            msgLen = 0
        if msgType != "Hashes" or not msg:
            return 0, None

        # Get peer height
        start = 0
        end = utils.INT_BYTE_LEN
        if msgLen < end:
            return 0, None
        peerHeight = utils.BytesToInt(msg[start:end])
        if peerHeight <= height:
            return 0, None

        # Get number of hashes
        start = end
        end += utils.INT_BYTE_LEN
        if msgLen < end:
            return 0, None
        numHashes = utils.BytesToInt(msg[start:end])

        start = end
        if msgLen != end + utils.HASH_BYTE_LEN * numHashes:
            return 0, None

        # Get hashes
        hashes = []
        step = utils.HASH_BYTE_LEN
        for i in range(start, msgLen, step):
            hashes.append(msg[i:i+step])

        return peerHeight, hashes

    def GetBlocks(self, blockHashes):
        # Send msg
        outMsg = utils.IntToBytes(len(blockHashes))
        for blockHash in blockHashes:
            outMsg += blockHash
        
        if not self.Send('GetBlocks', outMsg):
            return None

        # Receive response
        msgType, msg = self.Receive()
        msgLen = len(msg)
        if msgType == "Blocks" and msg and msgLen < utils.INT_BYTE_LEN:
            return None

        numBlocks = utils.BytesToInt(msg[:utils.INT_BYTE_LEN])
        blocks = []
        start = utils.INT_BYTE_LEN
        for _ in range(numBlocks):
            if start >= len(msg):
                return None
            
            b = block.DecodeBlock(msg[start:])
            if b is None:
                return []
            
            blocks.append(b)
            start += b.byteSize
        
        return blocks

    def Close(self):
        self.Send('Close', self.__GetServerAddrMsg())
        super().Close()

    #######################
   
    def __GetServerAddrMsg(self):
        if self.controller.server:
            serverPort = self.controller.server.port
            return ("%s:%d" % (network.GetHostname(), serverPort)).encode()
        return b''
