import hashlib
import utils
    

class Transaction:
    def __init__(self, fromAddr, toAddr, amount):
        self.fromAddr  = fromAddr
        self.toAddr    = toAddr
        self.amount    = amount
        self.signature = None # todo add here - solve proper signature first

    def Sign(self, signature):
        self.signature = signature
        return self.ValidateSignature()

    def ValidateSignature(self):
        # TODO: check if signature actually signs this
        return self.signature == self.GetHash()

    def GetHash(self):
        b = self.fromAddr
        b += self.toAddr
        b += utils.IntToBytes(self.amount)
        return hashlib.sha256(b).digest()

    def __repr__(self):
        HASH_STR_LEN = 8

        return 'Tx{%s, f:%s, t:%s, a:%d, s:%s}' % (
            self.GetHash().hex()[:HASH_STR_LEN],
            self.fromAddr.hex()[:HASH_STR_LEN],
            self.toAddr.hex()[:HASH_STR_LEN],
            self.amount,
            self.signature.hex()[:HASH_STR_LEN])

def EncodeTx(tx):
    if tx.signature is None:
        return None
    b = tx.fromAddr
    b += tx.toAddr
    b += utils.IntToBytes(tx.amount)
    b += tx.signature
    return b

def DecodeTx(txBytes):
    l = len(txBytes)
    if l != 32 + 32 + 4 + 32:
        print("Invalid Tx size: ", len())
        return None
    
    fromAddr = txBytes[:32]
    toAddr = txBytes[32:64]
    amount = utils.BytesToInt(txBytes[64:68])
    signature = txBytes[68:]
    
    tx = Transaction(fromAddr, toAddr, amount)
    tx.Sign(signature)    
    return tx
