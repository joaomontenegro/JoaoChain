import utils
import network
import transaction

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
            fromAddr = hashlib.sha256(b'1111').digest()
            toAddr = hashlib.sha256(b'2222').digest()
            amount = 0
            tx = transaction.Transaction(fromAddr, toAddr, amount)
            tx.Sign(tx.GetHash())
            print('Added:', client.AddTx(tx))

        elif msgType.lower() == "badtx":
            fromAddr = hashlib.sha256(b'1111').digest()
            toAddr = hashlib.sha256(b'2222').digest()
            amount = 123
            tx = transaction.Transaction(fromAddr, toAddr, amount)
            tx.Sign(hashlib.sha256(b'blah').digest())
            print('Added:', client.AddTx(tx))

        client.Close()

    else:
        print ("USAGE: %s HOSTNAME PORT [version|tx|badtx...]" )




