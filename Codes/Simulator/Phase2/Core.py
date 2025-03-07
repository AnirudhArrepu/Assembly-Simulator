class Core:
    def __init__(self, coreid, memory):
        self.pc = 0
        self.coreid = coreid
        self.memory = memory
        self.program_label_map = {}
        self.registers = [0] * 32

        self.data_segment = {}
        self.memory_data_index = 1020

        #x31 is the special register
        self.registers[31] = coreid

        #buffer registers
        self.pipeline_reg = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }

    def make_labels(self, insts):
        self.program = insts
        for i, inst in enumerate(insts):
            tokens = inst.split()
            if tokens and ":" in tokens[0]:
                label = tokens[0].split(":")[0]
                self.program_label_map[label] = i
        print("Label Map:", self.program_label_map)

    def IF(self):
        if self.pc < len(self.program):
            self.pipeline_reg["IF"] = self.program[self.pc]
            print(self.program[self.pc])
            self.pc+=1
        else:
            self.pipeline_reg["IF"] = None

    def ID(self):
        if self.pipeline_reg["IF"] is None:
            self.pipeline_reg["ID"] = None
        else:
            tokens = self.pipeline_reg["IF"].split()
            # Remove label if present
            if tokens and ":" in tokens[0]:
                tokens.pop(0)
            self.pipeline_reg["ID"] = tokens

    def EX(self):
        tokens = self.pipeline_reg["ID"]
        if tokens is None:
            self.pipeline_reg["EX"] = None
            return

        op = tokens[0].lower()
        result = None
        mem_addr = None

        if op == "la":  # la rd, data_label
            result = tokens[2]
        elif op == "add":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            result = self.registers[rs1] + self.registers[rs2]
        elif op == "addi":
            rs1 = int(tokens[2][1:])
            imm = int(tokens[3])
            result = self.registers[rs1] + imm
        elif op == "sub":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            result = self.registers[rs1] - self.registers[rs2]
        elif op == "slt":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            result = 1 if self.registers[rs1] < self.registers[rs2] else 0
        elif op == "li":
            imm = int(tokens[2])
            result = imm
        elif op == "lw":
            # lw rd, offset(rs)
            offset, reg = tokens[2].split('(')
            rs = int(reg[:-1][1:])
            mem_addr = self.registers[rs] + int(offset)
        elif op == "sw":
            # sw rs, offset(rd)
            offset, reg = tokens[2].split('(')
            rs = int(tokens[1][1:])
            rd = int(reg[:-1][1:])
            mem_addr = self.registers[rd] + int(offset)
        elif op in ("bne", "beq", "ble"):
            # For branch instructions, simply pass along register numbers and the label.
            result = (int(tokens[1][1:]), int(tokens[2][1:]), tokens[3])
        elif op == "jal":
            # Compute return address (pc+1) for jal.
            result = self.pc + 1
        elif op == "jr":
            rs = int(tokens[1][1:])
            result = self.registers[rs]
        elif op == "j":
            result = None
        else:
            print("Undefined operation in EX stage:", tokens[0])
        self.pipeline_reg["EX"] = {"tokens": tokens, "result": result, "mem_addr": mem_addr}

    def MEM(self):
        ex_data = self.pipeline_reg["EX"]
        if ex_data is None:
            self.pipeline_reg["MEM"] = None
            return

        tokens = ex_data["tokens"]
        op = tokens[0].lower()
        result = ex_data["result"]
        mem_addr = ex_data["mem_addr"]
        mem_result = result

        if op == "la":
            data_label = tokens[2]
            for val in self.data_segment[data_label]:
                self.memory.memory[self.memory_data_index + self.coreid] = val
                print("Core", self.coreid, "writing", val, "at memory index", self.memory_data_index)
                self.memory_data_index -= 4
            mem_result = self.memory_data_index + 4
        elif op == "lw":
            mem_result = self.memory.memory[mem_addr + self.coreid]
        elif op == "sw":
            rs = int(tokens[1][1:])
            self.memory.memory[mem_addr + self.coreid] = self.registers[rs]
        self.pipeline_reg["MEM"] = {"tokens": tokens, "mem_result": mem_result}

    def WB(self):
        mem_data = self.pipeline_reg["MEM"]
        if mem_data is None:
            self.pipeline_reg["WB"] = None
            return

        tokens = mem_data["tokens"]
        op = tokens[0].lower()
        mem_result = mem_data["mem_result"]

        if op in ("la", "add", "addi", "sub", "slt", "li", "lw", "jal"):
            rd = int(tokens[1][1:])
            self.registers[rd] = mem_result
        elif op in ("bne", "beq", "ble"):
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            label = tokens[3]
            if (op == "bne" and self.registers[rs1] != self.registers[rs2]) or \
               (op == "beq" and self.registers[rs1] == self.registers[rs2]) or \
               (op == "ble" and self.registers[rs1] <= self.registers[rs2]):
                self.pc = self.program_label_map[label]
            else:
                self.pc += 1
        elif op == "jal":
            label = tokens[2]
            self.pc = self.program_label_map[label]
        elif op == "jr":
            rs = int(tokens[1][1:])
            self.pc = self.registers[rs]
        elif op == "j":
            label = tokens[1]
            self.pc = self.program_label_map[label]
        else:
            self.pc += 1

        self.pipeline_reg["WB"] = {"tokens": tokens, "final_result": mem_result}

    def pipeline_empty(self):
        """Return True if all pipeline registers are empty (i.e., None)."""
        return (self.pipeline_reg["IF"] is None and 
                self.pipeline_reg["ID"] is None and 
                self.pipeline_reg["EX"] is None and 
                self.pipeline_reg["MEM"] is None and 
                self.pipeline_reg["WB"] is None)

    def pipeline_cycle(self):
        """
        Execute one full pipeline cycle.
        The stages are called in reverse order (WB → MEM → EX → ID → IF)
        so that each stage uses the previous cycle's outputs.
        """
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF()
