import math

class CacheWithLRU:
    def __init__(self, cache_size=1024, block_size=64, associativity=4):
        self.cache_size = cache_size
        self.block_size = block_size
        self.associativity = associativity
        self.num_sets = cache_size // (block_size * associativity)
        self.timestamp = 0

        self.cache = []
        for _ in range(self.num_sets):
            cache_set = []
            for _ in range(self.associativity):
                block = {
                    "valid": False,
                    "tag": None,
                    "data": [0] * block_size,
                    "last_used": -1
                }
                cache_set.append(block)
            self.cache.append(cache_set)

    def get(self, address, address_size=40):
        self.timestamp += 1
        address_bin = format(address, f'0{address_size}b')

        offset_bits = int(math.log2(self.block_size))
        index_bits = int(math.log2(self.num_sets))
        tag_bits = address_size - index_bits - offset_bits

        tag = address_bin[:tag_bits]
        index = address_bin[tag_bits:tag_bits + index_bits]
        offset = address_bin[tag_bits + index_bits:]

        tag_val = int(tag, 2)
        index_val = int(index, 2)
        offset_val = int(offset, 2)

        cache_set = self.cache[index_val]
        for block in cache_set:
            if block["valid"] and block["tag"] == tag_val:
                block["last_used"] = self.timestamp 
                print("hit")
                return block["data"][offset_val]

        print("cache miss")
        return None

    def put(self, address, data, address_size=40):
        self.timestamp += 1
        address_bin = format(address, f'0{address_size}b')

        offset_bits = int(math.log2(self.block_size))
        index_bits = int(math.log2(self.num_sets))
        tag_bits = address_size - index_bits - offset_bits

        tag = address_bin[:tag_bits]
        index = address_bin[tag_bits:tag_bits + index_bits]
        offset = address_bin[tag_bits + index_bits:]

        tag_val = int(tag, 2)
        index_val = int(index, 2)
        offset_val = int(offset, 2)

        cache_set = self.cache[index_val]

        #updating if tag already exists and is valid
        for block in cache_set:
            if block["valid"] and block["tag"] == tag_val:
                block["data"][offset_val] = data
                block["last_used"] = self.timestamp
                print("Cache UPDATE ✅")
                return

        #put in invalidated blocks
        for block in cache_set:
            if not block["valid"]:
                block["valid"] = True
                block["tag"] = tag_val
                block["data"][offset_val] = data
                block["last_used"] = self.timestamp
                print("Cache INSERT (empty block) ✅")
                return

        #lru
        lru_block = min(cache_set, key=lambda blk: blk["last_used"])
        print(f"Cache REPLACE (LRU) Tag {lru_block['tag']} replaced with {tag_val}")
        lru_block["tag"] = tag_val
        lru_block["data"] = [0] * self.block_size
        lru_block["data"][offset_val] = data
        lru_block["valid"] = True
        lru_block["last_used"] = self.timestamp
