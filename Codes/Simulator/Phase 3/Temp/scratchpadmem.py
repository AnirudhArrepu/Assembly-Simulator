class Memory:
    def __init__(self, size_bytes):
        self.size = size_bytes
        self.data = bytearray(size_bytes)
    
    def read_word(self, address):
        if address < 0 or address + 4 > self.size:
            raise ValueError(f"Memory access out of bounds: {address}")
        return int.from_bytes(self.data[address:address+4], byteorder='little')
    
    def write_word(self, address, value):
        if address < 0 or address + 4 > self.size:
            raise ValueError(f"Memory access out of bounds: {address}")
        self.data[address:address+4] = value.to_bytes(4, byteorder='little')


class Cache:
    def __init__(self, size_bytes, line_size=64, associativity=4):
        self.size = size_bytes
        self.line_size = line_size
        self.associativity = associativity
        self.num_sets = size_bytes // (line_size * associativity)
        
        # Each cache line stores: valid bit, tag, and data
        self.lines = [[{'valid': False, 'tag': 0, 'data': bytearray(line_size)} 
                      for _ in range(associativity)] for _ in range(self.num_sets)]
        self.replacement_counters = [[0 for _ in range(associativity)] for _ in range(self.num_sets)]
        
        # Cache statistics
        self.hits = 0
        self.misses = 0
    
    def get_set_index(self, address):
        return (address // self.line_size) % self.num_sets
    
    def get_tag(self, address):
        return address // (self.line_size * self.num_sets)
    
    def get_offset(self, address):
        return address % self.line_size
    
    def read_word(self, address, main_memory):
        set_idx = self.get_set_index(address)
        tag = self.get_tag(address)
        offset = self.get_offset(address)
        
        # Check if data is in cache
        for i, line in enumerate(self.lines[set_idx]):
            if line['valid'] and line['tag'] == tag:
                # Cache hit
                self.hits += 1
                # Update replacement counter (LRU policy)
                self.replacement_counters[set_idx][i] = 0
                for j in range(self.associativity):
                    if j != i:
                        self.replacement_counters[set_idx][j] += 1
                
                return int.from_bytes(line['data'][offset:offset+4], byteorder='little')
        
        # Cache miss
        self.misses += 1
        
        # Find line to replace (LRU)
        replace_idx = self.replacement_counters[set_idx].index(max(self.replacement_counters[set_idx]))
        
        # Calculate address of the start of the cache line in main memory
        line_start = (tag * self.num_sets + set_idx) * self.line_size
        
        # Read entire cache line from main memory
        for i in range(0, self.line_size, 4):
            if line_start + i < main_memory.size:
                word = main_memory.read_word(line_start + i)
                self.lines[set_idx][replace_idx]['data'][i:i+4] = word.to_bytes(4, byteorder='little')
        
        # Update cache line metadata
        self.lines[set_idx][replace_idx]['valid'] = True
        self.lines[set_idx][replace_idx]['tag'] = tag
        
        # Reset replacement counter for this line and increment others
        self.replacement_counters[set_idx] = [c + 1 for c in self.replacement_counters[set_idx]]
        self.replacement_counters[set_idx][replace_idx] = 0
        
        # Return requested word
        return int.from_bytes(self.lines[set_idx][replace_idx]['data'][offset:offset+4], byteorder='little')
    
    def write_word(self, address, value, main_memory):
        # Write-through policy
        set_idx = self.get_set_index(address)
        tag = self.get_tag(address)
        offset = self.get_offset(address)
        
        # Update main memory
        main_memory.write_word(address, value)
        
        # Check if address is in cache
        for i, line in enumerate(self.lines[set_idx]):
            if line['valid'] and line['tag'] == tag:
                # Update cache line
                line['data'][offset:offset+4] = value.to_bytes(4, byteorder='little')
                
                # Update replacement counter (LRU policy)
                self.replacement_counters[set_idx][i] = 0
                for j in range(self.associativity):
                    if j != i:
                        self.replacement_counters[set_idx][j] += 1
                
                break


class ScratchpadMemory:
    def __init__(self, size_bytes):
        self.size = size_bytes
        self.data = bytearray(size_bytes)
        # Statistics
        self.reads = 0
        self.writes = 0
    
    def read_word(self, address):
        if address < 0 or address + 4 > self.size:
            raise ValueError(f"Scratchpad memory access out of bounds: {address}")
        self.reads += 1
        return int.from_bytes(self.data[address:address+4], byteorder='little')
    
    def write_word(self, address, value):
        if address < 0 or address + 4 > self.size:
            raise ValueError(f"Scratchpad memory access out of bounds: {address}")
        self.writes += 1
        self.data[address:address+4] = value.to_bytes(4, byteorder='little')


class Processor:
    def __init__(self, memory_size=1024*1024, cache_l1_size=32*1024, spm_size=32*1024):
        self.main_memory = Memory(memory_size)
        self.l1i_cache = Cache(cache_l1_size)  # L1 instruction cache
        self.l1d_cache = Cache(cache_l1_size)  # L1 data cache
        self.scratchpad = ScratchpadMemory(spm_size)  # Scratchpad memory
        self.registers = [0] * 32  # RISC-V has 32 registers (r0 is hardwired to 0)
        self.pc = 0  # Program counter
        
        # Symbol table for labels
        self.symbol_table = {}
        
        # Initialize data segment pointer
        self.data_segment = 0x1000  # Default data segment start
        
        # System call parameters
        self.syscall_codes = {
            1: "print_int",
            4: "print_string",
            5: "read_int",
            10: "exit"
        }
        
        # For tracking whether program should continue
        self.running = True
    
    def load_data(self, data, start_address):
        """Load data into memory starting at start_address"""
        for i, word in enumerate(data):
            self.main_memory.write_word(start_address + i*4, word)
    
    def add_label(self, label, address):
        """Add a label to the symbol table"""
        self.symbol_table[label] = address
    
    def get_label_address(self, label):
        """Get the address for a label from the symbol table"""
        if label in self.symbol_table:
            return self.symbol_table[label]
        raise ValueError(f"Undefined label: {label}")
    
    def allocate_data(self, size_bytes):
        """Allocate space in the data segment and return the address"""
        addr = self.data_segment
        self.data_segment += size_bytes
        return addr
    
    def execute_instruction(self, instruction_str):
        """Execute a single instruction from string format"""
        instruction_str = instruction_str.strip().lower()
        
        # Skip empty lines and comments
        if not instruction_str or instruction_str.startswith('#'):
            return instruction_str
        
        # Check for label definitions
        if ':' in instruction_str:
            label_part, instruction_part = instruction_str.split(':', 1)
            label = label_part.strip()
            self.add_label(label, self.pc)
            instruction_str = instruction_part.strip()
            if not instruction_str:  # If only a label on this line
                return f"{label}:"
        
        # Parse the instruction
        parts = instruction_str.split()
        if not parts:
            return ""
            
        opcode = parts[0]
        
        # Handle different types of instructions
        if opcode == "addi":
            # Format: addi rd, rs1, imm
            rd_str, rs1_str, imm_str = self._parse_registers_and_imm(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            imm = self._parse_immediate(imm_str)
            
            # Execute addi
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs1] + imm
            
            return f"addi {rd_str}, {rs1_str}, {imm_str}"
        
        elif opcode == "add":
            # Format: add rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute add
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs1] + self.registers[rs2]
            
            return f"add {rd_str}, {rs1_str}, {rs2_str}"
        
        elif opcode == "mul":
            # Format: mul rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute mul
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs1] * self.registers[rs2]
            
            return f"mul {rd_str}, {rs1_str}, {rs2_str}"
        
        elif opcode == "div":
            # Format: div rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute div
            if rd != 0 and self.registers[rs2] != 0:  # r0 is hardwired to 0 and avoid division by zero
                self.registers[rd] = self.registers[rs1] // self.registers[rs2]
            elif self.registers[rs2] == 0:
                raise ValueError("Division by zero!")
            
            return f"div {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "and":
            # Format: and rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute and
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs1] & self.registers[rs2]
            
            return f"and {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "or":
            # Format: or rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute or
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs1] | self.registers[rs2]
            
            return f"or {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "xor":
            # Format: xor rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute xor
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs1] ^ self.registers[rs2]
            
            return f"xor {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "sll":
            # Format: sll rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute sll (shift left logical)
            if rd != 0:  # r0 is hardwired to 0
                shift_amount = self.registers[rs2] & 0x1F  # Use only lower 5 bits for 32-bit shift
                self.registers[rd] = (self.registers[rs1] << shift_amount) & 0xFFFFFFFF
            
            return f"sll {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "srl":
            # Format: srl rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute srl (shift right logical)
            if rd != 0:  # r0 is hardwired to 0
                shift_amount = self.registers[rs2] & 0x1F  # Use only lower 5 bits for 32-bit shift
                self.registers[rd] = (self.registers[rs1] >> shift_amount) & 0xFFFFFFFF
            
            return f"srl {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "sra":
            # Format: sra rd, rs1, rs2
            rd_str, rs1_str, rs2_str = self._parse_registers_and_reg(parts[1:])
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute sra (shift right arithmetic)
            if rd != 0:  # r0 is hardwired to 0
                shift_amount = self.registers[rs2] & 0x1F  # Use only lower 5 bits for 32-bit shift
                
                # Handle sign extension for arithmetic shift
                value = self.registers[rs1]
                if value & 0x80000000:  # Check if negative
                    # For negative numbers, shift right and fill with 1s
                    mask = ((1 << shift_amount) - 1) << (32 - shift_amount)
                    self.registers[rd] = ((value >> shift_amount) | mask) & 0xFFFFFFFF
                else:
                    # For positive numbers, just shift right
                    self.registers[rd] = (value >> shift_amount) & 0xFFFFFFFF
            
            return f"sra {rd_str}, {rs1_str}, {rs2_str}"
            
        elif opcode == "lw":
            # Format: lw rd, offset(rs1)
            rd_str, offset_base = self._parse_load_store(parts[1:])
            offset_str, rs1_str = self._parse_offset_base(offset_base)
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            offset = self._parse_immediate(offset_str)
            
            # Execute lw
            address = self.registers[rs1] + offset
            value = self.l1d_cache.read_word(address, self.main_memory)
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = value
            
            return f"lw {rd_str}, {offset}({rs1_str})"
            
        elif opcode == "sw":
            # Format: sw rs2, offset(rs1)
            rs2_str, offset_base = self._parse_load_store(parts[1:])
            offset_str, rs1_str = self._parse_offset_base(offset_base)
            rs2 = self._get_register_number(rs2_str)
            rs1 = self._get_register_number(rs1_str)
            offset = self._parse_immediate(offset_str)
            
            # Execute sw
            address = self.registers[rs1] + offset
            value = self.registers[rs2]
            self.l1d_cache.write_word(address, value, self.main_memory)
            
            return f"sw {rs2_str}, {offset}({rs1_str})"
            
        elif opcode == "lw_spm":
            # Format: lw_spm rd, offset(rs1)
            rd_str, offset_base = self._parse_load_store(parts[1:])
            offset_str, rs1_str = self._parse_offset_base(offset_base)
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            offset = self._parse_immediate(offset_str)
            
            # Execute lw_spm
            address = self.registers[rs1] + offset
            value = self.scratchpad.read_word(address)
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = value
            
            return f"lw_spm {rd_str}, {offset}({rs1_str})"
            
        elif opcode == "sw_spm":
            # Format: sw_spm rs2, offset(rs1)
            rs2_str, offset_base = self._parse_load_store(parts[1:])
            offset_str, rs1_str = self._parse_offset_base(offset_base)
            rs2 = self._get_register_number(rs2_str)
            rs1 = self._get_register_number(rs1_str)
            offset = self._parse_immediate(offset_str)
            
            # Execute sw_spm
            address = self.registers[rs1] + offset
            value = self.registers[rs2]
            self.scratchpad.write_word(address, value)
            
            return f"sw_spm {rs2_str}, {offset}({rs1_str})"
            
        elif opcode == "li":
            # Format: li rd, imm
            if len(parts) != 3:
                raise ValueError(f"Expected 2 operands for li, got {len(parts)-1}")
            
            rd_str = parts[1].rstrip(',')
            imm_str = parts[2]
            rd = self._get_register_number(rd_str)
            imm = self._parse_immediate(imm_str)
            
            # Execute li (load immediate)
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = imm
            
            return f"li {rd_str}, {imm_str}"
            
        elif opcode == "mv":
            # Format: mv rd, rs
            if len(parts) != 3:
                raise ValueError(f"Expected 2 operands for mv, got {len(parts)-1}")
            
            rd_str = parts[1].rstrip(',')
            rs_str = parts[2]
            rd = self._get_register_number(rd_str)
            rs = self._get_register_number(rs_str)
            
            # Execute mv (move)
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.registers[rs]
            
            return f"mv {rd_str}, {rs_str}"
            
        elif opcode == "la":
            # Format: la rd, label
            if len(parts) != 3:
                raise ValueError(f"Expected 2 operands for la, got {len(parts)-1}")
            
            rd_str = parts[1].rstrip(',')
            label = parts[2]
            rd = self._get_register_number(rd_str)
            
            # Get address for label
            try:
                addr = self.get_label_address(label)
            except ValueError:
                # If label doesn't exist yet, create a placeholder in data segment
                addr = self.allocate_data(4)
                self.add_label(label, addr)
            
            # Execute la (load address)
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = addr
            
            return f"la {rd_str}, {label}"
            
        elif opcode == "blt":
            # Format: blt rs1, rs2, label
            rs1_str, rs2_str, label = self._parse_branch(parts[1:])
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute blt (branch if less than)
            if self.registers[rs1] < self.registers[rs2]:
                try:
                    self.pc = self.get_label_address(label)
                except ValueError:
                    # For forward references, we'd handle this differently in a real simulator
                    print(f"Warning: Forward reference to label '{label}' not implemented in this simulator")
            
            return f"blt {rs1_str}, {rs2_str}, {label}"
            
        elif opcode == "bne":
            # Format: bne rs1, rs2, label
            rs1_str, rs2_str, label = self._parse_branch(parts[1:])
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute bne (branch if not equal)
            if self.registers[rs1] != self.registers[rs2]:
                try:
                    self.pc = self.get_label_address(label)
                except ValueError:
                    # For forward references, we'd handle this differently in a real simulator
                    print(f"Warning: Forward reference to label '{label}' not implemented in this simulator")
            
            return f"bne {rs1_str}, {rs2_str}, {label}"
            
        elif opcode == "ble":
            # Format: ble rs1, rs2, label
            rs1_str, rs2_str, label = self._parse_branch(parts[1:])
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute ble (branch if less than or equal)
            if self.registers[rs1] <= self.registers[rs2]:
                try:
                    self.pc = self.get_label_address(label)
                except ValueError:
                    # For forward references, we'd handle this differently in a real simulator
                    print(f"Warning: Forward reference to label '{label}' not implemented in this simulator")
            
            return f"ble {rs1_str}, {rs2_str}, {label}"
            
        elif opcode == "beq":
            # Format: beq rs1, rs2, label
            rs1_str, rs2_str, label = self._parse_branch(parts[1:])
            rs1 = self._get_register_number(rs1_str)
            rs2 = self._get_register_number(rs2_str)
            
            # Execute beq (branch if equal)
            if self.registers[rs1] == self.registers[rs2]:
                try:
                    self.pc = self.get_label_address(label)
                except ValueError:
                    # For forward references, we'd handle this differently in a real simulator
                    print(f"Warning: Forward reference to label '{label}' not implemented in this simulator")
            
            return f"beq {rs1_str}, {rs2_str}, {label}"
            
        elif opcode == "j":
            # Format: j label
            if len(parts) != 2:
                raise ValueError(f"Expected 1 operand for j, got {len(parts)-1}")
            
            label = parts[1]
            
            # Execute j (jump)
            try:
                self.pc = self.get_label_address(label)
            except ValueError:
                # For forward references, we'd handle this differently in a real simulator
                print(f"Warning: Forward reference to label '{label}' not implemented in this simulator")
            
            return f"j {label}"
            
        elif opcode == "jal":
            # Format: jal rd, label
            if len(parts) != 3:
                raise ValueError(f"Expected 2 operands for jal, got {len(parts)-1}")
            
            rd_str = parts[1].rstrip(',')
            label = parts[2]
            rd = self._get_register_number(rd_str)
            
            # Save return address
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.pc + 4  # Assuming 4-byte instructions
            
            # Execute jal (jump and link)
            try:
                self.pc = self.get_label_address(label)
            except ValueError:
                # For forward references, we'd handle this differently in a real simulator
                print(f"Warning: Forward reference to label '{label}' not implemented in this simulator")
            
            return f"jal {rd_str}, {label}"
            
        elif opcode == "jalr":
            # Format: jalr rd, offset(rs1)
            rd_str, offset_base = self._parse_load_store(parts[1:])
            offset_str, rs1_str = self._parse_offset_base(offset_base)
            rd = self._get_register_number(rd_str)
            rs1 = self._get_register_number(rs1_str)
            offset = self._parse_immediate(offset_str)
            
            # Save return address
            if rd != 0:  # r0 is hardwired to 0
                self.registers[rd] = self.pc + 4  # Assuming 4-byte instructions
            
            # Execute jalr (jump and link register)
            self.pc = (self.registers[rs1] + offset) & 0xFFFFFFFE  # Clear least significant bit
            
            return f"jalr {rd_str}, {offset}({rs1_str})"
            
        elif opcode == "ecall" or opcode == "syscall":
            # Format: ecall or syscall
            # Get syscall code from a0 (x10)
            syscall_code = self.registers[10]
            
            if syscall_code == 1:  # print_int
                print(f"Syscall print_int: {self.registers[11]}")
            elif syscall_code == 4:  # print_string
                # This would require a more complex memory model to support properly
                addr = self.registers[11]
                string_chars = []
                i = 0
                while True:
                    byte = self.main_memory.data[addr + i]
                    if byte == 0:  # Null terminator
                        break
                    string_chars.append(chr(byte))
                    i += 1
                print(f"Syscall print_string: {''.join(string_chars)}")
            elif syscall_code == 5:  # read_int
                try:
                    value = int(input("Enter an integer: "))
                    self.registers[10] = value
                except ValueError:
                    print("Invalid input, using 0")
                    self.registers[10] = 0
            elif syscall_code == 10:  # exit
                print("Program exit requested")
                self.running = False
            else:
                print(f"Unrecognized syscall code: {syscall_code}")
            
            return f"{opcode}"
            
        else:
            return f"Unsupported instruction: {instruction_str}"
    
    def _parse_registers_and_imm(self, parts):
        """Parse register and immediate operands from instruction parts"""
        if len(parts) != 3:
            raise ValueError(f"Expected 3 operands, got {len(parts)}")
        
        rd = parts[0].rstrip(',')
        rs1 = parts[1].rstrip(',')
        imm = parts[2]
        
        return rd, rs1, imm
        
    def _parse_registers_and_reg(self, parts):
        """Parse three register operands from instruction parts"""
        if len(parts) != 3:
            raise ValueError(f"Expected 3 operands, got {len(parts)}")
        
        rd = parts[0].rstrip(',')
        rs1 = parts[1].rstrip(',')
        rs2 = parts[2]
        
        return rd, rs1, rs2
        
    def _parse_branch(self, parts):
        """Parse branch instruction operands (rs1, rs2, label)"""
        if len(parts) != 3:
            raise ValueError(f"Expected 3 operands for branch, got {len(parts)}")
        
        rs1 = parts[0].rstrip(',')
        rs2 = parts[1].rstrip(',')
        label = parts[2]
        
        return rs1, rs2, label
    def _parse_load_store(self, parts):
        """Parse load/store instruction operands (reg, offset(base))"""
        if len(parts) != 2:
            raise ValueError(f"Expected 2 operands for load/store, got {len(parts)}")
        
        reg = parts[0].rstrip(',')
        offset_base = parts[1]
        
        return reg, offset_base
    
    def _parse_offset_base(self, offset_base):
        """Parse offset(base) format into offset and base register"""
        if '(' not in offset_base or not offset_base.endswith(')'):
            raise ValueError(f"Invalid offset(base) format: {offset_base}")
        
        offset_str, rest = offset_base.split('(', 1)
        rs1_str = rest.rstrip(')')
        
        return offset_str, rs1_str
    
    def _get_register_number(self, reg_str):
        """Convert register string (like 'x1' or 'a0') to register number"""
        if not reg_str.startswith(('x', 'a', 't', 's')):
            raise ValueError(f"Invalid register format: {reg_str}")
        
        # Handle register aliases
        if reg_str.startswith('zero'):
            return 0
        elif reg_str.startswith('ra'):
            return 1
        elif reg_str.startswith('sp'):
            return 2
        elif reg_str.startswith('gp'):
            return 3
        elif reg_str.startswith('tp'):
            return 4
        elif reg_str.startswith('t0'):
            return 5
        elif reg_str.startswith('t1'):
            return 6
        elif reg_str.startswith('t2'):
            return 7
        elif reg_str.startswith('s0') or reg_str.startswith('fp'):
            return 8
        elif reg_str.startswith('s1'):
            return 9
        elif reg_str.startswith('a0'):
            return 10
        elif reg_str.startswith('a1'):
            return 11
        elif reg_str.startswith('a2'):
            return 12
        elif reg_str.startswith('a3'):
            return 13
        elif reg_str.startswith('a4'):
            return 14
        elif reg_str.startswith('a5'):
            return 15
        elif reg_str.startswith('a6'):
            return 16
        elif reg_str.startswith('a7'):
            return 17
        elif reg_str.startswith('s2'):
            return 18
        elif reg_str.startswith('s3'):
            return 19
        elif reg_str.startswith('s4'):
            return 20
        elif reg_str.startswith('s5'):
            return 21
        elif reg_str.startswith('s6'):
            return 22
        elif reg_str.startswith('s7'):
            return 23
        elif reg_str.startswith('s8'):
            return 24
        elif reg_str.startswith('s9'):
            return 25
        elif reg_str.startswith('s10'):
            return 26
        elif reg_str.startswith('s11'):
            return 27
        elif reg_str.startswith('t3'):
            return 28
        elif reg_str.startswith('t4'):
            return 29
        elif reg_str.startswith('t5'):
            return 30
        elif reg_str.startswith('t6'):
            return 31
        else:
            # Handle numeric registers (x0-x31)
            try:
                reg_num = int(reg_str[1:])
                if 0 <= reg_num <= 31:
                    return reg_num
                raise ValueError(f"Register number out of range: {reg_str}")
            except ValueError:
                raise ValueError(f"Invalid register format: {reg_str}")
    
    def _parse_immediate(self, imm_str):
        """Parse immediate value from string (supports decimal and hex)"""
        try:
            if imm_str.startswith('0x'):
                return int(imm_str, 16)
            else:
                return int(imm_str)
        except ValueError:
            raise ValueError(f"Invalid immediate value: {imm_str}")
        
    def run_program(self, instructions):
        """Run a list of instructions in text format"""
        executed_instructions = []
        for instr in instructions:
            result = self.execute_instruction(instr)
            executed_instructions.append(result)
        return executed_instructions
    
    def get_stats(self):
        """Return performance statistics"""
        return {
            'L1I Cache Hits': self.l1i_cache.hits,
            'L1I Cache Misses': self.l1i_cache.misses,
            'L1D Cache Hits': self.l1d_cache.hits,
            'L1D Cache Misses': self.l1d_cache.misses,
            'SPM Reads': self.scratchpad.reads,
            'SPM Writes': self.scratchpad.writes,
        }


