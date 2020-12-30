import hashlib
import utils

class Transaction:
    def __init__(self, fromAddr, toAddr, amount):
        self.fromAddr  = fromAddr
        self.toAddr    = toAddr
        self.amount    = amount
        self.signature = None

    def Sign(self, signature):
        self.signature = signature

    def ValidateSignature(self):
        # TODO: check if signature actually signs this
        return self.signature == self.GetHash()

    def GetHash(self):
        b = self.fromAddr.encode()
        b += self.toAddr.encode()
        b += utils.IntToBytes(self.amount)
        return hashlib.sha256(b).hexdigest()

    def __repr__(self):
        HASH_STR_LEN = 8

        return 'Tx{%s, f:%s, t:%s, a:%d, s:%s}' % (
            self.GetHash()[:HASH_STR_LEN],
            self.fromAddr[:HASH_STR_LEN],
            self.toAddr[:HASH_STR_LEN],
            self.amount,
            self.signature[:HASH_STR_LEN])
