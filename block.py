class Block:
    def __init__(self, transactions, timestamp, previousHash):
        self.transactions = transactions
        self.timestamp    = timestamp
        self.previousHash = previousHash
        self.nonce        = 0
    
    def getHash(self):
        pass