def run_example():
    # Create processor
    proc = Processor()
    
    # Define memory regions
    DATA_MEMORY_START = 0x1000
    
    # Create test data
    test_data = [10, 20, 30, 40, 50]
    proc.load_data(test_data, DATA_MEMORY_START)
    
    # Define program with direct instructions
    program = [
        # Initialize register x1 with the address of main memory data
           "li x5, 300",
            "li x6, 4",
             "div x8, x5, x6",
             "addi x2 x5 2",
             "sw_spm x3, 0(x2)",
                "lw_spm x4, 0(x2)",
    
]
    
    # Run program
    executed = proc.run_program(program)
    
    # Print results
    print("Executed instructions:")
    for i, instr in enumerate(executed):
        print(f"{i+1:2d}: {instr}")
    
    print("\nRegister values after execution:")
    for i in range(32):
        if i % 4 == 0 and i > 0:
            print()
        print(f"x{i:2d}: {proc.registers[i]:8d}", end="  ")
    print("\n")
    
    print("Data in main memory after execution:")
    for i in range(6):
        addr = DATA_MEMORY_START + i*4
        value = proc.main_memory.read_word(addr)
        print(f"Mem[0x{addr:04x}] = {value}")
    
    print("\nData in scratchpad memory after execution:")
    for i in range(3):
        addr = i*4
        value = proc.scratchpad.read_word(addr)
        print(f"SPM[0x{addr:04x}] = {value}")
    
    print("\nPerformance statistics:")
    stats = proc.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


