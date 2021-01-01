import socket
import time
import threading
import utils

def GetHostname():
    return socket.gethostname()

class Message:
    def __init__(self, msgType, payload):
        self.msgType = msgType[:12]
        self.payload = payload

class Socket():
    def __init__(self, sock=None, blocking=True):
        self.sock = None
        
        if sock:
            self.sock = sock
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if blocking is not None:
            self.sock.setblocking(blocking)

    def Connect(self, hostname, port):
        self.sock.connect((hostname, port))

    def Bind(self, hostname, port):
        self.sock.bind((hostname, port))

    def Listen(self, backlog):
        self.sock.listen(backlog)

    def Accept(self):
        (clientSock, clientAddress) = self.sock.accept()
        return Socket(sock=clientSock), clientAddress

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
        b += utils.IntToBytes(payloadLen)
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
        payloadLen = utils.BytesToInt(chunk[12:16])

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

    def __repr__(self):
        return 'Client(%s:%d)' % (self.hostname, self.port)

    def __del__(self):
        if self.IsConnected():
            self.Close()

    def IsConnected(self):
        return self.sock != None

    def Connect(self):

        # todo: catch exception?
        if self.IsConnected():
            raise RuntimeError("Already Connected to: %s:%d" % (self.hostname, self.port))

        try:
            self.sock = Socket()
            print ("Connecting to %s:%d" % (self.hostname, self.port))
            self.sock.Connect(self.hostname, self.port)
            print ("Connected to %s:%d" % (self.hostname, self.port))
            return True
        except ConnectionRefusedError:
            self.sock = None
            print ("Connection refused: %s:%d" % (self.hostname, self.port))
            return False

    def Close(self):
        self.sock.Close()
        self.sock = None


class Server:
    def __init__(self, port):
        self.sock = None
        self.port = port
        self.active = False

    def __repr__(self):
        return 'Server(%d)' % (self.port)

    def __del__(self):
        self.Close()

    def IsBound(self):
        return self.sock != None

    def Start(self):
        # Create, bind and listen server socket
        self.sock = Socket(blocking=False)
        self.sock.Bind(socket.gethostname(), self.port)
        self.sock.Listen(5)
        print ("Listening to port", self.port)

        threads = []
        self.active = True
       
        while self.active:
            try:
                (clientSock, clientAddress) = self.sock.Accept()
                t = threading.Thread(name='Client_%s:%d' % clientAddress,
                                     target=self._HandleClient,
                                     args=(clientSock, clientAddress))
                threads.append(t)
                t.start()
            except BlockingIOError:
                time.sleep(0.1) # TODO: configure this?
                pass

            # Cleanup dead threads
            threads = [t for t in threads if t.is_alive()]

        # Wait for all live threads to end
        for t in threads:
            t.join()

        # Close the listening socket
        self.Close()
        
    def Stop(self):
        self.active = False

    def Close(self):
        if self.sock is not None:
            self.sock.Close()
            self.sock = None

    def ProcessMessage(self, msgType, msg, clientSock):
        raise NotImplementedError

    def _HandleClient(self, clientSock, clientAddress):
        print("Accepted connection:", clientAddress)

        while clientSock.IsConnected():
            msgType, msg = clientSock.Receive()
            print ("  Received:", msgType)
            self.ProcessMessage(msgType, msg, clientSock)

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
        
        elif msgType == 'Ping':
            clientSock.Send('Pong')

        if msgType == 'Stop':
            clientSock.Send('Bye!')
            clientSock.Close()
            self.Stop()


if __name__ == '__main__':
    import sys

    ok = False

    if len(sys.argv) > 1:
        if sys.argv[1] == 'server':
            ok = True
            server = TestServer(5001)
            server.Start()

        elif sys.argv[1] == 'client':
            ok = True
            client = TestClient(GetHostname(), 5001)
            client.Connect()
            for i in range(5) :
                print("Ping %d:" % i, client.Ping())
                time.sleep(1)
            client.Done()
        
        elif sys.argv[1] == 'ping':
            ok = True
            client = TestClient(GetHostname(), 5001)
            client.Connect()
            print("Ping:", client.Ping())
            client.Done()

        elif sys.argv[1] == 'stop':
            ok = True
            client = TestClient(GetHostname(), 5001)
            client.Connect()
            client.Stop()
            
    if not ok:
        print("Usage: %s [server|client|ping|stop]" % sys.argv[0])
