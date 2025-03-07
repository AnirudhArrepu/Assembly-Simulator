from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

#class imports
from Memory import Memory
from Core import Core
from Simulator import Simulator


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

program='''
.data

.text
addi x10 x10 2
loop: bne x8 x10 exit
addi x8 x8 1
j loop
exit: addi x0 x0 0
'''


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

    # print(sim.memory.printMemory())

    return sim

if __name__ == "__main__":
    main(program)