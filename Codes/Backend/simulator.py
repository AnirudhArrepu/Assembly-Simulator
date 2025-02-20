from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np

from flask import Flask, request, jsonify
from flask_cors import CORS

class Core:
    def __init__(self, coreid, memory):
        self.pc = 0
        self.coreid = coreid
        self.memory = memory
        self.program_label_map = {}
        self.registers = [0] * 32

        self.data_segment = {}
        self.memory_data_index = 1020

        self.registers[31] = coreid

    def make_labels(self, insts):
        for i, inst in enumerate(insts):
            inst = inst.split(" ")
            if(len(inst[0].split(":")) >= 2):
                self.program_label_map[inst[0].split(":")[0]] = i

        print(self.program_label_map)

    def execute(self, inst):
        inst = inst.split(" ")

        if(len(inst[0].split(":")) >= 2):
            # print(inst, "inst length greater than 4")
            # self.program_label_map[inst[0][:-1]] = self.pc
            inst.pop(0)

        # print(inst)
        # print(self.pc)
        if(inst[0] == "la"): # la rs, data
            rs = int(inst[1][1:])
            data = inst[2]
            for val in self.data_segment[data]:
                self.memory.memory[self.memory_data_index + self.coreid] = val
                print(self.memory_data_index)
                self.memory_data_index -= 4
            
            self.registers[rs] = self.memory_data_index + 4
            self.pc+=1

        elif(inst[0] == "add"): # add rd, rs1, rs2
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
            print(inst)
            rd = int(inst[1][1:])
            offset, rs1 = inst[2].split('(')
            rs1 = int(rs1[:-1][1:])
            mem_addr = self.registers[rs1] + int(offset)
            print(mem_addr)
            self.registers[rd] = self.memory.memory[mem_addr + self.coreid]
            self.pc+=1

            print(self.registers[rs1])
            print(self.registers[rd])
            
        elif(inst[0] == "sw"): #sw rs1 offest(rd)
            print(inst)
            rs1 = int(inst[1][1:])
            offset, rd = inst[2].split('(')
            rd = int(rd[:-1][1:])
            mem_addr = self.registers[rd] + int(offset)
            print(mem_addr)

            self.memory.memory[mem_addr + self.coreid] = self.registers[rs1]
            self.pc+=1

            print(self.registers[rd])
            print(self.registers[rs1])
            
        elif(inst[0] == "bne"): #bne rs1, rs2, label
            rs1 = int(inst[1][1:])
            rs2 = int(inst[2][1:])
            label = inst[3]

            if(self.registers[rs1] != self.registers[rs2]):
                self.pc = self.program_label_map[label]
                # print(self.pc)
            else:
                self.pc+=1

        elif(inst[0] == "ble"): #ble rs1, rs2, label
            rs1 = int(inst[1][1:])
            rs2 = int(inst[2][1:])
            label = inst[3]

            if(self.registers[rs1] <= self.registers[rs2]):
                self.pc = self.program_label_map[label]
                # print(self.pc)
            else:
                self.pc+=1

        elif(inst[0] == "beq"): #bne rs1, rs2, label
            rs1 = int(inst[1][1:])
            rs2 = int(inst[2][1:])
            label = inst[3]

            if(self.registers[rs1] == self.registers[rs2]):
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

        elif inst[0] == "slt":  # slt rd, rs1, rs2
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            rs2 = int(inst[3][1:])
            self.registers[rd] = 1 if self.registers[rs1] < self.registers[rs2] else 0
            self.pc += 1

        elif inst[0] == "j":  # j label  (unconditional jump: equivalent to jal x0, label)
            label = inst[1]
            self.pc = self.program_label_map[label]
        
        else: 
            print("instruction not defined", inst[0], self.pc)


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



class Simulator:
    def __init__(self):
        self.memory = Memory()
        self.cores = [Core(i, self.memory) for i in range(4)]
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
        while True:
            if(self.cores[0].pc >= len(self.program)):
                break

            # with ThreadPoolExecutor(max_workers=4) as executor:
            for core in self.cores:
                # print(core.pc)
                # print(self.program[core.pc], core.pc)
                core.execute(self.program[core.pc])
                # executor.submit(core.execute, self.program[core.pc])
                # core.pc += 1
            
            self.clock += 1

program = '''
.data
arr: .word 0x144 0x3 0x9 0x8 0x1 0x100

.text
la x3 arr
addi x4 x0 6
addi x7 x0 0
outer_loop: addi x11 x4 -1
beq x7 x11 outer_exit
addi x10 x3 0
addi x8 x0 0
inner_loop: addi x12 x4 0
sub x12 x12 x7
addi x12 x12 -1
beq x8 x12 inner_exit
lw x5 0(x10)
lw x6 4(x10)
slt x11 x6 x5
beq x11 x0 no_swap
sw x5 4(x10)
sw x6 0(x10)
no_swap: addi x10 x10 4
addi x8 x8 1
j inner_loop
inner_exit: addi x7 x7 1
j outer_loop
outer_exit: j exit
exit: addi x0 x0 0
'''


def preprocess(program):
    #getting data segment
    programs = program.split(".text")
    programs_data = programs[0].split(".data")[1].split("\n")
    programs_data = [inst for inst in programs_data if inst != '']
    print(programs_data)

    #getting text segment
    programs_text = programs[1]
    programs = programs_text.split("\n")
    programs_text = [inst for inst in programs if inst != '']
    print(programs_text)

    return programs_text, programs_data

def main(program):
    programs_text, programs_data = preprocess(program)
    sim = Simulator()
    sim.program = programs_text
    sim.make_data_segment(programs_data)
    sim.make_labels()
    sim.run()

    print(sim.cores[0].registers)
    print(sim.cores[1].registers)
    print(sim.cores[2].registers)
    print(sim.cores[3].registers)

    print(f"number of clock cycles: {sim.clock}")

    return sim

app = Flask(__name__)
CORS(app)

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    program = data['program']
    sim = main(program)

    memories = sim.memory.printMemory()

    return jsonify({
        'core0': sim.cores[0].registers,
        'core1': sim.cores[1].registers,
        'core2': sim.cores[2].registers,
        'core3': sim.cores[3].registers,
        'clock': sim.clock,
        'memory1': memories[0]
        'memory2': memories[1]
        'memory3': memories[2]
        'memory4': memories[3]
    })

if __name__ == "__main__":
    app.run(debug=True)


# sim = Simulator()
# sim.program = programs_text
# sim.make_data_segment(programs_data)
# sim.make_labels()
# sim.run()

# print(sim.cores[0].registers)
# print(sim.cores[1].registers)
# print(sim.cores[2].registers)
# print(sim.cores[3].registers)

# # plt.figure(figsize=(16, 8))
# # data = np.array([sim.cores[i].registers for i in range(4)])
# # plt.imshow(data, cmap="Blues")
# # for i in range(4):
# #     for j in range(32):
# #         plt.text(j, i, str(sim.cores[i].registers[j]))
# # plt.show()
# # plt.axis('off')

# print(f"number of clock cycles: {sim.clock}")


# print(sim.memory.memory)