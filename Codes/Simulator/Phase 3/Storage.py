import yaml
from Cache import CacheWithLRU
from Memory import Memory

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

        # per‑core private caches
        self.l1i = [ CacheWithLRU(**l1i_config) for _ in range(num_cores) ]
        self.l1d = [ CacheWithLRU(**l1d_config) for _ in range(num_cores) ]

        # shared
        self.l2 = CacheWithLRU(**l2_config)

        defaults = {
            'l1_hit':  1,
            'l1_miss': 3,
            'l2_hit':  4,
            'l2_miss': 6,
            'mem':     10
        }
        self.latencies = { **defaults, **(latencies or {}) }

        print(f"Cache latencies: {self.latencies}")

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
            l1.getToCache(address, self.memory)
            return l1.getFromCache(address), self.cycles

        # L2 miss
        self.cycles += self.latencies['l2_miss']
        # memory
        self.cycles += self.latencies['mem']

        # fill L2 then L1
        self.l2.getToCache(address, self.memory)

        l1.getToCache(address, self.memory)

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
            l1.getToCache(address, self.memory)
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

    def get_cycles(self) -> int:
        return self.cycles
