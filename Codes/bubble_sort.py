import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox

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
        if len(parts) == 0:
            self.pc += 1
            return

        opcode = parts[0]
        
        # ADDI X1 X2 IMM
        if opcode == "ADDI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3], 0)  # Handle hexadecimal and decimal values
            self.registers[rd] = self.registers[rs1] + imm
       
        # ADD X1 X2 X3
        elif opcode == "ADD":
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

        elif opcode == "J":
            label = parts[1]
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

        # BLE X1 X2 LABEL
        elif opcode == "BLE":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] <= self.registers[rs2]:
                self.pc = labels[label] - 1

        # BEQ X1 X2 LABEL
        elif opcode == "BEQ":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] == self.registers[rs2]:
                self.pc = labels[label] - 1

        # LA X1 LABEL
        elif opcode == "LA":
            rd = int(parts[1][1:])
            label = parts[2]
            self.registers[rd] = labels[label]

        # LI X1 IMM
        elif opcode == "LI":
            rd = int(parts[1][1:])
            imm = int(parts[2], 0)  # Handle hexadecimal values
            self.registers[rd] = imm

        # ECALL
        elif opcode == "ECALL":
            a7 = self.registers[17]
            a0 = self.registers[10]
            if a7 == 1:
                print(a0, end=' ')
            elif a7 == 4:
                s = ""
                while mem[a0] != 0:
                    s += chr(mem[a0])
                    a0 += 1
                print(s, end='')

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
        print(self.memory)  # Display only relevant memory
        
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

    def get_sorted_array(self):
        sorted_array = []
        for i in range(20):
            sorted_array.append(self.memory[i])
        return sorted_array

    def show_gui(self):
        root = tk.Tk()
        root.title("4-Core Simulator")
        
        # Text box for program input
        program_label = tk.Label(root, text="Program:")
        program_label.pack()
        program_text = tk.Text(root, height=10, width=50)
        program_text.pack()
        
        # Button to load and run the program
        def load_and_run():
            program_lines = program_text.get("1.0", tk.END).strip().split('\n')
            self.load_program(program_lines)
            self.run()
            self.display()
            sorted_array = self.get_sorted_array()
            print("Sorted Array:", sorted_array)
            messagebox.showinfo("Simulation Complete", f"Number of clock cycles: {self.clock}\nSorted Array: {sorted_array}")
        
        run_button = tk.Button(root, text="Run", command=load_and_run)
        run_button.pack()
        
        root.mainloop()

# Example Program with Bubble Sort
example_program = [
    "ADDI X2 X0 20",  # no. of elements
    "ADDI X1 X2 -1",  # n-1
    "ADDI X4 X0 0",   # outer loop i value

    # Initialize array in memory
    "LI X3 0",
    "LI X10 0x3", "SW X10 0(X3)",
    "LI X10 0x2", "SW X10 4(X3)",
    "LI X10 0x0", "SW X10 8(X3)",
    "LI X10 0x5", "SW X10 12(X3)",
    "LI X10 0x1", "SW X10 16(X3)",
    "LI X10 0x7", "SW X10 20(X3)",
    "LI X10 0xB", "SW X10 24(X3)",
    "LI X10 0x13", "SW X10 28(X3)",
    "LI X10 0x8", "SW X10 32(X3)",
    "LI X10 0x14", "SW X10 36(X3)",
    "LI X10 0x4", "SW X10 40(X3)",
    "LI X10 0x6", "SW X10 44(X3)",
    "LI X10 0x9", "SW X10 48(X3)",
    "LI X10 0xA", "SW X10 52(X3)",
    "LI X10 0xC", "SW X10 56(X3)",
    "LI X10 0xD", "SW X10 60(X3)",
    "LI X10 0xE", "SW X10 64(X3)",
    "LI X10 0xF", "SW X10 68(X3)",
    "LI X10 0x10", "SW X10 72(X3)",
    "LI X10 0x11", "SW X10 76(X3)",

    # Bubble Sort
    "OUTER_LOOP:",
    "BEQ X4 X1 EXIT1",
    "SUB X5 X1 X4",            # n-1-i
    "ADDI X6 X0 0",            # inner loop j value
    "LI X3 0",                 # reset X3 to the start of the array at the beginning of each outer loop 

    "INNER_LOOP:",
    "LW X7 0(X3)",
    "LW X8 4(X3)",
    "BEQ X6 X5 EXIT2",
    "BLE X7 X8 NO_SWAP",
    "SW X8 0(X3)",
    "SW X7 4(X3)",
    "NO_SWAP:",
    "ADDI X3 X3 4",   # move to the next element in the array
    "ADDI X6 X6 1",   # increment inner loop counter
    "J INNER_LOOP",

    "EXIT2:",
    "ADDI X4 X4 1",   # increment outer loop counter
    "J OUTER_LOOP",

    "EXIT1:",
    "LI A7 10",
    "ECALL"
]

# Initialize and Run Simulator
sim = Simulator()
sim.load_program(example_program)
sim.run()
print(f"Number of clock cycles: {sim.clock}")
sim.display()
sorted_array = sim.get_sorted_array()
print("Sorted Array:", sorted_array)