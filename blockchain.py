import hashlib
import time
from collections import OrderedDict

import block
import transaction
import utils

MAX_TX_PER_BLOCK = 10

doLog = True
def Log(msg):
    if doLog:
        print(msg)


class Blockchain:
    def __init__(self, difficulty=1):
        self.mempool    = OrderedDict()
        self.blocks     = {}
        self.difficulty = difficulty
        self.reward     = 10
        self.balances   = {}
        self.highest    = None
        self.height     = 0

    def SetDifficulty(self, newDifficulty):
        self.difficulty = newDifficulty

    def AddBlock(self, b):
        print (" - Adding Block:", b)
        hash = b.GetHash()

        if not self._ValidateMiner(b):
            Log("Invalid Miner Sig for %s" % b)
            return False

        if not self._ValidateParent(b):
            # TODO send to hanging blocks list?
            Log("Invalid Parent for %s" % b)
            return False

        if not self._ValidatePow(b):
            Log("Invalid POW for %s" % b)
            return False

        if not self._ValidateTxSignatures(b):
            Log("Invalid Tx Sigs for %s" % b)
            return False

        chain = self.GetChain(b.parent)
        blockBalances = self._CalculateBalances(b, chain)
        if blockBalances is None:
            Log("Invalid Balances for %s" % b)
            return False
        self.balances[hash] = blockBalances

        blockHeight = len(chain) + 1
        if blockHeight > self.height:
            self.height = blockHeight
            self.highest = hash

        self.blocks[hash] = b
        self.balances[hash] = blockBalances
        
        return True

    def GetBlock(self, hash):
        return self.blocks.get(hash, None)

    def GetHighestBlockHash(self):
        return self.highest

    def GetHighestBlock(self):
        if self.highest is None:
            return None
        return self.GetBlock(self.highest)

    def GetChain(self, hash):
        chain = []
        while hash is not None:
            b = self.blocks.get(hash, None)
            if not b: return None
            chain.append(b)
            hash = b.parent
        return chain

    def GetBalance(self, addr, hash=None):
        if hash is None:
            if self.highest is None:
                return None
            hash = self.highest

        chain = self.GetChain(hash)
        for b in chain:
            balance = self.balances.get(b.GetHash()).get(addr, None)
            if balance is not None:
                return balance
        return 0

    def Mine(self, miner, parent, maxNumTx=MAX_TX_PER_BLOCK):
        parentBalances = self.balances.get(parent, {})

        # Create the reward transaction
        rewardTx = transaction.Transaction(miner, miner, self.reward)
        # Todo properly sign:
        rewardTx.Sign(rewardTx.GetHash())

        transactions = [ rewardTx ]
        rejected = []
        tmpBalances = { miner : parentBalances.get(miner, 0) + self.reward }

        # Add transactions from mempool, checking if the from addr has enough balance
        while len(transactions) < maxNumTx + 1:
            # Stop if we ran out of mempool
            if not self.mempool: break

            # Get the first tx in the mempool and validate its sig
            tx = self.mempool.popitem(last=False)[1]
            if not tx.ValidateSignature(): continue

            # Calculate the balance of the from addr, minus the tx amout
            fromBal = tmpBalances.get(tx.fromAddr,
                        parentBalances.get(tx.fromAddr, 0)) - tx.amount
            if fromBal < 0:
                print("Rejected %s" % tx)
                # Reject tx and add to the end of the pool
                rejected.append(tx)
                continue
            
            # Calculate the balance of the to addr, plus the tx amout
            toBal = tmpBalances.get(tx.toAddr,
                        parentBalances.get(tx.toAddr, 0)) + tx.amount

            # Update the balances
            tmpBalances[tx.fromAddr] = fromBal
            tmpBalances[tx.toAddr] = toBal

            transactions.append(tx)

        # Add the rejected txs to the end of the mempool
        for rTx in rejected:
            self.mempool[rTx.GetHash()] = rTx

        # Create the Block
        b = block.Block(parent, transactions, utils.GetCurrentTime(), miner)
        
        # Mine it
        while(not self._ValidatePow(b)):
            b.nonce += 1
        
        # Todo properly sign:
        b.Sign(b.GetHash())

        return b

    def AddTransaction(self, tx):
        if tx.ValidateSignature():
            if tx.GetHash() not in self.mempool:
                Log("Adding tx: %s" % tx)
                self.mempool[tx.GetHash()] = tx
            return True
        else:
            Log("Tried to add invalid tx: %s" % tx)
            return False

    def _ValidateMiner(self, b):
        return b.miner is not None and b.ValidateSignature()

    def _ValidatePow(self, b):
        hash = b.GetHash()
        if hash is None:
            return False

        prefix = '0' * self.difficulty   
        return hash.hex().startswith(prefix)

    def _ValidateParent(self, b):
        if b.parent is None:
            return True

        return self.blocks.get(b.parent, None) != None
        
    def _ValidateTxSignatures(self, b):
        for tx in b.transactions:
            if not tx.ValidateSignature():
                return False
        return True

    def _CalculateBalances(self, b, chain):
        balances = {}
        for tx in b.transactions:

            if tx.fromAddr == tx.toAddr == b.miner:
                Log("  -> Tx: %s REWARD" % tx)
                pass
            else:
                fromBalance = balances.get(tx.fromAddr, None)
                if fromBalance is None:
                    fromBalance = self._GetBalanceInChain(tx.fromAddr, chain)
                
                fromBalance -= tx.amount
                if fromBalance < 0:
                    Log("  -> Tx: %s BAD" % tx)
                    return None
                Log("  -> Tx: %s OK" % tx)
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
    print("\nMiner: %s" % miner.hex())

    addrs = [hashlib.sha256(b"0000").digest(),
             hashlib.sha256(b"1111").digest(),
             hashlib.sha256(b"2222").digest(),
             hashlib.sha256(b"3333").digest(),
             hashlib.sha256(b"4444").digest(),
             hashlib.sha256(b"5555").digest()]

    print ('\nAdding Txs:')

    t0 = transaction.Transaction(miner, addrs[1], 10)
    t0.Sign(t0.GetHash())
    bc.AddTransaction(t0)

    t1 = transaction.Transaction(addrs[1], addrs[2], 5)
    t1.Sign(t1.GetHash())
    bc.AddTransaction(t1)

    t2 = transaction.Transaction(addrs[1], addrs[3], 4)
    t2.Sign(t2.GetHash())
    bc.AddTransaction(t2)

    t3 = transaction.Transaction(addrs[3], addrs[4], 1)
    t3.Sign(t3.GetHash())
    bc.AddTransaction(t3)

    t4 = transaction.Transaction(addrs[3], addrs[5], 3)
    t4.Sign(t4.GetHash())
    bc.AddTransaction(t4)

    print ('\nMining and Adding Blocks:')
    block0 = bc.Mine(miner, None, 3)
    print (" Adding", block0)
    if not bc.AddBlock(block0): exit()
    print ()

    block1 = bc.Mine(miner, block0.GetHash(), 3)
    print (" Adding", block1)
    if not bc.AddBlock(block1): exit()
    print ()

    block2 = bc.Mine(miner, block1.GetHash(), 3)
    print (" Adding", block2)
    if not bc.AddBlock(block2): exit()
    print ()

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
