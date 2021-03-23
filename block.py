import transaction

import hashlib
import utils

class Block:
    def __init__(self, parent, transactions, timestamp, miner, nonce=0):
        self.parent       = parent
        self.timestamp    = timestamp
        self.nonce        = nonce
        self.miner        = miner
        self.signature    = None
        #self.gas         = 0
        self.transactions = transactions

        # Metadata
        self.height    = None
        self.timeAdded = None
        self.balances  = {}
        self.byteSize  = 0

    def Sign(self, signature):
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

    def __eq__(self, other):
        if other is None:
            return False
        return self.GetHash() == other.GetHash()

#todo: add test
def EncodeBlock(bl):
    if bl.signature is None:
        return None
    
    if bl.parent is None:
        out = utils.ZeroHash()
    else:
        out = bl.parent
    
    out += utils.IntToBytes(bl.nonce)
    out += utils.IntToBytes(bl.timestamp)
    out += bl.miner
    out += bl.signature
    out += utils.IntToBytes(len(bl.transactions))
    
    for tx in bl.transactions:
        out += transaction.EncodeTx(tx)

    return out
    
#todo: add test
def DecodeBlock(blBytes):
    start = 0
    end = utils.HASH_BYTE_LEN
    parent = blBytes[start:end]
    if parent == utils.ZeroHash():
        parent = None
    
    start = end
    end += utils.INT_BYTE_LEN
    nonce = utils.BytesToInt(blBytes[start:end])

    start = end
    end += utils.INT_BYTE_LEN
    timestamp = utils.BytesToInt(blBytes[start:end])

    start = end
    end += utils.ADDR_BYTE_LEN
    miner = blBytes[start:end]
    
    start = end
    end += utils.SIGN_BYTE_LEN
    signature = blBytes[start:end]
    
    start = end
    end += utils.INT_BYTE_LEN
    numTx = utils.BytesToInt(blBytes[start:end])

    transactions = []
    for _ in range(numTx):
        start = end
        end += transaction.MSG_LEN
        tx = transaction.DecodeTx(blBytes[start:end])
        if tx:
            transactions.append(tx)
    
    bl = Block(parent, transactions, timestamp, miner, nonce)
    bl.byteSize = end
    bl.Sign(signature)

    if not bl.ValidateSignature():
        return None

    return bl