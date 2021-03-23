import block
import transaction

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
            addrsBytes = self.__GetAddrsMsg()
            clientSock.Send('Addrs', addrsBytes) 
            if msg:
                (hostname, port) = self.__GetServerAddrFromMsg(msg)
                self.controller.AddPeer(hostname, port)

    def _GetMempool(self, clientSock, clientAddress, msgType, msg):
        #TODO: get random sample
        mempoolBytes = self.__GetMempoolMsg()
        clientSock.Send('Mempool', mempoolBytes)

    def _AddBlock(self, clientSock, clientAddress, msgType, msg):
        if not msg:
            return
        
        bl = block.DecodeBlock(msg)
        self.controller.blockchain.AddBlock(bl)
        
    def _SyncBlocks(self, clientSock, clientAddress, msgType, msg):
        if not msg or len(msg) != utils.INT_BYTE_LEN:
            clientSock.Send('HashesNO')
            return

        theirHeight = utils.BytesToInt(msg)
        height = self.controller.blockchain.GetHeight()

        if height < theirHeight:
            clientSock.Send('HashesNO')
            return

        chain = []
        for b in self.controller.blockchain.GetHighestChain():
            chain.append(b.GetHash())
        
        msg = self.__GetBlockAddrsMessage(chain)
        clientSock.Send('Hashes', msg)

    def _GetBlocks(self, clientSock, clientAddress, msgType, msg):
        msgLen = len(msg)

        start = 0
        end = utils.INT_BYTE_LEN
        if not msg or msgLen < end:
            clientSock.Send('BlocksNo')
            return
        
        numHashes = utils.BytesToInt(msg[start:end])
        start = end
        end += numHashes * utils.HASH_BYTE_LEN
        if numHashes < 1 or msgLen != end:
            clientSock.Send('BlocksNo')
            return

        blocksMsg = utils.IntToBytes(numHashes)
        step = utils.HASH_BYTE_LEN
        for i in range(start, end, step):
            blockHash = msg[i:i+step]
            b = self.controller.blockchain.GetBlock(blockHash)
            if b is None:
                # TODO: currently bails if block not found
                clientSock.Send('BlocksNo')
                return

            blocksMsg += block.EncodeBlock(b)

        clientSock.Send('Blocks', blocksMsg)

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

    def __GetAddrsMsg(self):
        addrs = self.controller.GetPeerAddrs()
        addrsBytes = b''
        for addr in addrs:
            if (addrsBytes) : addrsBytes += b';'
            addrsBytes += ('%s:%d' % addr).encode()
        return addrsBytes

    def __GetMempoolMsg(self):
        msg = b''
        numTx = 0
        for tx in self.controller.blockchain.GetMempoolTransactions():
            txBytes = transaction.EncodeTx(tx)
            if txBytes:
                msg += txBytes
                numTx += 1        

        return utils.IntToBytes(numTx) + msg

    def __GetServerAddrFromMsg(self, msg):
        (hostname, port) = msg.decode().split(':')
        return (hostname, int(port))

    def __GetBlockAddrsMessage(self, chain):
        height = utils.IntToBytes(len(chain))
        numHashes = height #TODO: slice hashes into different messages?
        msg = height + numHashes

        for hash in reversed(chain):
            msg += hash
        
        return msg

