class Memory:
    def __init__(self):
        self.memory = [0] *4096
        self.core_memory = []

    def printMemory(self):
        core1 = []

        for i,memory in enumerate(self.memory):
            if i%4 == 0:
                core1.append(memory)

        self.core_memory = core1

        return self.core_memory

