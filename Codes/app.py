from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
        
        parts = pgm[self.pc].strip().replace(',', ' ').split()
        if len(parts) == 0:
            self.pc += 1
            return

        opcode = parts[0]
        
        if opcode == "ADDI":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            imm = int(parts[3], 0)  # Handle hexadecimal and decimal values
            self.registers[rd] = self.registers[rs1] + imm
        elif opcode == "ADD":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] + self.registers[rs2]
        elif opcode == "SUB":
            rd = int(parts[1][1:])
            rs1 = int(parts[2][1:])
            rs2 = int(parts[3][1:])
            self.registers[rd] = self.registers[rs1] - self.registers[rs2]
        elif opcode == "BNE":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] != self.registers[rs2]:
                self.pc = labels[label] - 1
        elif opcode == "JAL":
            rd = int(parts[1][1:])
            label = parts[2]
            self.registers[rd] = self.pc + 1  # Store return address
            self.pc = labels[label] - 1
        elif opcode == "J":
            label = parts[1]
            self.pc = labels[label] - 1
        elif opcode == "LW":
            rd = int(parts[1][1:])  # Destination register
            offset, rs1 = parts[2].split('(')  # Split at '(' to get offset and register
            rs1 = int(rs1[:-1][1:])  # Remove closing parenthesis and 'X'
            mem_addr = self.registers[rs1] + int(offset)  # Calculate memory address
            mem_index = (self.mem_start + (mem_addr // 4)) 
            self.registers[rd] = mem[mem_index]  # Load from memory to register
        elif opcode == "SW":
            rs2 = int(parts[1][1:])  # Source register to be stored
            offset, rs1 = parts[2].split('(')  # Split at '(' to get offset and register
            rs1 = int(rs1[:-1][1:])  # Remove closing parenthesis and 'X'
            mem_addr = self.registers[rs1] + int(offset)  # Calculate memory address
            mem_index = (self.mem_start + (mem_addr // 4)) 
            mem[mem_index] = self.registers[rs2]  # Store register value in memory
        elif opcode == "BLE":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] <= self.registers[rs2]:
                self.pc = labels[label] - 1
        elif opcode == "BEQ":
            rs1 = int(parts[1][1:])
            rs2 = int(parts[2][1:])
            label = parts[3]
            if self.registers[rs1] == self.registers[rs2]:
                self.pc = labels[label] - 1
        elif opcode == "LA":
            rd = int(parts[1][1:])
            label = parts[2]
            self.registers[rd] = labels[label]
        elif opcode == "LI":
            rd = int(parts[1][1:])
            imm = int(parts[2], 0)  # Handle hexadecimal values
            self.registers[rd] = imm
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
        for i in range(4):
            start = i * 1024 // 4
            end = start + 1024 // 4
            print(f"Core {i} Memory: {self.memory[start:end]}")
        
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

@app.route('/run', methods=['POST'])
def run_program():
    data = request.get_json()
    program_lines = data['program'].split('\n')
    
    sim = Simulator()
    sim.load_program(program_lines)
    sim.run()
    
    register_states = {}
    for i, core in enumerate(sim.cores):
        register_states[f'Core {i}'] = core.registers
    
    response = {
        'clock': sim.clock,
        'memory': sim.memory,
        'registerStates': register_states
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=5000)