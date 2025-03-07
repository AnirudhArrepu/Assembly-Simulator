from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np

from flask import Flask, request, jsonify, render_template
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
        # Initialize pipeline registers: each stage holds a dict (or None)
        self.pipeline = {'IF': None, 'ID': None, 'EX': None, 'MEM': None, 'WB': None}

    def make_labels(self, insts):
        for i, inst in enumerate(insts):
            tokens = inst.split()
            if tokens and (":" in tokens[0]):
                self.program_label_map[tokens[0].split(":")[0]] = i
        print("Labels:", self.program_label_map)

    # --- Pipeline Stage Helpers ---
    def decode_stage(self, pipe_reg):
        # Remove label if present and save parsed tokens
        inst = pipe_reg['inst']
        tokens = inst.split()
        if tokens and (":" in tokens[0]):
            tokens.pop(0)
        pipe_reg['parts'] = tokens

    def execute_stage(self, pipe_reg):
        tokens = pipe_reg.get('parts', [])
        if not tokens:
            return
        opcode = tokens[0].lower()
        # For ALU operations, use register values from the current register file.
        if opcode == "la":  # la rd, data
            rd = int(tokens[1][1:])
            data = tokens[2]
            # Write data segment values into memory (as in original)
            for val in self.data_segment[data]:
                self.memory.memory[self.memory_data_index + self.coreid] = val
                self.memory_data_index -= 4
            pipe_reg['alu_result'] = self.memory_data_index + 4
            pipe_reg['write_reg'] = rd
        elif opcode == "add":  # add rd, rs1, rs2
            rd = int(tokens[1][1:])
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            pipe_reg['alu_result'] = self.registers[rs1] + self.registers[rs2]
            pipe_reg['write_reg'] = rd
        elif opcode == "addi":  # addi rd, rs1, imm
            rd = int(tokens[1][1:])
            rs1 = int(tokens[2][1:])
            imm = int(tokens[3])
            pipe_reg['alu_result'] = self.registers[rs1] + imm
            pipe_reg['write_reg'] = rd
        elif opcode == "sub":  # sub rd, rs1, rs2
            rd = int(tokens[1][1:])
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            pipe_reg['alu_result'] = self.registers[rs1] - self.registers[rs2]
            pipe_reg['write_reg'] = rd
        elif opcode == "slt":  # slt rd, rs1, rs2
            rd = int(tokens[1][1:])
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            pipe_reg['alu_result'] = 1 if self.registers[rs1] < self.registers[rs2] else 0
            pipe_reg['write_reg'] = rd
        elif opcode == "li":  # li rd, imm
            rd = int(tokens[1][1:])
            imm = int(tokens[2])
            pipe_reg['alu_result'] = imm
            pipe_reg['write_reg'] = rd
        elif opcode == "lw":  # lw rd, offset(rs1)
            rd = int(tokens[1][1:])
            offset, rs1_part = tokens[2].split('(')
            rs1 = int(rs1_part[:-1][1:])
            effective_addr = self.registers[rs1] + int(offset)
            pipe_reg['effective_addr'] = effective_addr
            pipe_reg['write_reg'] = rd
        elif opcode == "sw":  # sw rs1, offset(rd)
            rs1 = int(tokens[1][1:])
            offset, rd_part = tokens[2].split('(')
            rd_val = int(rd_part[:-1][1:])
            effective_addr = self.registers[rd_val] + int(offset)
            pipe_reg['effective_addr'] = effective_addr
            pipe_reg['store_val'] = self.registers[rs1]
        elif opcode == "bne":  # bne rs1, rs2, label
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            label = tokens[3]
            if self.registers[rs1] != self.registers[rs2]:
                pipe_reg['branch_taken'] = True
                pipe_reg['new_pc'] = self.program_label_map[label]
            else:
                pipe_reg['branch_taken'] = False
        elif opcode == "ble":  # ble rs1, rs2, label
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            label = tokens[3]
            if self.registers[rs1] <= self.registers[rs2]:
                pipe_reg['branch_taken'] = True
                pipe_reg['new_pc'] = self.program_label_map[label]
            else:
                pipe_reg['branch_taken'] = False
        elif opcode == "beq":  # beq rs1, rs2, label
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            label = tokens[3]
            if self.registers[rs1] == self.registers[rs2]:
                pipe_reg['branch_taken'] = True
                pipe_reg['new_pc'] = self.program_label_map[label]
            else:
                pipe_reg['branch_taken'] = False
        elif opcode == "jal":  # jal rd, label
            rd = int(tokens[1][1:])
            label = tokens[2]
            pipe_reg['alu_result'] = self.pc + 1  # saving return address
            pipe_reg['write_reg'] = rd
            pipe_reg['branch_taken'] = True
            pipe_reg['new_pc'] = self.program_label_map[label]
        elif opcode == "jr":  # jr rs1
            rs1 = int(tokens[1][1:])
            pipe_reg['branch_taken'] = True
            pipe_reg['new_pc'] = self.registers[rs1]
        elif opcode == "j":  # j label
            label = tokens[1]
            pipe_reg['branch_taken'] = True
            pipe_reg['new_pc'] = self.program_label_map[label]
        else:
            print("instruction not defined:", tokens[0])

    def memory_stage(self, pipe_reg):
        tokens = pipe_reg.get('parts', [])
        if not tokens:
            return
        opcode = tokens[0].lower()
        if opcode == "lw":
            effective_addr = pipe_reg.get('effective_addr', 0)
            pipe_reg['mem_data'] = self.memory.memory[effective_addr + self.coreid]
        elif opcode == "sw":
            effective_addr = pipe_reg.get('effective_addr', 0)
            self.memory.memory[effective_addr + self.coreid] = pipe_reg.get('store_val', 0)

    def write_back(self, pipe_reg):
        tokens = pipe_reg.get('parts', [])
        if not tokens:
            return
        opcode = tokens[0].lower()
        if opcode in ["add", "addi", "sub", "slt", "li", "la", "jal"]:
            rd = pipe_reg.get('write_reg', None)
            if rd is not None:
                self.registers[rd] = pipe_reg.get('alu_result', 0)
        elif opcode == "lw":
            rd = pipe_reg.get('write_reg', None)
            if rd is not None:
                self.registers[rd] = pipe_reg.get('mem_data', 0)
        # For sw and branch/jump instructions, no register write-back is needed.

    def pipeline_cycle(self, program):
        # Shift pipeline registers one stage ahead:
        new_pipeline = {
            'WB': self.pipeline['MEM'],
            'MEM': self.pipeline['EX'],
            'EX': self.pipeline['ID'],
            'ID': self.pipeline['IF'],
            'IF': None
        }
        # Fetch stage: get new instruction if available.
        if self.pc < len(program):
            new_pipeline['IF'] = {'inst': program[self.pc]}
            self.pc += 1

        # Process WB stage (write back results)
        if new_pipeline['WB'] is not None:
            self.write_back(new_pipeline['WB'])

        # Process MEM stage (memory access)
        if new_pipeline['MEM'] is not None:
            self.memory_stage(new_pipeline['MEM'])

        # Process EX stage (ALU operations, branch decision)
        if new_pipeline['EX'] is not None:
            self.execute_stage(new_pipeline['EX'])
            if new_pipeline['EX'].get('branch_taken', False):
                # Flush IF and ID stages and update pc if branch is taken.
                new_pipeline['IF'] = None
                new_pipeline['ID'] = None
                self.pc = new_pipeline['EX']['new_pc']

        # Process ID stage (instruction decode)
        if new_pipeline['ID'] is not None:
            self.decode_stage(new_pipeline['ID'])

        self.pipeline = new_pipeline

