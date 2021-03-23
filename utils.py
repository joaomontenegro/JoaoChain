import time
import ecdsa

### Byte Encoding/Decoding ###
INT_BYTE_LEN  = 4
ADDR_BYTE_LEN = 64
ADDR_HEX_LEN  = ADDR_BYTE_LEN / 8
SIGN_BYTE_LEN = 32
HASH_BYTE_LEN = 32
MSGTYPE_BYTE_LEN = 12

def IntToBytes(i, size=INT_BYTE_LEN):
    return i.to_bytes(size, "big")

def BytesToInt(b):
    return int.from_bytes(b, "big")

def AddrStrToBytes(addrStr):
    if len(addrStr) != ADDR_HEX_LEN:
        raise ValueError("Invalid addr string size: %d" % len(addrStr))
    return bytes.fromhex(addrStr)

def BytesToAddrStr(addr):
    if len(addr) != ADDR_BYTE_LEN:
        raise ValueError("Invalid addr byte size: %d" % len(addr))
    return addr.hex()

def ZeroAddr():
    return IntToBytes(0, ADDR_BYTE_LEN)

def ZeroHash():
    return IntToBytes(0, HASH_BYTE_LEN)

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

def GetCurrentTime():
    return int(round(time.time()))

class Timer:
    def __init__(self, interval):
        self.interval = interval
        self.starTime = GetCurrentTime()

    def Reset(self, interval=None):
        self.starTime = GetCurrentTime()

    def GetEllapsed(self):
        return GetCurrentTime() - self.starTime

    def GetRemaining(self):
        return max(self.interval - self.GetEllapsed(), 0)

    def SleepUntilDone(self):
        time.sleep(self.GetRemaining())
        
    def IsDone(self):
        return self.GetEllapsed() > self.interval

