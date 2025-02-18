import numpy as np
import matplotlib.pyplot as plt

class Cores:
    def __init__(self, cid, mem_start, mem_size):
        self.registers = [0] * 32
        self.registers[31] = cid  # Core ID Register (Read-Only)
        self.pc = 0
        self.coreid = cid
        self.mem_start = mem_start
        self.mem_size = mem_size
    
    
    def execute(self, pgm, mem):
        if self.pc >= len(pgm):
            return
        
        # Split the instruction, handle different spacings and formats
        parts = pgm[self.pc].strip().replace(',', ' ').split()
        opcode = parts[0]

        # ADD X1 X2 X3
        if opcode == "ADD":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] + self.registers[rs2]
       
        # SUB X1 X2 X3
        elif opcode == "SUB":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] - self.registers[rs2]
        
        # ADDI X1 X2 IMM
        elif opcode == "ADDI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3])
            self.registers[rd] = self.registers[rs1] + imm

        # BNE X1 X2 LABEL
        elif opcode == "BNE":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] != self.registers[rs2]:
                self.pc = labels[label] - 1
        
        # JAL X1 LABEL
        elif opcode == "JAL":
            rd = int(parts[1][1:])
            label = parts[2]
            self.registers[rd] = self.pc + 1  # Store return address
            self.pc = labels[label] - 1
        
        # LW X1 OFFSET(X2)
        elif opcode == "LW":
            rd = int(parts[1][1:])  # Destination register
            offset, rs1 = parts[2].split('(')  # Split at '(' to get offset and register
            rs1 = int(rs1[:-1][1:])  # Remove closing parenthesis and 'X'
            mem_addr = self.registers[rs1] + int(offset)  # Calculate memory address
            mem_index = (self.mem_start + (mem_addr // 4)) 
            self.registers[rd] = mem[mem_index]  # Load from memory to register
            
        # SW X1 OFFSET(X2)
        elif opcode == "SW":
            rs2 = int(parts[1][1:])  # Source register to be stored
            offset, rs1 = parts[2].split('(')  # Split at '(' to get offset and register
            rs1 = int(rs1[:-1][1:])  # Remove closing parenthesis and 'X'
            mem_addr = self.registers[rs1] + int(offset)  # Calculate memory address
            mem_index = (self.mem_start + (mem_addr // 4)) 
            mem[mem_index] = self.registers[rs2] # Store register value in memory

        # MOD X1 X2 X3
        elif opcode == "MOD":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            if self.registers[rs2] != 0:
                self.registers[rd] = self.registers[rs1] % self.registers[rs2]

        # MUL X1 X2 X3
        elif opcode == "MUL":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] * self.registers[rs2]

        # XOR X1 X2 X3
        elif opcode == "XOR":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] ^ self.registers[rs2]

        # XORI X1 X2 IMM
        elif opcode == "XORI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3])
            self.registers[rd] = self.registers[rs1] ^ imm

        # AND X1 X2 X3
        elif opcode == "AND":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] & self.registers[rs2]

        # ANDI X1 X2 IMM
        elif opcode == "ANDI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3])
            self.registers[rd] = self.registers[rs1] & imm

        # OR X1 X2 X3
        elif opcode == "OR":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] | self.registers[rs2]
        
        # ORI X1 X2 IMM
        elif opcode == "ORI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3])
            self.registers[rd] = self.registers[rs1] | imm
        
        # J LABEL
        elif opcode == "J":
            label = parts[1]
            self.pc = labels[label] - 1

        # MV X1 X2
        elif opcode == "MV":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            self.registers[rd] = self.registers[rs1]

        # LI X1 IMM
        elif opcode == "LI":
            rd = int(parts[1][1:])
            imm = int(parts[2])
            self.registers[rd] = imm

        # SLL X1 X2 X3
        elif opcode == "SLL":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] << self.registers[rs2]

        # SLLI X1 X2 IMM
        elif opcode == "SLLI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3])
            self.registers[rd] = self.registers[rs1] << imm

        self.pc += 1

class Simulator:
     def __init__(self):
        self.total_memory = 4096  # Total memory size in bytes
        self.memory = [0] * (self.total_memory // 4)  # 4KB Shared Memory (4 bytes per entry)
        self.clock = 0
        self.cores = []
        core_memory_size = self.total_memory //4 //4   # Divide memory among 4 cores
        for i in range(4):
            self.cores.append(Cores(i, i * core_memory_size, core_memory_size))
        self.program = []

     def load_program(self, program_lines):
        global labels
        labels = {}
        self.program = []
        for idx, line in enumerate(program_lines):
            line = line.strip()
            if line.endswith(":"):
                labels[line[:-1]] = len(self.program)
            else:
                self.program.append(line)
        
     def run(self):
        try:
            while any(core.pc < len(self.program) for core in self.cores):
                for core in self.cores:
                    core.execute(self.program, self.memory)
                self.clock += 1
        except KeyboardInterrupt:
            print("Simulation interrupted.")
        
     def display(self):
        print("\n=== Register States ===")
        for i, core in enumerate(self.cores):
            print(f"Core {i}: {core.registers}")
        
        print("\n=== Shared Memory ===")
        print(self.memory)  # Display only relevant memorydef display(self):
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

# Example Program
example_program = [
    "ADDI X5,X0,3",        # X5 = 3
    "ADDI X6 X0 2",        # X6 = 2
    "ADD X4 X5 X6",        # X4 = X5 + X6
    "SUB X7 X4 X6",        # X7 = X4 - X6
    "MUL X14 X4 X6",       # X14 = X4 * X6
    "MV X15 X14",          # Move X14 to X15
    "AND X16 X15 X14",     # X16 = X15 & X14
    "OR X17 X16 X15",      # X17 = X16 | X15
    "SLLI X18 X17 4",      # X18 = X17 << 4
    "SW X4 0(X5)",         # Store X4 in memory at address X5 + 0
    "LW X9 0(X5)",         # Load value from memory at address X5 + 0 to X9
    "BNE X9 X4 END",       # Branch to END if X9 != X4
    "JAL X10 LOOP",        # Jump to LOOP
    "MOD X13 X4 X6",       # X13 = X4 % X6
    "END:",                # Label
    "ADDI X11 X0 99",      # X11 = 99
    "LOOP:",               # Label
    "ADD X12 X11 X11"      # X12 = X11 + X11
]

# Initialize and Run Simulator
sim = Simulator()
sim.load_program(example_program)
sim.run()
print(f"Number of clock cycles: {sim.clock}")
sim.display()