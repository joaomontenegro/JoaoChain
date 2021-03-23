import utils
import network
import blockchain
import server
import client
import rpc

import hashlib
import threading
import time
import random

# TODO: add a config
VERSION = 1
#INITIAL_ADDRS = [("PORTO", 5001)]
INITIAL_ADDRS = [("PORTO", 5001), ("18.217.77.113", 5001)]
DEFAULT_SERVER_PORT = 5001
DEFAULT_RPC_PORT = 4001
MAIN_LOOP_TIME = 0.1
UPDATE_PEERS_TIME = 5
UPDATE_MEMPOOL_TIME = 1
CLEAN_MEMPOOL_TIME = 60
CLEAN_MEMPOOL_MINUTES_AGO = 60 * 60
SYNC_BLOCKCHAIN_TIME = 10.0
NUM_PEERS = 5 # TODO: find a way of not limiting the size of the network!!!
DIFFICULTY = 5

doLog = True
def Log(msg):
    if doLog:
        print(msg)

class Controller:
    def __init__(self, minerAddr=None, privateKey=None):
        self.isRunning    = False
        self.blockchain   = blockchain.Blockchain(DIFFICULTY)
        self.peers        = []
        self.server       = None
        self.serverThread = None
        self.rpc          = None
        self.rpcThread    = None
        self.minerAddr    = minerAddr
        self.privateKey   = privateKey # TODO: use a callback that safely decrypts and returns the private key
        self.minedBlock   = None
        self.minerThread  = None
        self.peerLock     = threading.Lock()

        if minerAddr and not privateKey:
            raise ValueError("Miner Address set but private key not specified!")

    def GetVersion(self):
        return VERSION

    def IsMiner(self):
        return self.minerAddr is not None

    def IsMining(self):
        return self.minerThread is not None

    def Start(self, startServer=True, serverPort=DEFAULT_SERVER_PORT,
              startRPC=False, rpcPort=DEFAULT_RPC_PORT):
        if self.isRunning:
            return

        if self.minerAddr:
            Log("Miner Address: %s" % utils.Shorten(self.minerAddr))
        
        self.isRunning      = True
        timerMainLoop       = utils.Timer(MAIN_LOOP_TIME)
        timerUpdatePeers    = utils.Timer(UPDATE_PEERS_TIME, startDone=True)
        timerUpdateMempool  = utils.Timer(UPDATE_MEMPOOL_TIME)
        timerCleanMempool   = utils.Timer(CLEAN_MEMPOOL_TIME)
        timerSyncBlocks     = utils.Timer(SYNC_BLOCKCHAIN_TIME, startDone=True)

        if startServer:
            Log("Starting server")
            self.server = server.Server(serverPort, self)
            self.serverThread = threading.Thread(name='Server', target=self.server.Start)
            self.serverThread.start()

        if startRPC:
            Log("Starting RPC server")
            self.rpc = rpc.RPCServer(rpcPort, self)
            self.rpcThread = threading.Thread(name='RPCServer', target=self.rpc.Start)
            self.rpcThread.start()

        try:
            # Main Loop
            while True:
                # Update Peers
                if timerUpdatePeers.IsDone():
                    self._UpdatePeers()
                    timerUpdatePeers.Reset()
                    #Log("My Peers: " + str(self.GetPeerAddrs()))

                # Update mempool
                if timerUpdateMempool.IsDone():
                    self._UpdateMempool()
                    timerUpdateMempool.Reset()
                    Log("My Mempool: " + str(len(self.blockchain.mempool)))

                # Cleanup the mempool
                if timerCleanMempool.IsDone():
                    self._CleanMempool()
                    timerCleanMempool.Reset()

                # Sync Blockchain with peers
                if timerSyncBlocks.IsDone():
                    self._SyncBlocks()
                    timerSyncBlocks.Reset()
                    Log("My Blocks: " + str(self.blockchain.GetHeight()))

                # Mine in a separate thread
                if self.IsMiner():
                    if not self.IsMining() and self.blockchain.HasMemPool():
                        self.minerThread = threading.Thread(name='Miner',
                                                            target=self._Mine)
                        self.minerThread.start()
                    elif self.minedBlock:
                        # Add block and broadcast it
                        if self.blockchain.AddBlock(self.minedBlock):
                            self._BroadcastBlock(self.minedBlock)
                        self.minerThread.join()
                        self.minerThread = None
                        self.minedBlock = None
                
                # Sleep until main loop time has passed
                timerMainLoop.SleepUntilDone()
                timerMainLoop.Reset()
        except:
            if self.serverThread and self.serverThread.is_alive():
                self.server.Stop()

            if self.rpcThread and self.rpcThread.is_alive():
                self.rpc.Stop()

            raise

    def ValidateVersion(self, version):
        return version == VERSION

    def GetPeerAddrs(self):
        with self.peerLock:
            return self._GetPeerAddrs()

    def AddPeer(self, hostname, port):
        with self.peerLock:
            if not self._HasPeer(hostname, port) and not self._IsMe(hostname, port):
                peer = client.Client(hostname, port, self)
                if peer.Connect():
                    # Validate version
                    peerVersion = peer.Version()
                    if peerVersion and self.ValidateVersion(peerVersion):
                        self.peers.append(peer)
                        Log("My Peers: %s"  % self._GetPeerAddrs())
                        return True
                    else:
                        peer.Close()
                        Log("Invalid peer version:%d" % peerVersion)
        return False

    def RemovePeer(self, hostname, port):
        with self.peerLock:
            Log("Removing peer: %s:%d" % (hostname, port))
            self.peers = [c for c in self.peers if not (c.hostname == hostname and c.port == port)]

    def _GetRandomPeer(self):
        if not self.peers:
            return None
        
        i = random.randrange(len(self.peers))
        return self.peers[i]

    def _HasPeer(self, hostname, port):
        for peer in self.peers:
            if peer.hostname == hostname and peer.port == port:
                return True
        return False

    def _GetPeerAddrs(self):
        addrs = []
        for peer in self.peers:
            if peer:
                addrs.append((peer.hostname, peer.port))
        return addrs

    def _IsMe(self, hostname, port):
        return (self.server and
                    hostname in (network.GetHostname(), 'localhost', '127.0.0.1') and
                    port == self.server.port)

    def _AddInitialPeers(self):
        for addr in INITIAL_ADDRS:
            hostname, port = addr
            self.AddPeer(hostname, port)

    def _SanitizePeers(self):
        newPeers = []
        
        for peer in self.peers:
            if not peer.IsConnected():
                if not peer.Connect() and peer.failedAttempts > 3:
                    Log("Dropping peer: %s" % peer)
                    continue
            newPeers.append(peer)

        self.peers = newPeers

    def _UpdatePeers(self):
        self._SanitizePeers()
        
        if not self.peers:
            #Log("No peers: adding initial peers.")
            self._AddInitialPeers()

        if len(self.peers) >= NUM_PEERS:
            return

        for peer in self.peers:
            addrs = peer.GetAddrs()
            for addr in addrs:
                hostname, port = addr
                self.AddPeer(hostname, port)
                if len(self.peers) >= NUM_PEERS:
                    return

    def _UpdateMempool(self):
        peer = self._GetRandomPeer()
        if not peer or not peer.IsConnected():
            return

        mempool = peer.GetMempool()
        for tx in mempool:
            self.blockchain.AddTransaction(tx)

    def _CleanMempool(self):
        timestamp = int(utils.GetCurrentTime() - 60 * CLEAN_MEMPOOL_MINUTES_AGO)
        self.blockchain.CleanMempool(timestamp)

    def _Mine(self):
        if self.minedBlock is not None:
            return

        self.minedBlock = self.blockchain.Mine(self.minerAddr,
                                               self.privateKey)
        Log("Mined Block %s" % utils.Shorten(self.minedBlock.GetHash()))

    def _BroadcastBlock(self, bl):
        for peer in self.peers:
            peer.AddBlock(bl)

    def _SyncBlocks(self):
        # TODO: look for a higher peer?
        peer = self._GetRandomPeer()
        if not peer:
            return

        height = self.blockchain.GetHeight()
        peerHeight, blockHashes = peer.SyncBlocks(height)

        # Compare heights
        if peerHeight <= height:
            return

        if height == 0:
            newBlockHashes = blockHashes
        else :
            newBlockHashes = []
            # todo: optimize
            for i in reversed(range(len(blockHashes))):
                blockHash = blockHashes[i]
                if self.blockchain.HasBlock(blockHash):
                    newBlockHashes = blockHashes[i + 1:]
                    break

        #TODO: ask new blocks to several peers, rather than just this
        if newBlockHashes:
            newBlocks = peer.GetBlocks(newBlockHashes)
            if newBlocks:
                self.blockchain.AddBlocks(newBlocks)


