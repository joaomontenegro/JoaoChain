import time

def IntToBytes(i, size=4):
    return i.to_bytes(size, "big")

def BytesToInt(b):
    return int.from_bytes(b, "big")


def GetCurrentTime():
    return int(round(time.time() * 1000))