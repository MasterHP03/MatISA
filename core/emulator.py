from core.spec import *

def to_signed(num, size):
    sgn = 1 << (size - 1)
    return (num ^ sgn) - sgn

def check_mem_addr(addr):
    if not 0 <= addr < mem_size:
        raise ISAError(f"Segmentation fault: Memory access out of bounds ({addr})")

def check_jump(line_n, next_line):
    if not 1 <= next_line <= line_n:
        raise ISAError(f"Invalid jump to Line {next_line}")

class Emulator:
    def __init__(self):
        self.regs = [0] * reg_n
        self.mem = [0] * mem_size

    def decode(self, encoded):
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
                    self.regs[rd] = self.regs[rs1] + self.regs[rs2]
                elif op_code == 0x13: # addi
                    imm = to_signed(imm_i, imm_short)
                    self.regs[rd] = self.regs[rs1] + imm
                elif op_code == 0x03: # lw
                    off = to_signed(imm_i, imm_short)
                    addr = self.regs[rs1] + off
                    check_mem_addr(addr)
                    self.regs[rd] = self.mem[addr]
                elif op_code == 0x23: # sw
                    off = to_signed(imm_s, imm_short)
                    addr = self.regs[rs1] + off
                    check_mem_addr(addr)
                    self.mem[addr] = self.regs[rs2]
                elif op_code == 0x6F: # jal
                    off = to_signed(imm_u, imm_long)
                    check_jump(len(encoded), curr_line + off)
                    self.regs[rd] = curr_line + line_incr
                    line_incr = off
                elif op_code == 0x67: # jalr
                    imm = to_signed(imm_i, imm_short)
                    next_line = self.regs[rs1] + imm
                    check_jump(len(encoded), next_line)
                    self.regs[rd] = curr_line + line_incr
                    line_incr = next_line - curr_line
                elif op_code == 0x63: # beq
                    off = to_signed(imm_s, imm_short)
                    check_jump(len(encoded), curr_line + off)
                    if self.regs[rs1] == self.regs[rs2]:
                        line_incr = off
                elif op_code == 0x73: # ecall
                    if self.regs[reg_map["a7"]] == 1:
                        print(self.regs[reg_map["a0"]])

                self.regs[0] = 0
                curr_line += line_incr
            except ISAError as e:
                print(f"Line {curr_line}: {e}")
                break