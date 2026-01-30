import re
from dataclasses import dataclass
from pathlib import Path

# =========================
#  ASM -> bytes for your CPU8Bit
# =========================

OP = {
    "LDI":   0b00000001,
    "LDI16": 0b00000010,
    "MOV":   0b00000011,
    "LDM":   0b00000100,
    "STM":   0b00000101,
    "LDR":   0b00000110,
    "STR":   0b00000111,

    "ADD":   0b00001000,
    "ADC":   0b00001001,
    "SUB":   0b00001010,
    "SBC":   0b00001011,
    "INC":   0b00001100,
    "DEC":   0b00001101,
    "CMP":   0b00001110,

    "AND":   0b00001111,
    "OR":    0b00010000,
    "XOR":   0b00010001,
    "NOT":   0b00010010,
    "SHL":   0b00010011,
    "SHR":   0b00010100,

    "JMP":   0b00010101,
    "JZ":    0b00010110,
    "JNZ":   0b00010111,
    "JC":    0b00011000,
    "JNC":   0b00011001,

    "PUSH":  0b00011010,
    "POP":   0b00011011,
    "PUSH16":0b00011100,
    "POP16": 0b00011101,
    "CALL":  0b00011110,
    "RET":   0b00011111,

    "IN":    0b00100000,
    "OUT":   0b00100001,

    "HALT":  0b11111111,
}

# Регистр-алиасы (поменяй под себя)
REG = {f"R{i}": i for i in range(16)}
REG.update({
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
    "G": 6,
    "H": 7,
    "I": 8,
    "J": 9,
    "K": 10,
    "L": 11,
    "M": 12,
    "N": 13,
    "O": 14,
    "P": 15,
})

COMMENT_RE = re.compile(r"(;|#|//).*?$")

@dataclass
class SrcLine:
    lineno: int
    raw: str
    text: str
    addr: int = 0

def _strip_comment(s: str) -> str:
    return COMMENT_RE.sub("", s).strip()

def _tokens(s: str):
    return [t for t in re.split(r"[,\s]+", s.strip()) if t]

def parse_number(tok: str) -> int:
    t = tok.strip().lower().replace("_", "")
    sign = 1
    if t.startswith("-"):
        sign = -1
        t = t[1:]

    if t.startswith("0x"):
        v = int(t[2:], 16)
    elif t.endswith("h") and t[:-1]:
        v = int(t[:-1], 16)
    elif t.startswith("0b"):
        v = int(t[2:], 2)
    elif t.endswith("b") and t[:-1]:
        body = t[:-1]
        if not all(c in "01" for c in body):
            raise ValueError(f"Некорректное двоичное число: {tok}")
        v = int(body, 2)
    else:
        v = int(t, 10)

    return sign * v

def parse_reg(tok: str) -> int:
    u = tok.upper()
    if u not in REG:
        raise ValueError(f"Неизвестный регистр: {tok}")
    return REG[u]

def parse_reg_pair(tok: str):
    """
    XX = HI,LO (два обычных регистра).
    Пример: AH -> (A,H)
    Также допускается R0R1.
    """
    u = tok.upper()

    m = re.fullmatch(r"(R(?:[0-9]|1[0-5]))(R(?:[0-9]|1[0-5]))", u)
    if m:
        return parse_reg(m.group(1)), parse_reg(m.group(2))

    if len(u) == 2:
        hi, lo = u[0], u[1]
        if hi not in REG or lo not in REG:
            raise ValueError(f"Пара {tok}: оба символа должны быть регистрами")
        return parse_reg(hi), parse_reg(lo)

    raise ValueError(f"Некорректная пара регистров: {tok}")

def parse_value(tok: str, labels: dict) -> int:
    if re.fullmatch(r"[A-Za-z_]\w*", tok):
        if tok not in labels:
            raise ValueError(f"Неизвестная метка: {tok}")
        return labels[tok]
    return parse_number(tok)

def emit_u8(out, v: int):
    out.append(v & 0xFF)

def emit_u16_lohi(out, v: int):
    v &= 0xFFFF
    out.append(v & 0xFF)         # LO
    out.append((v >> 8) & 0xFF)  # HI

def estimate_len(tokens):
    if not tokens:
        return 0
    head = tokens[0].upper()

    if head == "$":
        n = 0
        for t in tokens[1:]:
            # метка может означать 16бит, считаем как 2
            if re.fullmatch(r"[A-Za-z_]\w*", t):
                n += 2
            else:
                v = parse_number(t)
                n += 2 if (v < 0 or v > 0xFF) else 1
        return n

    if head in ("HALT", "RET"):
        return 1

    if head in ("INC", "DEC", "NOT", "SHL", "SHR", "PUSH", "POP"):
        return 2

    if head in ("ADD","ADC","SUB","SBC","CMP","AND","OR","XOR","MOV","IN","OUT"):
        return 3

    if head in ("JMP","JZ","JNZ","JC","JNC","CALL"):
        return 3

    if head == "LDI":
        return 3

    if head == "LDI16":
        return 5

    if head in ("LDM","STM","LDR","STR"):
        return 4

    if head in ("PUSH16","POP16"):
        return 3

    raise ValueError(f"Неизвестная инструкция: {tokens[0]}")

