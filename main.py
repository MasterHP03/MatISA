import re

instructions = {
    "add": ('R', 0x33, 0, 0),
    "addi": ('I', 0x13, 0, 0),
    "lw": ('I', 0x03, 0b010, 0),
    "sw": ('S', 0x23, 0b010, 0),
    "jal": ('J', 0x6F, 0, 0),
    "jalr": ('I', 0x67, 0, 0),
    "beq": ('B', 0x63, 0, 0),
    "ecall": ('I', 0x73, 0, 0),
}

reg_n = 32
regs = [0] * reg_n
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

mem_size = 1024
mem = [0] * mem_size

symbol_table: dict[str, int] = {}

imm_short = 12  # I, S, B
imm_long = 20  # U, J


class ISAError(Exception):
    pass


def to_signed(num, size):
    sgn = 1 << (size - 1)
    return (num ^ sgn) - sgn


def need_args(args, count):
    if len(args) < count + 1:
        raise ISAError(f"Instruction needs {count} arguments")


def get_inst_info(inst_name):
    inst_info = instructions.get(inst_name)
    if inst_info is None:
        raise ISAError(f"Invalid instruction: {inst_name}")
    return inst_info


def get_reg_id(reg_name):
    reg_id = reg_map.get(reg_name)
    if reg_id is None:
        if reg_name.startswith('x') and len(reg_name) > 1:
            try:
                reg_id = int(reg_name[1:])
                if 0 <= reg_id < reg_n:
                    return reg_id
            except ValueError:
                pass # to below
        raise ISAError(f"Invalid register: {reg_name}")
    return reg_id


def get_imm(arg, size):
    mask = (1 << size) - 1
    try:
        return int(arg) & mask
    except ValueError:
        raise ISAError(f"Value {arg} is not an integer")


def parse_mem(arg):
    match = re.match(r"(-?\d+)\(([^)]+)\)", arg)
    if not match:
        raise ISAError(f"Invalid memory argument format: {arg}")

    offset = get_imm(match.group(1), imm_short)
    base_reg = get_reg_id(match.group(2))

    return offset, base_reg


def check_mem_addr(addr):
    if not 0 <= addr < mem_size:
        raise ISAError(f"Segmentation fault: Memory access out of bounds ({addr})")


def get_label_addr(label_name):
    addr = symbol_table.get(label_name)
    if addr is None:
        raise ISAError(f"Invalid label: {label_name}")
    return addr


def check_jump(line_n, next_line):
    if not 1 <= next_line <= line_n:
        raise ISAError(f"Invalid jump to Line {next_line}")


