import hashlib
import utils

class Block:
    def __init__(self, parent, transactions, timestamp, miner=None):
        self.parent       = parent
        self.transactions = transactions
        self.timestamp    = timestamp
        self.nonce        = 0
        self.miner        = None
        self.signature    = None
        #self.gas         = 0

    def Sign(self, miner, signature):
        self.miner = miner
        self.signature = signature

    def ValidateSignature(self):
        # TODO: check if signature actually signs this
        return self.signature == self.GetHash()

    def GetHash(self):
        if self.parent is None:
            parent = b''
        else:
            parent = self.parent
           
        b = parent
        b += utils.IntToBytes(len(self.transactions))
        b += utils.IntToBytes(self.timestamp, 8)
        b += utils.IntToBytes(self.nonce)
        return hashlib.sha256(b).digest()

    def __repr__(self):
        HASH_STR_LEN = 8

        if self.parent is None:
            p = 'ROOT'
        else:
            p = self.parent.hex()[:HASH_STR_LEN]

        return 'Block{%s, p:%s, m:%s, t:%d, tx:%d, n:%d}' % (
            self.GetHash().hex()[:HASH_STR_LEN],
            p,
            self.miner.hex()[:HASH_STR_LEN],
            self.timestamp,
            len(self.transactions),
            self.nonce)

