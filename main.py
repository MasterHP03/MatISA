import re

instructions = {
    "add": (0x01, 'R'),
    "addi": (0x02, 'I'),
    "lw": (0x10, 'M'),
    "sw": (0x18, 'M'),
    "jal": (0x20, 'J'),
    "jalr": (0x21, 'I'),
    "beq": (0x30, 'B'),
    "prt": (0xFF, 'U'),
}

reg_num = 32
regs = [0] * reg_num
reg_map = {
    "zero": 0,
    "x": 1,
    "y": 2
}

mem_size = 1024
mem = [0] * mem_size

symbol_table: dict[str, int] = {}


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
                if 0 <= reg_id < reg_num:
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

    offset = get_imm(match.group(1), 8)
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
        line = line.strip()
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
            line = line.strip()
            if len(line) == 0: continue
            args = re.split(r'[,\s]+', line)

            # Label check
            while args and args[0].endswith(':'):
                args = args[1:]
            if not args: # If only label (no actual instruction)
                continue

            cmd = args[0]
            dest = 0
            src1 = 0
            src2 = 0

            op_code, inst_type = get_inst_info(cmd)
            if inst_type == 'R':
                need_args(args, 3)
                dest = get_reg_id(args[1])
                src1 = get_reg_id(args[2])
                src2 = get_reg_id(args[3])
            elif inst_type == 'I':
                need_args(args, 3)
                dest = get_reg_id(args[1])
                src1 = get_reg_id(args[2])
                src2 = get_imm(args[3], 8)
            elif inst_type == 'M':
                need_args(args, 2)
                dest = get_reg_id(args[1])
                src2, src1 = parse_mem(args[2])
            elif inst_type == 'J':
                need_args(args, 2)
                dest = get_reg_id(args[1])
                imm = get_label_addr(args[2]) - curr_line
                src1 = imm & 0xFF
                src2 = imm >> 8
            elif inst_type == 'B':
                need_args(args, 3)
                src1 = get_reg_id(args[1])
                src2 = get_reg_id(args[2])
                imm = get_label_addr(args[3]) - curr_line
                dest = imm & 0xFF
            elif inst_type == 'U':
                need_args(args, 1)
                dest = get_reg_id(args[1])

            encoded = op_code | (dest << 8) | (src1 << 16) | (src2 << 24)
            insts.append(encoded)
            # print(f"{curr_line} {len(insts)} {line} {inst_type} {encoded:08x} {op_code:08x} {dest:08x} {src1:08x} {src2:08x}")
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
            op_code = line & 0xFF
            dest = (line >> 8) & 0xFF
            src1 = (line >> 16) & 0xFF
            src2 = (line >> 24) & 0xFF
            # print(f"{curr_line} {line:08x} {op_code:08x} {dest:08x} {src1:08x} {src2:08x}")

            line_incr = 1
            if False:
                pass
            elif op_code == 0xFF: # prt
                print(regs[dest])
            elif op_code == 0x01: # add
                regs[dest] = regs[src1] + regs[src2]
            elif op_code == 0x02: # addi
                imm = to_signed(src2, 8)
                regs[dest] = regs[src1] + imm
            elif op_code == 0x10: # lw
                off = to_signed(src2, 8)
                addr = regs[src1] + off
                check_mem_addr(addr)
                regs[dest] = mem[addr]
            elif op_code == 0x18: # sw
                off = to_signed(src2, 8)
                addr = regs[src1] + off
                check_mem_addr(addr)
                mem[addr] = regs[dest]
            elif op_code == 0x20: # jal
                off = to_signed((src2 << 8) | src1, 16)
                check_jump(len(encoded), curr_line + off)
                regs[dest] = curr_line + line_incr
                line_incr = off
            elif op_code == 0x30: # beq
                off = to_signed(dest, 8)
                check_jump(len(encoded), curr_line + off)
                if regs[src1] == regs[src2]:
                    line_incr = off

            regs[0] = 0
            curr_line += line_incr
        except ISAError as e:
            print(f"Line {curr_line}: {e}")
            break


enc_prog = encode()
print()
print("[Log]")
decode(enc_prog)