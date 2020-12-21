import socket
import time

INITIAL_ADDRS = ["127.0.0.1:5001", "127.0.0.1:5002"]

def GetHostname():
    return socket.gethostname()

class Message:
    def __init__(self, msgType, payload):
        self.msgType = msgType[:12]
        self.payload = payload

def IntToBytes(i, size=4):
    return i.to_bytes(size, "big")

def BytesToInt(b):
    return int.from_bytes(b, "big")

class Socket():
    def __init__(self, sock=None):
        self.sock = None
        
        if sock:
            self.sock = sock
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def Connect(self, hostname, port):
        self.sock.connect((hostname, port))

    def Bind(self, hostname, port):
        self.sock.bind((hostname, port))

    def Listen(self, backlog):
        self.sock.listen(backlog)

    def Accept(self):
        (clientSock, clientAddress) = self.sock.accept()
        return Socket(clientSock), clientAddress

    def Close(self):
        self.sock.close()
        self.sock = None

    def IsConnected(self):
        return self.sock != None

    def Send(self, msgType, payload=b''):
        totalSent = 0
        payloadLen = len(payload)
        msgLen = 12 + 4 + payloadLen # type|size|payload

        b = msgType.ljust(12).encode()
        b += IntToBytes(payloadLen)
        b += payload
        
        while totalSent < msgLen:
            sent = self.sock.send(b[totalSent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalSent += sent

    def Receive(self):
        # Type and Size 
        chunk = self.sock.recv(12 + 4)
        if chunk == b'':
                raise RuntimeError("socket connection broken")
        msgType = chunk[:12].decode().rstrip()
        payloadLen = BytesToInt(chunk[12:16])

        chunks = []
        bytesReceived = 0
        while bytesReceived < payloadLen:
            chunk = self.sock.recv(min(payloadLen - bytesReceived, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytesReceived = bytesReceived + len(chunk)
        
        payload = b''.join(chunks)
        return msgType, payload

class Client:
    def __init__(self, hostname, port):
        self.hostname = hostname
        self.port = port
        self.sock = None
    
    def IsConnected(self):
        return self.sock != None

    def Connect(self):
        if self.IsConnected():
            raise RuntimeError("Already Connected to: %s:%d" % (self.hostname, self.port))

        self.sock = Socket()
        self.sock.Connect(self.hostname, self.port)
        print ("Connected to %s:%d" % (self.hostname, self.port))

    def Close(self):
        self.sock.Close()
        self.sock = None

class Server:
    def __init__(self, port):
        self.sock = None
        self.port = port

    def IsBound(self):
        return self.sock != None

    def Bind(self):
        self.sock = Socket()
        self.sock.Bind(socket.gethostname(), self.port)
        self.sock.Listen(5)

        while True:
            print ("Listening to port", self.port)
            (clientSock, clientAddress) = self.sock.Accept()
            
            print("Accepted connection:", clientAddress)
            
            while clientSock.IsConnected():
                msgType, msg = clientSock.Receive()
                print ("  Received:", msgType)
                if not self.ProcessMessage(msgType, msg, clientSock):
                    if clientSock.IsConnected():
                        clientSock.Close()
                    self.sock.Close()
                    return
            
    def Close(self):
        self.sock.Close()
        self.sock = None

    def ProcessMessage(self, msgType, msg, clientSock):
        raise NotImplementedError


class TestClient(Client):
    def Ping(self):
        self.sock.Send('Ping')
        msgType, _msg = self.sock.Receive()
        return  msgType == 'Pong'

    def Done(self):
        self.sock.Send('Done')

    def Stop(self):
        self.sock.Send('Stop')
        msgType, _msg = self.sock.Receive()
        return msgType == 'Bye!'

class TestServer(Server):
    def ProcessMessage(self, msgType, msg, clientSock):
        if msgType == 'Done':
            clientSock.Close()
            return True
        
        elif msgType == 'Ping':
            print( " -> Ping: ", msg)
            clientSock.Send('Pong')
            return True

        if msgType == 'Stop':
            clientSock.Send('Bye!')
            return False

        return True

if __name__ == '__main__':
    import sys

    ok = False

    if len(sys.argv) > 1:
        if sys.argv[1] == 'server':
            ok = True
            server = TestServer(5001)
            server.Bind()
        
        elif sys.argv[1] == 'client':
            ok = True
            client = TestClient(GetHostname(), 5001)
            client.Connect()
            print("Ping 1:", client.Ping())
            print("Ping 2:", client.Ping())
            client.Done()

        elif sys.argv[1] == 'stop':
            ok = True
            client = TestClient(GetHostname(), 5001)
            client.Connect()
            client.Stop()
            
    if not ok:
        print("Usage: %s [server|ping|stop]" % sys.argv[0])
