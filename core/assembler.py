import re
from core.spec import *

symbol_table: dict[str, int] = {}

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


def get_label_addr(label_name):
    addr = symbol_table.get(label_name)
    if addr is None:
        raise ISAError(f"Invalid label: {label_name}")
    return addr


def encode(filepath):
    lines = []
    with open(filepath, 'r', encoding='utf-8') as file:
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