from concurrent.futures import ThreadPoolExecutor

class Core:
    def __init__(self, coreid):
        self.pc = 0
        self.coreid = coreid
        self.memory = Memory()
        self.program_label_map = {}
        self.registers = [0] * 32

        self.registers[coreid] = coreid

    def execute(self, inst):
        inst = inst.split(" ")

        if(len(inst) == 0):
            self.program_label_map[inst[0][:-1]] = self.pc
            inst = inst[1:]

        if(inst[0] == "add"): # add rd, rs1, rs2
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            rs2 = int(inst[3][1:])

            self.registers[rd] = self.registers[rs1] + self.registers[rs2]

        elif(inst[0] == "addi"): # addi rd, rs1, imm
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            imm = int(inst[3])

            self.registers[rd] = self.registers[rs1] + imm

        elif(inst[0] == "sub"): # sub rd, rs1, rs2
            rd = int(inst[1][1:])
            rs1 = int(inst[2][1:])
            rs2 = int(inst[3][1:])

            self.registers[rd] = self.registers[rs1] - self.registers[rs2]
        
        elif(inst[0] == "lw"): #lw rd offest(rs1)
            rd = int(inst[1][1:])
            offset, rs1 = inst[2].split('(')
            rs1 = int(rs1[:-1][1:])
            mem_addr = self.registers[rs1] + offset
            
            self.registers[rd] = self.memory.memory[mem_addr + self.coreid]
            
        elif(inst[0] == "sw"): #sw rs1 offest(rd)
            rs1 = int(inst[1][1:])
            offset, rd = inst[2].split('(')
            rd = int(rd[:-1][1:])
            mem_addr = self.registers[rd] + offset

            self.memory.memory[mem_addr + self.coreid] = self.registers[rs1]
            
        elif(inst[0] == "bne"): #bne rs1, rs2, label
            rs1 = int(inst[1][1:])
            rs2 = int(inst[2][1:])
            label = inst[3]

            if(self.registers[rs1] != self.registers[rs2]):
                self.pc = self.program_label_map[label]

        elif(inst[0] == "jal"): #jal rd, label
            rd = int(inst[1][1:])
            label = inst[2]

            self.registers[rd] = self.pc + 1
            self.pc = self.program_label_map[label]

        elif(inst[0] == "jr"): #jr rs1
            rs1 = int(inst[1][1:])

            self.pc = self.registers[rs1]


class Memory:
    def __init__(self):
        self.memory = [0] * 1000
        # index%4 is the core it belongs to


class Simulator:
    def __init__(self):
        self.cores = [Core(i) for i in range(4)]
        self.program = []
        self.clock = 0

    def run(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            while True:
                if(self.clock >= len(self.program)):
                    break
                
                for core in self.cores:
                    executor.submit(core.execute, self.program[core.pc])
                    core.pc += 1
                
                self.clock += 1