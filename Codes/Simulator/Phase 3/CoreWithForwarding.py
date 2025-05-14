import math
from Storage import CacheAndMemory
from Memory import Memory

class If_program:
    program = []
    cores = None
    global_sync_pointer = None

    @staticmethod
    def IF(pipeline_reg_if, pc, core):
        # If there is already an instruction in IF buffer, we may still be
        # waiting on cache stalls—so don't fetch a new one until cycles_remaining==1.
        if pipeline_reg_if is not None:
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
            return pc, pipeline_reg_if

        if pc < len(If_program.program):
            instr = If_program.program[pc]
            addr = pc * 4 + 320  # address offset of first instruction

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
            print(core.coreid, pc, "pc greater than limits")
            pipeline_reg_if = None
        return pc, pipeline_reg_if

class CoreWithForwarding:
    latencies = {"add": 1, "addi": 1, "sub": 1}
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
        # x31 holds core ID
        self.registers[31] = coreid
        # Pipeline registers
        self.pipeline_reg = {stage: None for stage in ("IF","ID","EX","MEM","WB")}
        self.stall_count = 0
        self.pipeline_flush_count = 0
        self.inst_executed = 0

    def make_labels(self, insts):
        If_program.program = insts
        If_program.global_sync_pointer = [[0]*4 for _ in insts]
        for i, inst in enumerate(insts):
            tokens = inst.split()
            if tokens and ":" in tokens[0]:
                label = tokens[0].split(":")[0]
                self.program_label_map[label] = i
        print("Label Map:", self.program_label_map)

    # --- Hazard Detection & Forwarding Helpers ---
    def get_destination_register(self, tokens):
        op = tokens[0].lower()
        if op in ("add","addi","sub","slt","li","lw","lw_spm","jal","la"):
            try:
                return int(tokens[1][1:])
            except:
                return None
        return None

    def extract_source_registers(self, tokens):
        op = tokens[0].lower()
        srcs = []
        if op in ("add","sub","slt"):
            srcs = [int(tokens[2][1:]), int(tokens[3][1:])]
        elif op == "addi":
            srcs = [int(tokens[2][1:])]
        elif op in ("lw","lw_spm"):
            off, reg = tokens[2].split('(')
            srcs = [int(reg[:-1][1:])]
        elif op in ("sw","sw_spm"):
            try: srcs = [int(tokens[1][1:])]
            except: srcs = []
            parts = tokens[2].split('(')
            if len(parts)>1:
                srcs.append(int(parts[1][:-1][1:]))
        elif op in ("bne","beq","ble"):
            srcs = [int(tokens[1][1:]), int(tokens[2][1:])]
        elif op == "jr":
            srcs = [int(tokens[1][1:])]
        return srcs

    def op_writes_reg(self, tokens):
        return self.get_destination_register(tokens) is not None

    def _forward_operand(self, reg_index):
        # Check MEM stage
        mem = self.pipeline_reg["MEM"]
        if mem and "mem_result" in mem:
            dest = self.get_destination_register(mem["tokens"])
            if dest == reg_index:
                return mem["mem_result"]
        # Check WB stage
        wb = self.pipeline_reg["WB"]
        if wb and "final_result" in wb:
            dest = self.get_destination_register(wb["tokens"])
            if dest == reg_index:
                return wb["final_result"]
        # Otherwise from register file
        return self.registers[reg_index]

    def detect_load_use_hazard(self, tokens):
        ex = self.pipeline_reg["EX"]
        if ex:
            op = ex["tokens"][0].lower()
            if op in ("lw","lw_spm"):
                dest = self.get_destination_register(ex["tokens"])
                if dest in self.extract_source_registers(tokens):
                    return True
        return False

    def detect_data_hazard(self, tokens):
        # Only stall on load-use hazards
        return self.detect_load_use_hazard(tokens)

    def detect_war_hazard(self, tokens):
        # unchanged WAR detection if needed
        return False

    def flush_pipeline(self):
        self.pipeline_flush_count += 1
        for s in ("IF","ID","EX","MEM"): self.pipeline_reg[s] = None

    def ID(self):
        if self.pipeline_reg["IF"] is None or self.pipeline_reg["IF"].get("cycles_remaining",0)>1:
            self.pipeline_reg["ID"] = None
            return
        tokens = self.pipeline_reg["IF"]["raw"].split()
        if tokens and ":" in tokens[0]: tokens.pop(0)
        # Structural hazard: EX busy
        ex = self.pipeline_reg["EX"]
        if ex and ex.get("cycles_remaining",0)>1:
            print("Stall in ID due to EX busy for", tokens)
            self.pipeline_reg["ID"]=["NOP"]; self.stall_count+=1; return
        # Control ops bypass data hazard
        if tokens[0].lower() in ("bne","beq","ble","j","jal","jr"):
            self.pipeline_reg["ID"] = tokens; self.pipeline_reg["IF"] = None; return
        # Data hazard: only load-use
        if self.detect_data_hazard(tokens):
            print("Stall in ID due to load-use for", tokens)
            self.pipeline_reg["ID"]=["NOP"]; self.stall_count+=1; return
        # No stall
        self.pipeline_reg["ID"] = tokens; self.pipeline_reg["IF"] = None

    def EX(self):
        # Stall if multi-cycle
        ex = self.pipeline_reg["EX"]
        if ex and ex.get("cycles_remaining",0)>1:
            ex["cycles_remaining"]-=1; self.stall_count+=1; print("EX stall for", ex["tokens"]); return
        # Load from ID
        if not self.pipeline_reg["ID"] or self.pipeline_reg["ID"][0]=="nop":
            self.pipeline_reg["EX"] = None; return
        tokens = self.pipeline_reg["ID"]; op = tokens[0].lower()
        # helper to get operand with forwarding
        def get_val(idx): return self._forward_operand(int(tokens[idx][1:]))
        result=None; mem_addr=None
        if op=="add": result=get_val(2)+get_val(3)
        elif op=="addi": result=get_val(2)+int(tokens[3])
        elif op=="sub": result=get_val(2)-get_val(3)
        elif op=="slt": result=1 if get_val(2)<get_val(3) else 0
        elif op=="li": result=int(tokens[2])
        elif op=="la": result=tokens[2]
        elif op in ("lw","lw_spm","sw","sw_spm"): 
            off, reg = tokens[2].split('(')
            base = get_val(1 if op.startswith("sw") else 0)
            mem_addr = base + int(off)
        elif op in ("bne","beq","ble"): result=(int(tokens[1][1:]),int(tokens[2][1:]),tokens[3])
        elif op=="jal": result=self.pc+1
        elif op=="jr": result=self._forward_operand(int(tokens[1][1:]))
        elif op=="j": pass
        elif op=="ecall": result=0
        elif op=="sync": result=0
        else: print("UNDEF EX op",op)
        latency=Core.latencies.get(op,1)
        self.pipeline_reg["EX"]={"tokens":tokens,"result":result,
                                  "mem_addr":mem_addr,"cycles_remaining":latency}
        self.pipeline_reg["ID"] = None

    def MEM(self):
        mem = self.pipeline_reg["MEM"]
        if mem and mem.get("cycles_remaining",0)>1:
            mem["cycles_remaining"]-=1; self.stall_count+=1; print("MEM stall for",mem["tokens"]); return
        ex = self.pipeline_reg["EX"]
        if not ex or ex.get("cycles_remaining",0)>1:
            self.pipeline_reg["MEM"] = None; return
        tokens, res, addr = ex["tokens"], ex["result"], ex["mem_addr"]
        mem_res=res; mem_stalls=0
        if tokens[0]=="la":
            for v in self.data_segment[tokens[2]]:
                mem_stalls += Core.candm.write(self.coreid,self.memory_data_index,v)
                self.memory_data_index-=4
            mem_res=self.memory_data_index+4
        elif tokens[0]=="lw": mem_res,mem_stalls=Core.candm.read(self.coreid,addr,False)
        elif tokens[0]=="sw": mem_stalls=Core.candm.write(self.coreid,addr,self.registers[int(tokens[1][1:])])
        elif tokens[0]=="sw_spm": mem_stalls=Core.candm.write_scratch_pad(self.coreid,addr,self.registers[int(tokens[1][1:])])
        elif tokens[0]=="lw_spm": mem_res,mem_stalls=Core.candm.read_scratch_pad(self.coreid,addr)
        elif tokens[0]=="sync": mem_stalls=Core.candm.flush_l1_dirty_to_l2(self.coreid)
        self.inst_executed+=1
        self.pipeline_reg["MEM"]={"tokens":tokens,"mem_result":mem_res,
                                   "cycles_remaining":max(1,mem_stalls)}
        self.pipeline_reg["EX"] = None

    def WB(self):
        mem = self.pipeline_reg["MEM"]
        if not mem or mem.get("cycles_remaining",0)>1:
            self.pipeline_reg["WB"]=None; return
        tokens, res = mem["tokens"], mem["mem_result"]
        op=tokens[0]
        if op in ("la","add","addi","sub","slt","li","lw","lw_spm"):
            self.registers[int(tokens[1][1:])] = res
        elif op in ("bne","beq","ble"):
            r1,r2,label = int(tokens[1][1:]),int(tokens[2][1:]),tokens[3]
            taken = ((op=="bne" and self.registers[r1]!=self.registers[r2]) or
                     (op=="beq" and self.registers[r1]==self.registers[r2]) or
                     (op=="ble" and self.registers[r1]<=self.registers[r2]))
            if taken:
                print("Branch taken",tokens)
                self.pc = self.program_label_map[label]; self.flush_pipeline()
        elif op=="jal":
            rd,label=int(tokens[1][1:]),tokens[2]
            self.registers[rd]=res; print("JAL",tokens)
            self.pc=self.program_label_map[label]; self.flush_pipeline()
        elif op=="jr":
            rs=int(tokens[1][1:]); self.pc=self.registers[rs]
            print("JR",tokens); self.flush_pipeline()
        elif op=="j":
            self.pc=self.program_label_map[tokens[1]]; print("J",tokens)
            self.flush_pipeline()
        elif op=="ecall":
            rd=int(tokens[1][1:]); print("ECALL x{}=".format(rd),self.registers[rd])
        self.pipeline_reg["WB"]={"tokens":tokens,"final_result":res}

    def pipeline_empty(self):
        return all(self.pipeline_reg[s] is None for s in ("IF","ID","EX","MEM","WB"))

    def pipeline_cycle(self):
        self.WB(); self.MEM(); self.EX(); self.ID()
        self.pc, self.pipeline_reg["IF"] = If_program.IF(self.pipeline_reg["IF"], self.pc, self)
