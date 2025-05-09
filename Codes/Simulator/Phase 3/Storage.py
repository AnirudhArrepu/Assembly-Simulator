from .Cache import CacheWithLRU
from .Memory       import Memory

class CacheAndMemory:
    def __init__(self, l1_config: dict, l2_config: dict, memory: Memory, latencies: dict = None):
        """
        Two-level write-back cache (L1, L2) with LRU + main memory.
        Dirty blocks are written back on eviction.
        """
        self.l1 = CacheWithLRU(**l1_config)
        self.l2 = CacheWithLRU(**l2_config)
        self.memory = memory
        self.cycles = 0

        defaults = {
            'l1_hit':  1,
            'l1_miss': 5,
            'l2_hit': 10,
            'l2_miss':20,
            'mem':    100
        }
        self.latencies = { **defaults, **(latencies or {}) }

    def read(self, address: int):
        self.cycles = 0
        print(f"Read request @ {address}")

        # L1
        data = self.l1.getFromCache(address)
        if data is not None:
            self.cycles += self.latencies['l1_hit']
            print(f"L1 hit, cycles={self.cycles}")
            return data

        self.cycles += self.latencies['l1_miss']
        print(f"L1 miss, cycles={self.cycles}")

        # L2
        data = self.l2.getFromCache(address)
        if data is not None:
            self.cycles += self.latencies['l2_hit']
            print(f"L2 hit, cycles={self.cycles}")
            # promote to L1
            self.l1.getToCache(address, self.memory)
            self.cycles += self.latencies['l1_miss']
            print(f"Refilled L1 from L2, cycles={self.cycles}")
            return self.l1.getFromCache(address)

        # Miss both → main memory
        self.cycles += self.latencies['l2_miss']
        print(f"L2 miss, cycles={self.cycles}")
        self.cycles += self.latencies['mem']
        print(f"Access memory, cycles={self.cycles}")

        # Fill L2 then L1
        self.l2.getToCache(address, self.memory)
        self.cycles += self.latencies['l2_miss']
        print(f"Refilled L2, cycles={self.cycles}")

        self.l1.getToCache(address, self.memory)
        self.cycles += self.latencies['l1_miss']
        print(f"Refilled L1, cycles={self.cycles}")

        return self.l1.getFromCache(address)

    def write(self, address: int, value: int):
        """
        Write-back: update L1 & L2 only; dirty blocks go back on eviction.
        """
        self.cycles = 0
        print(f"Write request @ {address} ← {value}")

        # L1 write-allocate
        if self.l1.getFromCache(address) is None:
            self.l1.getToCache(address, self.memory)
            self.cycles += self.latencies['l1_miss']
            print(f"L1 alloc on write, cycles={self.cycles}")
        self.l1.writeToCache(address, value)
        self.cycles += self.latencies['l1_hit']
        print(f"L1 write, cycles={self.cycles}")

        # L2 write-allocate
        if self.l2.getFromCache(address) is None:
            self.l2.getToCache(address, self.memory)
            self.cycles += self.latencies['l2_miss']
            print(f"L2 alloc on write, cycles={self.cycles}")
        self.l2.writeToCache(address, value)
        self.cycles += self.latencies['l2_hit']
        print(f"L2 write, cycles={self.cycles}")

        print(f"Total write cycles = {self.cycles}")

    def get_cycles(self) -> int:
        return self.cycles
