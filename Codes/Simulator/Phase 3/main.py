import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

#class imports
from Memory import Memory
from Core import Core, If_program
from Simulator import Simulator
from CoreWithForwarding import CoreWithForwarding


# Define test programs
# control hazards
program_control_hazards = '''
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
program_data_hazards = '''
.data

.text
addi x3 x0 3
addi x4 x0 4
add x2 x3 x4
beq x2 x3 label
addi x5 x4 4
label: addi x0 x0 3
'''

program_loop = '''
.data

.text
addi x3 x0 2
loop: bne x3 x0 exit
addi x3 x3 -1
j loop
exit: addi x0 x0 0
'''

program_array = '''
.data
arr: .word 0x1 0x2 0x3 0x4 0x5 0x6 0x7 0x8 0x9 0xA 0xB 0xC 0xD 0xE 0xF 0x10 0x11 0x12 0x13 0x14 0x15 0x16 0x17 0x18 0x19 0x1A 0x1B 0x1C 0x1D 0x1E 0x1F 0x20 0x21 0x22 0x23 0x24 0x25 0x26 0x27 0x28 0x29 0x2A 0x2B 0x2C 0x2D 0x2E 0x2F 0x30 0x31 0x32 0x33 0x34 0x35 0x36 0x37 0x38 0x39 0x3A 0x3B 0x3C 0x3D 0x3E 0x3F 0x40 0x41 0x42 0x43 0x44 0x45 0x46 0x47 0x48 0x49 0x4A 0x4B 0x4C 0x4D 0x4E 0x4F 0x50 0x51 0x52 0x53 0x54 0x55 0x56 0x57 0x58 0x59 0x5A 0x5B 0x5C 0x5D 0x5E 0x5F 0x60 0x61 0x62 0x63 0x64
.text
la x10 arr #array pointer
addi x1 x0 1 #coreid
addi x2 x0 2 #coreid
addi x3 x0 3 #coreid
addi x11 x10 0  #array breaks
addi x12 x11 100
addi x13 x11 200
addi x14 x11 300
addi x7 x0 25 #contains 25 value
addi x8 x0 0 #contains sum value
bne x31 x0 exit1
loop1: beq x7 x0 exit1
lw x4 0(x11)
lw x8 0(x0)
add x8 x8 x4
sw x8 0(x0)
addi x11 x11 4
addi x7 x7 -1
j loop1
exit1: bne x31 x1 exit2
loop2: beq x7 x0 exit2
lw x4 0(x12)
lw x8 4(x0)
add x8 x8 x4
sw x8 4(x0)
addi x12 x12 4
addi x7 x7 -1
j loop2
exit2: bne x31 x2 exit3
loop3: beq x7 x0 exit3
lw x4 0(x13)
lw x8 8(x0)
add x8 x8 x4
sw x8 8(x0)
addi x13 x13 4
addi x7 x7 -1
j loop3
exit3: bne x31 x3 exit
loop4: beq x7 x0 exit
lw x4 0(x14)
lw x8 12(x0)
add x8 x8 x4
sw x8 12(x0)
addi x14 x14 4
addi x7 x7 -1
j loop4
exit: addi x0 x0 0
lw x16 0(x0)
lw x17 4(x0)
lw x18 8(x0)
lw x19 12(x0)
add x16 x16 x17
add x16 x16 x18
add x16 x16 x19
sw x16 16(x0)
bne x31 x0 exitt
ecall x16
exitt: addi x2 x2 0
'''

#bubble sort
program_bubble_sort = '''
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

program_core_test = '''
.data

.text
addi x1 x0 1
addi x2 x0 2
addi x3 x0 3
addi x5 x0 10

bne x31 x0 exit1
addi x5 x0 0
exit1: addi x0 x0 0

bne x31 x1 exit2
addi x5 x1 0
exit2: addi x0 x0 0

bne x31 x2 exit3
addi x5 x2 0
exit3: addi x0 x0 0

bne x31 x3 exit4
addi x5 x3 0
exit4: addi x0 x0 0
'''

