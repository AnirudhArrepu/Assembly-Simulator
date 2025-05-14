import math

class CacheWithLRU:
    def __init__(self, cache_size=1024, block_size=64, associativity=4):
        self.cache_size   = cache_size
        self.block_size   = block_size
        self.associativity= associativity
        self.num_sets     = cache_size // (block_size * associativity)
        self.timestamp    = 0

        self.cache = []
        for _ in range(self.num_sets):
            cache_set = []
            for _ in range(self.associativity):
                cache_set.append({
                    "valid":     False,
                    "tag":       None,
                    "data":      [0] * block_size,
                    "dirty":     False,
                    "last_used": -1
                })
            self.cache.append(cache_set)

    def _split_address(self, address, address_size=40):
        address_bin  = format(address, f'0{address_size}b')
        offset_bits  = int(math.log2(self.block_size))
        index_bits   = int(math.log2(self.num_sets))
        tag_bits     = address_size - index_bits - offset_bits

        tag    = int(address_bin[:tag_bits], 2)
        index  = int(address_bin[tag_bits: tag_bits+index_bits], 2)
        offset = int(address_bin[tag_bits+index_bits:], 2)
        return tag, index, offset

    def getFromCache(self, address, address_size=40):
        self.timestamp += 1
        tag, index, offset = self._split_address(address, address_size)
        cache_set = self.cache[index]

        for block in cache_set:
            if block["valid"] and block["tag"] == tag:
                block["last_used"] = self.timestamp
                print(f"Cache hit at set {index}, tag {tag}")
                return block["data"][offset]

        print(f"Cache miss at set {index}")
        return None

    def getToCache(self, address, memory, l2_cache = None, address_size=40):
        """
        Load the block containing `address` from main memory into cache.
        If eviction of a dirty block is needed, write it back first.
        """
        self.timestamp += 1
        tag, index, offset = self._split_address(address, address_size)
        cache_set = self.cache[index] 
        
        base_addr = address - offset
        block_data = memory.memory[base_addr : base_addr + self.block_size]

        # If block already present, refresh data & clear dirty
        for block in cache_set:
            if block["valid"] and block["tag"] == tag:
                block.update({
                    "data":      list(block_data),
                    "dirty":     False,
                    "last_used": self.timestamp
                })
                print(f"Cache UPDATE at set {index}, tag {tag}")
                return

        # Look for an invalid slot
        for block in cache_set:
            if not block["valid"]:
                block.update({
                    "valid":     True,
                    "tag":       tag,
                    "data":      list(block_data),
                    "dirty":     False,
                    "last_used": self.timestamp
                })
                print(f"Cache INSERT (empty) at set {index}, tag {tag}")
                return

        # Evict LRU block
        lru_block = min(cache_set, key=lambda b: b["last_used"])
        if lru_block["dirty"]:
            old_tag = lru_block["tag"]
            # Reconstruct its base address
            offset_bits = int(math.log2(self.block_size))
            index_bits  = int(math.log2(self.num_sets))
            evict_base = (old_tag << (index_bits + offset_bits)) | (index << offset_bits)
            # Write back
            for i in range(self.block_size):
                addr = evict_base + i
                value = lru_block["data"][i]
                memory.memory[addr] = value
                
                # Also write back to L2 if present
                if l2_cache:
                    l2_cache.writeToCache(addr, value, address_size=address_size)
                    
            print(f"Write-back eviction: set {index}, tag {old_tag} → memory")

        # Replace
        lru_block.update({
            "tag":       tag,
            "data":      list(block_data),
            "dirty":     False,
            "last_used": self.timestamp
        })
        print(f"Cache REPLACE LRU at set {index}, new tag {tag}")

    def writeToCache(self, address, value, address_size=40):
        """
        Update cache block containing `address` (must already be loaded),
        mark it dirty.
        """
        self.timestamp += 1
        tag, index, offset = self._split_address(address, address_size)
        cache_set = self.cache[index]
        for block in cache_set:
            if block["valid"] and block["tag"] == tag:
                block["data"][offset] = value
                block["dirty"]        = True
                block["last_used"]    = self.timestamp
                print(f"Cache write at set {index}, tag {tag}, offset {offset}")
                return
        print(f"Warning: writeToCache miss at set {index}, tag {tag}")



