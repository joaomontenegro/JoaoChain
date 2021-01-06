import hashlib
import time

import block
import transaction
import utils

MAX_SUPPLY = 1000

doLog = True
def Log(msg):
    if doLog:
        print(msg)


class Blockchain:
    def __init__(self):
        self.mempool    = {}
        self.blocks     = {}
        self.difficulty = 1
        self.reward     = 10
        self.balances   = {}
        self.highest    = None
        self.height     = 0

    def SetDifficulty(self, newDifficulty):
        self.difficulty = newDifficulty

    def AddBlock(self, block):
        hash = block.GetHash()

        if not self._ValidateMiner(block):
            Log("Invalid Miner Sig for %s" % block)
            return False

        if not self._ValidateParent(block):
            # TODO send to hanging blocks list?
            Log("Invalid Parent for %s" % block)
            return False

        if not self._ValidatePow(block):
            Log("Invalid POW for %s" % block)
            return False

        if not self._ValidateTxSignatures(block):
            Log("Invalid Tx Sigs for %s" % block)
            return False

        chain = self.GetChain(block.parent)
        blockBalances = self._CalculateBalances(block, chain)
        if blockBalances is None:
            Log("Invalid Balances for %s" % block)
            return False
        self.balances[hash] = blockBalances

        blockHeight = len(chain) + 1
        if blockHeight > self.height:
            self.height = blockHeight
            self.highest = hash

        self.blocks[hash] = block
        self.balances[hash] = blockBalances
        
        return True

    def GetBlock(self, hash):
        return self.blocks.get(hash, None)

    def GetHighestBlock(self):
        if self.highest is None:
            return None
        return self.GetBlock(self.highest)

    def GetChain(self, hash):
        chain = []
        while hash is not None:
            block = self.blocks.get(hash, None)
            if not block: return None
            chain.append(block)
            hash = block.parent
        return chain

    def GetBalance(self, addr, hash=None):
        if hash is None:
            if self.highest is None:
                return None
            hash = self.highest

        chain = self.GetChain(hash)
        for block in chain:
            balance = self.balances.get(block.GetHash()).get(addr, None)
            if balance is not None:
                return balance
        return 0

    def Mine(self, block, miner):
        block.miner = miner
        block.nonce = 0

        rewardTx = transaction.Transaction(miner, miner, self.reward)
        # Todo properly sign:
        rewardTx.Sign(rewardTx.GetHash())
        block.transactions.append(rewardTx)
        
        while(not self._ValidatePow(block)):
            block.nonce += 1
        
        # Todo properly sign:
        block.Sign(miner, block.GetHash())

    def AddTransaction(self, tx):
        if tx.ValidateSignature():
            Log("Adding tx: %s" % tx)
            self.mempool[tx.GetHash()] = tx
            return True
        else:
            Log("Tried to add invalid tx: %s" % tx)
            return False

    def _ValidateMiner(self, block):
        return block.miner is not None and block.ValidateSignature()

    def _ValidatePow(self, block):
        hash = block.GetHash()
        if hash is None:
            return False
        
        prefix = b'0' * self.difficulty        
        return hash[:self.difficulty] == prefix

    def _ValidateParent(self, block):
        if block.parent is None:
            return True

        return self.blocks.get(block.parent, None) != None
        
    def _ValidateTxSignatures(self, block):
        for tx in block.transactions:
            if not tx.ValidateSignature():
                return False
        return True

    def _CalculateBalances(self, block, chain):
        balances = {}
        for tx in block.transactions:
            Log("-> Tx: %s" % tx)

            if tx.fromAddr == tx.toAddr == block.miner:
                pass
            else:
                fromBalance = balances.get(tx.fromAddr, None)
                if fromBalance is None:
                    fromBalance = self._GetBalanceInChain(tx.fromAddr, chain)
                
                fromBalance -= tx.amount
                if fromBalance < 0:
                    Log("    Bad!!")
                    return None
                balances[tx.fromAddr] = fromBalance

            toBalance = self._GetBalanceInChain(tx.toAddr, chain)
            balances[tx.toAddr] = toBalance + tx.amount
        
        return balances

    def _GetBalanceInChain(self, addr, chain):
        for ancestor in chain:
            hash = ancestor.GetHash()
            balance = self.balances.get(hash, {}).get(addr, None)
            if balance is not None:
                return balance
        return 0



if __name__ == '__main__':
    bc = Blockchain()
    bc.SetDifficulty(2)
    
    miner = hashlib.sha256(b'miner123').digest()
    print("Miner: %s\n" % miner.hex())

    addrs = [hashlib.sha256(b"0000").digest(),
             hashlib.sha256(b"1111").digest(),
             hashlib.sha256(b"2222").digest(),
             hashlib.sha256(b"3333").digest(),
             hashlib.sha256(b"4444").digest(),
             hashlib.sha256(b"5555").digest()]

    t0 = transaction.Transaction(miner, addrs[1], 10)
    t0.Sign(t0.GetHash())
    t1 = transaction.Transaction(addrs[1], addrs[2], 5)
    t1.Sign(t1.GetHash())
    t2 = transaction.Transaction(addrs[1], addrs[3], 4)
    t2.Sign(t2.GetHash())
    
    t3 = transaction.Transaction(addrs[3], addrs[4], 1)
    t3.Sign(t3.GetHash())
    t4 = transaction.Transaction(addrs[3], addrs[5], 3)
    t4.Sign(t4.GetHash())

    block0 = block.Block(None, [], utils.GetCurrentTime())
    bc.Mine(block0, miner)

    block1 = block.Block(block0.GetHash(), [t0, t1, t2], utils.GetCurrentTime())
    bc.Mine(block1, miner)

    block2 = block.Block(block1.GetHash(), [t3, t4], utils.GetCurrentTime())
    bc.Mine(block2, miner)
    
    print ("Adding", block0)
    if not bc.AddBlock(block0): exit()
    print()

    print ("Adding", block1)
    if not bc.AddBlock(block1): exit()
    print()

    print ("Adding", block2)
    if not bc.AddBlock(block2): exit()
    print()

    from pprint import pprint
    print ('\n')
    print("Chain:")
    chain = bc.GetChain(block2.GetHash())
    i = 0
    for b in chain:
        print("%d: %s" % (i, b))
        for (hash, amount) in bc.balances.get(b.GetHash(), {}).items():
            print("  %s: %d" % (hash.hex()[0:8], amount))

        i += 1
    print()

    # Expectd Results: 
    #      Miner: 30
    #      9af15b33: 0
    #      0ffe1abd: 1
    #      edee29f8: 5
    #      318aee3f: 0
    #      79f06f8f: 1
    #      c1f330d0: 3
    print("Balances:")
    print ("   Miner: %d" % bc.GetBalance(miner))
    for addr in addrs:
        print("   %s: %d" % (addr.hex()[0:8],  bc.GetBalance(addr)))