#testing cache
program_cache_test = '''
.data
a: .space 409600       # space for a[100000]
sum: .word 0 0 0 0
CID: .word 0

.text
# Load CID into x5
    la x1 CID
    lw x5 0(x1)             # x5 = CID

    li x6 100               # loop limit
    li x7 0                 # count = 0 (outer loop counter)
    li x8 100               # inner loop limit
    li x9 100               # X = 100 (L1D cache size in words)

outer_loop: bge x7 x6 after_outer  # if count >= 100, exit

    li x10 0                # i = 0

inner_loop: bge x10 x8 after_inner

    mul x11 x10 x9         # x11 = i * X
    slli x11 x11 2         # byte offset = x11 * 4

    la x12 a
    add x13 x12 x11        # address of a[i * X]
    lw x14 0(x13)           # x14 = a[i * X]

    la x15 sum
    slli x16 x5 2          # offset = CID * 4
    add x17 x15 x16        # &sum[CID]
    lw x18 0(x17)           # load sum[CID]
    add x18 x18 x14        # add a[i * X]
    sw x18 0(x17)           # store back

    addi x10 x10 1         # i++
    j inner_loop

after_inner: addi x7 x7 1           # count++
    j outer_loop

after_outer: li x19 1
    bne x5 x19 end_if      # if CID != 1, skip reduce & print

    li x20 2                # i = 2
    li x21 3                # upper bound for i

combine_loop: bgt x20 x21 end_combine

    la x22 sum
    slli x23 x20 2         # offset = i * 4
    add x24 x22 x23        # &sum[i]
    lw x25 0(x24)           # sum[i]

    li x26 1
    slli x26 x26 2         # offset = 1 * 4
    add x27 x22 x26        # &sum[1]
    lw x28 0(x27)           # sum[1]
    add x28 x28 x25
    sw x28 0(x27)

    addi x20 x20 1
    j combine_loop

end_combine: lw a0 0(x27)
    li a7 1
    ecall

end_if: ret
'''
program_cache_test_1 = '''
.data
a:      .space 409600       # a[100000]
CID:    .word 0             # core ID

.text

    # Load CID into x1
    la x2 CID
    lw x1 0(x2)           # x1 = CID

    # Initialize sum[CID] register: we'll use x5–x8 for sum[0]–sum[3]
    li x5 0               # sum[0]
    li x6 0               # sum[1]
    li x7 0               # sum[2]
    li x8 0               # sum[3]

    # ---------------------------------------------
    # Step 1: Fill SPM[i] = a[i * X]  for i = 0 to 99
    # X = 100 → byte offset = i * 100 * 4 = i * 400
    li x9 0               # i = 0
    li x10 100            # loop limit
    li x11 400            # stride in bytes (100 * 4)
    la x12 a              # base address of a

fill_spm_loop: bge x9, x10, done_fill_spm

    mul x13 x9 x11       # offset = i * 400
    add x14 x12 x13      # address = a + offset
    lw x15 0(x14)         # x15 = a[i * X]

    # sw_spm x15, i
    # We'll assume sw_spm uses x9 as word index, so no shifting needed
    sw_spm x15 0(x9)      # pseudo-instruction

    addi x9 x9 1
    j fill_spm_loop

done_fill_spm:  li x16 0              # count = 0
outer_loop: bge x16, x10, done_outer

    li x17 0              # i = 0
inner_loop: bge x17 x10 done_inner

    lw_spm x18 0(x17)     # pseudo-instruction: x18 = SPM[i]

    # sum[CID] += SPM[i]
    beq x1 x0 add_cid_0
    li x19 1
    beq x1 x19 add_cid_1
    li x19 2
    beq x1 x19 add_cid_2
    li x19 3
    beq x1 x19 add_cid_3
    j skip_add

add_cid_0: add x5 x5 x18
    j skip_add
add_cid_1: add x6 x6 x18
    j skip_add
add_cid_2: add x7 x7 x18
    j skip_add
add_cid_3: add x8 x8 x18
skip_add: addi x17 x17 1
    j inner_loop
done_inner: addi x16 x16 1
    j outer_loop
done_outer: li x19 1
    bne x1 x19 done_if

    add x6 x6 x7         # sum[1] += sum[2]
    add x6 x6 x8         # sum[1] += sum[3]

    mv a0 x6              # move sum[1] to a0
    li a7 1               # syscall: print int
    ecall

done_if: ret
'''

