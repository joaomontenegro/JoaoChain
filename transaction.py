class Transaction:
    def __init__(self, fromAddr, toAddr, amount, signature):
        self.fromAddr  = fromAddr
        self.toAddr    = toAddr
        self.amount    = amount
        self.signature = signature

    def validateSignature(self):
        # TODO: check if signature actually signs this
        return True

    def getHash(self):
        pass