class CacheWithSRRIP:
    def __init__(self, cache_size=1024, block_size=64, associativity=4, rrpv_bits=2):
        self.cache_size   = cache_size
        self.block_size   = block_size
        self.associativity= associativity
        self.num_sets     = cache_size // (block_size * associativity)
        self.max_rrpv     = (1 << rrpv_bits) - 1  # 2-bit RRPV max = 3

        self.cache = []
        for _ in range(self.num_sets):
            cache_set = []
            for _ in range(self.associativity):
                cache_set.append({
                    "valid": False,
                    "tag": None,
                    "data": [0] * block_size,
                    "dirty": False,
                    "rrpv": self.max_rrpv  # Initially max, so considered least useful
                })
            self.cache.append(cache_set)

    def _split_address(self, address, address_size=40):
        address_bin  = format(address, f'0{address_size}b')
        offset_bits  = int(math.log2(self.block_size))
        index_bits   = int(math.log2(self.num_sets))
        tag_bits     = address_size - index_bits - offset_bits

        tag    = int(address_bin[:tag_bits], 2)
        index  = int(address_bin[tag_bits: tag_bits+index_bits], 2)
        offset = int(address_bin[tag_bits+index_bits:], 2)
        return tag, index, offset

    def getFromCache(self, address, address_size=40):
        tag, index, offset = self._split_address(address, address_size)
        cache_set = self.cache[index]

        for block in cache_set:
            if block["valid"] and block["tag"] == tag:
                block["rrpv"] = 0  # On hit, reset RRPV
                print(f"Cache hit at set {index}, tag {tag}")
                return block["data"][offset]

        print(f"Cache miss at set {index}")
        return None

    def getToCache(self, address, memory, l2_cache=None, address_size=40):
        tag, index, offset = self._split_address(address, address_size)
        cache_set = self.cache[index]

        base_addr = address - offset
        block_data = memory.memory[base_addr : base_addr + self.block_size]

        # Refresh if already present
        for block in cache_set:
            if block["valid"] and block["tag"] == tag:
                block.update({
                    "data": list(block_data),
                    "dirty": False,
                    "rrpv": 0
                })
                print(f"Cache UPDATE at set {index}, tag {tag}")
                return

        # Look for invalid block
        for block in cache_set:
            if not block["valid"]:
                block.update({
                    "valid": True,
                    "tag": tag,
                    "data": list(block_data),
                    "dirty": False,
                    "rrpv": self.max_rrpv - 1  # Insert with RRPV = 2
                })
                print(f"Cache INSERT (empty) at set {index}, tag {tag}")
                return

        # SRRIP replacement: find block with RRPV = max
        while True:
            for block in cache_set:
                if block["rrpv"] == self.max_rrpv:
                    # Evict this block
                    if block["dirty"]:
                        old_tag = block["tag"]
                        offset_bits = int(math.log2(self.block_size))
                        index_bits  = int(math.log2(self.num_sets))
                        evict_base = (old_tag << (index_bits + offset_bits)) | (index << offset_bits)

                        for i in range(self.block_size):
                            addr = evict_base + i
                            memory.memory[addr] = block["data"][i]
                            if l2_cache:
                                l2_cache.writeToCache(addr, block["data"][i], address_size=address_size)
                        print(f"Write-back eviction: set {index}, tag {old_tag} → memory")

                    # Replace it
                    block.update({
                        "valid": True,
                        "tag": tag,
                        "data": list(block_data),
                        "dirty": False,
                        "rrpv": self.max_rrpv - 1  # Insert with RRPV = 2
                    })
                    print(f"Cache REPLACE at set {index}, tag {tag}")
                    return

            # No block with RRPV == max, increment all RRPVs
            for block in cache_set:
                if block["rrpv"] < self.max_rrpv:
                    block["rrpv"] += 1

    def writeToCache(self, address, value, address_size=40):
        tag, index, offset = self._split_address(address, address_size)
        cache_set = self.cache[index]
        for block in cache_set:
            if block["valid"] and block["tag"] == tag:
                block["data"][offset] = value
                block["dirty"] = True
                block["rrpv"] = 0  # Re-reference prediction reset
                print(f"Cache write at set {index}, tag {tag}, offset {offset}")
                return
        print(f"Warning: writeToCache miss at set {index}, tag {tag}")