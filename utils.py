import time
import ecdsa

### Byte Encoding/Decoding ###
INT_BYTE_LEN     = 4
ADDR_BYTE_LEN    = 64
SIGN_BYTE_LEN    = 64
HASH_BYTE_LEN    = 32
MSGTYPE_BYTE_LEN = 12
SHORTEN_BYTE_LEN = 8
PRIVKEY_BYTE_LEN = 32

def IntToBytes(i, size=INT_BYTE_LEN):
    return i.to_bytes(size, "big")

def BytesToInt(b):
    return int.from_bytes(b, "big")

def AddrStrToBytes(addrStr):
    if len(addrStr) != ADDR_BYTE_LEN * 2:
        raise ValueError("Invalid addr string size: %d" % len(addrStr))
    return bytes.fromhex(addrStr)

def BytesToAddrStr(addr):
    if len(addr) != ADDR_BYTE_LEN:
        raise ValueError("Invalid addr byte size: %d" % len(addr))
    return addr.hex()

def ZeroAddr():
    return IntToBytes(0, ADDR_BYTE_LEN)

def PrivKeyStrToBytes(privKeyStr):
    if len(privKeyStr) != PRIVKEY_BYTE_LEN * 2:
        raise ValueError("Invalid private key string size: %d" % len(privKeyStr))
    return bytes.fromhex(privKeyStr)

def BytesToPrivKeyStr(privKey):
    if len(privKey) != PRIVKEY_BYTE_LEN:
        raise ValueError("Invalid private key byte size: %d" % len(privKey))
    return privKey.hex()

def ZeroHash():
    return IntToBytes(0, HASH_BYTE_LEN)

def Shorten(data):
    return data.hex()[:SHORTEN_BYTE_LEN]

### Cryptography ###

def GenerateKeys():
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    privateKey = sk.to_string()

    vk = sk.get_verifying_key()
    publicKey = vk.to_string()

    return privateKey, publicKey

def SignData(data, privateKey):
    sk = ecdsa.SigningKey.from_string(privateKey, curve=ecdsa.SECP256k1)
    return sk.sign(data)

def ValidateSignature(data, signature, publicKey):
    try:
        vk = ecdsa.VerifyingKey.from_string(publicKey, curve=ecdsa.SECP256k1)
        return vk.verify(signature, data)
    except:
        return False

### Time ###

def GetCurrentTime(asInt=True):
    if asInt:
        return int(round(time.time()))
    else:
        return time.time()

class Timer:
    def __init__(self, interval=1.0, startDone=False, asInt=True):
        self.interval = interval
        self.asInt = asInt
        if startDone:
            self.starTime = 0
        else:    
            self.starTime = GetCurrentTime(self.asInt)

    def Reset(self, interval=None):
        self.starTime = GetCurrentTime(self.asInt)

    def GetEllapsed(self):
        return GetCurrentTime(self.asInt) - self.starTime

    def GetRemaining(self):
        return max(self.interval - self.GetEllapsed(), 0)

    def SleepUntilDone(self):
        time.sleep(self.GetRemaining())
        
    def IsDone(self):
        return self.GetEllapsed() > self.interval

