class Memory:
    def __init__(self):
        self.memory = [0] * 1024
        # index%4 is the core it belongs to
        self.core_memory = []

    def printMemory(self):
        core1 = []
        core2 = []
        core3 = []
        core4 = []

        for i,memory in enumerate(self.memory):
            if i%4 == 0:
                core1.append(memory)
            elif i%4 == 1:
                core2.append(memory)
            elif i%4 == 2:
                core3.append(memory)
            elif i%4 == 3:
                core4.append(memory)

        self.core_memory = [core1, core2, core3, core4]

        return self.core_memory

