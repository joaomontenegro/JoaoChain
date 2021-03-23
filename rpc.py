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



if __name__ == '__main__':
    import sys
    import hashlib

    if len(sys.argv) > 3:
        hostname = sys.argv[1]
        port = int(sys.argv[2])
        msgType = sys.argv[3]

        client = RPCClient(hostname, port)
        client.Connect()

        if msgType.lower() == "version":
            print('Version: %d' % client.Version())
        
        elif msgType.lower() == "tx":
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

        elif msgType.lower() == "txs":
            timerMainLoop = utils.Timer(0.5)
            while True:
                if random.randint(0, 4) == 0:
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

        elif msgType.lower() == "badtx":
            privateKey, publicKey = utils.GenerateKeys()
            fromAddr = publicKey
            toAddr = hashlib.sha256(b'2222').digest()
            amount = 123
            tx = transaction.Transaction(fromAddr, toAddr, amount)
            tx.Sign(privateKey)
            print('Added:', client.AddTx(tx))

        elif msgType.lower() == "balance":
            if len(sys.argv) < 5:
                print("No Address Specified...")
                exit(1)
            bal = client.GetBalance(sys.argv[4])
            print('Balance:', bal)

        client.Close()

    else:
        print ("USAGE: %s HOSTNAME PORT [version|tx|badtx|balance...]" )




