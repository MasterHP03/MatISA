from core.spec import *

regs = [0] * reg_n
mem = [0] * mem_size

def to_signed(num, size):
    sgn = 1 << (size - 1)
    return (num ^ sgn) - sgn


def check_mem_addr(addr):
    if not 0 <= addr < mem_size:
        raise ISAError(f"Segmentation fault: Memory access out of bounds ({addr})")


def check_jump(line_n, next_line):
    if not 1 <= next_line <= line_n:
        raise ISAError(f"Invalid jump to Line {next_line}")


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
            if op_code == 0x33: # add
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