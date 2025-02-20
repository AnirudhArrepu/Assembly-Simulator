import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox

class Cores:
    def __init__(self, cid, mem_start, mem_size):
        self.registers = [0] * 32
        self.registers[31] = cid  # Core ID Register (Read-Only)
        self.pc = 0
        self.coreid = cid
        self.mem_start = mem_start
        self.mem_size = mem_size
        
    def execute(self, pgm, mem, data_mem, labels):
        if self.pc >= len(pgm):
            return
        
        # Split the instruction
        parts = pgm[self.pc].strip().replace(',', ' ').split()
        if len(parts) == 0:
            self.pc += 1
            return

        opcode = parts[0]

        if opcode == "ADDI"or opcode=="addi":
            rd, rs1, imm = int(parts[1][1:]), int(parts[2][1:]), int(parts[3], 0)
            self.registers[rd] = self.registers[rs1] + imm
       
        elif opcode == "ADD" or opcode=="add":
            rd, rs1, rs2 = int(parts[1][1:]), int(parts[2][1:]), int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] + self.registers[rs2]
       
        elif opcode == "SUB"or opcode=="sub":
            rd, rs1, rs2 = int(parts[1][1:]), int(parts[2][1:]), int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] - self.registers[rs2]

        elif opcode == "LW" or opcode=="lw":
            rd = int(parts[1][1:])
            offset, rs1 = parts[2].split('(')
            rs1 = int(rs1[:-1][1:])
            mem_addr = self.registers[rs1] + int(offset)
            mem_index = mem_addr // 4
            if 0 <= mem_index < len(data_mem):
                self.registers[rd] = data_mem[mem_index]

        elif opcode == "SW"or opcode=="sw":
            rs2 = int(parts[1][1:])
            offset, rs1 = parts[2].split('(')
            rs1 = int(rs1[:-1][1:])
            mem_addr = self.registers[rs1] + int(offset)
            mem_index = mem_addr // 4
            if 0 <= mem_index < len(data_mem):
                data_mem[mem_index] = self.registers[rs2]

        elif opcode == "LA"or opcode=="la":
            rd = int(parts[1][1:])
            label = parts[2]
            self.registers[rd] = labels[label]

        elif opcode == "J"or opcode=="j":
            label = parts[1]
            self.pc = labels[label] - 1

        elif opcode == "MOD"or opcode=="mod":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            if self.registers[rs2] != 0:
                self.registers[rd] = self.registers[rs1] % self.registers[rs2]
        
        elif opcode == "JAL"or opcode=="jal":
            rd = int(parts[1][1:])
            label = parts[2]
            self.registers[rd] = self.pc + 1  # Store return address
            self.pc = labels[label] - 1

        elif opcode == "BEQ"or opcode=="beq":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] == self.registers[rs2]:
                self.pc = labels[label] - 1

        elif opcode == "BLE"or opcode=="ble":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] <= self.registers[rs2]:
                self.pc = labels[label] - 1

        # ECALL
        elif opcode == "ECALL"or opcode=="ecall":
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
        self.total_memory = 4096  # 4KB total memory
        self.memory = [0] * (self.total_memory // 4)
        self.data_memory = [0] * (self.total_memory // 4)  # Separate data section
        self.clock = 0
        self.cores = []
        core_memory_size = self.total_memory // 4 // 4  # Split memory for 4 cores
        for i in range(4):
            self.cores.append(Cores(i, i * core_memory_size, core_memory_size))
        self.program = []
        
        self.data_section = []
        self.text_section = []
        self.labels = {}

    def load_program(self, program_lines):
        self.program = []
        self.data_section = []
        self.text_section = []
        self.labels = {}
        in_data = False
        in_text = False

        for line in program_lines:
            line = line.strip()
            
            if line == ".data":
                in_data = True
                in_text = False
                continue
            elif line == ".text":
                in_data = False
                in_text = True
                continue
            
            if in_data:
                self.data_section.append(line)
            elif in_text:
                self.text_section.append(line)
        
        # Store data section into memory and record labels
        mem_address = 0
        for line in self.data_section:
            parts = line.split()
            if len(parts) >= 3 and parts[1] == ".word":
                label = parts[0][:-1]
                self.labels[label] = mem_address // 4
                words = parts[2:]
                for word in words:
                    data_index = mem_address // 4
                    self.data_memory[data_index] = int(word,16)
                    mem_address += 4
        
        # Record labels in the text section
        for idx, line in enumerate(self.text_section):
            if line.endswith(":"):
                label = line[:-1]
                self.labels[label] = idx

        self.program = self.text_section

        # Load the same program into each core
        for core in self.cores:
            core.pc = 0  # Reset the program counter for each core
            core.registers = [0] * 32  # Reset registers for each core
            core.registers[31] = core.coreid  # Core ID Register (Read-Only)

    def run(self):
        try:
            while any(core.pc < len(self.program) for core in self.cores):
                for core in self.cores:
                    core.execute(self.program, self.memory, self.data_memory, self.labels)
                self.clock += 1
        except KeyboardInterrupt:
            print("Simulation interrupted.")

    def display(self):
        print("\n=== Register States ===")
        for i, core in enumerate(self.cores):
            print(f"Core {i}: {core.registers}")
        
        
        print("\n=== Data Memory for Each Core ===")
    
        for i in range(4):  # Loop over each core
            start = i * 1024 // 4
            end = start + 1024 // 4
            if i != 0:  
                self.data_memory[start:end] = self.data_memory[0:1024 // 4]
            print(f"Core {i} Memory: {self.data_memory[start:end]}")


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

    

    
    def show_gui(self):
        root = tk.Tk()
        root.title("4-Core Simulator")
        
        # Set a nice background color
        root.configure(bg='#2c3e50')
        
        # Add a background image
        # Frame for Simulator Name
        title_frame = tk.Frame(root, bg='#1abc9c', bd=5)
        title_frame.place(relx=0.5, rely=0.05, relwidth=0.6, relheight=0.04, anchor='n')

        # Label for Simulator Name
        title_label = tk.Label(title_frame, text="x25++ Simulator", bg='#1abc9c', fg='white', 
                       font=('Arial', 18, 'bold'))
        title_label.place(relwidth=1, relheight=1)
        
        program_frame = tk.Frame(root, bg='#34495e', bd=5)
        program_frame.place(relx=0.5, rely=0.1, relwidth=0.75, relheight=0.75, anchor='n')
        
        program_label = tk.Label(program_frame, text="Program:", bg='#34495e', fg='white', font=('Arial', 12))
        program_label.place(relwidth=0.15, relheight=1)
        
        program_text = tk.Text(program_frame, height=70, width=50, bg='#ecf0f1', font=('Arial', 12))
        program_text.place(relx=0.16, relwidth=0.84, relheight=1)
        
        run_button_frame = tk.Frame(root, bg='#34495e', bd=5)
        run_button_frame.place(relx=0.5, rely=0.87, relwidth=0.3, relheight=0.1, anchor='n')
        
        run_button = tk.Button(run_button_frame, text="Run", bg='#27ae60', fg='white', font=('Arial', 14, 'bold'), command=lambda: self.load_and_run(program_text))
        run_button.place(relwidth=1, relheight=1)
        
        root.mainloop()
        
    def load_and_run(self, program_text):
        program_lines = program_text.get("1.0", tk.END).strip().split('\n')
        self.load_program(program_lines)
        self.run()
           
          
        self.display()
           
        
      

# Assembly Program with .data and .text
example_program = [
    ".data",
    "arr: .word 0x3 0x2",
    ".text",
   
    "la X3, arr",       # Load base address of arr into X3
    "lw X6, 0(X3)",      # Load arr[i] into X6
    "lw X7, 4(X3)",      # Load arr[i+1] into X7
    "add X5, X6, X7",    # Add arr[i] and arr[i+1]
    "sub x8,x6,x7",
    "mod x9 x5 x8"  


    

]

# Initialize and Run Simulator
sim = Simulator()
sim.load_program(example_program)
sim.run()
print(f"Number of clock cycles: {sim.clock}")
sim.display()
sim.show_gui()
