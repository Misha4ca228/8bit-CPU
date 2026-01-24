opcode_map = {
    # 1) Память и регистры
    "LDI":  0b00000001,  # [op][r][imm8]
    "LD":   0b00000010,  # [op][r][hi][lo]
    "ST":   0b00000011,  # [op][r][hi][lo]
    "MOV":  0b00000100,  # [op][rA][rB]
    "STI":  0b00000101,  # [op][r_src][r_addr]  (zero-page indirect)

    # 2) Арифметика
    "ADD":  0b00001000,  # [op][rA][rB]
    "ADDI": 0b00001001,  # [op][r][imm8]
    "SUB":  0b00001010,  # [op][rA][rB]
    "SUBI": 0b00001011,  # [op][r][imm8]
    "MUL":  0b00001100,  # [op][rA][rB]
    "DIV":  0b00001101,  # [op][rA][rB]
    "MOD":  0b00001110,  # [op][rA][rB]
    "INC":  0b00001111,  # [op][r]
    "DEC":  0b00010000,  # [op][r]

    # 3) Логика
    "AND":  0b00010001,  # [op][rA][rB]
    "OR":   0b00010010,  # [op][rA][rB]
    "XOR":  0b00010011,  # [op][rA][rB]
    "NOT":  0b00010100,  # [op][r]

    # 4) Переходы (16-bit адрес)
    "JMP":  0b00011000,  # [op][hi][lo]
    "JZ":   0b00011001,  # [op][r][hi][lo]
    "JNZ":  0b00011010,  # [op][r][hi][lo]

    # 5) Стек
    "PUSH": 0b00011011,  # [op][r]
    "POP":  0b00011100,  # [op][r]

    # 6) Стоп
    "HALT": 0b11111111,  # [op]
}

operand_count = {
    "LDI":  2,
    "LD":   2,
    "ST":   2,
    "MOV":  2,
    "STI":  2,

    "ADD":  2,
    "ADDI": 2,
    "SUB":  2,
    "SUBI": 2,
    "MUL":  2,
    "DIV":  2,
    "MOD":  2,
    "INC":  1,
    "DEC":  1,

    "AND":  2,
    "OR":   2,
    "XOR":  2,
    "NOT":  1,

    "JMP":  1,
    "JZ":   2,
    "JNZ":  2,

    "PUSH": 1,
    "POP":  1,

    "HALT": 0
}

# Архитектурные ограничения
MEM_SIZE = 65536
STACK_START = 0xFFE0
VIDEO_START = 0xFFF0
MAX_PROGRAM_SIZE = STACK_START  # можно использовать всё до 0xFFE0 (не включая)


def _parse_int(token: str, line_num: int) -> int:
    """
    int(token, 0) позволяет:
    123, 0xFF, 0b1010
    """
    try:
        return int(token, 0)
    except ValueError:
        raise SyntaxError(f"Неверное число '{token}' (строка {line_num})")


def _resolve_label_or_number(token: str, labels: dict, line_num: int) -> int:
    if token in labels:
        return labels[token]
    return _parse_int(token, line_num)


def _emit_addr16(bytecode: list[int], addr_val: int, line_num: int):
    if not (0 <= addr_val <= 0xFFFF):
        raise ValueError(f"Адрес {addr_val} вне диапазона 0–65535 (строка {line_num})")
    hi = (addr_val >> 8) & 0xFF
    lo = addr_val & 0xFF
    bytecode.append(hi)
    bytecode.append(lo)


