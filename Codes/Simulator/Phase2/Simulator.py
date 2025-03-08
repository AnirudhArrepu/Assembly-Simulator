from Memory import Memory
from Core import Core
from CoreWithForwarding import CoreWithForwarding

class Simulator:
    def __init__(self, forwarding=False):
        self.memory = Memory()
        self.forwarding = forwarding
        if not self.forwarding:
            self.cores = [Core(i, self.memory) for i in range(4)]
        else:
            self.cores = [CoreWithForwarding(i, self.memory) for i in range(4)]
        self.program = []
        self.clock = 0
        self.data_segment = {}

    def make_data_segment(self, program_data):
        for data in program_data:
            values_data = data.split(".word")[1].split(" ")
            values_data = [int(value, 16) for value in values_data if value != '']
            values_data.reverse()
            self.data_segment[data.split(":")[0]] = values_data

        for core in self.cores:
            core.data_segment = self.data_segment

    def make_labels(self):
        for core in self.cores:
            core.make_labels(self.program)

    def run(self):
        for core in self.cores:
            core.pipeline_reg = {
                "IF": None,
                "ID": None,
                "EX": None,
                "MEM": None,
                "WB": None,
            }

        while not all(core.pc >= len(self.program) and core.pipeline_empty() for core in self.cores):
            # print(self.program[self.cores[0].pc])
            for core in self.cores:
                core.pipeline_cycle()
            self.clock += 1
        self.clock -= 1

        print("clock cycles:", self.clock)
