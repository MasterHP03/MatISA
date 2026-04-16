import core.assembler as asm
import core.emulator as emul

enc_prog = asm.encode("code.txt")
print()
print("[Log]")
emul.decode(enc_prog)