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
        
    def _SyncBlockHashes(self, clientSock, clientAddress, msgType, msg):
        if not msg or len(msg) != 4:
            return

        theirHeight = utils.BytesToInt(msg)
        height = self.controller.blockchain.GetHeight()

        if height < theirHeight:
            clientSock.Send('HashesNO')
            return

        chain = self.controller.blockchain.GetChain()
        msg = self.__GetBlockAddrsMessage(chain)
        clientSock.Send('Hashes', msg)

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

        return utils.IntToBytes(numTx, 4) + msg

    def __GetServerAddrFromMsg(self, msg):
        (hostname, port) = msg.decode().split(':')
        return (hostname, int(port))

    def __GetBlockAddrsMessage(self, chain):
        msg = b''
        for hash in chain:
            msg += hash
        
        return msg

