import hashlib
import time
from collections import OrderedDict

import block
import transaction
import utils
import threading

MAX_TX_PER_BLOCK = 10

doLog = True
def Log(msg):
    if doLog:
        print(msg)


class Blockchain:
    def __init__(self, difficulty=1):
        self.mempool     = OrderedDict()
        self.blocks      = {}
        self.difficulty  = difficulty
        self.reward      = 10
        self.highest     = None

        self.mempoolLock = threading.Lock()
        self.blockLock   = threading.Lock()

    def SetDifficulty(self, newDifficulty):
        self.difficulty = newDifficulty

    def AddBlock(self, b):
        print ("Adding Block:", b)
        hash = b.GetHash()

        #TODO: check if block is already present in chain

        with self.blockLock:
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

            chain = self._GetChain(b.parent)
            blockBalances = self._CalculateBalances(b, chain)
            if blockBalances is None:
                Log("Invalid Balances for %s" % b)
                return False

            # Get the parent height     
            self._RemoveTxsFromMemPool(b)

            # Get the parent height   
            parent = self.blocks.get(b.parent, None)
            if parent:
                parentHeight = parent.height
            else:
                parentHeight = 0

            # Update highest if this is indeed the highest
            highestBlock = self.blocks.get(self.highest, None)
            if highestBlock is None or parentHeight == highestBlock.height:
                self.highest = b.GetHash()

            # Set the metadata
            b.height    = parentHeight + 1
            b.timeAdded = utils.GetCurrentTime()
            b.balances  = blockBalances

            # Add the block
            self.blocks[hash] = b
        
        return True

    def AddBlocks(self, blocks):
        for b in blocks:
            self.AddBlock(b)

    def HasBlock(self, hash):
        with self.blockLock:
            return hash in self.blocks

    def GetBlock(self, hash):
        with self.blockLock:
            return self.blocks.get(hash, None)

    def GetChain(self, hash=None):
        with self.blockLock:
            return self._GetChain(hash)

    def GetHighestChain(self):
        with self.blockLock:
            return self._GetChain(self.highest)

    def GetHeight(self):
        with self.blockLock:
            highestBlock = self.blocks.get(self.highest, None)
            if highestBlock is None:
                return 0
            
            return highestBlock.height

    def GetHighestBlockHash(self):
        with self.blockLock:
            return self.highest

    def GetHighestBlock(self):
        with self.blockLock:
            return self.blocks.get(self.highest, None)

    def GetBalance(self, addr):
        with self.blockLock:
            chain = self._GetChain(self.highest)
            return self._GetBalanceInChain(addr, chain)
            
    def Mine(self, miner, privateKey, maxNumTx=MAX_TX_PER_BLOCK):
        Log ("Mining...")
        if not self.HasMemPool():
            return None

        parentHash = self.highest
        if parentHash:
            parentBalances = self.GetBlock(parentHash).balances
        else:
            parentBalances = {}

        # Create the reward transaction
        rewardTx = transaction.Transaction(miner, miner, self.reward)
        # Todo properly sign:
        rewardTx.Sign(privateKey)

        transactions = [ rewardTx ]
        rejected = []
        tmpBalances = { miner : parentBalances.get(miner, 0) + self.reward }

        # Add transactions from mempool, checking if the from addr has enough balance
        with self.mempoolLock:
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
        b = block.Block(parentHash,
                        transactions,
                        utils.GetCurrentTime(),
                        miner)
        
        # Mine it
        while(not self._ValidatePow(b)):
            b.nonce += 1
        
        # Todo properly sign:
        b.Sign(privateKey)

        return b

    def AddTransaction(self, tx):
        txHash = tx.GetHash()

        with self.mempoolLock:
            with self.blockLock:
                if self._IsTxInChain(txHash):
                    return False

            if tx.ValidateSignature():
                if tx.GetHash() not in self.mempool:
                    self.mempool[txHash] = tx

                    # Set the metadata
                    tx.timeAdded = utils.GetCurrentTime()
                    
                return True
            else:
                Log("Tried to add invalid tx: %s" % tx)
                return False

    def HasMemPool(self):
        with self.mempoolLock:
            return len(self.mempool) > 0

    def GetMempoolTransactions(self):
        with self.mempoolLock:
            return self.mempool.values()

    def CleanMempool(self, timestamp):
        for txHash, tx in self.mempool.items():
            if tx.timeAdded < timestamp:
                del self.mempool[txHash]

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

    def _GetChain(self, hash=None):
        chain = []
        while hash is not None:
            b = self.blocks.get(hash, None)
            if not b: return None
            chain.append(b)
            hash = b.parent
        return chain

    def _GetBalanceInChain(self, addr, chain):
        for ancestor in chain:
            balance = ancestor.balances.get(addr, None)
            if balance is not None:
                return balance
        return 0

    def _RemoveTxsFromMemPool(self, b):
       for tx in b.transactions:
           txHash = tx.GetHash()
           if txHash in self.mempool:
               self.mempool.pop(txHash)

    def _IsTxInChain(self, txHash):
        # TODO cache tx hashes?
        chain = self._GetChain(self.highest)
        for b in chain:
            for tx in b.transactions:
                if txHash == tx.GetHash():
                    return True
        return False