def compile_program(file_path: str) -> list[int]:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # ---------- ПЕРВЫЙ ПРОХОД: считаем адреса меток ----------
    labels: dict[str, int] = {}
    addr = 0

    for line_num, line in enumerate(lines, start=1):
        line = line.split("#")[0].strip()
        if not line:
            continue

        # Метка
        if line.endswith(":"):
            label = line[:-1].strip()
            if not label.isidentifier():
                raise SyntaxError(f"Недопустимая метка '{label}' (строка {line_num})")
            if label in labels:
                raise SyntaxError(f"Метка '{label}' уже существует (строка {line_num})")
            labels[label] = addr
            continue

        if not line.endswith(";"):
            raise SyntaxError(f"Строка должна заканчиваться ';' (строка {line_num})")
        line = line[:-1].strip()
        if not line:
            continue

        # Данные: $x, $y ... (байты 0..255)
        if "$" in line and not any(op == line.split()[0].upper() for op in opcode_map):
            parts = [p.strip() for p in line.replace(",", " ").split()]
            addr += len(parts)
            continue

        # Инструкция
        parts = line.replace(",", " ").split()
        instr = parts[0].upper()

        if instr not in opcode_map:
            raise ValueError(f"Неизвестная инструкция '{instr}' (строка {line_num})")

        # Размер инструкции в байтах
        if instr in ("LD", "ST", "JZ", "JNZ"):
            # opcode + reg + addr16
            addr += 1 + 1 + 2
        elif instr == "JMP":
            # opcode + addr16 (без регистра)
            addr += 1 + 2
        else:
            # opcode + операнды-байты
            addr += 1 + operand_count[instr]

    # ---------- ВТОРОЙ ПРОХОД: собираем байткод ----------
    bytecode: list[int] = []

    for line_num, line in enumerate(lines, start=1):
        line = line.split("#")[0].strip()
        if not line or line.endswith(":"):
            continue

        segments = [seg.strip() for seg in line.split(";") if seg.strip()]

        for segment in segments:
            # Данные ($..): байты
            if "$" in segment and not any(op == segment.split()[0].upper() for op in opcode_map):
                parts = [p.strip() for p in segment.replace(",", " ").split()]
                for p in parts:
                    if not p.startswith("$"):
                        raise SyntaxError(f"Неверная директива '{p}' (строка {line_num})")
                    val = _parse_int(p[1:], line_num)
                    if not (0 <= val <= 255):
                        raise ValueError(f"Данные {val} вне диапазона 0–255 (строка {line_num})")
                    bytecode.append(val & 0xFF)
                continue

            # Инструкция
            parts = segment.replace(",", " ").split()
            instr = parts[0].upper()
            if instr not in opcode_map:
                raise ValueError(f"Неизвестная инструкция '{instr}' (строка {line_num})")

            bytecode.append(opcode_map[instr])
            operands = parts[1:]

            # LD/ST: [op][r][hi][lo]
            if instr in ("LD", "ST"):
                if len(operands) != 2:
                    raise SyntaxError(f"{instr} требует 2 операнда (строка {line_num})")

                reg = _parse_int(operands[0], line_num)
                if not (0 <= reg <= 255):
                    raise ValueError(f"Регистр {reg} вне диапазона 0–255 (строка {line_num})")
                bytecode.append(reg & 0xFF)

                addr_val = _resolve_label_or_number(operands[1], labels, line_num)
                _emit_addr16(bytecode, addr_val, line_num)
                continue

            # JMP: [op][hi][lo]
            if instr == "JMP":
                if len(operands) != 1:
                    raise SyntaxError(f"JMP требует 1 операнд (строка {line_num})")

                addr_val = _resolve_label_or_number(operands[0], labels, line_num)
                _emit_addr16(bytecode, addr_val, line_num)
                continue

            # JZ/JNZ: [op][r][hi][lo]
            if instr in ("JZ", "JNZ"):
                if len(operands) != 2:
                    raise SyntaxError(f"{instr} требует 2 операнда (строка {line_num})")

                reg = _parse_int(operands[0], line_num)
                if not (0 <= reg <= 255):
                    raise ValueError(f"Регистр {reg} вне диапазона 0–255 (строка {line_num})")
                bytecode.append(reg & 0xFF)

                addr_val = _resolve_label_or_number(operands[1], labels, line_num)
                _emit_addr16(bytecode, addr_val, line_num)
                continue

            # Остальные инструкции: все операнды = байты (0..255) или метки (НО метка -> адрес, но тут должен влезть в байт)
            expected = operand_count[instr]
            if len(operands) != expected:
                raise SyntaxError(f"{instr} требует {expected} операнд(а/ов) (строка {line_num})")

            for operand in operands:
                value = _resolve_label_or_number(operand, labels, line_num)
                if not (0 <= value <= 255):
                    raise ValueError(f"Операнд {value} вне диапазона 0–255 (строка {line_num})")
                bytecode.append(value & 0xFF)

    # --- ограничения размера ---
    if len(bytecode) > MAX_PROGRAM_SIZE:
        raise ValueError(f"Программа слишком большая (максимум {MAX_PROGRAM_SIZE} байт)")

    return bytecode


if __name__ == "__main__":
    bytecode = compile_program("program.txt")
    print(f"\nРазмер программы: {len(bytecode)} байт")
    print(f"Свободно: {MAX_PROGRAM_SIZE - len(bytecode)} байт\n")
    print("Байт-код:")
    print(", ".join(f"0b{val:08b}" for val in bytecode))
