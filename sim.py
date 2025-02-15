import numpy as np
import matplotlib.pyplot as plt

class Cores:
    def __init__(self, cid):
        self.registers = [0] * 32
        self.registers[31] = cid  # Core ID Register (Read-Only)
        self.pc = 0
        self.coreid = cid
    
    def execute(self, pgm, mem):
        if self.pc >= len(pgm):
            return
        
        # Split the instruction
        parts = pgm[self.pc].split()
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
            mem_index = (mem_addr // 4) % len(mem)
            self.registers[rd] = mem[mem_index]  # Load from memory to register
            
       # SW X1 OFFSET(X2)
        elif opcode == "SW":
            rs2 = int(parts[1][1:])  # Source register to be stored
            offset, rs1 = parts[2].split('(')  # Split at '(' to get offset and register
            rs1 = int(rs1[:-1][1:])  # Remove closing parenthesis and 'X'
            mem_addr = self.registers[rs1] + int(offset)  # Calculate memory address
            mem_index = (mem_addr // 4) % len(mem)
            mem[mem_index] = self.registers[rs2]  # Store register value in memory
           

        # MOD X1 X2 X3
        elif opcode=="MOD":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            if(rs2!=0):
                self.registers[rd]=self.registers[rs1] % self.registers[rs2]
            
        self.pc += 1

class Simulator:
    def __init__(self):
        self.memory = [0] * (4096 // 4)  # 4KB Shared Memory (4 bytes per entry)
        self.clock = 0
        self.cores = [Cores(i) for i in range(4)]
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
        while any(core.pc < len(self.program) for core in self.cores):
            for core in self.cores:
                core.execute(self.program, self.memory)
            self.clock += 1

    def display(self):
        print("\n=== Register States ===")
        for i, core in enumerate(self.cores):
            print(f"Core {i}: {core.registers}")
        
        print("\n=== Shared Memory ===")
        print(self.memory)
        
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
    "ADDI X5 X0 3",        # X5 = 3
    "ADDI X6 X0 2",        # X6 = 2
    "ADD X4 X5 X6",        # X4 = X5 + X6
    "SUB X7 X4 X6",        # X7 = X4 - X6
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
sim.display()

print(f"Number of clock cycles: {sim.clock}")
