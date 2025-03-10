class If_program:
    program = []

    @staticmethod
    def IF(pipeline_reg_if, pc):
        # Only fetch a new instruction if the IF register is empty.
        if pipeline_reg_if is not None:
            return pc, pipeline_reg_if  # Preserve stalled instruction in IF.
        if pc < len(If_program.program):
            pipeline_reg_if = If_program.program[pc]
            print("IF:", If_program.program[pc])
            pc += 1
        else:
            pipeline_reg_if = None
        return pc, pipeline_reg_if


class Core:
    def __init__(self, coreid, memory):
        self.pc = 0
        self.coreid = coreid
        self.memory = memory
        self.program_label_map = {}
        self.registers = [0] * 32

        self.data_segment = {}
        self.memory_data_index = 1020

        # Latency settings for arithmetic instructions.
        self.latencies = {
            "add": 1,    # Example: 2-cycle latency.
            "addi": 3,
            "sub": 1
        }

        # x31 is the special register holding the core id.
        self.registers[31] = coreid

        # Pipeline registers.
        self.pipeline_reg = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }

        self.stall_count = 0  # For counting stall cycles.

    def make_labels(self, insts):
        If_program.program = insts
        for i, inst in enumerate(insts):
            tokens = inst.split()
            if tokens and ":" in tokens[0]:
                label = tokens[0].split(":")[0]
                self.program_label_map[label] = i
        print("Label Map:", self.program_label_map)

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
        """Detect a RAW hazard: if any source register in the instruction is
        the destination of an instruction in EX or MEM."""
        sources = self.extract_source_registers(tokens)
        for stage in ["EX", "MEM"]:
            inst = self.pipeline_reg[stage]
            if inst is not None:
                dest = self.get_destination_register(inst["tokens"])
                if dest is not None and dest in sources:
                    return True
        return False

    def detect_war_hazard(self, tokens):
        """Detect a WAR hazard: if the instruction's destination register is
        needed as a source by an instruction in EX or MEM.
        Note: In an in-order pipeline, WAR hazards typically do not occur."""
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
        """Combine RAW (and WAR) hazard detection."""
        return self.detect_raw_hazard(tokens)

    def flush_pipeline(self):
        """Flush the pipeline registers for control hazards."""
        self.pipeline_reg["IF"] = None
        self.pipeline_reg["ID"] = None
        self.pipeline_reg["EX"] = None
        self.pipeline_reg["MEM"] = None

    # --- Pipeline Stages ---
    def IF(self):
        # IF stage: Fetch a new instruction only if IF register is empty.
        self.pc, self.pipeline_reg["IF"] = If_program.IF(self.pipeline_reg["IF"], self.pc)

    def ID(self):
        # Do not override the current instruction in ID if one already exists.
        if self.pipeline_reg["ID"] is not None:
            return

        # Only move an instruction from IF to ID if IF is not empty.
        if self.pipeline_reg["IF"] is None:
            return

        tokens = self.pipeline_reg["IF"].split()
        # Remove label if present.
        if tokens and ":" in tokens[0]:
            tokens.pop(0)
        # For branch/jump instructions, bypass hazard detection.
        if tokens[0].lower() in ("bne", "beq", "ble", "j", "jal", "jr"):
            self.pipeline_reg["ID"] = tokens
            self.pipeline_reg["IF"] = None
        else:
            # Check for data hazards.
            if self.detect_data_hazard(tokens):
                print("Stalling in ID due to data hazard for instruction:", tokens)
                # Insert a stall (bubble) by setting a NOP in ID.
                # (Keep IF unchanged so the same instruction is retried.)
                self.pipeline_reg["ID"] = ["NOP"]
                self.stall_count += 1
            else:
                # Advance instruction from IF to ID.
                self.pipeline_reg["ID"] = tokens
                self.pipeline_reg["IF"] = None

    def EX(self):
        # If there is already an instruction in EX, process it.
        if self.pipeline_reg["EX"] is not None:
            inst = self.pipeline_reg["EX"]
            tokens = inst["tokens"]
            op = tokens[0].lower()
            # For arithmetic instructions, check if we are still in the latency period.
            if op in ("add", "addi", "sub", "slt"):
                if "remaining_latency" in inst and inst["remaining_latency"] > 0:
                    print(f"EX stage: stalling {tokens} with remaining latency {inst['remaining_latency']}")
                    inst["remaining_latency"] -= 1
                    return  # Stall in EX until latency cycles have elapsed.
            # Once latency is done (or for non-arithmetic instructions), move the instruction to MEM.
            result = inst.get("result")
            mem_addr = inst.get("mem_addr")
            self.pipeline_reg["MEM"] = {
                "tokens": tokens,
                "mem_result": result
            }
            self.pipeline_reg["EX"] = None
            return

        # If EX is empty, try to load an instruction from the ID stage.
        # If ID holds a stall bubble (NOP), then wait.
        if self.pipeline_reg["ID"] is None or (self.pipeline_reg["ID"] and self.pipeline_reg["ID"][0].lower() == "nop"):
            return

        tokens = self.pipeline_reg["ID"]
        op = tokens[0].lower()
        result = None
        mem_addr = None

        # Compute the result or set up the memory address.
        if op == "la":  # load address
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
            # Compute branch condition in EX.
            result = (int(tokens[1][1:]), int(tokens[2][1:]), tokens[3])
        elif op == "jal":
            result = self.pc + 1
        elif op == "jr":
            rs = int(tokens[1][1:])
            result = self.registers[rs]
        elif op == "j":
            # For an unconditional jump no result is needed.
            pass
        else:
            print("undefined operation in EX stage:", tokens[0])

        # For arithmetic instructions, attach the variable latency.
        if op in ("add", "addi", "sub", "slt"):
            latency = self.latencies.get(op, 0)
            if latency > 0:
                # Start the latency countdown.
                self.pipeline_reg["EX"] = {
                    "tokens": tokens,
                    "result": result,
                    "mem_addr": mem_addr,
                    "remaining_latency": latency - 1  # One cycle consumed upon entry.
                }
                print(f"EX stage: loaded {tokens} with latency {latency}")
                # Clear ID after moving the instruction into EX.
                self.pipeline_reg["ID"] = None
                return

        # For non-arithmetic instructions (or with zero latency), immediately load into EX.
        self.pipeline_reg["EX"] = {
            "tokens": tokens,
            "result": result,
            "mem_addr": mem_addr
        }
        self.pipeline_reg["ID"] = None

    def MEM(self):
        # Only move the instruction from EX to MEM if it is ready.
        if self.pipeline_reg["EX"] is None:
            self.pipeline_reg["MEM"] = None
            return

        ex_data = self.pipeline_reg["EX"]
        tokens = ex_data["tokens"]
        op = tokens[0].lower()
        # For arithmetic instructions, check if latency is still remaining.
        if op in ("add", "addi", "sub", "slt") and "remaining_latency" in ex_data and ex_data["remaining_latency"] > 0:
            # Do not transfer to MEM yet.
            return

        result = ex_data.get("result")
        mem_addr = ex_data.get("mem_addr")
        mem_result = result

        if op == "la":
            data_label = tokens[2]
            for val in self.data_segment.get(data_label, []):
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
        self.pipeline_reg["EX"] = None

    def WB(self):
        mem_data = self.pipeline_reg["MEM"]
        if mem_data is None:
            self.pipeline_reg["WB"] = None
            return

        tokens = mem_data["tokens"]
        op = tokens[0].lower()
        mem_result = mem_data["mem_result"]

        # For non-control instructions, write the result to the destination register.
        if op in ("la", "add", "addi", "sub", "slt", "li", "lw"):
            rd = int(tokens[1][1:])
            self.registers[rd] = mem_result

        # For branch instructions, decide in WB whether to change the PC.
        elif op in ("bne", "beq", "ble"):
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            label = tokens[3]
            if (op == "bne" and self.registers[rs1] != self.registers[rs2]) or \
               (op == "beq" and self.registers[rs1] == self.registers[rs2]) or \
               (op == "ble" and self.registers[rs1] <= self.registers[rs2]):
                print("Branch taken in WB for instruction:", tokens)
                self.pc = self.program_label_map[label]
                self.flush_pipeline()
            else:
                print("Branch not taken in WB for instruction:", tokens)
        
        # For jump-and-link, jump-register, and unconditional jump instructions:
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

        self.pipeline_reg["WB"] = {"tokens": tokens, "final_result": mem_result}

    def pipeline_empty(self):
        """Return True if all pipeline registers are empty."""
        return (self.pipeline_reg["IF"] is None and 
                self.pipeline_reg["ID"] is None and 
                self.pipeline_reg["EX"] is None and 
                self.pipeline_reg["MEM"] is None and 
                self.pipeline_reg["WB"] is None)

    def pipeline_cycle(self):
        """
        Execute one full pipeline cycle.
        The stages are processed in reverse order (WB → MEM → EX → ID → IF)
        so that each stage works with the outputs from the previous cycle.
        """
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        self.IF() #abstraction to call the shared IF