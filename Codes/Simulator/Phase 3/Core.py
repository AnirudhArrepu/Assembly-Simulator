class If_program:
    program = []

    cores = None

    global_sync_pointer = None

    active_pcs = [0, 0, 0, 0]

    global_min = 0

    setInactive = [False, False, False, False]

    call_count = 0

    @staticmethod
    def IF(pipeline_reg_if, pc, core):
        # If there is already an instruction in IF buffer, we may still be
        # waiting on cache stalls—so don't fetch a new one until cycles_remaining==1.
        if pipeline_reg_if is not None:
            # decrement its stall counter if >1
            if pipeline_reg_if.get("cycles_remaining", 0) > 1:
                pipeline_reg_if["cycles_remaining"] -= 1
                core.stall_count += 1
                print("IF stage stalling, cycles remaining:", pipeline_reg_if["cycles_remaining"],
                      "for instruction fetch at PC", pc - 1, If_program.program[pc - 1])
                
                if pipeline_reg_if["cycles_remaining"] == 1:
                    if pipeline_reg_if["raw"] == "sync":
                        print("Core", core.coreid, "sync instruction at PC", pc - 1)
                        If_program.global_sync_pointer[pc-1][core.coreid] = 1
                        if If_program.global_sync_pointer[pc-1] != [1,1,1,1]:
                            pipeline_reg_if["cycles_remaining"] += 1
                            print("Core", core.coreid, "waiting for other cores to sync at PC", pc - 1)
                            print("adding more clock cycles to work")
                
                return pc, pipeline_reg_if
            # once cycles_remaining==1, let it move to ID next cycle
            
            return pc, pipeline_reg_if

        if pc < len(If_program.program):
            # if If_program.call_count%4==0:
            #     If_program.global_min = min([core.pc for core in If_program.cores])
            #     print("global minimum pc", If_program.global_min)
            
            # if pc != If_program.global_min:
            #     print("moved down the pipeline at core", core.coreid, "to PC", pc)
            #     If_program.setInactive[core.coreid] = True
            #     If_program.active_pcs[core.coreid] = pc
            #     pc = If_program.global_min

            # print(If_program.setInactive[core.coreid], "at core", core.coreid, "at PC", pc)
            # if If_program.setInactive[core.coreid] == True and pc == If_program.active_pcs[core.coreid]:
            #     If_program.setInactive[core.coreid] = False
            #     print("core in concurrency with other cores", core.coreid, "at PC", pc)

            If_program.call_count += 1
            
            # if (pc != If_program.global_min):
            #     If_program.active_pcs[core.coreid] = pc
            #     pc = min([core.pc for core in If_program.cores])
            #     print("active instruction in core", core.coreid, "at PC", pc)
            #     If_program.setInactive[core.coreid] = True

            # if pc == If_program.active_pcs[core.coreid]:
            #     print("deactivated instruction in core", core.coreid, "at PC", pc)
            #     If_program.setInactive[core.coreid] = False

            instr = If_program.program[pc]
            addr = pc * 4 + 320 #40 is the address offset of the first instruciton in memory

            fetched, stall_cycles = core.candm.read(core.coreid, addr, True)

            pipeline_reg_if = {
                "raw": instr,
                "cycles_remaining": max(1, stall_cycles)
            }
            print(core.coreid, "IF: fetched", instr, "at PC", pc, "with", stall_cycles, "stall cycles")
            pc += 1

            if "sync" in instr:
                If_program.global_sync_pointer[pc-1][core.coreid] = 1
                print("Core", core.coreid, "sync instruction at PC", pc - 1)
                if If_program.global_sync_pointer[pc-1] != [1,1,1,1]:
                    if pipeline_reg_if["cycles_remaining"] == 1:
                        pipeline_reg_if["cycles_remaining"] += 1
                    print("Core", core.coreid, "waiting for other cores to sync at PC", pc - 1)

        else:
            print(core.coreid, "pc greater than limits")
            pipeline_reg_if = None
        return pc, pipeline_reg_if


from Storage import CacheAndMemory
from Memory import Memory

