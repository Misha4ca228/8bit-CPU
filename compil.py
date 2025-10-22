opcode_map = {
    "NOP":  0b00000000,
    "LDI":  0b00000001,
    "LD":   0b00000010,
    "ST":   0b00000011,
    "MOV":  0b00000100,
    "ADD":  0b00000101,
    "ADDI": 0b00000110,
    "SUB":  0b00000111,
    "SUBI": 0b00001000,
    "DIV":  0b00001001,
    "MOD":  0b00001010,
    "INC":  0b00001011,
    "DEC":  0b00001100,
    "JMP":  0b00001101,
    "JZ":   0b00001110,
    "JNZ":  0b00001111,
    "STI":  0b00010000,
    "HALT": 0b11111111,
}

operand_count = {
    "NOP":  0, "HALT": 0,
    "LDI": 2, "LD": 2, "ST": 2,
    "MOV": 2, "ADD": 2, "ADDI": 2,
    "SUB": 2, "SUBI": 2,
    "INC": 1, "DEC": 1,
    "JMP": 1, "JZ": 2, "JNZ": 2,
    "DIV": 2, "STI": 2,
    "MOD": 2,
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

        # 💡 Метка
        if line.endswith(":"):
            label_name = line[:-1].strip()
            if not label_name.isidentifier():
                raise SyntaxError(f"Неверное имя метки '{label_name}' (строка {line_num})")
            if label_name in labels:
                raise SyntaxError(f"Метка '{label_name}' уже определена (строка {line_num})")
            labels[label_name] = addr
            continue

        if not line.endswith(";"):
            raise SyntaxError(f"Ошибка синтаксиса (строка {line_num}): строка должна заканчиваться ';'")
        line = line[:-1].strip()

        # ✅ Поддержка нескольких $ на одной строке
        if "$" in line and not any(op in line.split()[0].upper() for op in opcode_map):
            parts = [p.strip() for p in line.replace(",", " ").split() if p.strip()]
            for p in parts:
                if not p.startswith("$"):
                    raise SyntaxError(f"Неверная директива данных '{p}' (строка {line_num})")
                addr += 1
            continue

        # Команда
        parts = line.replace(",", " ").split()
        instr = parts[0].upper()
        if instr not in opcode_map:
            raise ValueError(f"Неизвестная инструкция '{instr}' (строка {line_num})")
        addr += 1 + operand_count[instr]

    # ---------- ВТОРОЙ ПРОХОД ----------
    bytecode = []

    for line_num, line in enumerate(lines, start=1):
        line = line.split("#")[0].strip()
        if not line or line.endswith(":"):
            continue

        # Строка должна заканчиваться ';' — но может содержать много ';' внутри
        if ";" not in line:
            raise SyntaxError(f"Ошибка синтаксиса (строка {line_num}): отсутствует ';' в конце инструкции или данных")

        # Разбиваем строку по ';' и обрабатываем каждую часть отдельно
        segments = [seg.strip() for seg in line.split(";") if seg.strip()]

        for segment in segments:
            # Пропускаем пустые строки и комментарии
            if not segment:
                continue

            # Обработка нескольких $ на одной строке
            if "$" in segment and not any(op in segment.split()[0].upper() for op in opcode_map):
                # поддержка синтаксиса $1, $2, $3
                data_parts = [p.strip() for p in segment.replace(",", " ").split() if p.strip()]
                for p in data_parts:
                    if not p.startswith("$"):
                        raise SyntaxError(f"Неверная директива данных '{p}' (строка {line_num})")
                    val_str = p[1:].strip()
                    if val_str.startswith(("0x", "0b")):
                        val = int(val_str, 0)  # поддержка 0x.., 0b..
                    elif val_str.isdigit():
                        val = int(val_str)
                    else:
                        raise ValueError(f"После '$' должно быть число (строка {line_num})")
                    if not (0 <= val <= 255):
                        raise ValueError(f"Значение {val} вне диапазона 0–255 (строка {line_num})")
                    bytecode.append(val)
                continue

            # Обычная инструкция
            parts = segment.replace(",", " ").split()
            instr = parts[0].upper()

            if instr not in opcode_map:
                raise ValueError(f"Неизвестная инструкция '{instr}' (строка {line_num})")

            bytecode.append(opcode_map[instr])

            for operand in parts[1:]:
                if operand in labels:
                    value = labels[operand]
                elif operand.isdigit():
                    value = int(operand)
                else:
                    raise ValueError(f"Неизвестный операнд '{operand}' (строка {line_num})")

                if not (0 <= value <= 255):
                    raise ValueError(f"Операнд {value} вне диапазона 0–255 (строка {line_num})")
                bytecode.append(value)

    if len(bytecode) > 256:
        raise ValueError("Скомпилированная программа слишком большая (макс 256 байт)")

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