def assemble_text(asm_text: str):
    # ---- read lines ----
    raw_lines = asm_text.splitlines()
    lines = []
    for i, raw in enumerate(raw_lines, start=1):
        s = _strip_comment(raw)
        if not s:
            continue
        lines.append(SrcLine(lineno=i, raw=raw, text=s))

    # ---- pass 1: labels ----
    labels = {}
    pc = 0
    for ln in lines:
        text = ln.text

        while True:
            m = re.match(r"^([A-Za-z_]\w*):", text)
            if not m:
                break
            name = m.group(1)
            if name in labels:
                raise ValueError(f"Повтор метки {name} (строка {ln.lineno})")
            labels[name] = pc
            text = text[m.end():].strip()
            ln.text = text
            if not text:
                break

        ln.addr = pc
        if not ln.text:
            continue

        pc = (pc + estimate_len(_tokens(ln.text))) & 0xFFFF

    # ---- pass 2: emit ----
    out = []
    for ln in lines:
        if not ln.text:
            continue
        tok = _tokens(ln.text)
        if not tok:
            continue

        ins = tok[0].upper()

        if ins == "$":
            for t in tok[1:]:
                v = parse_value(t, labels)
                if v < 0 or v > 0xFF:
                    emit_u16_lohi(out, v)  # lo,hi
                else:
                    emit_u8(out, v)
            continue

        if ins not in OP:
            raise ValueError(f"Неизвестная инструкция {ins} (строка {ln.lineno})")

        emit_u8(out, OP[ins])

        if ins in ("HALT","RET"):
            continue

        elif ins == "LDI":
            r = parse_reg(tok[1])
            imm = parse_value(tok[2], labels)
            emit_u8(out, r)
            emit_u8(out, imm)

        elif ins == "LDI16":
            hi, lo = parse_reg_pair(tok[1])
            imm16 = parse_value(tok[2], labels)
            emit_u8(out, hi)
            emit_u8(out, lo)
            emit_u16_lohi(out, imm16)

        elif ins == "MOV":
            emit_u8(out, parse_reg(tok[1]))
            emit_u8(out, parse_reg(tok[2]))

        elif ins == "LDM":
            emit_u8(out, parse_reg(tok[1]))
            emit_u16_lohi(out, parse_value(tok[2], labels))

        elif ins == "STM":
            emit_u16_lohi(out, parse_value(tok[1], labels))
            emit_u8(out, parse_reg(tok[2]))

        elif ins == "LDR":
            emit_u8(out, parse_reg(tok[1]))
            emit_u8(out, parse_reg(tok[2]))
            emit_u8(out, parse_reg(tok[3]))

        elif ins == "STR":
            emit_u8(out, parse_reg(tok[1]))
            emit_u8(out, parse_reg(tok[2]))
            emit_u8(out, parse_reg(tok[3]))

        elif ins in ("ADD","ADC","SUB","SBC","CMP","AND","OR","XOR"):
            emit_u8(out, parse_reg(tok[1]))
            emit_u8(out, parse_reg(tok[2]))

        elif ins in ("INC","DEC","NOT","SHL","SHR","PUSH","POP"):
            emit_u8(out, parse_reg(tok[1]))

        elif ins in ("JMP","JZ","JNZ","JC","JNC","CALL"):
            emit_u16_lohi(out, parse_value(tok[1], labels))

        elif ins == "IN":
            emit_u8(out, parse_reg(tok[1]))
            emit_u8(out, parse_value(tok[2], labels))

        elif ins == "OUT":
            emit_u8(out, parse_value(tok[1], labels))
            emit_u8(out, parse_reg(tok[2]))

        elif ins in ("PUSH16", "POP16"):
            # PUSH16 HI LO  или  PUSH16 HL (пара)
            if len(tok) == 2:
                hi, lo = parse_reg_pair(tok[1])  # например AH
            else:
                hi, lo = parse_reg(tok[1]), parse_reg(tok[2])  # например A H
            emit_u8(out, hi)
            emit_u8(out, lo)


        else:
            raise ValueError(f"Кодирование не реализовано для {ins} (строка {ln.lineno})")

    return out, labels

def assemble_file(asm_path: str, bin_path: str | None = None, encoding: str = "utf-8"):
    asm_path = str(asm_path)
    text = Path(asm_path).read_text(encoding=encoding)

    program, labels = assemble_text(text)

    if bin_path:
        with open(bin_path, "w", encoding="utf-8") as f:
            f.write("[\n")
            for i, b in enumerate(program):
                # записываем байт как 0bXXXXXXXX
                f.write(f"  0b{b:08b}")

                # запятая после каждого байта кроме последнего
                if i != len(program) - 1:
                    f.write(",")

                f.write("\n")
            f.write("]\n")

    return program, labels




# =========================
# CLI example
# =========================
if __name__ == "__main__":
    prog, labels = assemble_file("program_asm.txt", "program_b.txt")
    print("Wrote program.bin, size:", len(prog))
    print("Labels:", labels)