def preprocess(program):
    """
    Preprocess the program by splitting it into data and text segments.
    
    Args:
        program (str): The entire assembly program as a string
        
    Returns:
        tuple: (programs_text, programs_data) where programs_text is a list of text instructions
               and programs_data is a list of data segment instructions
    """
    # Convert to lowercase and remove commas for consistency
    program = program.lower()
    
    # Check if .data and .text segments exist
    if ".data" not in program:
        # If no data segment, assume everything is text
        programs_data = []
        programs_text = program.replace(".text", "").strip().split("\n")
    else:
        # Split by .text to separate data and text segments
        parts = program.split(".text")
        
        # Process data segment if it exists
        if len(parts) > 0 and ".data" in parts[0]:
            data_segment = parts[0].split(".data")[1].strip()
            programs_data = [inst.strip() for inst in data_segment.split("\n") if inst.strip()]
        else:
            programs_data = []
        
        # Process text segment
        if len(parts) > 1:
            programs_text = [inst.strip() for inst in parts[1].split("\n") if inst.strip()]
        else:
            programs_text = []
    
    print("Data segment:", programs_data)
    print("Text segment:", programs_text)
    
    return programs_text, programs_data


def main(program, forwarding=False):
    """
    Main function to run the simulator with the given program.
    
    Args:
        program (str): The assembly program as a string
        forwarding (bool): Whether to use forwarding or not
        
    Returns:
        Simulator: The simulator object after running the program
    """
    try:
        programs_text, programs_data = preprocess(program)
        
        sim = Simulator(forwarding=forwarding)
        sim.program = programs_text
        
        # Make data segment if it exists
        if programs_data:
            sim.make_data_segment(programs_data)
            
        sim.make_labels()
        sim.run()

        # Print results
        print("\n=== Simulation Results ===")
        print("Register values for each core:")
        for i, core in enumerate(sim.cores):
            print(f"Core {i}: {core.registers}")

        print(f"\nNumber of clock cycles: {sim.clock}")

        shared_memory = sim.memory.printMemory()
        print("\nShared memory:", shared_memory)

        # Print performance metrics
        print("\n=== Performance Metrics ===")
        for i, core in enumerate(sim.cores):
            print(f"Core {i} - Stalls: {core.stall_count}, IPC: {core.get_ipc()}")

        return sim
        
    except Exception as e:
        print(f"Error in simulation: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    try:
        # Choose which program to run
        current_program = program_bubble_sort  # Change this to any program you want to test
        
        # Run the simulation
        sim = main(program=current_program, forwarding=False)
        
        if sim is None:
            print("Simulation failed. Please check the error messages above.")
        
    except Exception as e:
        print(f"Error running main: {e}")
        import traceback
        traceback.print_exc()

# Flask server code (commented out for local testing)
'''
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('gui.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    program = data['program']
    if program is None:
        program = program_file
    forwarding = data['forwarding']
    latencies = data["latencies"]
    
    Core.latencies["add"] = latencies["add"]
    Core.latencies["addi"] = latencies["addi"]
    Core.latencies["sub"] = latencies["sub"]
    
    CoreWithForwarding.latencies["add"] = latencies["add"]
    CoreWithForwarding.latencies["addi"] = latencies["addi"]
    CoreWithForwarding.latencies["sub"] = latencies["sub"]
    
    print(program)
    print(forwarding)
    sim = main(program, forwarding=forwarding)

    shared_memory = sim.memory.printMemory()

    return jsonify({
        'core0': sim.cores[0].get_ipc(),
        'core1': sim.cores[1].get_ipc(),
        'core2': sim.cores[2].get_ipc(),
        'core3': sim.cores[3].get_ipc(),

        'core0_stalls': sim.cores[0].stall_count,
        'core1_stalls': sim.cores[1].stall_count,
        'core2_stalls': sim.cores[2].stall_count,
        'core3_stalls': sim.cores[3].stall_count,
        'clock': sim.clock,
        'memory': shared_memory,
    })

if __name__ == "__main__":
    app.run(debug=True)
'''