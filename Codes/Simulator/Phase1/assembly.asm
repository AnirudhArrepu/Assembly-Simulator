.data
arr: .word 0x144 0x3 0x9 0x8 0x1 0x100

.text
la x3 arr
addi x4 x0 6
addi x7 x0 0
outer_loop: addi x11 x4 -1
beq x7 x11 outer_exit
addi x10 x3 0
addi x8 x0 0
inner_loop: addi x12 x4 0
sub x12 x12 x7
addi x12 x12 -1
beq x8 x12 inner_exit
lw x5 0(x10)
lw x6 4(x10)
slt x11 x6 x5
beq x11 x0 no_swap
sw x5 4(x10)
sw x6 0(x10)
no_swap: addi x10 x10 4
addi x8 x8 1
j inner_loop
inner_exit: addi x7 x7 1
j outer_loop
outer_exit: j exit
exit: addi x0 x0 0
