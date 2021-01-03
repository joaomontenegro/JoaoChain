import time

def IntToBytes(i, size=4):
    return i.to_bytes(size, "big")

def BytesToInt(b):
    return int.from_bytes(b, "big")


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
