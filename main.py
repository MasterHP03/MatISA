from core.assembler import Assembler
from core.emulator import Emulator

asm = Assembler()
machine_code = asm.encode("code.txt")

if machine_code:
    print("\n[Log]")
    emul = Emulator()
    emul.decode(machine_code)