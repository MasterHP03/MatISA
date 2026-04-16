instructions = {
    "add": ('R', 0x33, 0, 0),
    "sll": ('R', 0x33, 0x1, 0),
    "srl": ('R', 0x33, 0x5, 0),
    "or": ('R', 0x33, 0x6, 0),
    "and": ('R', 0x33, 0x7, 0),
    "addi": ('I', 0x13, 0, 0),
    "lw": ('I', 0x03, 0x2, 0),
    "sw": ('S', 0x23, 0x2, 0),
    "jal": ('J', 0x6F, 0, 0),
    "jalr": ('I', 0x67, 0, 0),
    "beq": ('B', 0x63, 0, 0),
    "ecall": ('I', 0x73, 0, 0),
}

mem_size = 1024

reg_n = 32
reg_map = {
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "fp": 8,
}

for i in range(2):
    reg_map[f"s{i}"] = i + 8 # s0, s1

for i in range(2, 12):
    reg_map[f"s{i}"] = i + 16 # s2 - s7

for i in range(8):
    reg_map[f"a{i}"] = i + 10 # a0 - a7

for i in range(3):
    reg_map[f"t{i}"] = i + 5 # t0 - t2

for i in range(3, 7):
    reg_map[f"t{i}"] = i + 25 # t3 - t6

imm_short = 12  # I, S, B
imm_long = 20  # U, J

class ISAError(Exception):
    pass