def encode():
    lines = []
    with open('code.txt', 'r', encoding='utf-8') as file:
        for line in file:
            lines.append(line)

    insts = []

    # 1st pass: Check labels
    curr_line = 1
    for line in lines:
        line = re.split(r'[#;]', line)[0].strip()
        if len(line) <= 1: continue
        args = re.split(r'[,\s]+', line)

        # Process every label in the line
        while args and args[0].endswith(':'):
            symbol_table[args[0][:-1]] = curr_line
            # print(curr_line, args[0][:-1])
            args = args[1:]

        # Increment only if an actual instruction exists
        if len(args) > 0:
            curr_line += 1

    # 2nd pass: Encode instructions
    curr_line = 1
    for line in lines:
        try:
            line = re.split(r'[#;]', line)[0].strip()
            if len(line) == 0: continue
            args = re.split(r'[,\s]+', line)

            # Label check
            while args and args[0].endswith(':'):
                args = args[1:]
            if not args: # If only label (no actual instruction)
                continue

            cmd = args[0]
            inst_type, op_code, func3, func7 = get_inst_info(cmd)
            rd = 0
            rs1 = 0
            rs2 = 0
            if cmd == 'ecall':
                pass
            elif inst_type == 'R':
                need_args(args, 3)
                rd = get_reg_id(args[1])
                rs1 = get_reg_id(args[2])
                rs2 = get_reg_id(args[3])
            elif inst_type == 'I':
                need_args(args, 2)
                rd = get_reg_id(args[1])
                try:
                    offset, rs1 = parse_mem(args[2])
                    imm = offset & 0xFFF
                except ISAError:
                    need_args(args, 3)
                    rs1 = get_reg_id(args[2])
                    imm = get_imm(args[3], 12)
                rs2 = imm & 0b11111
                func7 = imm >> 5
            elif inst_type == 'S':
                need_args(args, 2)
                rs2 = get_reg_id(args[1])
                offset, base_reg = parse_mem(args[2])
                imm = offset & 0xFFF
                rs1 = base_reg
                rd = imm & 0x1F
                func7 = (imm >> 5) & 0x7F
            elif inst_type == 'J':
                need_args(args, 2)
                rd = get_reg_id(args[1])
                imm = get_label_addr(args[2]) - curr_line
                # Jump unit: line. No implicit tailing one
                func3 = imm & 0x07
                rs1 = (imm >> 3) & 0x1F
                rs2 = (imm >> 8) & 0x1F
                func7 = (imm >> 13) & 0x7F
            elif inst_type == 'B':
                need_args(args, 3)
                rs1 = get_reg_id(args[1])
                rs2 = get_reg_id(args[2])
                imm = get_label_addr(args[3]) - curr_line
                # Jump unit: line. No implicit tailing one
                rd = imm & 0x1F
                func7 = (imm >> 5) & 0x7F
            elif inst_type == 'U':
                need_args(args, 2)
                rd = get_reg_id(args[1])
                imm = get_imm(args[2], 20)
                func3 = imm & 0x07
                rs1 = (imm >> 3) & 0x1F
                rs2 = (imm >> 8) & 0x1F
                func7 = imm >> 13

            encoded = op_code | (rd << 7) | (func3 << 12) | (rs1 << 15) | (rs2 << 20) | (func7 << 25)
            insts.append(encoded)
            # print(f"{curr_line} {len(insts)} {line} {inst_type} {encoded:08x} {func7:02x} {rs2:02x} {rs1:02x} {func3:01x} {rd:02x} {op_code:02x}")
            curr_line += 1
        except ISAError as e:
            print(f"Line {curr_line}: {e}")
            return []

    return insts


def decode(encoded):
    curr_line = 1
    while True:
        try:
            if curr_line > len(encoded):
                break
            line = encoded[curr_line - 1]
            op_code = line & 0x7F
            rd = (line >> 7) & 0x1F
            func3 = (line >> 12) & 0x07
            rs1 = (line >> 15) & 0x1F
            rs2 = (line >> 20) & 0x1F
            func7 = (line >> 25) & 0x7F

            imm_i = (func7 << 5) | rs2
            imm_s = (func7 << 5) | rd
            imm_u = (imm_i << 8) | (rs1 << 3) | func3

            line_incr = 1
            if False:
                pass
            elif op_code == 0x33: # add
                regs[rd] = regs[rs1] + regs[rs2]
            elif op_code == 0x13: # addi
                imm = to_signed(imm_i, imm_short)
                regs[rd] = regs[rs1] + imm
            elif op_code == 0x03: # lw
                off = to_signed(imm_i, imm_short)
                addr = regs[rs1] + off
                check_mem_addr(addr)
                regs[rd] = mem[addr]
            elif op_code == 0x23: # sw
                off = to_signed(imm_s, imm_short)
                addr = regs[rs1] + off
                check_mem_addr(addr)
                mem[addr] = regs[rs2]
            elif op_code == 0x6F: # jal
                off = to_signed(imm_u, imm_long)
                check_jump(len(encoded), curr_line + off)
                regs[rd] = curr_line + line_incr
                line_incr = off
            elif op_code == 0x67: # jalr
                imm = to_signed(imm_i, imm_short)
                next_line = regs[rs1] + imm
                check_jump(len(encoded), next_line)
                regs[rd] = curr_line + line_incr
                line_incr = next_line - curr_line
            elif op_code == 0x63: # beq
                off = to_signed(imm_s, imm_short)
                check_jump(len(encoded), curr_line + off)
                if regs[rs1] == regs[rs2]:
                    line_incr = off
            elif op_code == 0x73: # ecall
                if regs[reg_map["a7"]] == 1:
                    print(regs[reg_map["a0"]])

            regs[0] = 0
            curr_line += line_incr
        except ISAError as e:
            print(f"Line {curr_line}: {e}")
            break


enc_prog = encode()
print()
print("[Log]")
decode(enc_prog)