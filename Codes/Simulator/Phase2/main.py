from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

#class imports
from Memory import Memory
from Core import Core, If_program
from Simulator import Simulator


# control hazards
program='''
.data

.text
addi x1 x0 2
addi x10 x0 4
loop: beq x10 x1 exit
addi x10 x10 -1
j loop
exit: addi x0 x0 0
'''

# data hazards
program=''''
.data

.text
addi x3 x0 3
addi x4 x0 4
add x2 x3 x4
beq x2 x3 label
addi x5 x4 4
label: addi x0 x0 3
'''

program = '''
.data

.text
addi x3 x0 2
loop: bne x3 x0 exit
addi x3 x3 -1
j loop
exit: addi x0 x0 0
'''

program2 = '''
.data
arr: .word 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xA 0xB, 0xC, 0xD, 0xE, 0xF, 0x10, 0x11, 0x12, 0x13, 0x14 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x54 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60, 0x61, 0x62, 0x63, 0x64
.text
 la x14 arr
 addi x27 x0 1
 addi x28 x0 2
 addi x29 x0 3
 bne x31 x0 after1
 addi x11 x0 0
 addi x12 x0 25
 addi x13 x0 0
 loop: beq x11 x25 exit1
     lw x15 0(x14)
     add x13 x13 x15
     addi x14 x14 4
     addi x11 x11 1
     j loop
 exit1: sw x13 0(x0)
 after1: bne x31 x27 after2
     addi x11 x0 0
     addi x12 x0 25
     addi x13 x13 0
 loop_1: beq x11 x25 exit2
     lw x15 100(x14)
     add x13 x13 x15
     addi x14 x14 4
     addi x11 x11 1
     j loop_1
 exit2: sw x13 4(x0)
 after2: bne x31 x28 after3
     addi x11 x0 0
     addi x12 x0 25
     addi x13 x13 0
 loop_2: beq x11 x25 exit3
     lw x15 200(x14)
     add x13 x13 x15
     addi x14 x14 4
     addi x11 x11 1
     j loop_2
 exit3: sw x13 8(x0)
 after3: bne x31 x29 after4
     addi x11 x0 0
     addi x12 x0 25
     addi x13 x13 0
 loop_3: beq x11 x25 exit4
     lw x15 300(x14)
     add x13 x13 x15
     addi x14 x14 4
     addi x11 x11 1
     j loop_1
 exit4: sw x13 12(x0)
 after4: bne x31 x0 nop
     lw x17 0(x0)
     lw x18 4(x0)
     lw x19 8(x0)
     lw x20 12(x0)
     add x21 x17 x18
     add x22 x21 x19
     add x23 x22 x20
     sw x23 16(x0)
 nop: addi x26 x0 3
'''

#bubble sort
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


forward = True



def preprocess(program):
    #getting data segment
    program = program.lower()
    program = program.replace(",", "")
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

def main(program, forwarding=False):
    programs_text, programs_data = preprocess(program)
    sim = Simulator(forwarding=forwarding)
    sim.program = programs_text
    sim.make_data_segment(programs_data)
    sim.make_labels()
    sim.run()

    print(sim.cores[0].registers)
    print(sim.cores[1].registers)
    print(sim.cores[2].registers)
    print(sim.cores[3].registers)

    print(f"number of clock cycles: {sim.clock}")

    shared_memory = sim.memory.printMemory()
    print("Shared memory: ", shared_memory)
    # print("Core 0: ", memories[0])
    # print("Core 1: ", memories[1])
    # print("Core 2: ", memories[2])
    # print("Core 3: ", memories[3])

    # Print the stall count for each core
    for i, core in enumerate(sim.cores):
        print(f"Stall count for Core {i}: {core.stall_count}")

    print("IPC", len(If_program.program)/(sim.clock-4))

    return sim

## Local ###
main(program=program, forwarding=True)


# ### Server ###
# app = Flask(__name__)
# CORS(app)

# @app.route('/')
# def index():
#     return render_template('gui.html')

# @app.route('/simulate', methods=['POST'])
# def simulate():
#     data = request.json
#     program = data['program']
#     forwarding = data['forwarding']
#     print(program)
#     print(forwarding)
#     sim = main(program, forwarding=forwarding)

#     shared_memory = sim.memory.printMemory()

#     return jsonify({
#         'core0': sim.cores[0].registers,
#         'core1': sim.cores[1].registers,
#         'core2': sim.cores[2].registers,
#         'core3': sim.cores[3].registers,
#         'clock': sim.clock,
#         'memory': shared_memory,
#     })

# if __name__ == "__main__":
#     app.run(debug=True)