def interactive_mode():
    """Interactive mode to execute instructions one by one"""
    proc = Processor()
    
    print("RISC-V Processor Simulation with Scratchpad Memory")
    print("Available instructions: addi, lw, sw, lw_spm, sw_spm")
    print("Type 'exit' to quit, 'stats' to see performance statistics")
    print("Type 'memory <address>' to view main memory")
    print("Type 'spm <address>' to view scratchpad memory")
    print("Type 'registers' to view all registers")
    print("Type 'loaddata <address> <value>' to load data into main memory")
    print()
    
    while True:
        try:
            user_input = input("> ").strip()
            
            if user_input.lower() == 'exit':
                break
                
            elif user_input.lower() == 'stats':
                stats = proc.get_stats()
                for key, value in stats.items():
                    print(f"{key}: {value}")
                    
            elif user_input.lower() == 'registers':
                for i in range(32):
                    if i % 4 == 0 and i > 0:
                        print()
                    print(f"x{i:2d}: {proc.registers[i]:8d}", end="  ")
                print()
                
            elif user_input.lower().startswith('memory '):
                try:
                    addr = int(user_input.split()[1], 0)  # 0 prefix for auto base detection
                    value = proc.main_memory.read_word(addr)
                    print(f"Mem[0x{addr:04x}] = {value}")
                except (ValueError, IndexError):
                    print("Invalid address. Usage: memory <address>")
                    
            elif user_input.lower().startswith('spm '):
                try:
                    addr = int(user_input.split()[1], 0)  # 0 prefix for auto base detection
                    value = proc.scratchpad.read_word(addr)
                    print(f"SPM[0x{addr:04x}] = {value}")
                except (ValueError, IndexError):
                    print("Invalid address. Usage: spm <address>")
                    
            elif user_input.lower().startswith('loaddata '):
                try:
                    parts = user_input.split()
                    addr = int(parts[1], 0)  # 0 prefix for auto base detection
                    value = int(parts[2], 0)
                    proc.main_memory.write_word(addr, value)
                    print(f"Loaded value {value} to Mem[0x{addr:04x}]")
                except (ValueError, IndexError):
                    print("Invalid input. Usage: loaddata <address> <value>")
                    
            elif user_input.strip():
                result = proc.execute_instruction(user_input)
                print(f"Executed: {result}")
                
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    mode = input("Select mode (1 for example program, 2 for interactive): ")
    if mode == "1":
        run_example()
    elif mode == "2":
        interactive_mode()
    else:
        print("Invalid selection, running example program")
        run_example()