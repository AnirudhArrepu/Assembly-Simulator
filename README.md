# Assembly-Simulator

Course project - COA

## Developers

- [Anirudh Arrepu](https://github.com/AnirudhArrepu)
- [Raghavendra Pappu](https://github.com/raghavaa2506)

## MOMs

1.  - Date: 19-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: Raghavendra completed the GUI using HTML, CSS, and JavaScript, while Anirudh worked on integrating the GUI with the Python backend. Anirudh decided to use Flask for this integration.

2.  - Date: 17-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: The team decided to implement a GUI for the simulator. Initially, Raghavendra developed a basic GUI using Tkinter (import tkinter as tk from tkinter import messagebox). However, it was not visually appealing, so We decided to build the GUI using HTML, CSS, and JavaScript instead.

3.  - Date: 15-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: The team tested the code with various programs using the data segment format. We verified the correct addressing of arrays and successfully obtained the correct output for sum-of-elements problems.

4.  - Date: 13-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: The team collaboratively implemented the Bubble Sort algorithm. We also added a data segment to the code by creating an array to store input data in the format: arr: .word 0x4 ...

5.  - Date: 11-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: Realised array indexing is 1, but addi can also perform arithmetic operations and hence differentiating logical and pointer arithmetic will not be possible.
    Hence made memory of 4*x allocations, index belonging to its module 4 coreid.

6.  - Date: 09-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: The team divided responsibilities:
      1.Raghavendra was assigned to implement arithmetic operations.
      2.Anirudh was responsible for memory operations.
      3.We discussed defining unique instructions that differ from the RISC-V instruction set.

7.  - Date: 07-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision:
      1.Anirudh was assigned to complete the Software Design by 10-02-2025.
      2.Raghavendra was tasked with reviewing relevant topics and enhancing his Python knowledge.

8.  - Date: 06-02-2025
    - Memebers: Anirudh A, Raghavendra P
    - Decision: Decided to complete and build the GPU simulator with `python` language since,
      1.Python has a simpler syntax compared to C/C++, making it easier to implement and understand complex GPU architectures.
      2.Python has great visualization tools like Matplotlib and Seaborn, which help analyze performance metrics.


### Note:
- special register: x31
- instructions implemented: add addi sub la lw sw bne ble beq jal jr slt j li
- implemented .word in data segment

- memory starts being used from the end for storing .data segment values

### To Execute:

- GUI
```cmd
cd Codes
cd Backend
pip install -r requirements.txt
python simulator.py
Open 1270.0.1:5000 in browser
```

- File Reading: change assembly.asm
```bash
cd Codes
cd Backend
pip install -r requirements.txt
python file_reading_simulator.py
```
