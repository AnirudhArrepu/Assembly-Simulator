from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np

class Core:
    def __init__(self, coreid, memory):
        self.pc = 0
        self.coreid = coreid
        self.memory = memory
        self.program_label_map = {}
        self.registers = [0] * 32

        self.registers[coreid] = coreid

    def make_labels(self, insts):
        for i, inst in enumerate(insts):
            inst = inst.split(" ")
            if(len(inst) > 4):
                self.program_label_map[inst[0].split(":")[0]] = i

        print(self.program_label_map)

    def execute(self, inst):
        inst = inst.split(" ")

        if(len(inst) > 4):
            # print(inst)
            # self.program_label_map[inst[0][:-1]] = self.pc
            inst.pop(0)

        # print(inst)
        # print(self.pc)

        if(inst[0] == "add"): # add rd, rs1, rs2
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            rs2 = int(inst[3][1:])

            self.registers[rd] = self.registers[rs1] + self.registers[rs2]
            self.pc+=1

        elif(inst[0] == "addi"): # addi rd, rs1, imm
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            imm = int(inst[3])

            self.registers[rd] = self.registers[rs1] + imm
            self.pc+=1

        elif(inst[0] == "sub"): # sub rd, rs1, rs2
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            rs2 = int(inst[3][1:])

            self.registers[rd] = self.registers[rs1] - self.registers[rs2]
            self.pc+=1
        
        elif(inst[0] == "lw"): #lw rd offest(rs1)
            rd = int(inst[1][1:])
            offset, rs1 = inst[2].split('(')
            rs1 = int(rs1[:-1][1:])
            mem_addr = self.registers[rs1] + int(offset)
            
            self.registers[rd] = self.memory.memory[4*mem_addr + self.coreid]
            self.pc+=1
            
        elif(inst[0] == "sw"): #sw rs1 offest(rd)
            rs1 = int(inst[1][1:])
            offset, rd = inst[2].split('(')
            rd = int(rd[:-1][1:])
            mem_addr = self.registers[rd] + int(offset)

            self.memory.memory[4*mem_addr + self.coreid] = self.registers[rs1]
            self.pc+=1
            
        elif(inst[0] == "bne"): #bne rs1, rs2, label
            rs1 = int(inst[1][1:])
            rs2 = int(inst[2][1:])
            label = inst[3]

            if(self.registers[rs1] != self.registers[rs2]):
                self.pc = self.program_label_map[label]
                # print(self.pc)
            else:
                self.pc+=1

        elif(inst[0] == "jal"): #jal rd, label
            rd = int(inst[1][1:])
            label = inst[2]

            self.registers[rd] = self.pc + 1
            self.pc = self.program_label_map[label]
            # print(self.pc)

        elif(inst[0] == "jr"): #jr rs1
            rs1 = int(inst[1][1:])

            self.pc = self.registers[rs1]

class Memory:
    def __init__(self):
        self.memory = [0] * 1024
        # index%4 is the core it belongs to


class Simulator:
    def __init__(self):
        self.memory = Memory()
        self.cores = [Core(i, self.memory) for i in range(4)]
        self.program = []
        self.clock = 0

    def make_labels(self):
        for core in self.cores:
            core.make_labels(self.program)

    def run(self):
        while True:
            if(self.cores[0].pc >= len(self.program)):
                break

            # with ThreadPoolExecutor(max_workers=4) as executor:
            for core in self.cores:
                # print(core.pc)
                print(self.program[core.pc], core.pc)
                core.execute(self.program[core.pc])
                # executor.submit(core.execute, self.program[core.pc])
                # core.pc += 1
            
            self.clock += 1

programs = [
    "addi x9 x0 10",
    "addi x3 x0 4",
    "sw x3 0(x9)",
    "addi x8 x9 0",
    "addi x9 x9 4",
    "sw x3 0(x9)",
    "lw x6 4(x8)"
]

sim = Simulator()
sim.program = programs
sim.make_labels()
sim.run()

print(sim.cores[0].registers)
print(sim.cores[1].registers)
print(sim.cores[2].registers)
print(sim.cores[3].registers)

# plt.figure(figsize=(16, 8))
# data = np.array([sim.cores[i].registers for i in range(4)])
# plt.imshow(data, cmap="Blues")
# for i in range(4):
#     for j in range(32):
#         plt.text(j, i, str(sim.cores[i].registers[j]))
# plt.show()
# plt.axis('off')

print(f"number of clock cycles: {sim.clock}")