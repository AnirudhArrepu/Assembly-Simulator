class CoreWithForwarding:
    def __init__(self, coreid, memory):
        self.pc = 0
        self.coreid = coreid
        self.memory = memory
        self.program_label_map = {}
        self.registers = [0] * 32

        self.data_segment = {}
        self.memory_data_index = 1020

        self.latencies = {
            "add": 0,
            "addi": 1,
            "sub": 0,
        }

        # x31 is the special register
        self.registers[31] = coreid

        # Pipeline registers
        self.pipeline_reg = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }

        self.stall_count = 0  # Initialize stall count

    def make_labels(self, insts):
        self.program = insts
        for i, inst in enumerate(insts):
            tokens = inst.split()
            if tokens and ":" in tokens[0]:
                label = tokens[0].split(":")[0]
                self.program_label_map[label] = i
        print("Label Map:", self.program_label_map)

    # --- Forwarding Helper ---
    def get_operand_value(self, reg_num):
        """
        Return the most up-to-date value for a given register.
        First check if the MEM stage holds an instruction that writes
        to that register. (In a real pipeline you might also check EX,
        but with our stage ordering MEM is sufficient.)
        """
        mem_inst = self.pipeline_reg["MEM"]
        if mem_inst is not None:
            dest = self.get_destination_register(mem_inst["tokens"])
            if dest == reg_num and "mem_result" in mem_inst:
                return mem_inst["mem_result"]
        return self.registers[reg_num]

    # --- Helper Methods for Hazard Detection ---
    def get_destination_register(self, tokens):
        """Return the destination register for instructions that write to a register."""
        op = tokens[0].lower()
        if op in ("add", "addi", "sub", "slt", "li", "lw", "jal", "la"):
            try:
                return int(tokens[1][1:])
            except Exception:
                return None
        return None

    def extract_source_registers(self, tokens):
        """Return a list of registers that the instruction reads from."""
        op = tokens[0].lower()
        sources = []
        if op in ("add", "sub", "slt"):
            sources = [int(tokens[2][1:]), int(tokens[3][1:])]
        elif op in ("addi",):
            sources = [int(tokens[2][1:])]
        elif op == "lw":
            # Format: lw rd, offset(rs) => source is rs.
            parts = tokens[2].split('(')
            if len(parts) >= 2:
                reg_str = parts[1].replace(")", "")
                sources = [int(reg_str[1:])]
        elif op == "sw":
            # Format: sw rs, offset(rd) => sources: rs and rd.
            try:
                src1 = int(tokens[1][1:])
            except Exception:
                src1 = None
            parts = tokens[2].split('(')
            if len(parts) >= 2:
                reg_str = parts[1].replace(")", "")
                src2 = int(reg_str[1:])
                sources = [src1, src2]
            else:
                sources = [src1]
        elif op in ("bne", "beq", "ble"):
            sources = [int(tokens[1][1:]), int(tokens[2][1:])]
        elif op in ("jr",):
            sources = [int(tokens[1][1:])]
        return sources

    def detect_raw_hazard(self, tokens):
        """
        Detect a RAW hazard. However, if the hazard is caused by an ALU
        instruction in EX (whose result is available for forwarding), do not stall.
        A stall is inserted only if a load (lw) in EX is the source of the hazard.
        """
        sources = self.extract_source_registers(tokens)
        for stage in ["EX", "MEM"]:
            inst = self.pipeline_reg[stage]
            if inst is not None:
                dest = self.get_destination_register(inst["tokens"])
                if dest is not None and dest in sources:
                    if stage == "EX":
                        op_ex = inst["tokens"][0].lower()
                        if op_ex == "lw":
                            return True  # Must stall if load result not yet ready
                        else:
                            continue  # Forwarding available for ALU operations
        return False

    def detect_war_hazard(self, tokens):
        """Detect a WAR hazard (typically not a problem in in-order pipelines)."""
        dest = self.get_destination_register(tokens)
        if dest is None:
            return False
        for stage in ["EX", "MEM"]:
            inst = self.pipeline_reg[stage]
            if inst is not None:
                srcs = self.extract_source_registers(inst["tokens"])
                if dest in srcs:
                    return True
        return False

    def detect_data_hazard(self, tokens):
        """Combine RAW and WAR hazard detection."""
        return self.detect_raw_hazard(tokens)
        # (WAR hazards are not expected in our in-order pipeline.)

    def flush_pipeline(self):
        """Flush the pipeline registers for control hazards."""
        self.pipeline_reg["IF"] = None
        self.pipeline_reg["ID"] = None
        self.pipeline_reg["EX"] = None
        self.pipeline_reg["MEM"] = None

    # --- Pipeline Stages ---
    def IF(self):
        # Only fetch a new instruction if the IF register is empty.
        if self.pipeline_reg["IF"] is not None:
            return  # Preserve stalled instruction in IF.
        if self.pc < len(self.program):
            self.pipeline_reg["IF"] = self.program[self.pc]
            print("IF:", self.program[self.pc])
            self.pc += 1
        else:
            self.pipeline_reg["IF"] = None

    def ID(self):
        if self.pipeline_reg["IF"] is None:
            self.pipeline_reg["ID"] = None
        else:
            tokens = self.pipeline_reg["IF"].split()
            # Remove label if present.
            if tokens and ":" in tokens[0]:
                tokens.pop(0)
            # For branch or jump instructions, bypass hazard detection.
            if tokens[0].lower() in ("bne", "beq", "ble", "j", "jal", "jr"):
                self.pipeline_reg["ID"] = tokens
                self.pipeline_reg["IF"] = None
            else:
                # For other instructions, check for data hazards.
                if self.detect_data_hazard(tokens):
                    print("Stalling in ID due to RAW hazard for instruction:", tokens)
                    # Insert a stall (bubble) by setting a NOP in ID.
                    # Note: IF is not cleared so the instruction will be retried.
                    self.pipeline_reg["ID"] = ["NOP"]
                    self.stall_count += 1  # Increment stall count
                else:
                    self.pipeline_reg["ID"] = tokens
                    self.pipeline_reg["IF"] = None

    def EX(self):
        tokens = self.pipeline_reg["ID"]
        if tokens is None or tokens[0].lower() == "nop":
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
            val1 = self.get_operand_value(rs1)
            val2 = self.get_operand_value(rs2)
            result = val1 + val2
        elif op == "addi":
            rs1 = int(tokens[2][1:])
            imm = int(tokens[3])
            val1 = self.get_operand_value(rs1)
            result = val1 + imm
        elif op == "sub":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            val1 = self.get_operand_value(rs1)
            val2 = self.get_operand_value(rs2)
            result = val1 - val2
        elif op == "slt":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            val1 = self.get_operand_value(rs1)
            val2 = self.get_operand_value(rs2)
            result = 1 if val1 < val2 else 0
        elif op == "li":
            imm = int(tokens[2])
            result = imm
        elif op == "lw":
            # lw rd, offset(rs)
            offset, reg = tokens[2].split('(')
            rs = int(reg[:-1][1:])
            base_val = self.get_operand_value(rs)
            mem_addr = base_val + int(offset)
        elif op == "sw":
            # sw rs, offset(rd)
            offset, reg = tokens[2].split('(')
            rs = int(tokens[1][1:])
            rd = int(reg[:-1][1:])
            base_val = self.get_operand_value(rd)
            mem_addr = base_val + int(offset)
        elif op in ("bne", "beq", "ble"):
            # For branch instructions, forward the operand values and resolve the branch here.
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            val1 = self.get_operand_value(rs1)
            val2 = self.get_operand_value(rs2)
            branch_taken = False
            if op == "bne" and val1 != val2:
                branch_taken = True
            elif op == "beq" and val1 == val2:
                branch_taken = True
            elif op == "ble" and val1 <= val2:
                branch_taken = True

            if branch_taken:
                print("Branch taken in EX for instruction:", tokens)
                self.pc = self.program_label_map[tokens[3]]
                self.flush_pipeline()
                result = None
            else:
                print("Branch not taken in EX for instruction:", tokens)
                result = None
        elif op == "jal":
            result = self.pc + 1  # Compute return address.
        elif op == "jr":
            rs = int(tokens[1][1:])
            result = self.get_operand_value(rs)
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
        # For branch instructions, nothing further needs to be done in MEM.
        self.pipeline_reg["MEM"] = {"tokens": tokens, "mem_result": mem_result}
    
    def WB(self):
        mem_data = self.pipeline_reg["MEM"]
        if mem_data is None:
            self.pipeline_reg["WB"] = None
            return

        tokens = mem_data["tokens"]
        op = tokens[0].lower()
        mem_result = mem_data["mem_result"]

        # For non-control instructions, write the result.
        if op in ("la", "add", "addi", "sub", "slt", "li", "lw"):
            rd = int(tokens[1][1:])
            self.registers[rd] = mem_result

        # For branch instructions, they have been resolved in EX stage.
        elif op in ("bne", "beq", "ble"):
            pass
        
        # For jump-and-link, jump-register, and unconditional jump instructions.
        elif op == "jal":
            rd = int(tokens[1][1:])
            self.registers[rd] = mem_result  # Return address computed in EX.
            label = tokens[2]
            print("Jump-and-link taken in WB for instruction:", tokens)
            self.pc = self.program_label_map[label]
            self.flush_pipeline()
        elif op == "jr":
            rs = int(tokens[1][1:])
            print("Jump-register taken in WB for instruction:", tokens)
            self.pc = self.registers[rs]
            self.flush_pipeline()
        elif op == "j":
            label = tokens[1]
            print("Jump taken in WB for instruction:", tokens)
            self.pc = self.program_label_map[label]
            self.flush_pipeline()
        else:
            pass

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