def Usage():
    print("USAGE: controller.py [PORT]")
    print("     | controller.py rpc [PORT RPC_PORT]")
    print("     | controller.py miner [PRIV_KEY PUB_KEY] [PORT]")
    print("     | controller.py genkeys")
    print("     | controller.py help")

if __name__ == '__main__':
    import sys

    numArgs = len(sys.argv)

    if numArgs == 1:
        port = int(sys.argv[2]) if numArgs > 2 else 5003
        
        c = Controller()
        c.Start(True, port)

    elif sys.argv[1] == "help":
        Usage()
        sys.exit(1)

    elif sys.argv[1] == "genkeys":
        privateKey, publicKey = utils.GenerateKeys()
        print("Private Key: %s" % utils.BytesToPrivKeyStr(privateKey))
        print("Public Key:  %s" % utils.BytesToAddrStr(publicKey))

    elif sys.argv[1] == "rpc":
        port = int(sys.argv[2]) if numArgs > 2 else 5001
        rpcPort = int(sys.argv[3]) if numArgs > 3 else 4001
        
        c = Controller()
        c.Start(True, port, True, rpcPort)
    
    elif sys.argv[1] == "miner":
        if numArgs > 3:
            privateKey = utils.PrivKeyStrToBytes(sys.argv[2])
            minerAddr  = utils.AddrStrToBytes(sys.argv[3])
            nextArg = 4
        else:
            privateKey, minerAddr = utils.GenerateKeys()
            nextArg = 2

        port = int(sys.argv[nextArg]) if numArgs > nextArg else 5002
        
        c = Controller(minerAddr=minerAddr, privateKey=privateKey)
        c.Start(True, port)
    
