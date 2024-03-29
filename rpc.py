import sys
import utils
import network
import transaction
import random

class RPCServer(network.Server):
    def __init__(self, port, controller):
        super().__init__(port)
        self.controller = controller

    def _Version(self, clientSock, clientAddress, msgType, msg):
        versionBytes = utils.IntToBytes(self.controller.GetVersion())
        clientSock.Send('Version', versionBytes)

    def _AddTx(self, clientSock, clientAddress, msgType, msg):
        tx = transaction.DecodeTx(msg)

        if self.controller.blockchain.AddTransaction(tx):
            clientSock.Send('TxOK')
        else:
            clientSock.Send('TxNO')

    def _GetBalance(self, clientSock, clientAddress, msgType, msg):
        addr = msg[:256]
        balance = self.controller.blockchain.GetBalance(addr)
        if balance is not None:
            clientSock.Send('Balance', utils.IntToBytes(balance))
        else:
            clientSock.Send('NoBalance')


class RPCClient(network.Client):

    def Version(self):
        self.Send('Version')
        msgType, msg = self.Receive()
        if  msgType == 'Version':
            return utils.BytesToInt(msg)
        return None

    def AddTx(self, tx):
        self.Send('AddTx', transaction.EncodeTx(tx))
        msgType, _msg = self.Receive()
        return msgType == 'TxOK'

    def GetBalance(self, addrStr):
        addr = utils.AddrStrToBytes(addrStr)
        self.Send('GetBalance', addr)
        msgType, msg = self.Receive()
        if msgType == 'Balance':
            return utils.BytesToInt(msg[0:utils.INT_BYTE_LEN])
        return None



def Usage(extraCmds = ""):
    print ("Usage: rpc.py [genkeys] | [version,tx,randomtxs,badtx] HOSTNAME PORT | [balance] HOSTNAME PORT ADDR")

if __name__ == '__main__':

    numArgs = len(sys.argv)

    if numArgs < 2: 
        Usage()
        sys.exit(1)

    msgType = sys.argv[1].lower()

    if numArgs == 2: 
        if msgType == "genkeys":
            privateKey, publicKey = utils.GenerateKeys()
            print("Private Key: %s" % utils.BytesToPrivKeyStr(privateKey))
            print("Public Key:  %s" % utils.BytesToAddrStr(publicKey))
        else:
            Usage()

    elif numArgs > 3:
        hostname = sys.argv[2]
        port = int(sys.argv[3])

        client = RPCClient(hostname, port)
        if not client.Connect():
            sys.exit(1)

        if msgType == "version":
            print('Version: %d' % client.Version())

        elif msgType == "tx":
            if numArgs > 8:
                privateKey = utils.PrivKeyStrToBytes(sys.argv[4])
                fromAddr   = utils.AddrStrToBytes(sys.argv[5])
                toAddr     = utils.AddrStrToBytes(sys.argv[6])
                amount     = int(sys.argv[7])
                nonce      = int(sys.argv[8])
            else:
                privateKey, publicKey = utils.GenerateKeys()
                fromAddr = publicKey
                toAddr = utils.GenerateKeys()[1]
                amount = 0
                nonce = random.randint(0, 10000)
            
            tx = transaction.Transaction(fromAddr, toAddr, amount, nonce)
            tx.Sign(privateKey)
            if client.AddTx(tx):
                print('Added:', tx)
            else:
                print ('Failed:', tx)

        elif msgType == "randomtxs":
            timerMainLoop = utils.Timer(1.0)
            while True:
                privateKey, publicKey = utils.GenerateKeys()
                fromAddr = publicKey
                toAddr = utils.GenerateKeys()[1]
                amount = 0
                nonce = random.randint(0, 10000)
                tx = transaction.Transaction(fromAddr, toAddr, amount, nonce)
                tx.Sign(privateKey)
                if client.AddTx(tx):
                    print('Added:', tx)
                else:
                    print ('Failed:', tx)
                
                timerMainLoop.SleepUntilDone()
                timerMainLoop.Reset()

        elif msgType == "badtx":
            privateKey, publicKey = utils.GenerateKeys()
            fromAddr = publicKey
            toAddr = utils.GenerateKeys()[1]
            amount = 123
            tx = transaction.Transaction(fromAddr, toAddr, amount)
            tx.Sign(privateKey)
            print('Bad TX:', client.AddTx(tx))

        elif msgType == "balance":
            if numArgs < 5:
                Usage()
            
            bal = client.GetBalance(sys.argv[4])
            print('Balance:', bal)
        
        else:
            Usage()

        client.Close()
