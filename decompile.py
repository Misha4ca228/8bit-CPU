opcode_map = {
    "NOP": 0b00000000,
    "LDI": 0b00000001,
    "LD": 0b00000010,
    "ST": 0b00000011,
    "MOV": 0b00000100,
    "ADD": 0b00000101,
    "ADDI": 0b00000110,
    "SUB": 0b00000111,
    "SUBI": 0b00001000,
    "INC": 0b00001001,
    "DEC": 0b00001010,
    "JMP": 0b00001011,
    "JZ": 0b00001100,
    "JNZ": 0b00001101,
    "OUT": 0b00001110,
    "HALT": 0b11111111,
}

operand_count = {
    "NOP": 0, "HALT": 0, "LDI": 2, "LD": 2, "ST": 2,
    "MOV": 2, "ADD": 2, "ADDI": 2, "SUB": 2, "SUBI": 2,
    "INC": 1, "DEC": 1, "JMP": 1, "JZ": 2, "JNZ": 2, "OUT": 1
}

# Инвертируем opcode_map для быстрого поиска по байту
opcode_to_name = {v: k for k, v in opcode_map.items()}


def decompile(bytecode):
    """
    Декомпилирует список байтов в ассемблерный текст.
    """
    lines = []
    pc = 0
    while pc < len(bytecode):
        opcode = bytecode[pc]
        instr = opcode_to_name.get(opcode, None)

        if instr is None:
            lines.append(f"# Нераспознанный байт {opcode:08b} на позиции {pc}")
            pc += 1
            continue

        operands_needed = operand_count[instr]
        operands = []

        for i in range(operands_needed):
            if pc + 1 + i < len(bytecode):
                operands.append(bytecode[pc + 1 + i])
            else:
                operands.append("???")

        # Формируем строку ASM
        if operands:
            operand_str = ", ".join(str(o) for o in operands)
            line = f"{instr} {operand_str};"
        else:
            line = f"{instr};"

        # Добавляем комментарий с адресом и бинарной формой
        line += f"    # [PC={pc:03}] 0b{opcode:08b}"
        lines.append(line)

        pc += 1 + operands_needed

    return "\n".join(lines)


# ---------------------------
# Пример использования
# ---------------------------
if __name__ == "__main__":
    # Пример байт-кода (например, результат компиляции)
    bytecode = [
        0b00000001, 0b00000000, 0b00000111, 0b00000001, 0b00000001, 0b00001001, 0b00000001, 0b00000010, 0b00000000,
        0b00000100, 0b00000011, 0b00000001, 0b00000101, 0b00000010, 0b00000000, 0b00001010, 0b00000011, 0b00001101,
        0b00000011, 0b00001100, 0b00001110, 0b00000010, 0b11111111

        # HALT
    ]

    asm_text = decompile(bytecode)
    print("=== Декомпиляция ===")
    print(asm_text)
