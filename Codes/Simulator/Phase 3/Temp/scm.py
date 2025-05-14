class MemorySystem:
    def __init__(self, cache_size=8, scratch_pad_size=32, block_size=4, memory_size=256):
        # Initialize memory components
        self.main_memory = [0] * memory_size
        
        # Cache with tags
        self.cache = [{"valid": False, "tag": None, "data": [0] * block_size} for _ in range(cache_size)]
        
        # Scratch pad without tags (just raw storage blocks)
        # Increased to 32 blocks to match the register count for direct addressing
        self.scratch_pad = [[0] * block_size for _ in range(scratch_pad_size)]
        
        # Register file to simulate CPU registers
        self.registers = [0] * 32  # x0 to x31 registers
        
        # Configuration
        self.cache_size = cache_size
        self.scratch_pad_size = scratch_pad_size
        self.block_size = block_size
        self.memory_size = memory_size
        
        # For simulation purposes, initialize memory with some data
        for i in range(memory_size):
            self.main_memory[i] = i + 100  # Just some arbitrary values
    
    def get_cache_index_and_tag(self, address):
        """Convert memory address to cache index and tag"""
        block_offset = address % self.block_size
        cache_index = (address // self.block_size) % self.cache_size
        tag = address // (self.block_size * self.cache_size)
        return cache_index, tag, block_offset
    
    def lw(self, rd, offset, rs1):
        """Load word from memory to register (RISC-V format: lw rd, offset(rs1))"""
        # Calculate effective address
        address = self.registers[rs1] + offset
        
        cache_index, tag, block_offset = self.get_cache_index_and_tag(address)
        
        # Check if data is in cache (cache hit)
        if self.cache[cache_index]["valid"] and self.cache[cache_index]["tag"] == tag:
            print(f"Cache HIT: Loading from cache block {cache_index}")
            value = self.cache[cache_index]["data"][block_offset]
        else:
            # Cache miss - load data from main memory to cache
            print(f"Cache MISS: Loading from main memory to cache block {cache_index}")
            # Calculate the starting address of the block in main memory
            block_start = (tag * self.cache_size + cache_index) * self.block_size
            
            # Load entire block into cache
            for i in range(self.block_size):
                if block_start + i < self.memory_size:
                    self.cache[cache_index]["data"][i] = self.main_memory[block_start + i]
            
            self.cache[cache_index]["valid"] = True
            self.cache[cache_index]["tag"] = tag
            value = self.cache[cache_index]["data"][block_offset]
        
        # Store value in destination register (except for x0 which is always 0)
        if rd != 0:
            self.registers[rd] = value
        
        return value
    
    def sw(self, rs2, offset, rs1):
        """Store word from register to memory (RISC-V format: sw rs2, offset(rs1))"""
        # Calculate effective address
        address = self.registers[rs1] + offset
        
        cache_index, tag, block_offset = self.get_cache_index_and_tag(address)
        
        # Get value from source register
        value = self.registers[rs2]
        
        # Update main memory
        if 0 <= address < self.memory_size:
            self.main_memory[address] = value
        else:
            print(f"Memory access error: address {address} out of bounds")
            return False
        
        # Check if block is in cache, update it if present (write-through policy)
        if self.cache[cache_index]["valid"] and self.cache[cache_index]["tag"] == tag:
            print(f"Updating cache block {cache_index} during store")
            self.cache[cache_index]["data"][block_offset] = value
        
        return True
    
    def lw_spm(self, rd, offset, rs1):
        """Load word from scratch pad to register (Format: lw_spm rd, offset(rs1))
        rs1 register number corresponds directly to the scratch pad block number"""
        # Use the rs1 register number directly as the block number
        block_num = rs1
        
        # Calculate element index within the block (assuming 4-byte words)
        element_index = offset // 4
        
        if 0 <= block_num < self.scratch_pad_size and 0 <= element_index < self.block_size:
            print(f"Loading from scratch pad block {block_num} (register x{rs1}), element index {element_index} (offset {offset})")
            value = self.scratch_pad[block_num][element_index]
            
            # Store value in destination register (except for x0 which is always 0)
            if rd != 0:
                self.registers[rd] = value
                
            return value
        else:
            print(f"Invalid scratch pad access: block {block_num}, element index {element_index}")
            return None
    
    def sw_spm(self, rs2, offset, rs1):
        """Store word from register to scratch pad (Format: sw_spm rs2, offset(rs1))
        rs1 register number corresponds directly to the scratch pad block number
        offset is the index into the block (0, 4, 8, ...)
        rs2 contains the value to store"""
        # Use the rs1 register number directly as the block number
        block_num = rs1
        value = self.registers[rs2]
        
        # Calculate element index within the block (assuming 4-byte words)
        element_index = offset // 4
        
        if 0 <= block_num < self.scratch_pad_size and 0 <= element_index < self.block_size:
            print(f"Storing to scratch pad block {block_num} (register x{rs1}), element index {element_index} (offset {offset})")
            self.scratch_pad[block_num][element_index] = value
            return True
        else:
            print(f"Invalid scratch pad access: block {block_num}, element index {element_index}")
            return False
    
    # Arithmetic and logical operations
    def add(self, rd, rs1, rs2):
        """Add operation: add rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = self.registers[rs1] + self.registers[rs2]
        return self.registers[rd] if rd != 0 else 0
    
    def sub(self, rd, rs1, rs2):
        """Subtract operation: sub rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = self.registers[rs1] - self.registers[rs2]
        return self.registers[rd] if rd != 0 else 0
    
    def addi(self, rd, rs1, imm):
        """Add immediate operation: addi rd, rs1, imm"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = self.registers[rs1] + imm
        return self.registers[rd] if rd != 0 else 0
    
    def mul(self, rd, rs1, rs2):
        """Multiply operation: mul rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = self.registers[rs1] * self.registers[rs2]
        return self.registers[rd] if rd != 0 else 0
    
    def div(self, rd, rs1, rs2):
        """Divide operation: div rd, rs1, rs2"""
        if rd != 0 and self.registers[rs2] != 0:  # Check for division by zero
            self.registers[rd] = self.registers[rs1] // self.registers[rs2]  # Integer division
            return self.registers[rd]
        elif self.registers[rs2] == 0:
            print("Error: Division by zero")
            return None
        return 0
    
    def and_op(self, rd, rs1, rs2):
        """Bitwise AND operation: and rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = self.registers[rs1] & self.registers[rs2]
        return self.registers[rd] if rd != 0 else 0
    
    def xor_op(self, rd, rs1, rs2):
        """Bitwise XOR operation: xor rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = self.registers[rs1] ^ self.registers[rs2]
        return self.registers[rd] if rd != 0 else 0
    
    def sll(self, rd, rs1, rs2):
        """Shift left logical operation: sll rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            shift_amount = self.registers[rs2] & 0x1F  # Only use bottom 5 bits
            self.registers[rd] = self.registers[rs1] << shift_amount
        return self.registers[rd] if rd != 0 else 0
    
    def slt(self, rd, rs1, rs2):
        """Set less than operation: slt rd, rs1, rs2"""
        if rd != 0:  # x0 is always 0
            self.registers[rd] = 1 if self.registers[rs1] < self.registers[rs2] else 0
        return self.registers[rd] if rd != 0 else 0
    
    def set_register(self, reg_num, value):
        """Set register value (for simulation purposes)"""
        if 0 <= reg_num < len(self.registers) and reg_num != 0:  # x0 is always 0
            self.registers[reg_num] = value
            return True
        elif reg_num == 0:
            print("Cannot set register x0 (always 0)")
            return False
        else:
            print("Invalid register number")
            return False
    
    def get_register(self, reg_num):
        """Get register value (for simulation purposes)"""
        if 0 <= reg_num < len(self.registers):
            return self.registers[reg_num]
        else:
            print("Invalid register number")
            return None
    
    def display_status(self):
        """Display the status of cache, scratch pad, and registers"""
        print("\n--- CACHE STATUS ---")
        for i in range(self.cache_size):
            if self.cache[i]["valid"]:
                print(f"Block {i}: Tag={self.cache[i]['tag']}, Data={self.cache[i]['data']}")
            else:
                print(f"Block {i}: Invalid")
        
        print("\n--- SCRATCH PAD STATUS ---")
        # Only print scratch pad blocks that have been used (non-zero)
        for i in range(self.scratch_pad_size):
            if any(self.scratch_pad[i]):  # Check if any value in block is non-zero
                print(f"Block {i}: Data={self.scratch_pad[i]}")
        
        print("\n--- REGISTER FILE ---")
        registers_per_row = 4
        for i in range(0, len(self.registers), registers_per_row):
            reg_values = []
            for j in range(registers_per_row):
                if i + j < len(self.registers):
                    reg_values.append(f"x{i+j}={self.registers[i+j]}")
            print(" | ".join(reg_values))
        
        print("\n")


class AssemblyExecutor:
    """Class to simulate execution of assembly instructions"""
    def __init__(self):
        self.memory = MemorySystem()
        self.program_counter = 0
        self.instructions = []
        self.labels = {}  # Dictionary to store label addresses
    
    def load_program(self, assembly_code):
        """Load assembly code into instruction memory"""
        # Parse assembly instructions
        lines = assembly_code.strip().split('\n')
        parsed_instructions = []
        
        # First pass: collect all labels
        pc = 0
        for line in lines:
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')].strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Process labels
            if ':' in line:
                label_parts = line.split(':', 1)
                label = label_parts[0].strip()
                self.labels[label] = pc
                instruction = label_parts[1].strip()
                if not instruction:
                    continue
            else:
                instruction = line.strip()
            
            parsed_instructions.append(instruction)
            pc += 1
        
        self.instructions = parsed_instructions
        self.program_counter = 0
        
        print(f"Loaded {len(self.instructions)} instructions")
        if self.labels:
            print(f"Labels: {self.labels}")
    
    def execute_instruction(self, instruction):
        """Execute a single assembly instruction"""
        # Split the instruction into parts, first by spaces, then handle commas
        parts = instruction.split()
        if not parts:
            return
            
        opcode = parts[0]
        
        if opcode == "li":
            # Load immediate: li rd, imm
            # Remove any trailing commas from register name
            rd_str = parts[1].rstrip(',')
            rd = int(rd_str[1:])  # Extract register number from "x1" -> 1
            imm = int(parts[2])
            print(f"Executing: {instruction}")
            self.memory.set_register(rd, imm)
        
        elif opcode == "lw":
            # Load word: lw rd, offset(rs1)
            # Remove any trailing commas from register name
            rd_str = parts[1].rstrip(',')
            rd = int(rd_str[1:])
            offset_rs1 = parts[2]
            
            # Parse offset(rs1) format
            if '(' in offset_rs1 and ')' in offset_rs1:
                offset_str = offset_rs1[:offset_rs1.index('(')]
                rs1_str = offset_rs1[offset_rs1.index('(')+1:offset_rs1.index(')')]
                
                offset = int(offset_str) if offset_str else 0
                rs1 = int(rs1_str[1:])  # Extract register number from "x1" -> 1
                
                print(f"Executing: {instruction}")
                self.memory.lw(rd, offset, rs1)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "sw":
            # Store word: sw rs2, offset(rs1)
            # Remove any trailing commas from register name
            rs2_str = parts[1].rstrip(',')
            rs2 = int(rs2_str[1:])
            offset_rs1 = parts[2]
            
            # Parse offset(rs1) format
            if '(' in offset_rs1 and ')' in offset_rs1:
                offset_str = offset_rs1[:offset_rs1.index('(')]
                rs1_str = offset_rs1[offset_rs1.index('(')+1:offset_rs1.index(')')]
                
                offset = int(offset_str) if offset_str else 0
                rs1 = int(rs1_str[1:])  # Extract register number from "x1" -> 1
                
                print(f"Executing: {instruction}")
                self.memory.sw(rs2, offset, rs1)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "lw_spm":
            # Load word from scratch pad: lw_spm rd, offset(rs1)
            # Remove any trailing commas from register name
            rd_str = parts[1].rstrip(',')
            rd = int(rd_str[1:])
            offset_rs1 = parts[2]
            
            # Parse offset(rs1) format
            if '(' in offset_rs1 and ')' in offset_rs1:
                offset_str = offset_rs1[:offset_rs1.index('(')]
                rs1_str = offset_rs1[offset_rs1.index('(')+1:offset_rs1.index(')')]
                
                offset = int(offset_str) if offset_str else 0
                rs1 = int(rs1_str[1:])  # Extract register number from "x1" -> 1
                
                print(f"Executing: {instruction}")
                self.memory.lw_spm(rd, offset, rs1)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "sw_spm":
            # Store word to scratch pad: sw_spm rs2, offset(rs1)
            # Remove any trailing commas from register name
            rs2_str = parts[1].rstrip(',')
            rs2 = int(rs2_str[1:])
            offset_rs1 = parts[2]
            
            # Parse offset(rs1) format
            if '(' in offset_rs1 and ')' in offset_rs1:
                offset_str = offset_rs1[:offset_rs1.index('(')]
                rs1_str = offset_rs1[offset_rs1.index('(')+1:offset_rs1.index(')')]
                
                offset = int(offset_str) if offset_str else 0
                rs1 = int(rs1_str[1:])  # Extract register number from "x1" -> 1
                
                print(f"Executing: {instruction}")
                self.memory.sw_spm(rs2, offset, rs1)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        # Arithmetic operations
        elif opcode == "add":
            # add rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.add(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "sub":
            # sub rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.sub(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "addi":
            # addi rd, rs1, imm
            if len(parts) >= 4:
                rd_str = parts[1].rstrip(',')
                rs1_str = parts[2].rstrip(',')
                imm_str = parts[3]
                
                rd = int(rd_str[1:])
                rs1 = int(rs1_str[1:])
                imm = int(imm_str)
                
                print(f"Executing: {instruction}")
                self.memory.addi(rd, rs1, imm)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "mul":
            # mul rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.mul(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "div":
            # div rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.div(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "and":
            # and rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.and_op(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "xor":
            # xor rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.xor_op(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "sll":
            # sll rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.sll(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "slt":
            # slt rd, rs1, rs2
            registers = self._parse_three_registers(parts)
            if registers:
                rd, rs1, rs2 = registers
                print(f"Executing: {instruction}")
                self.memory.slt(rd, rs1, rs2)
            else:
                print(f"Error: Invalid format for {instruction}")
        
        # Branch instructions
        elif opcode == "beq":
            # beq rs1, rs2, label
            if len(parts) >= 4:
                rs1_str = parts[1].rstrip(',')
                rs2_str = parts[2].rstrip(',')
                label = parts[3]
                
                rs1 = int(rs1_str[1:])
                rs2 = int(rs2_str[1:])
                
                print(f"Executing: {instruction}")
                if self.memory.registers[rs1] == self.memory.registers[rs2]:
                    if label in self.labels:
                        self.program_counter = self.labels[label] - 1  # -1 because it will be incremented after this function
                        print(f"Branch taken to {label} at PC {self.labels[label]}")
                    else:
                        print(f"Error: Label {label} not found")
                else:
                    print("Branch not taken")
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "bne":
            # bne rs1, rs2, label
            if len(parts) >= 4:
                rs1_str = parts[1].rstrip(',')
                rs2_str = parts[2].rstrip(',')
                label = parts[3]
                
                rs1 = int(rs1_str[1:])
                rs2 = int(rs2_str[1:])
                
                print(f"Executing: {instruction}")
                if self.memory.registers[rs1] != self.memory.registers[rs2]:
                    if label in self.labels:
                        self.program_counter = self.labels[label] - 1  # -1 because it will be incremented after this function
                        print(f"Branch taken to {label} at PC {self.labels[label]}")
                    else:
                        print(f"Error: Label {label} not found")
                else:
                    print("Branch not taken")
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "ble":
            # ble rs1, rs2, label
            if len(parts) >= 4:
                rs1_str = parts[1].rstrip(',')
                rs2_str = parts[2].rstrip(',')
                label = parts[3]
                
                rs1 = int(rs1_str[1:])
                rs2 = int(rs2_str[1:])
                
                print(f"Executing: {instruction}")
                if self.memory.registers[rs1] <= self.memory.registers[rs2]:
                    if label in self.labels:
                        self.program_counter = self.labels[label] - 1  # -1 because it will be incremented after this function
                        print(f"Branch taken to {label} at PC {self.labels[label]}")
                    else:
                        print(f"Error: Label {label} not found")
                else:
                    print("Branch not taken")
            else:
                print(f"Error: Invalid format for {instruction}")
        
        # Jump instructions
        elif opcode == "j":
            # j label
            if len(parts) >= 2:
                label = parts[1]
                
                print(f"Executing: {instruction}")
                if label in self.labels:
                    self.program_counter = self.labels[label] - 1  # -1 because it will be incremented after this function
                    print(f"Jump to {label} at PC {self.labels[label]}")
                else:
                    print(f"Error: Label {label} not found")
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "jal":
            # jal rd, label
            if len(parts) >= 3:
                rd_str = parts[1].rstrip(',')
                label = parts[2]
                
                rd = int(rd_str[1:])
                
                print(f"Executing: {instruction}")
                # Store return address (next instruction) in rd
                if rd != 0:  # x0 is always 0
                    self.memory.registers[rd] = self.program_counter + 1
                
                if label in self.labels:
                    self.program_counter = self.labels[label] - 1  # -1 because it will be incremented after this function
                    print(f"Jump and link to {label} at PC {self.labels[label]}")
                else:
                    print(f"Error: Label {label} not found")
            else:
                print(f"Error: Invalid format for {instruction}")
        
        elif opcode == "jalr":
            # jalr rd, rs1, offset
            if len(parts) >= 4:
                rd_str = parts[1].rstrip(',')
                rs1_str = parts[2].rstrip(',')
                offset_str = parts[3]
                
                rd = int(rd_str[1:])
                rs1 = int(rs1_str[1:])
                offset = int(offset_str)
                
                print(f"Executing: {instruction}")
                # Store return address (next instruction) in rd
                if rd != 0:  # x0 is always 0
                    self.memory.registers[rd] = self.program_counter + 1
                
                # Jump to address in rs1 + offset
                target_pc = self.memory.registers[rs1] + offset
                if 0 <= target_pc < len(self.instructions):
                    self.program_counter = target_pc - 1  # -1 because it will be incremented after this function
                    print(f"Jump and link register to PC {target_pc}")
                else:
                    print(f"Error: Target PC {target_pc} out of bounds")
            else:
                print(f"Error: Invalid format for {instruction}")
        
        else:
            print(f"Error: Unknown instruction {instruction}")
    
    def _parse_three_registers(self, parts):
        """Helper method to parse three register operands"""
        if len(parts) >= 4:
            rd_str = parts[1].rstrip(',')
            rs1_str = parts[2].rstrip(',')
            rs2_str = parts[3]
            
            rd = int(rd_str[1:])
            rs1 = int(rs1_str[1:])
            rs2 = int(rs2_str[1:])
            
            return rd, rs1, rs2
        return None
    
    def run_program(self):
        """Execute all instructions in the program"""
        while 0 <= self.program_counter < len(self.instructions):
            self.execute_instruction(self.instructions[self.program_counter])
            self.program_counter += 1
        
        print("\nProgram execution completed.")
        self.memory.display_status()


# Example assembly program to demonstrate the new instructions
example_program = """
# Initialize registers with values
li x1, 100     # Memory address to load from
li x2, 5       # Value for arithmetic operations
li x3, 3       # Another value

# Demonstrate arithmetic operations
add x4, x2, x3   # x4 = x2 + x3 = 5 + 3 = 8
sub x5, x2, x3   # x5 = x2 - x3 = 5 - 3 = 2
mul x6, x2, x3   # x6 = x2 * x3 = 5 * 3 = 15
div x7, x6, x3   # x7 = x6 / x3 = 15 / 3 = 5
addi x8, x2, 10  # x8 = x2 + 10 = 5 + 10 = 15

# Logical operations
and x9, x2, x3   # x9 = x2 & x3 = 5 & 3 = 1
xor x10, x2, x3  # x10 = x2 ^ x3 = 5 ^ 3 = 6
sll x11, x3, x2  # x11 = x3 << x2 = 3 << 5 = 96
slt x12, x3, x2  # x12 = (x3 < x2) ? 1 : 0 = (3 < 5) ? 1 : 0 = 1

# Store a value to the scratch pad using register as block number
sw_spm x4, 0(x3)   # Store x4 to scratch pad block x3 (block 3), element index 0
sw x4, 0(x3)

# Load from scratch pad
lw_spm x13, 0(x3)  # Load from scratch pad block x3 (block 3), element index 0 to x13
lw_spm x13 4(x7)
# Store to scratch pad at block 7
li x14, 777
sw_spm x14, 4(x7)  # Store x14 to scratch pad block x7 (block 7), element index 1
lw_spm x13 4(x7)
lw_spm x28 0(x3)
sw_spm x28 0(x31)
# Demonstrate branch and jump
loop_start:
  addi x15, x15, 1    # Increment x15
  beq x15, x2, loop_end  # If x15 == x2 (5), exit loop

  # Store loop counter to scratch pad using the counter itself as block number
  # Store loop counter to scratch pad using the counter itself as block number
  sw_spm x15, 0(x15)  # Store x15 to scratch pad block x15, element index 0
  
  j loop_start        # Jump back to loop_start

loop_end:
  # Load from main memory with caching
  lw x16, 0(x1)       # Load from address in x1 to x16 (address 100)
  addi x1, x1, 4      # Increment address by 4
  lw x17, 0(x1)       # Load from address in x1 to x17 (address 104)

  # Store to main memory
  sw x6, 0(x1)        # Store x6 to address in x1 (address 104)

  # Jump to end
  jal x18, end        # Jump to end, saving PC+1 to x18
  
  # This should not execute
  li x19, 999

end:
  # Done
  li x20, 42          # Exit code
"""

# Test and run the program
simulator = AssemblyExecutor()
simulator.load_program(example_program)
simulator.run_program()