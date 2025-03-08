import numpy as np
import matplotlib.pyplot as plt

INSTRUCTION_LATENCY = {
    'ADD': 1,
    'SUB': 1,
    'MUL': 2,
    'MOD': 2,
    'AND': 1,
    'OR': 1,
    'XOR': 1,
    'SLL': 1,
    'ADDI': 1,
    'XORI': 1,
    'ANDI': 1,
    'ORI': 1,
    'SLLI': 1,
    'LW': 2,
    'SW': 2,
    'MV': 1,
    'LI': 1,
    'J': 1,
    'JAL': 1,
    'BNE': 1,
}

class Cores:
    def __init__(self, cid, mem_start, mem_size, labels, data_forwarding):
        self.registers = [0] * 32
        self.registers[31] = cid  # Core ID Register (Read-Only)
        self.pc = 0
        self.coreid = cid
        self.mem_start = mem_start
        self.mem_size = mem_size
        self.labels = labels
        self.pipeline = {
            'IF': None,
            'ID': None,
            'EX1': None,
            'EX2': None,
            'MEM': None,
            'WB': None
        }
        self.pipeline_latency = {
            'EX1': 0,
            'EX2': 0
        }
        self.stall = False
        self.stall_count = 0
        self.branch_stall = False
        self.data_forwarding = data_forwarding

    def detect_hazards(self):
        """ Improved hazard detection and stall logic. """
        id_stage = self.pipeline['ID']
        ex1_stage = self.pipeline['EX1']
        ex2_stage = self.pipeline['EX2']
        mem_stage = self.pipeline['MEM']

        if not id_stage:
            self.stall = False
            return

        # Extracting destination and source registers for the ID stage
        id_opcode = id_stage[0]
        id_rd = id_rs1 = id_rs2 = None

        if id_opcode in ["ADD", "SUB", "MUL", "MOD", "AND", "OR", "XOR", "SLL"]:
            id_rd = int(id_stage[1][1:])
            id_rs1 = int(id_stage[2][1:])
            id_rs2 = int(id_stage[3][1:])
        elif id_opcode in ["ADDI", "XORI", "ANDI", "ORI", "SLLI"]:
            id_rd = int(id_stage[1][1:])
            id_rs1 = int(id_stage[2][1:])
        elif id_opcode == "LW":
            id_rd = int(id_stage[1][1:])
            id_rs1 = int(id_stage[2].split('(')[1][1:-1])
        elif id_opcode == "SW":
           id_rs2 = int(id_stage[1][1:])  # Source register (value to store)
           offset, id_rs1 = id_stage[2].split('(')  # Split offset and base register
           id_rs1 = int(id_rs1[:-1][1:])  # Extract base register (rs1)
        elif id_opcode == "BNE":
             id_rs1 = int(id_stage[1][1:])  # First source register
             id_rs2 = int(id_stage[2][1:])  # Second source register
        # Helper function to extract destination register from previous stages
        def get_rd(stage):
            if stage:
                opcode = stage[0]
                if opcode in ["ADD", "SUB", "MUL", "MOD", "AND", "OR", "XOR", "SLL",
                              "ADDI", "XORI", "ANDI", "ORI", "SLLI", "LW" ,"SW"]:
                    return int(stage[1][1:])
            return None

        # Extracting destination registers from EX1, EX2, and MEM stages
        ex1_rd = get_rd(ex1_stage)
        ex2_rd = get_rd(ex2_stage)
        mem_rd = get_rd(mem_stage)

        # Check for RAW hazard (ID depends on EX1, EX2, or MEM)
        if (id_rs1 == ex1_rd or id_rs2 == ex1_rd) and ex1_rd is not None:
            if self.data_forwarding:
                self.forward_data('EX1', id_rs1, id_rs2)
                self.stall = False
            else:
                self.stall = True
        elif (id_rs1 == ex2_rd or id_rs2 == ex2_rd) and ex2_rd is not None:
            if self.data_forwarding:
                self.forward_data('EX2', id_rs1, id_rs2)
                self.stall = False
            else:
                self.stall = True
        
        elif (id_rs1 == mem_rd or id_rs2 == mem_rd) and mem_rd is not None:
            if self.data_forwarding:
                self.forward_data('MEM', id_rs1, id_rs2)
                self.stall = False
            else:
                self.stall = True
        else:
            self.stall = False

        # Special case: Load-Use Hazard (if LW in EX1 or EX2 affects ID stage)
        if (ex1_stage and ex1_stage[0] == "LW" and (id_rs1 == ex1_rd or id_rs2 == ex1_rd)) or \
           (ex2_stage and ex2_stage[0] == "LW" and (id_rs1 == ex2_rd or id_rs2 == ex2_rd)):
            self.stall = True
        if (ex1_stage and ex1_stage[0] == "SW" and (id_rs1 == ex1_rd or id_rs2 == ex1_rd)) or \
           (ex2_stage and ex2_stage[0] == "SW" and (id_rs1 == ex2_rd or id_rs2 == ex2_rd)):
            self.stall = True
        # Increment stall count if stalling
        if self.stall and self.pipeline['ID']:
            self.stall_count += 1

    def forward_data(self, stage, id_rs1, id_rs2):
        if stage == 'EX1' and self.pipeline['EX1']:
            if int(self.pipeline['EX1'][1][1:]) == id_rs1:
                self.registers[id_rs1] = self.registers[int(self.pipeline['EX1'][1][1:])]
            if int(self.pipeline['EX1'][1][1:]) == id_rs2:
                self.registers[id_rs2] = self.registers[int(self.pipeline['EX1'][1][1:])]
        elif stage == 'EX2' and self.pipeline['EX2']:
            if int(self.pipeline['EX2'][1][1:]) == id_rs1:
                self.registers[id_rs1] = self.registers[int(self.pipeline['EX2'][1][1:])]
            if int(self.pipeline['EX2'][1][1:]) == id_rs2:
                self.registers[id_rs2] = self.registers[int(self.pipeline['EX2'][1][1:])]
        elif stage == 'MEM' and self.pipeline['MEM']:
            if int(self.pipeline['MEM'][1][1:]) == id_rs1:
                self.registers[id_rs1] = self.registers[int(self.pipeline['MEM'][1][1:])]
            if int(self.pipeline['MEM'][1][1:]) == id_rs2:
                self.registers[id_rs2] = self.registers[int(self.pipeline['MEM'][1][1:])]

    def execute_pipeline_stage(self, stage, pgm, mem):
        if self.stall and stage in ['IF', 'ID']:
            return

        if stage == 'IF':
            if self.branch_stall:
                return
            if self.pc < len(pgm):
                self.pipeline['IF'] = pgm[self.pc].strip()
                self.pc += 1
            else:
                self.pipeline['IF'] = None

        elif stage == 'ID':
            if self.pipeline['IF'] is not None:
                self.pipeline['ID'] = self.pipeline['IF'].replace(',', ' ').split()
                if self.pipeline['ID'][0] in ['J', 'JAL', 'BNE']:
                    self.branch_stall = True
            else:
                self.pipeline['ID'] = None

        elif stage == 'EX1':
            if self.pipeline['ID'] is not None:
                parts = self.pipeline['ID']
                opcode = parts[0]
                if self.pipeline_latency['EX1'] == 0:
                    self.pipeline_latency['EX1'] = INSTRUCTION_LATENCY.get(opcode, 1) - 1
                    self.pipeline['EX1'] = parts
                else:
                    # Continue executing if latency is not zero
                    if self.pipeline_latency['EX1'] > 1:
                        self.pipeline_latency['EX1'] -= 1
                        return
                    else:
                        # If latency is done, move to EX2 or MEM
                        if opcode == 'MUL'or opcode == 'LW' or opcode == 'SW':
                            self.pipeline['EX2'] = self.pipeline['EX1']
                        else:
                            self.pipeline['MEM'] = self.pipeline['EX1']
                        self.pipeline['EX1'] = None
                        if opcode in ['J', 'JAL', 'BNE']:
                            self.branch_stall = False
            else:
                self.pipeline['EX1'] = None

        elif stage == 'EX2':
            if self.pipeline['EX1'] is not None and self.pipeline['EX1'][0] == 'MUL':
                if self.pipeline_latency['EX2'] == 0:
                    self.pipeline_latency['EX2'] = INSTRUCTION_LATENCY['MUL'] - 1
                    self.pipeline['EX2'] = self.pipeline['EX1']
                    
                else:
                    # Continue executing if latency is not zero
                    if self.pipeline_latency['EX2'] > 1:
                        self.pipeline_latency['EX2'] -= 1
                        return
                    else:
                        # If latency is done, move to MEM
                        self.pipeline['MEM'] = self.pipeline['EX2']
            
                        self.pipeline['EX2'] = None
            elif self.pipeline['EX1'] is not None and self.pipeline['EX1'][0] == 'LW':
                if self.pipeline_latency['EX2'] == 0:
                    self.pipeline_latency['EX2'] = INSTRUCTION_LATENCY['LW'] - 1
                    self.pipeline['EX2'] = self.pipeline['EX1']
                else:
                    # Continue executing if latency is not zero
                    if self.pipeline_latency['EX2'] > 1:
                        self.pipeline_latency['EX2'] -= 1
                        return
                    else:
                        # If latency is done, move to MEM
                        self.pipeline['MEM'] = self.pipeline['EX2']
                        self.pipeline['EX2'] = None
            elif self.pipeline['EX1'] is not None and self.pipeline['EX1'][0] == 'SW':
                if self.pipeline_latency['EX2'] == 0:
                    self.pipeline_latency['EX2'] = INSTRUCTION_LATENCY['SW'] - 1
                    self.pipeline['EX2'] = self.pipeline['EX1']
                else:
                    # Continue executing if latency is not zero
                    if self.pipeline_latency['EX2'] > 1:
                        self.pipeline_latency['EX2'] -= 1
                        return
                    else:
                        # If latency is done, move to MEM
                        self.pipeline['MEM'] = self.pipeline['EX2']
                        self.pipeline['EX2'] = None
            else:
                self.pipeline['EX2'] = None

        elif stage == 'MEM':
            if self.pipeline['EX1'] is not None and self.pipeline['EX1'][0] != 'MUL':
                parts = self.pipeline['EX1']
                opcode = parts[0]
                if opcode == "LW" or opcode == "SW":
                    self.pipeline['MEM'] = parts
                else:
                    self.pipeline['MEM'] = self.pipeline['EX1']
            elif self.pipeline['EX2'] is not None:
                self.pipeline['MEM'] = self.pipeline['EX2']
            else:
                self.pipeline['MEM'] = None

        elif stage == 'WB':
            if self.pipeline['MEM'] is not None:
                parts = self.pipeline['MEM']
                opcode = parts[0]
                if opcode == "ADD":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] + self.registers[rs2]
                elif opcode == "SUB":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] - self.registers[rs2]
                elif opcode == "ADDI":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    imm = int(parts[3])
                    self.registers[rd] = self.registers[rs1] + imm
                elif opcode == "MUL":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] * self.registers[rs2]
                elif opcode == "MOD":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    if self.registers[rs2] != 0:
                        self.registers[rd] = self.registers[rs1] % self.registers[rs2]
                elif opcode == "XOR":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] ^ self.registers[rs2]
                elif opcode == "XORI":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    imm = int(parts[3])
                    self.registers[rd] = self.registers[rs1] ^ imm
                elif opcode == "AND":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] & self.registers[rs2]
                elif opcode == "ANDI":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    imm = int(parts[3])
                    self.registers[rd] = self.registers[rs1] & imm
                elif opcode == "OR":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] | self.registers[rs2]
                elif opcode == "ORI":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    imm = int(parts[3])
                    self.registers[rd] = self.registers[rs1] | imm
                elif opcode == "SLL":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    rs2 = int(parts[3][1:])
                    self.registers[rd] = self.registers[rs1] << self.registers[rs2]
                elif opcode == "SLLI":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    imm = int(parts[3])
                    self.registers[rd] = self.registers[rs1] << imm
                elif opcode == "LW":
                    rd = int(parts[1][1:])
                    offset, rs1 = parts[2].split('(')
                    rs1 = int(rs1[:-1][1:])
                    mem_addr = self.registers[rs1] + int(offset)
                    mem_index = (mem_addr // 4)
                    self.registers[rd] = mem[mem_index]
                elif opcode == "SW":
                    rs2 = int(parts[1][1:])
                    offset, rs1 = parts[2].split('(')
                    rs1 = int(rs1[:-1][1:])
                    mem_addr = self.registers[rs1] + int(offset)
                    mem_index = (mem_addr // 4)
                    mem[mem_index] = self.registers[rs2]
                elif opcode == "MV":
                    rd = int(parts[1][1:])
                    rs1 = int(parts[2][1:])
                    self.registers[rd] = self.registers[rs1]
                elif opcode == "LI":
                    rd = int(parts[1][1:])
                    imm = int(parts[2])
                    self.registers[rd] = imm
                elif opcode == "J":
                    label = parts[1]
                    self.pc = self.labels[label] - 1
                elif opcode == "JAL":
                    rd = int(parts[1][1:])
                    label = parts[2]
                    self.registers[rd] = self.pc + 1
                    self.pc = self.labels[label] - 1
                elif opcode == "BNE":
                    rs1 = int(parts[1][1:])
                    rs2 = int(parts[2][1:])
                    label = parts[3]
                    if self.registers[rs1] != self.registers[rs2]:
                        self.pc = self.labels[label] - 1
            self.pipeline['WB'] = None

    def execute(self, pgm, mem):
        stages = ['WB', 'MEM', 'EX2', 'EX1', 'ID', 'IF']
        for stage in stages:
            self.detect_hazards()
            self.execute_pipeline_stage(stage, pgm, mem)

class Simulator:
    def __init__(self, data_forwarding=False):
        self.total_memory = 4096  # Total memory size in bytes
        self.memory = [0] * (self.total_memory // 4)  # 4KB Shared Memory (4 bytes per entry)
        self.clock = 0
        self.cores = []
        self.labels = {}
        self.data_forwarding = data_forwarding
        core_memory_size = self.total_memory // 4 // 4  # Divide memory among 4 cores
        for i in range(4):
            self.cores.append(Cores(i, i * core_memory_size, core_memory_size, self.labels, self.data_forwarding))
        self.program = []

    def load_program(self, program_lines):
        self.program = []
        for idx, line in enumerate(program_lines):
            line = line.strip()
            if line.endswith(":"):
                self.labels[line[:-1]] = len(self.program)
            else:
                self.program.append(line)

    def run(self):
        try:
            while any(core.pc < len(self.program) or any(core.pipeline.values()) for core in self.cores):
                for core in self.cores:
                    core.execute(self.program, self.memory)
                self.clock += 1
        except KeyboardInterrupt:
            print("Simulation interrupted.")
        finally:
            self.display()

    def display(self):
        print("\n=== Register States ===")
        for i, core in enumerate(self.cores):
            print(f"Core {i}: {core.registers}")

        print("\n=== Shared Memory ===")
        for i in range(4):
            start = i * 1024 // 4
            end = start + 1024 // 4
            print(f"Core {i} Memory: {self.memory[start:end]}")

        # Visualization
        plt.figure(figsize=(16, 8))
        data = np.array([self.cores[i].registers for i in range(4)])
        plt.imshow(data, cmap="Blues", aspect='auto')
        for i in range(4):
            for j in range(32):
                plt.text(j, i, str(self.cores[i].registers[j]), 
                         ha='center', va='center', color='black')
        plt.title("Register States of 4 Cores")
        plt.axis('off')
        plt.show()

        for i, core in enumerate(self.cores):
            print(f"Core {i} Stall Count: {core.stall_count // 4}")

# Example Program
example_program = [
    "ADDI X5,X0,3",  
    "ADDI X7,X5,6",    
    "ADDI X6,X0,2",        
    "ADD X4,X5,X6",
    "SLLI X8,X4,1",
    "ADDI X10,X0,11",
    "ADD X9,X0,X0",
    "ADDI X13,X0,0",
    "ADDI X15,X8,15",
    "ADD X17,X15,X5",
    "ADDI X17 X15 4",
    "ADDI X20 X0 4",
     "SW X17 0(X18)",
     "ADDI X20 X0 4",
    
    
]
sim=Simulator( data_forwarding=False)
sim.load_program(example_program)
sim.run()
print(f"Number of clock cycles: {sim.clock}")