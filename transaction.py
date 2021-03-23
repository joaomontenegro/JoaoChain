import hashlib
import utils

class Transaction:

    def __init__(self, fromAddr, toAddr, amount, nonce=0):
        self.fromAddr  = fromAddr
        self.toAddr    = toAddr
        self.amount    = amount
        self.nonce     = nonce
        self.signature = None # todo add here - solve proper signature first

        # Metadata
        self.timeAdded = None

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
        b += utils.IntToBytes(self.nonce)
        return hashlib.sha256(b).digest()

    def __repr__(self):
        return 'Tx{%s, f:%s, t:%s, a:%d, n:%d, s:%s}' % (
            utils.Shorten(self.GetHash()),
            utils.Shorten(self.fromAddr),
            utils.Shorten(self.toAddr),
            self.amount,
            self.nonce,
            utils.Shorten(self.signature))

    def __eq__(self, other):
        if other is None:
            return False
        return self.GetHash() == other.GetHash()

MSG_LEN = (utils.ADDR_BYTE_LEN  + # fromAddr
            utils.ADDR_BYTE_LEN + # toAddr
            utils.INT_BYTE_LEN  + # amount
            utils.INT_BYTE_LEN  + # nonce
            utils.SIGN_BYTE_LEN   # signature
            )

def EncodeTx(tx):
    if tx.signature is None:
        return None
    out = tx.fromAddr
    out += tx.toAddr
    out += utils.IntToBytes(tx.amount)
    out += utils.IntToBytes(tx.nonce)
    out += tx.signature

    if len(out) != MSG_LEN:
        raise ValueError("Invalid Tx size: %d" % len(out))

    return out

def DecodeTx(txBytes):
    l = len(txBytes)
    if l < MSG_LEN:
        raise ValueError("Invalid Tx size: %d" % len(txBytes))
    
    start = 0
    end = utils.ADDR_BYTE_LEN
    fromAddr = txBytes[start:end]
    
    start = end
    end += utils.ADDR_BYTE_LEN
    toAddr = txBytes[start:end]

    start = end
    end += utils.INT_BYTE_LEN
    amount = utils.BytesToInt(txBytes[start:end])
    
    start = end
    end += utils.INT_BYTE_LEN
    nonce = utils.BytesToInt(txBytes[start:end])
    
    start = end
    end += utils.SIGN_BYTE_LEN
    signature = txBytes[start:end]
    
    if end != MSG_LEN:
        raise ValueError("Invalid tx length: %d" % end)

    tx = Transaction(fromAddr, toAddr, amount, nonce)
    tx.Sign(signature)    
    return tx