class Core:
    latencies = {
        "add": 1,
        "addi": 1,
        "sub": 1,
    }
    memory = Memory()
    candm = CacheAndMemory(config_path="config.yaml",
                          memory=memory,
                          num_cores=4)

    def __init__(self, coreid):
        self.pc = 0
        self.coreid = coreid
        self.program_label_map = {}
        self.registers = [0] * 32

        self.data_segment = {}
        self.memory_data_index = 4092

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

        self.stall_count = 0  # Total stall cycles.
        self.pipeline_flush_count = 0
        self.inst_executed = 0

    def get_ipc(self):
        i = self.inst_executed
        s = self.stall_count
        pf = self.pipeline_flush_count

        return i / (i + s + pf)

    def make_labels(self, insts):
        If_program.program = insts
        If_program.global_sync_pointer = [[0,0,0,0] for _ in range(len(insts))]
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
        if op in ("add", "addi", "sub", "slt", "li", "lw", "lw_spm", "jal", "la"):
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
        elif op == "lw" or op == "lw_spm":
            # Format: lw rd, offset(rs) => source is rs.
            parts = tokens[2].split('(')
            if len(parts) >= 2:
                reg_str = parts[1].replace(")", "")
                sources = [int(reg_str[1:])]
        elif op == "sw" or op == "sw_spm":
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
        """Detect a RAW hazard if any source register of the new instruction is the destination
        of an instruction in EX or MEM."""
        sources = self.extract_source_registers(tokens)
        for stage in ["EX", "MEM"]:
            inst = self.pipeline_reg[stage]
            if inst is not None:
                dest = self.get_destination_register(inst["tokens"])
                if dest is not None and dest in sources:
                    return True
        return False

    def detect_war_hazard(self, tokens):
        """Detect a WAR hazard if the new instruction's destination is needed by an instruction in EX or MEM."""
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

    def flush_pipeline(self):
        """Flush the pipeline registers for control hazards."""
        self.pipeline_flush_count += 1
        self.pipeline_reg["IF"] = None
        self.pipeline_reg["ID"] = None
        self.pipeline_reg["EX"] = None
        self.pipeline_reg["MEM"] = None

    # --- Pipeline Stages ---
    def ID(self):
        if self.pipeline_reg["IF"] is None or self.pipeline_reg["IF"]["cycles_remaining"] > 1 or self.pipeline_reg["IF"]["raw"]== "nop" or If_program.setInactive[self.coreid] == True:
            self.pipeline_reg["ID"] = None
        else:
            tokens = self.pipeline_reg["IF"]["raw"].split()
            # Remove label if present.
            if tokens and ":" in tokens[0]:
                tokens.pop(0)
            # Check for a structural hazard: if EX is still busy with an instruction that hasn't
            # finished its multi-cycle execution, stall ID.
            if (self.pipeline_reg["EX"] is not None and
                "cycles_remaining" in self.pipeline_reg["EX"] and
                self.pipeline_reg["EX"]["cycles_remaining"] > 1):
                print("Stalling in ID due to busy EX stage (structural hazard) for instruction:", tokens)
                self.pipeline_reg["ID"] = ["NOP"]
                self.stall_count += 1
            #     # Do not clear IF so the instruction remains.
            # elif (self.pipeline_reg["MEM"] is not None and 
            #       "cycles_remaining" in self.pipeline_reg["MEM"] and
            #       self.pipeline_reg["MEM"]["cycles_remaining"] > 1):
            #     print("Stalling in ID due to busy MEM stage (structural hazard) for instruction:", tokens)
            #     self.pipeline_reg["ID"] = ["NOP"]
            #     self.stall_count += 1
                # Do not clear IF so the instruction remains.
            else:
                # For branch/jump instructions, bypass hazard detection.
                if tokens[0].lower() in ("bne", "beq", "ble", "j", "jal", "jr"):
                    self.pipeline_reg["ID"] = tokens
                    self.pipeline_reg["IF"] = None
                else:
                    # Check for data hazards.
                    if self.detect_data_hazard(tokens):
                        print("Stalling in ID due to data hazard for instruction:", tokens)
                        self.pipeline_reg["ID"] = ["NOP"]
                        self.stall_count += 1
                    else:
                        # No hazards: move instruction from IF to ID.
                        self.pipeline_reg["ID"] = tokens
                        self.pipeline_reg["IF"] = None

    def EX(self):
        # If an instruction is already in EX, check its remaining cycles.
        if self.pipeline_reg["EX"] is not None:
            ex_inst = self.pipeline_reg["EX"]
            if "cycles_remaining" in ex_inst and ex_inst["cycles_remaining"] > 1:
                ex_inst["cycles_remaining"] -= 1
                self.stall_count += 1  # Count this cycle as a stall due to multi-cycle execution.
                print("EX stage stalling, cycles remaining:", ex_inst["cycles_remaining"],
                      "for instruction:", ex_inst["tokens"])
            # If cycles_remaining is 1, the instruction is now ready to be passed to MEM.
            return

        # EX is empty; so load the instruction from ID.
        if self.pipeline_reg["ID"] is None or self.pipeline_reg["ID"][0].lower() == "nop":
            self.pipeline_reg["EX"] = None
            return

        tokens = self.pipeline_reg["ID"]
        op = tokens[0].lower()
        result = None
        mem_addr = None

        # Compute the result based on the operation.
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
        elif op == "lw" or op == "lw_spm":
            offset, reg = tokens[2].split('(')
            rs = int(reg[:-1][1:])
            mem_addr = self.registers[rs] + int(offset)
        elif op == "sw" or op == "sw_spm":
            offset, reg = tokens[2].split('(')
            rs = int(tokens[1][1:])
            rd = int(reg[:-1][1:])
            mem_addr = self.registers[rd] + int(offset)
        elif op in ("bne", "beq", "ble"):
            result = (int(tokens[1][1:]), int(tokens[2][1:]), tokens[3])
        elif op == "jal":
            result = self.pc + 1
        elif op == "jr":
            rs = int(tokens[1][1:])
            result = self.registers[rs]
        elif op == "j":
            # For an unconditional jump no result is needed.
            pass
        elif op == "ecall":
            # For ecall, we do no computation in EX.
            result = 0
        else:
            print("undefined operation in EX stage:", tokens[0])

        # Set the instruction's specific latency.
        latency = Core.latencies.get(op, 1)
        # The instruction remains in EX for 'latency' cycles.
        self.pipeline_reg["EX"] = {
            "tokens": tokens,
            "result": result,
            "mem_addr": mem_addr,
            "cycles_remaining": latency
        }
        # Clear ID since the instruction moves to EX.
        self.pipeline_reg["ID"] = None

    def MEM(self):
        #check if tehre is already an instruction in MEM stage
        if self.pipeline_reg["MEM"] is not None:
            mem_inst = self.pipeline_reg["MEM"]
            # If it still has >1 cycles to go, consume one and stall
            if mem_inst.get("cycles_remaining", 0) > 1:
                mem_inst["cycles_remaining"] -= 1
                self.stall_count += 1
                print("MEM stage stalling, cycles remaining:", mem_inst["cycles_remaining"],
                    "for instruction:", mem_inst["tokens"])
                return

        # Only move the instruction from EX to MEM if there is one.
        if self.pipeline_reg["EX"] is None:
            self.pipeline_reg["MEM"] = None
            return

        ex_data = self.pipeline_reg["EX"]
        # If the instruction is still in multi-cycle EX, wait.
        if "cycles_remaining" in ex_data and ex_data["cycles_remaining"] > 1:
            print("MEM stage waiting on EX stage stall for instruction:", ex_data["tokens"])
            self.pipeline_reg["MEM"] = None
            return

        tokens = ex_data["tokens"]
        op = tokens[0].lower()
        result = ex_data["result"]
        mem_addr = ex_data["mem_addr"]
        mem_result = result
        mem_stalls = 0

        if op == "la":
            data_label = tokens[2]
            for val in self.data_segment[data_label]:
                # self.memory.memory[self.memory_data_index] = val
                mem_stalls += Core.candm.write(self.coreid, self.memory_data_index, val)
                print("Core", self.coreid, "writing", val, "at memory index", self.memory_data_index)
                self.memory_data_index -= 4
            mem_result = self.memory_data_index + 4
        elif op == "lw":
            # mem_result = self.memory.memory[mem_addr]
            mem_result, mem_stalls = Core.candm.read(self.coreid, mem_addr, False)
        elif op == "sw":
            rs = int(tokens[1][1:])
            # self.memory.memory[mem_addr] = self.registers[rs]
            mem_stalls = Core.candm.write(self.coreid, mem_addr, self.registers[rs])
        elif op == "sw_spm":
            rs = int(tokens[1][1:])
            # self.memory.scratch_pad[self.coreid][mem_addr] = self.registers[rs]
            mem_stalls = Core.candm.write_scratch_pad(self.coreid, mem_addr, self.registers[rs])
        elif op == "lw_spm":
            # mem_result = self.memory.scratch_pad[self.coreid][mem_addr]
            mem_result, mem_stalls = Core.candm.read_scratch_pad(self.coreid, mem_addr)
        

        self.pipeline_reg["MEM"] = {"tokens": tokens, "mem_result": mem_result, "cycles_remaining": max(1, mem_stalls)}
        # Clear EX since the instruction moves to MEM.
        self.inst_executed += 1
        self.pipeline_reg["EX"] = None
        print(mem_stalls)

    def WB(self):
        mem_data = self.pipeline_reg["MEM"]
        if mem_data is None or mem_data["cycles_remaining"] > 1:
            self.pipeline_reg["WB"] = None
            return

        tokens = mem_data["tokens"]
        op = tokens[0].lower()
        mem_result = mem_data["mem_result"]

        # For non-control instructions, write the result to the destination register.
        if op in ("la", "add", "addi", "sub", "slt", "li", "lw", "lw_spm"):
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
        elif op == "ecall":
            # For ecall, we expect the second token to contain the register to print.
            reg = int(tokens[1][1:])
            # Print only the register's value.
            print("ECALL: Register x{} = {}".format(reg, self.registers[reg]))
            # Optionally, you can set the final result to that register value.
            mem_result = self.registers[reg]

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
        Stages are processed in reverse order so that outputs from the previous cycle are used.
        """
        self.WB()
        self.MEM()
        self.EX()
        self.ID()
        pc, pip_if = If_program.IF(self.pipeline_reg["IF"], self.pc, self)
        self.pc = pc
        self.pipeline_reg["IF"] = pip_if
