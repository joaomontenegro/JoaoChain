import utils
import network

class RPCServer(network.Server):
    def __init__(self, port, controller):
        super().__init__(port)
        self.controller = controller

    def _Version(self, clientSock, clientAddress, msgType, msg):
        versionBytes = utils.IntToBytes(self.controller.GetVersion())
        clientSock.Send('Version', versionBytes)


class RPCClient(network.Client):

    def Version(self):
        self.Send('Version')
        msgType, msg = self.Receive()
        if  msgType == 'Version':
            return utils.BytesToInt(msg)
        return None

    def AddTransaction(self, tx):
        #TODO: encode transaction in Transaction object?
        pass

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 3:
        hostname = sys.argv[1]
        port = int(sys.argv[2])
        msgType = sys.argv[3]

        client = RPCClient(hostname, port)
        client.Connect()

        if msgType.lower() == "version":
            print('Version: %d' % client.Version())

        client.Close()

    else:
        print ("USAGE: %s HOSTNAME PORT [VERSION|...]" )




