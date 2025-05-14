import yaml
from Cache import CacheWithLRU
from Memory import Memory
import math

class CacheAndMemory:
    """
    Multi‑core (4) with private L1‑I / L1‑D and shared L2 + Memory.
    Write‑back + write‑allocate.
    """

    def __init__(self,
                 config_path: str,
                 memory: Memory,
                 latencies: dict = None,
                 num_cores: int = 4):
        self.num_cores = num_cores
        self.memory = memory
        self.cycles = 0

        # Load cache config from YAML
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        l1i_config = config['l1i_config']
        l1d_config = config['l1d_config']
        l2_config  = config['l2_config']
        scratch_pad_config = config['scratch_pad_config']

        self.l1d_config = l1d_config

        # per‑core private caches
        self.l1i = [ CacheWithLRU(**l1i_config) for _ in range(num_cores) ]
        self.l1d = [ CacheWithLRU(**l1d_config) for _ in range(num_cores) ]
        self.scratch_pad = [ [0]*scratch_pad_config["size"] for _ in range(num_cores)]
        print(f"Scratch pad size: {scratch_pad_config['size']}")
        print(f"Scratch pad: {self.scratch_pad}")

        # shared
        self.l2 = CacheWithLRU(**l2_config)

        defaults = {
            'l1_hit':  1,
            'l1_miss': 3,
            'l2_hit':  4,
            'l2_miss': 6,
            'mem':     10,
            'scratch_pad': 1,
        }
        self.latencies = { **defaults, **(latencies or {}) }

        print(f"Cache latencies: {self.latencies}")

    def read_scratch_pad(self, core_id: int, address: int) -> int:
        """
        Read from scratch pad memory.
        Returns the word; updates self.cycles.
        """
        self.cycles = 0
        data = self.scratch_pad[core_id][address]
        self.cycles += self.latencies['scratch_pad']
        return data, self.cycles
    
    def write_scratch_pad(self, core_id: int, address: int, value: int):
        """
        Write to scratch pad memory.
        Returns the word; updates self.cycles.
        """
        self.cycles = 0
        self.scratch_pad[core_id][address] = value
        self.cycles += self.latencies['scratch_pad']
        return self.cycles

    def read(self, core_id: int, address: int, is_instruction: bool=False) -> int:
        """
        Read from L1‑I or L1‑D; on miss go to L2, then memory.
        Returns the word; updates self.cycles.
        """
        self.cycles = 0
        l1 = self.l1i[core_id] if is_instruction else self.l1d[core_id]

        # L1
        data = l1.getFromCache(address)
        if data is not None:
            self.cycles += self.latencies['l1_hit']
            return data, self.cycles

        # L1 miss
        self.cycles += self.latencies['l1_miss']

        # L2
        data = self.l2.getFromCache(address)
        if data is not None:
            self.cycles += self.latencies['l2_hit']
            # promote to L1
            l1.getToCache(address, self.memory, self.l2)
            return l1.getFromCache(address), self.cycles

        # L2 miss
        self.cycles += self.latencies['l2_miss']
        # memory
        self.cycles += self.latencies['mem']

        # fill L2 then L1
        self.l2.getToCache(address, self.memory)

        l1.getToCache(address, self.memory, self.l2)

        return l1.getFromCache(address), self.cycles

    def write(self, core_id: int, address: int, value: int):
        """
        Write‑back/write‑allocate:
         - allocate in L1‑D & L2 on miss, then write both.
        """
        self.cycles = 0
        l1 = self.l1d[core_id]

        # L1‑D write‑allocate
        if l1.getFromCache(address) is None:
            l1.getToCache(address, self.memory, self.l2)
            self.cycles += self.latencies['l1_miss']
        l1.writeToCache(address, value)
        self.cycles += self.latencies['l1_hit']

        # L2 write‑allocate
        if self.l2.getFromCache(address) is None:
            self.l2.getToCache(address, self.memory)
            self.cycles += self.latencies['l2_miss']
        self.l2.writeToCache(address, value)
        self.cycles += self.latencies['l2_hit']

        return self.cycles
    
    def flush_l1_dirty_to_l2(self, core_id: int) -> int:
        """
        Write-back all dirty blocks from L1‑D of the given core into shared L2.
        Returns accumulated stall cycles.
        """
        self.cycles = 0
        l1 = self.l1d[core_id]

        print("flushing l1 of core ", core_id)

        # address splitting parameters
        offset_bits = int(math.log2(l1.block_size))
        index_bits  = int(math.log2(l1.num_sets))

        # iterate each set and block in L1-D
        for set_idx, cache_set in enumerate(l1.cache):
            for block in cache_set:
                if block['valid'] and block['dirty']:
                    tag = block['tag']
                    # reconstruct base address of this block
                    base_addr = (tag << (index_bits + offset_bits)) | (set_idx << offset_bits)

                    # write-allocate in L2 if missing
                    if self.l2.getFromCache(base_addr) is None:
                        self.l2.getToCache(base_addr, self.memory)

                    # write each word of the block into L2 (write-back style)
                    for i, val in enumerate(block['data']):
                        self.l2.writeToCache(base_addr + i, val)

                    # clear dirty bit in L1
                    block['dirty'] = False

        
        self.l1d = [ CacheWithLRU(**self.l1d_config) for _ in range(self.num_cores) ]

        return self.latencies['l1_hit'] + self.latencies['l2_hit']

    def get_cycles(self) -> int:
        return self.cycles