class Memory:
    def __init__(self):
        self.memory = [0] * 1024
        self.core_memory = []

    def printMemory(self):
        core1, core2, core3, core4 = [], [], [], []
        for i, mem_val in enumerate(self.memory):
            if i % 4 == 0:
                core1.append(mem_val)
            elif i % 4 == 1:
                core2.append(mem_val)
            elif i % 4 == 2:
                core3.append(mem_val)
            elif i % 4 == 3:
                core4.append(mem_val)
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
            values_data = data.split(".word")[1].split()
            values_data = [int(value, 16) for value in values_data if value != '']
            values_data.reverse()
            self.data_segment[data.split(":")[0]] = values_data
        for core in self.cores:
            core.data_segment = self.data_segment

    def make_labels(self):
        for core in self.cores:
            core.make_labels(self.program)

    def run_pipeline(self):
        # Initialize each core's pipeline registers.
        for core in self.cores:
            core.pipeline = {'IF': None, 'ID': None, 'EX': None, 'MEM': None, 'WB': None}
        done = False
        while not done:
            for core in self.cores:
                core.pipeline_cycle(self.program)
            self.clock += 1
            # Check if all cores have finished: no instruction left to fetch and pipeline stages are empty.
            done = True
            for core in self.cores:
                if core.pc < len(self.program) or any(stage is not None for stage in core.pipeline.values()):
                    done = False
                    break

# Sample program (same as before)
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
    program = program.lower()
    program = program.replace(",", "")
    programs = program.split(".text")
    programs_data = programs[0].split(".data")[1].split("\n")
    programs_data = [inst for inst in programs_data if inst != '']
    print("Data segment:", programs_data)
    programs_text = programs[1]
    programs = programs_text.split("\n")
    programs_text = [inst for inst in programs if inst != '']
    print("Text segment:", programs_text)
    return programs_text, programs_data

def main(program):
    programs_text, programs_data = preprocess(program)
    sim = Simulator()
    sim.program = programs_text
    sim.make_data_segment(programs_data)
    sim.make_labels()
    # Run pipelined simulation
    sim.run_pipeline()

    # Print register state for each core
    print("Core 0 registers:", sim.cores[0].registers)
    print("Core 1 registers:", sim.cores[1].registers)
    print("Core 2 registers:", sim.cores[2].registers)
    print("Core 3 registers:", sim.cores[3].registers)
    print(f"Number of clock cycles: {sim.clock}")
    return sim

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('gui.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    program_input = data['program']
    print("Program received:", program_input)
    sim = main(program_input)
    memories = sim.memory.printMemory()
    return jsonify({
        'core0': sim.cores[0].registers,
        'core1': sim.cores[1].registers,
        'core2': sim.cores[2].registers,
        'core3': sim.cores[3].registers,
        'clock': sim.clock,
        'memory': memories,
        'memory1': memories[0],
        'memory2': memories[1],
        'memory3': memories[2],
        'memory4': memories[3],
    })

if __name__ == "__main__":
    # app.run(debug=True)
    main(program)
