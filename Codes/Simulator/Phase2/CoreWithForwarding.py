from Core import If_program


class CoreWithForwarding:
    def __init__(self, coreid, memory):
        self.pc = 0
        self.coreid = coreid
        self.memory = memory
        self.program_label_map = {}
        self.registers = [0] * 32

        self.data_segment = {}
        self.memory_data_index = 1020

        # Latency values for operations.
        # (If a latency is set to 0, we treat it as 1 cycle.)
        self.latencies = {
            "add": 1,
            "addi": 1,
            "sub": 1,
            # Other instructions not in the dictionary default to 1 cycle.
        }

        # x31 is the special register.
        self.registers[31] = coreid

        # Pipeline registers.
        self.pipeline_reg = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }

        self.stall_count = 0  # Stall count initialization

    def make_labels(self, insts):
        If_program.program = insts
        for i, inst in enumerate(insts):
            tokens = inst.split()
            if tokens and ":" in tokens[0]:
                label = tokens[0].split(":")[0]
                self.program_label_map[label] = i
        print("Label Map:", self.program_label_map)

    # --- Helper Methods for Hazard Detection and Forwarding ---
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
            parts = tokens[2].split('(')
            if len(parts) >= 2:
                reg_str = parts[1].replace(")", "")
                sources = [int(reg_str[1:])]
        elif op == "sw":
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

    def detect_data_hazard(self, tokens):
        """
        With forwarding, most RAW hazards are handled.
        However, a load-use hazard may require a stall because the loaded value
        is not available until after the MEM stage.
        Here we detect if the instruction in EX is a load (lw) whose result is
        needed by the instruction in ID.
        """
        ex_inst = self.pipeline_reg["EX"]
        if ex_inst is not None and ex_inst["tokens"][0].lower() == "lw":
            dest = self.get_destination_register(ex_inst["tokens"])
            if dest is not None and dest in self.extract_source_registers(tokens):
                return True
        return False

    def flush_pipeline(self):
        """Flush the pipeline registers for control hazards."""
        self.pipeline_reg["IF"] = None
        self.pipeline_reg["ID"] = None
        self.pipeline_reg["EX"] = None
        self.pipeline_reg["MEM"] = None

    def forward_value(self, reg):
        """
        Return the most up-to-date value for register `reg`.
        Check MEM stage first (forwarding from a previous ALU operation or load),
        then WB stage if needed; otherwise return the register file value.
        """
        mem_inst = self.pipeline_reg["MEM"]
        if mem_inst is not None:
            dest = self.get_destination_register(mem_inst["tokens"])
            if dest == reg:
                return mem_inst["mem_result"]
        return self.registers[reg]

    # --- Pipeline Stages ---
    def ID(self):
        # Structural hazard check: if EX is busy with a multi-cycle instruction, stall ID.
        if self.pipeline_reg["EX"] is not None:
            ex_inst = self.pipeline_reg["EX"]
            if "cycles_remaining" in ex_inst and ex_inst["cycles_remaining"] > 1:
                print("Stalling in ID due to busy EX stage for instruction in IF:",
                      self.pipeline_reg["IF"])
                self.stall_count += 1
                # Do not clear IF; keep the instruction waiting.
                return

        if self.pipeline_reg["IF"] is None:
            self.pipeline_reg["ID"] = None
        else:
            tokens = self.pipeline_reg["IF"].split()
            # Remove label if present.
            if tokens and ":" in tokens[0]:
                tokens.pop(0)
            # For branch/jump instructions, bypass hazard detection.
            if tokens[0].lower() in ("bne", "beq", "ble", "j", "jal", "jr"):
                self.pipeline_reg["ID"] = tokens
                self.pipeline_reg["IF"] = None
            else:
                # Check for load-use hazard.
                if self.detect_data_hazard(tokens):
                    print("Stalling in ID due to load-use hazard for instruction:", tokens)
                    self.pipeline_reg["ID"] = ["NOP"]
                    self.stall_count += 1
                else:
                    self.pipeline_reg["ID"] = tokens
                    self.pipeline_reg["IF"] = None

    def EX(self):
        # If an instruction is already in EX, check if it is still executing.
        if self.pipeline_reg["EX"] is not None:
            ex_inst = self.pipeline_reg["EX"]
            if "cycles_remaining" in ex_inst and ex_inst["cycles_remaining"] > 1:
                ex_inst["cycles_remaining"] -= 1
                self.stall_count += 1  # Count this cycle as a stall due to multi-cycle execution.
                print("EX stage stalling, cycles remaining:",
                      ex_inst["cycles_remaining"], "for instruction:", ex_inst["tokens"])
                return
            # When cycles_remaining equals 1, the instruction is now ready to move to MEM.
            return

        # If EX is empty, load the instruction from ID.
        if self.pipeline_reg["ID"] is None or self.pipeline_reg["ID"][0].lower() == "nop":
            self.pipeline_reg["EX"] = None
            return

        tokens = self.pipeline_reg["ID"]
        op = tokens[0].lower()
        result = None
        mem_addr = None

        # Compute result using forwarded register values.
        if op == "la":  # la rd, data_label
            result = tokens[2]
        elif op == "add":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            result = self.forward_value(rs1) + self.forward_value(rs2)
        elif op == "addi":
            rs1 = int(tokens[2][1:])
            imm = int(tokens[3])
            result = self.forward_value(rs1) + imm
        elif op == "sub":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            result = self.forward_value(rs1) - self.forward_value(rs2)
        elif op == "slt":
            rs1 = int(tokens[2][1:])
            rs2 = int(tokens[3][1:])
            result = 1 if self.forward_value(rs1) < self.forward_value(rs2) else 0
        elif op == "li":
            imm = int(tokens[2])
            result = imm
        elif op == "lw":
            # lw rd, offset(rs)
            offset, reg = tokens[2].split('(')
            rs = int(reg[:-1][1:])
            base_val = self.forward_value(rs)
            mem_addr = base_val + int(offset)
        elif op == "sw":
            # sw rs, offset(rd)
            offset, reg = tokens[2].split('(')
            rs = int(tokens[1][1:])
            rd = int(reg[:-1][1:])
            base_val = self.forward_value(rd)
            mem_addr = base_val + int(offset)
        elif op in ("bne", "beq", "ble"):
            rs1 = int(tokens[1][1:])
            rs2 = int(tokens[2][1:])
            val1 = self.forward_value(rs1)
            val2 = self.forward_value(rs2)
            condition = False
            if op == "bne":
                condition = (val1 != val2)
            elif op == "beq":
                condition = (val1 == val2)
            elif op == "ble":
                condition = (val1 <= val2)
            if condition:
                print("Branch taken in EX for instruction:", tokens)
                self.pc = self.program_label_map[tokens[3]]
                self.flush_pipeline()
                # Do not set EX; the branch flushes the pipeline.
                return
            else:
                print("Branch not taken in EX for instruction:", tokens)
        elif op == "jal":
            result = self.pc + 1
        elif op == "jr":
            rs = int(tokens[1][1:])
            result = self.forward_value(rs)
        elif op == "j":
            # Unconditional jump does not compute a result.
            pass
        else:
            print("undefined operation in EX stage:", tokens[0])

        # Determine the number of cycles this instruction should spend in EX.
        # If the latency value is 0, we treat it as 1 cycle.
        latency = self.latencies.get(op, 1)
        if latency < 1:
            latency = 1

        # Place the instruction in EX with its computed result, memory address,
        # and the appropriate multi-cycle latency counter.
        self.pipeline_reg["EX"] = {
            "tokens": tokens,
            "result": result,
            "mem_addr": mem_addr,
            "cycles_remaining": latency
        }
        # Clear ID as the instruction moves to EX.
        self.pipeline_reg["ID"] = None

    def MEM(self):
        # Only move the instruction from EX to MEM if there is one.
        if self.pipeline_reg["EX"] is None:
            self.pipeline_reg["MEM"] = None
            return

        ex_data = self.pipeline_reg["EX"]
        # If the instruction is still in multi-cycle EX, then wait.
        if "cycles_remaining" in ex_data and ex_data["cycles_remaining"] > 1:
            print("MEM stage waiting on EX stage stall for instruction:", ex_data["tokens"])
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
                self.memory.memory[self.memory_data_index] = val
                print("Core", self.coreid, "writing", val,
                      "at memory index", self.memory_data_index)
                self.memory_data_index -= 4
            mem_result = self.memory_data_index + 4
        elif op == "lw":
            mem_result = self.memory.memory[mem_addr]
        elif op == "sw":
            rs = int(tokens[1][1:])
            self.memory.memory[mem_addr] = self.registers[rs]

        self.pipeline_reg["MEM"] = {"tokens": tokens, "mem_result": mem_result}
        # Clear EX since its result is now in MEM.
        self.pipeline_reg["EX"] = None

    def WB(self):
        mem_data = self.pipeline_reg["MEM"]
        if mem_data is None:
            self.pipeline_reg["WB"] = None
            return

        tokens = mem_data["tokens"]
        op = tokens[0].lower()
        mem_result = mem_data["mem_result"]

        if op in ("la", "add", "addi", "sub", "slt", "li", "lw"):
            rd = int(tokens[1][1:])
            self.registers[rd] = mem_result
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
        elif op == "jal":
            rd = int(tokens[1][1:])
            self.registers[rd] = mem_result
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
        return (self.pipeline_reg["IF"] is None and 
                self.pipeline_reg["ID"] is None and 
                self.pipeline_reg["EX"] is None and 
                self.pipeline_reg["MEM"] is None and 
                self.pipeline_reg["WB"] is None)

    def pipeline_cycle(self):
        # Execute pipeline stages in reverse order so that each stage
        # uses the previous cycle's outputs.
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        pc, pip_if = If_program.IF(self.pipeline_reg["IF"], self.pc)
        self.pc = pc
        self.pipeline_reg["IF"] = pip_if
