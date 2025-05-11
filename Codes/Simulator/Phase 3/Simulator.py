from Memory import Memory
from Core import Core
from CoreWithForwarding import CoreWithForwarding
from Storage import CacheAndMemory

class Simulator:
    def __init__(self, forwarding=False):
        self.memory = Memory()
        self.forwarding = forwarding
        
        # Initialize CacheAndMemory first so it's available to cores
        self.candm = CacheAndMemory(config_path="config.yaml",
                                   memory=self.memory,
                                   num_cores=4)
        
        # Set the shared CacheAndMemory instance for all cores
        Core.candm = self.candm
        Core.memory = self.memory
        
        if not self.forwarding:
            self.cores = [Core(i) for i in range(4)]
        else:
            self.cores = [CoreWithForwarding(i, self.memory) for i in range(4)]
            
        self.program = []
        self.clock = 0
        self.data_segment = {}
        self.labels = {}

    def make_data_segment(self, program_data):
        """
        Parse the data segment and store variables in memory
        
        Args:
            program_data (list): List of strings containing data segment instructions
        """
        current_address = 0  # Start at memory address 0
        
        for data in program_data:
            data = data.strip()
            
            # Skip empty lines
            if not data:
                continue
                
            # Process label if present
            label = None
            if ":" in data:
                parts = data.split(":", 1)
                label = parts[0].strip()
                self.labels[label] = current_address
                
                # Store address in data_segment dictionary for label
                self.data_segment[label] = current_address
                
                # If there's nothing after the label, continue to next line
                if len(parts) == 1 or not parts[1].strip():
                    continue
                    
                data = parts[1].strip()
            
            # Handle .word directive
            if ".word" in data:
                try:
                    # Extract values after .word
                    values_str = data.split(".word")[1].strip()
                    values_data = [val.strip() for val in values_str.split() if val.strip()]
                    
                    # Store values in memory and track them for the label
                    values_int = []
                    start_address = current_address
                    
                    for value in values_data:
                        if value.startswith("0x"):
                            val_int = int(value, 16)
                        else:
                            val_int = int(value)
                            
                        self.memory.store_word(current_address, val_int)
                        values_int.append(val_int)
                        current_address += 4  # Word size is 4 bytes
                    
                    # Store data in data_segment for backwards compatibility
                    if label:
                        # Store the actual data values and address
                        self.data_segment[label] = {
                            'address': start_address,
                            'values': values_int,
                            'size': len(values_int) * 4
                        }
                        
                except Exception as e:
                    print(f"Error parsing .word directive: {data}")
                    print(f"Exception: {e}")
            
            # Handle .space directive
            elif ".space" in data:
                try:
                    space_size = int(data.split(".space")[1].strip())
                    start_address = current_address
                    
                    # Reserve the specified amount of bytes by initializing them to 0
                    for _ in range(0, space_size, 4):  # Allocate in word-sized chunks
                        self.memory.store_word(current_address, 0)
                        current_address += 4
                    
                    # Store data in data_segment for backwards compatibility
                    if label:
                        # Store just the starting address and size for space directives
                        self.data_segment[label] = {
                            'address': start_address,
                            'values': [0] * (space_size // 4),  # Initialize with zeros
                            'size': space_size
                        }
                        
                except Exception as e:
                    print(f"Error parsing .space directive: {data}")
                    print(f"Exception: {e}")
            
            # Handle unknown directives
            else:
                print(f"Warning: Unrecognized data directive: {data}")
        
        # Share data segment with all cores
        for core in self.cores:
            core.data_segment = self.data_segment

    def make_labels(self):
        for core in self.cores:
            core.make_labels(self.program)

    def run(self):
        # Reset pipeline registers before starting execution
        for core in self.cores:
            core.pipeline_reg = {
                "IF": None,
                "ID": None,
                "EX": None,
                "MEM": None,
                "WB": None,
            }
            
        # Add debugging to help track what's happening
        print(f"Starting simulation with {len(self.program)} instructions")
        
        try:
            while not all(core.pc >= len(self.program) and core.pipeline_empty() for core in self.cores):
                for core in self.cores:
                    core.pipeline_cycle()
                self.clock += 1
                
                # Optional: Add a safety limit to prevent infinite loops
                if self.clock > 10000:  # Arbitrary large number
                    print("Warning: Maximum cycle count reached. Stopping simulation.")
                    break
                    
            self.clock -= 1
            
            print("clock cycles:", self.clock)
            print("Simulation completed successfully")
            
        except Exception as e:
            print(f"Simulation error at cycle {self.clock}: {e}")
            # Print state information to help with debugging
            for i, core in enumerate(self.cores):
                print(f"Core {i} - PC: {core.pc}, Pipeline State:")
                for stage, reg in core.pipeline_reg.items():
                    print(f"  {stage}: {reg}")
            raise  # Re-raise the exception to see the full traceback