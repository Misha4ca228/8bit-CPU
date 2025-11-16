opcode_map = {
    # 1️⃣ Работа с памятью и регистрами
    "LDI":  0b00000001,
    "LD":   0b00000010,
    "ST":   0b00000011,
    "MOV":  0b00000100,
    "STI":  0b00000101,

    # 2️⃣ Арифметика
    "ADD":  0b00001000,
    "ADDI": 0b00001001,
    "SUB":  0b00001010,
    "SUBI": 0b00001011,
    "MUL":  0b00001100,
    "DIV":  0b00001101,
    "MOD":  0b00001110,
    "INC":  0b00001111,
    "DEC":  0b00010000,

    # 3️⃣ Логические операции
    "AND":  0b00010001,
    "OR":   0b00010010,
    "XOR":  0b00010011,
    "NOT":  0b00010100,

    # 4️⃣ Условия и переходы
    "JMP":  0b00011000,
    "JZ":   0b00011001,
    "JNZ":  0b00011010,

    # 4️⃣ Стек

    "PUSH": 0b00011011,
    "POP":  0b00011100,

    # 5️⃣ Остановка
    "HALT": 0b11111111,
}


operand_count = {
    # 1️⃣ Работа с памятью и регистрами
    "LDI":  2,
    "LD":   2,
    "ST":   2,
    "MOV":  2,
    "STI":  2,

    # 2️⃣ Арифметика
    "ADD":  2,
    "ADDI": 2,
    "SUB":  2,
    "SUBI": 2,
    "MUL":  2,
    "DIV":  2,
    "MOD":  2,
    "INC":  1,
    "DEC":  1,

    # 3️⃣ Логические операции
    "AND":  2,
    "OR":   2,
    "XOR":  2,
    "NOT":  1,

    # 4️⃣ Условия и переходы
    "JMP":  1,
    "JZ":   2,
    "JNZ":  2,

    # 4️⃣ Стек

    "PUSH": 1,
    "POP": 1,

    # 5️⃣ Остановка
    "HALT": 0
}



def compile_program(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # ---------- ПЕРВЫЙ ПРОХОД ----------
    labels = {}
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

        # Данные $x, $y
        if "$" in line and not any(op in line.split()[0].upper() for op in opcode_map):
            parts = [p.strip() for p in line.replace(",", " ").split()]
            addr += len(parts)
            continue

        # Команда
        parts = line.replace(",", " ").split()
        instr = parts[0].upper()

        if instr not in opcode_map:
            raise ValueError(f"Неизвестная инструкция '{instr}' (строка {line_num})")

        # обычная инструкция = opcode + операнды
        # но если здесь есть адрес — нужно +2 байта на адрес
        count = operand_count[instr]

        # инструкции с адресом требуют 2 байта вместо 1
        if instr in ("LD", "ST", "JMP", "JZ", "JNZ"):
            addr += 1 + 1 + 2   # opcode + reg? + 12-бит адрес
        else:
            addr += 1 + count

    # ---------- ВТОРОЙ ПРОХОД ----------
    bytecode = []

    for line_num, line in enumerate(lines, start=1):
        line = line.split("#")[0].strip()
        if not line or line.endswith(":"):
            continue

        segments = [seg.strip() for seg in line.split(";") if seg.strip()]

        for segment in segments:

            # Данные
            if "$" in segment and not any(op in segment.split()[0].upper() for op in opcode_map):
                parts = [p.strip() for p in segment.replace(",", " ").split()]
                for p in parts:
                    if not p.startswith("$"):
                        raise SyntaxError(f"Неверная директива '{p}' (строка {line_num})")
                    val = int(p[1:], 0)
                    if not (0 <= val <= 255):
                        raise ValueError(f"Данные {val} вне диапазона 0–255")
                    bytecode.append(val)
                continue

            # Инструкция
            parts = segment.replace(",", " ").split()
            instr = parts[0].upper()
            bytecode.append(opcode_map[instr])

            operands = parts[1:]

            # --- Инструкции с 12-битным адресом ---
            if instr == "LD" or instr == "ST":
                if len(operands) != 2:
                    raise SyntaxError(f"{instr} требует 2 операнда (строка {line_num})")

                # первый = регистр
                reg = int(operands[0])
                bytecode.append(reg)

                # второй = адрес
                addr_val = labels.get(operands[1], None)
                if addr_val is None:
                    addr_val = int(operands[1])

                if not (0 <= addr_val <= 4095):
                    raise ValueError(f"Адрес {addr_val} вне диапазона 0–4095")

                high = (addr_val >> 8) & 0x0F
                low = addr_val & 0xFF

                bytecode.append(high)
                bytecode.append(low)
                continue

            if instr == "JMP":
                if len(operands) != 1:
                    raise SyntaxError(f"JMP требует 1 операнд (строка {line_num})")

                addr_val = labels.get(operands[0], None)
                if addr_val is None:
                    addr_val = int(operands[0])

                high = (addr_val >> 8) & 0x0F
                low = addr_val & 0xFF

                bytecode.append(high)
                bytecode.append(low)
                continue

            if instr in ("JZ", "JNZ"):
                if len(operands) != 2:
                    raise SyntaxError(f"{instr} требует 2 операнда (строка {line_num})")

                reg = int(operands[0])
                bytecode.append(reg)

                addr_val = labels.get(operands[1], None)
                if addr_val is None:
                    addr_val = int(operands[1])

                high = (addr_val >> 8) & 0x0F
                low = addr_val & 0xFF

                bytecode.append(high)
                bytecode.append(low)
                continue

            # --- Обычные инструкции ---
            for operand in operands:
                if operand in labels:
                    value = labels[operand]
                else:
                    value = int(operand)

                if not (0 <= value <= 255):
                    raise ValueError(f"Операнд {value} вне диапазона 0–255")
                bytecode.append(value)

    if len(bytecode) > 4096:
        raise ValueError("Программа слишком большая (максимум 4096 байт)")

    return bytecode




# ---------------------------
# Пример использования
# ---------------------------
if __name__ == "__main__":
    bytecode = compile_program("program.txt")
    print(f"\nРазмер программы: {len(bytecode)} байт")
    print(f"Свободно: {256 - len(bytecode)} байт\n")
    print("Байт-код:")
    print(", ".join(f"0b{val:08b}" for val in bytecode))
