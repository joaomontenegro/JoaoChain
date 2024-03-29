import socket
import time
import threading
import utils

LISTEN_SLEEP_TIME = 0.1
CONNECTION_TIMEOUT = 0.5

def GetHostname():
    return socket.gethostname()

class Message:
    def __init__(self, msgType, payload):
        self.msgType = msgType[:utils.MSGTYPE_BYTE_LEN]
        self.payload = payload

class Socket():
    def __init__(self, sock=None, blocking=True):
        self.sock = None
        
        if sock:
            self.sock = sock
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.setblocking(blocking)

    def Connect(self, hostname, port):
        t = self.sock.gettimeout()
        self.sock.settimeout(CONNECTION_TIMEOUT)
        self.sock.connect((hostname, port))
        self.sock.settimeout(t)

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
        if len(msgType) > utils.MSGTYPE_BYTE_LEN:
            raise ConnectionError("MsgType > %d letters: %s" % (utils.MSGTYPE_BYTE_LEN, msgType))

        totalSent = 0
        payloadLen = len(payload)
        msgLen = utils.MSGTYPE_BYTE_LEN + utils.INT_BYTE_LEN + payloadLen # type|size|payload

        b = msgType.ljust(utils.MSGTYPE_BYTE_LEN).encode()
        b += utils.IntToBytes(payloadLen)
        b += payload
        
        while totalSent < msgLen:
            sent = self.sock.send(b[totalSent:])
            if sent == 0:
                raise ConnectionError("socket connection broken")
            totalSent += sent

    def Receive(self):
        # Type and Size 
        chunk = self.sock.recv(utils.MSGTYPE_BYTE_LEN + utils.INT_BYTE_LEN)
        if chunk == b'':
            raise ConnectionError("socket connection broken")
        msgType = chunk[:utils.MSGTYPE_BYTE_LEN].decode().rstrip()
        start = utils.MSGTYPE_BYTE_LEN
        end = start + utils.INT_BYTE_LEN
        payloadLen = utils.BytesToInt(chunk[start:end])

        chunks = []
        bytesReceived = 0
        while bytesReceived < payloadLen:
            chunk = self.sock.recv(min(payloadLen - bytesReceived, 2048))
            if chunk == b'':
                raise ConnectionError("socket connection broken")
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
        if self.IsConnected():
            raise RuntimeError("Already Connected to: %s:%d" % (self.hostname, self.port))

        try:
            self.sock = Socket()
            self.sock.Connect(self.hostname, self.port)
            print ("Connected to %s:%d" % (self.hostname, self.port))
            return True
        except (ConnectionRefusedError,
                TimeoutError,
                socket.timeout,
                socket.gaierror):
            self.sock = None
            print ("Connection refused: %s:%d" % (self.hostname, self.port))
            return False

    def Send(self, msgType, payload=b''):
        if not self.IsConnected():
            return False
        try:
            #print ("Sending", msgType)
            self.sock.Send(msgType, payload)
            return True
        except (ConnectionError, OSError):
            self.sock = None
            return False

    def Receive(self):
        if not self.IsConnected():
            return None, None

        try:
            return self.sock.Receive()
        except ConnectionError:
            self.sock = None
            return None, None

    def Close(self):
        if self.IsConnected():
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

    class ClientListenerThread(threading.Thread):
        def __init__(self, clientSock, clientAddress, target, args):
            super().__init__(name='Client_%s:%d' % clientAddress,
                             target=target,
                             args=args)
            self.clientSock = clientSock
            self.clientAddress = clientAddress

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
                t = self.ClientListenerThread(clientSock, clientAddress,
                                              target=self._HandleClient,
                                              args=(clientSock, clientAddress))
                threads.append(t)
                t.start()
            except BlockingIOError:
                time.sleep(LISTEN_SLEEP_TIME)
                pass

            # Cleanup dead threads
            threads = [t for t in threads if t.is_alive()]

        # Wait for all live threads to end
        for t in threads:
            if t.is_alive():
                if t.clientSock.IsConnected():
                    t.clientSock.Close()
                t.join()

        # Close the listening socket
        self.Close()
        
    def Stop(self):
        self.active = False

    def Close(self):
        if self.sock is not None:
            self.sock.Close()
            self.sock = None

    def _HandleClient(self, clientSock, clientAddress):
        print("Accepted connection:", clientAddress)

        while clientSock.IsConnected():
            try:
                msgType, msg = clientSock.Receive()

                # Call the methor with the name of the message type prefixed with _.
                methodName = '_%s' % msgType
                if msgType and hasattr(self, methodName):
                    method = getattr(self, methodName)
                    method(clientSock, clientAddress, msgType, msg)
                else:
                    raise RuntimeError("Server method for message type not found: %s" % msgType)
            except ConnectionError:
                print("Disconnected", clientAddress)
                return
