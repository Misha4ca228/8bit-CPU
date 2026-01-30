# highlang_compiler.py
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# =========================
# CHAR MAP (from your CPU)
# =========================
CHAR_MAP = {
    0: "",
    1: " ",
    2: ":", 3: "!", 4: "?", 5: "*", 6: "-",
    7: "+", 8: "/", 9: ",", 10: ".",
    11: "A", 12: "B", 13: "C", 14: "D", 15: "E",
    16: "F", 17: "G", 18: "H", 19: "I", 20: "J",
    21: "K", 22: "L", 23: "M", 24: "N", 25: "O",
    26: "P", 27: "Q", 28: "R", 29: "S", 30: "T",
    31: "U", 32: "V", 33: "W", 34: "X", 35: "Y",
    36: "Z",
    37: "Б", 38: "Г", 39: "Д", 40: "Ж", 41: "З",
    42: "И", 43: "Л", 44: "П", 45: "Ф", 46: "Ц",
    47: "Ч", 48: "Ш", 49: "Щ", 50: "Ъ", 51: "Ы",
    52: "Ь", 53: "Э", 54: "Ю", 55: "Я",
    56: "0", 57: "1", 58: "2", 59: "3", 60: "4",
    61: "5", 62: "6", 63: "7", 64: "8", 65: "9",
    66: "=", 67: "(", 68: ")", 69: "_", 70: "&",
    71: "@", 72: "%", 73: "$", 74: "~", 75: "|",
    76: "<", 77: ">", 78: ";", 79: "✡", 80: "^",
    81: "#", 82: "[", 83: "]", 84: "{", 85: "}",
}
CHAR_TO_CODE = {v: k for k, v in CHAR_MAP.items() if v != ""}

# =========================
# Tokenizer
# =========================
TOKEN_RE = re.compile(
    r"""
    (?P<WS>\s+)
  | (?P<COMMENT>//[^\n]*|;[^\n]*|\#[^\n]*)
  | (?P<LET>\blet:)
  | (?P<IF>\bif\b)
  | (?P<ELSE>\belse\b)
  | (?P<WHILE>\bwhile\b)
  | (?P<REG>\breg\b)
  | (?P<MEM>\bmem\b)
  | (?P<NOT>\bnot\b)
  | (?P<IN>\bin\b)
  | (?P<OUT>\bout\b)
  | (?P<TYPE>\bu8\b|\bu16\b|\bchar\b)
  | (?P<BIN>0b[01]+)
  | (?P<NUM>\d+)
  | (?P<CHARLIT>'[^']') 
  | (?P<OP>\+\+|--|\+=|-=|&=|\|=|\^=|<<=|>>=|==|!=|<=|>=|<<|>>|=|<|>)
  | (?P<LBRACE>\{)
  | (?P<RBRACE>\})
  | (?P<LPAREN>\()
  | (?P<RPAREN>\))
  | (?P<LBRACK>\[)
  | (?P<RBRACK>\])
  | (?P<COMMA>,)
  | (?P<IDENT>[A-Za-z_]\w*)
    """,
    re.VERBOSE,
)



@dataclass
class Token:
    kind: str
    text: str
    line: int
    col: int

def tokenize(src: str) -> List[Token]:
    out: List[Token] = []
    i = 0
    line = 1
    col = 1
    while i < len(src):
        m = TOKEN_RE.match(src, i)
        if not m:
            raise SyntaxError(f"Unexpected char {src[i]!r} at line {line}, col {col}")
        kind = m.lastgroup
        text = m.group(kind)
        if kind in ("WS", "COMMENT"):
            # update line/col
            newlines = text.count("\n")
            if newlines:
                line += newlines
                col = 1 + len(text) - (text.rfind("\n") + 1)
            else:
                col += len(text)
            i = m.end()
            continue
        out.append(Token(kind, text, line, col))
        # update line/col
        col += len(text)
        i = m.end()
    return out

# =========================
# AST nodes (minimal)
# =========================
@dataclass
class VarDecl:
    name: str
    vtype: str
    line: int

@dataclass
class Operand:
    # kind: 'num','char','var','reg','regpair','mem','in'
    kind: str
    value: Any
    line: int

@dataclass
class Target:
    # kind: 'var','reg','regpair','mem'
    kind: str
    value: Any
    line: int

@dataclass
class Stmt:
    kind: str
    data: Any
    line: int

# =========================
# Parser
# =========================
class Parser:
    def __init__(self, tokens: List[Token]):
        self.toks = tokens
        self.i = 0

    def peek(self, k: int = 0) -> Optional[Token]:
        j = self.i + k
        return self.toks[j] if 0 <= j < len(self.toks) else None

    def accept(self, kind: str) -> Optional[Token]:
        t = self.peek()
        if t and t.kind == kind:
            self.i += 1
            return t
        return None

    def expect(self, kind: str) -> Token:
        t = self.peek()
        if not t or t.kind != kind:
            got = t.kind if t else "EOF"
            line = t.line if t else (self.toks[-1].line if self.toks else 1)
            col = t.col if t else (self.toks[-1].col if self.toks else 1)
            raise SyntaxError(f"Expected {kind}, got {got} at line {line}, col {col}")
        self.i += 1
        return t

    def parse_program(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while self.peek():
            stmts.append(self.parse_stmt())
        return stmts

    def parse_block(self) -> List[Stmt]:
        self.expect("LBRACE")
        stmts: List[Stmt] = []
        while True:
            if self.accept("RBRACE"):
                break
            if not self.peek():
                raise SyntaxError("Unclosed block: missing '}'")
            stmts.append(self.parse_stmt())
        return stmts

    def parse_stmt(self) -> Stmt:
        t = self.peek()
        if not t:
            raise SyntaxError("Unexpected EOF")

        if t.kind == "LET":
            return self.parse_let()
        if t.kind == "IF":
            return self.parse_if()
        if t.kind == "WHILE":
            return self.parse_while()
        if t.kind == "OUT":
            return self.parse_out_stmt()

        # generic expression/assignment forms:
        # - X++
        # - X--
        # - target OP= operand
        # - target = operand
        # - target = not operand
        return self.parse_assignment_like()

    def parse_let(self) -> Stmt:
        let_tok = self.expect("LET")
        name = self.expect("IDENT").text
        self.expect("OP")  # should be '='
        ttype = self.expect("TYPE").text
        return Stmt("let", VarDecl(name=name, vtype=ttype, line=let_tok.line), let_tok.line)

    def parse_if(self) -> Stmt:
        if_tok = self.expect("IF")
        self.expect("LPAREN")
        cond = self.parse_condition()
        self.expect("RPAREN")
        then_block = self.parse_block()
        else_block = None
        if self.accept("ELSE"):
            else_block = self.parse_block()
        return Stmt("if", {"cond": cond, "then": then_block, "else": else_block}, if_tok.line)

    def parse_while(self) -> Stmt:
        w_tok = self.expect("WHILE")
        self.expect("LPAREN")
        cond = self.parse_condition()
        self.expect("RPAREN")
        body = self.parse_block()
        return Stmt("while", {"cond": cond, "body": body}, w_tok.line)

    def parse_out_stmt(self) -> Stmt:
        out_tok = self.expect("OUT")
        self.expect("LPAREN")
        port = self.parse_operand()
        self.expect("COMMA")
        val = self.parse_operand()
        self.expect("RPAREN")
        return Stmt("out", {"port": port, "val": val}, out_tok.line)

    def parse_assignment_like(self) -> Stmt:
        # target first
        target = self.parse_target()

        # postfix ++ / --
        nxt = self.peek()
        if nxt and nxt.kind == "OP" and nxt.text in ("++", "--"):
            op = self.expect("OP").text
            return Stmt("postfix", {"target": target, "op": op}, target.line)

        # op or = or op=
        op_tok = self.expect("OP")
        op = op_tok.text

        if op == "=":
            # allow: target = not operand
            if self.peek() and self.peek().kind == "NOT":
                self.expect("NOT")
                rhs = self.parse_operand()
                return Stmt("assign_not", {"target": target, "rhs": rhs}, op_tok.line)

            # allow: target = in(...)
            rhs = self.parse_operand()
            return Stmt("assign", {"target": target, "rhs": rhs}, op_tok.line)

        # op= forms
        if op in ("+=", "-=", "&=", "|=", "^=", "<<=", ">>="):
            rhs = self.parse_operand()
            return Stmt("opassign", {"target": target, "op": op, "rhs": rhs}, op_tok.line)

        raise SyntaxError(f"Unsupported operator {op} at line {op_tok.line}")

    def parse_condition(self) -> Dict[str, Any]:
        left = self.parse_operand()
        op_tok = self.expect("OP")
        if op_tok.text not in ("==", "!=", "<", ">", "<=", ">="):
            raise SyntaxError(f"Invalid condition operator {op_tok.text} at line {op_tok.line}")
        right = self.parse_operand()
        return {"left": left, "op": op_tok.text, "right": right, "line": op_tok.line}

    def parse_target(self) -> Target:
        t = self.peek()
        if not t:
            raise SyntaxError("Unexpected EOF in target")

        # reg[...]
        if t.kind == "REG":
            reg_tok = self.expect("REG")
            self.expect("LBRACK")
            regname = self.expect("IDENT").text.upper()
            self.expect("RBRACK")
            if len(regname) == 1:
                return Target("reg", regname, reg_tok.line)
            elif len(regname) == 2:
                return Target("regpair", regname, reg_tok.line)
            else:
                raise SyntaxError(f"Invalid reg name {regname} at line {reg_tok.line}")

        # mem[...]
        if t.kind == "MEM":
            mem_tok = self.expect("MEM")
            self.expect("LBRACK")
            addr = self.parse_address()
            self.expect("RBRACK")
            return Target("mem", addr, mem_tok.line)

        # variable name
        if t.kind == "IDENT":
            tok = self.expect("IDENT")
            return Target("var", tok.text, tok.line)

        raise SyntaxError(f"Invalid target at line {t.line}")

    def parse_address(self) -> Operand:
        # address may be constant number/bin, variable, or regpair like AH / BC / GH
        t = self.peek()
        if not t:
            raise SyntaxError("Unexpected EOF in address")

        if t.kind in ("NUM", "BIN", "CHARLIT"):
            # char literal as address is weird - reject
            if t.kind == "CHARLIT":
                raise SyntaxError(f"Char literal not allowed as address at line {t.line}")
            return self.parse_operand()

        if t.kind == "IDENT":
            tok = self.expect("IDENT")
            name = tok.text.upper()
            # if two letters and both are A..P we treat as regpair address (e.g. GH)
            if len(name) == 2 and all(ch in "ABCDEFGHIJKLMNOP" for ch in name):
                return Operand("regpair", name, tok.line)
            # else variable name (u16 expected later)
            return Operand("var", tok.text, tok.line)

        if t.kind == "REG":
            # allow mem[reg[GH]] if user wants, but optional; keep simple:
            raise SyntaxError(f"Use mem[GH] not mem[reg[GH]] at line {t.line}")

        raise SyntaxError(f"Invalid address at line {t.line}")

    def parse_operand(self) -> Operand:
        t = self.peek()
        if not t:
            raise SyntaxError("Unexpected EOF in operand")

        # in(...)
        if t.kind == "IN":
            in_tok = self.expect("IN")
            self.expect("LPAREN")
            port = self.parse_operand()
            self.expect("RPAREN")
            return Operand("in", port, in_tok.line)

        # reg[...]
        if t.kind == "REG":
            reg_tok = self.expect("REG")
            self.expect("LBRACK")
            regname = self.expect("IDENT").text.upper()
            self.expect("RBRACK")
            if len(regname) == 1:
                return Operand("reg", regname, reg_tok.line)
            elif len(regname) == 2:
                return Operand("regpair", regname, reg_tok.line)
            else:
                raise SyntaxError(f"Invalid reg name {regname} at line {reg_tok.line}")

        # mem[...]
        if t.kind == "MEM":
            mem_tok = self.expect("MEM")
            self.expect("LBRACK")
            addr = self.parse_address()
            self.expect("RBRACK")
            return Operand("mem", addr, mem_tok.line)

        if t.kind == "CHARLIT":
            tok = self.expect("CHARLIT")
            ch = tok.text[1]  # 'A'
            return Operand("char", ch, tok.line)

        if t.kind == "BIN":
            tok = self.expect("BIN")
            return Operand("num", int(tok.text[2:], 2), tok.line)

        if t.kind == "NUM":
            tok = self.expect("NUM")
            return Operand("num", int(tok.text, 10), tok.line)

        if t.kind == "IDENT":
            tok = self.expect("IDENT")
            return Operand("var", tok.text, tok.line)

        raise SyntaxError(f"Invalid operand at line {t.line}")

# =========================
# Codegen
# =========================
class Codegen:
    def __init__(self):
        self.vars: Dict[str, Dict[str, Any]] = {}  # name -> {type, labels}
        self.asm: List[str] = []
        self.data: List[str] = []
        self.lbl_id = 0

    def new_label(self, prefix: str) -> str:
        s = f"{prefix}_{self.lbl_id}"
        self.lbl_id += 1
        return s

    def emit(self, line: str):
        self.asm.append(line)

    def emit_data(self, line: str):
        self.data.append(line)

    # ---------- values ----------
    def const_u8(self, n: int) -> int:
        return n & 0xFF

    def const_u16(self, n: int) -> int:
        return n & 0xFFFF

    def char_code(self, ch: str, line: int) -> int:
        if ch not in CHAR_TO_CODE:
            raise ValueError(f"Unknown char {ch!r} at line {line} (not in CHAR_MAP)")
        return CHAR_TO_CODE[ch]

    def reg_ok(self, r: str):
        if len(r) != 1 or r not in "ABCDEFGHIJKLMNOP":
            raise ValueError(f"Invalid register {r}")

    def regpair_ok(self, rp: str):
        if len(rp) != 2 or any(ch not in "ABCDEFGHIJKLMNOP" for ch in rp):
            raise ValueError(f"Invalid register pair {rp}")

    # ---------- variable labels ----------
    def declare_var(self, name: str, vtype: str, line: int):
        if name in self.vars:
            raise ValueError(f"Variable {name} redeclared at line {line}")
        if vtype not in ("u8", "u16", "char"):
            raise ValueError(f"Unknown type {vtype} at line {line}")

        if vtype in ("u8", "char"):
            self.vars[name] = {"type": vtype, "labels": {"byte": name}}
            self.emit_data(f"{name}: $ 0")
        else:
            lo = f"{name}_lo"
            hi = f"{name}_hi"
            self.vars[name] = {"type": vtype, "labels": {"lo": lo, "hi": hi}}
            self.emit_data(f"{lo}: $ 0")
            self.emit_data(f"{hi}: $ 0")

    def vartype(self, name: str, line: int) -> str:
        if name not in self.vars:
            raise ValueError(f"Unknown variable {name} at line {line}")
        return self.vars[name]["type"]

    def varlabel_u8(self, name: str, line: int) -> str:
        t = self.vartype(name, line)
        if t not in ("u8", "char"):
            raise ValueError(f"Variable {name} is {t}, expected u8/char at line {line}")
        return self.vars[name]["labels"]["byte"]

    def varlabels_u16(self, name: str, line: int) -> Tuple[str, str]:
        t = self.vartype(name, line)
        if t != "u16":
            raise ValueError(f"Variable {name} is {t}, expected u16 at line {line}")
        lo = self.vars[name]["labels"]["lo"]
        hi = self.vars[name]["labels"]["hi"]
        return lo, hi

    # ---------- load/store u8 ----------
    def load_u8_into(self, op: Operand, dst: str, avoid: Optional[str] = None):
        """
        Load u8 value of operand into dst register.
        """
        self.reg_ok(dst)
        if avoid and dst == avoid:
            raise ValueError("Internal: dst conflicts with avoid")

        if op.kind == "num":
            self.emit(f"LDI {dst}, {self.const_u8(op.value)}")
            return

        if op.kind == "char":
            code = self.char_code(op.value, op.line)
            self.emit(f"LDI {dst}, {code}")
            return

        if op.kind == "reg":
            self.reg_ok(op.value)
            if op.value != dst:
                self.emit(f"MOV {dst}, {op.value}")
            return

        if op.kind == "var":
            lbl = self.varlabel_u8(op.value, op.line)
            self.emit(f"LDM {dst}, {lbl}")
            return

        if op.kind == "mem":
            self.load_mem_u8_into(op.value, dst, op.line)
            return

        if op.kind == "in":
            # IN dst, port
            port = op.value
            # port must be numeric constant
            if port.kind == "num":
                self.emit(f"IN {dst}, {port.value & 0xFF}")
            elif port.kind == "bin":
                self.emit(f"IN {dst}, {port.value & 0xFF}")
            elif port.kind == "var":
                raise ValueError(f"in(port) requires constant port 0..7 (got var) at line {op.line}")
            else:
                if port.kind == "num":
                    pass
                raise ValueError(f"in(port) requires constant port 0..7 at line {op.line}")
            return

        raise ValueError(f"Unsupported operand for u8 load: {op.kind} at line {op.line}")

    def store_u8_from(self, target: Target, src_reg: str):
        self.reg_ok(src_reg)

        if target.kind == "reg":
            self.reg_ok(target.value)
            if target.value != src_reg:
                self.emit(f"MOV {target.value}, {src_reg}")
            return

        if target.kind == "var":
            lbl = self.varlabel_u8(target.value, target.line)
            self.emit(f"STM {lbl}, {src_reg}")
            return

        if target.kind == "mem":
            self.store_mem_u8_from(target.value, src_reg, target.line)
            return

        raise ValueError(f"Unsupported u8 store target {target.kind} at line {target.line}")

    # ---------- memory helpers (byte) ----------
    def load_mem_u8_into(self, addr: Operand, dst: str, line: int):
        """
        dst = mem[addr] (byte)
        addr is Operand: num/var(u16)/regpair
        """
        self.reg_ok(dst)
        if addr.kind == "num":
            self.emit(f"LDM {dst}, {self.const_u16(addr.value)}")
            return
        if addr.kind == "regpair":
            rp = addr.value
            self.regpair_ok(rp)
            hi, lo = rp[0], rp[1]
            self.emit(f"LDR {dst}, {hi}, {lo}")
            return
        if addr.kind == "var":
            # u16 variable -> load into GH temp, then LDR
            lo_lbl, hi_lbl = self.varlabels_u16(addr.value, addr.line)
            # GH: G=HI, H=LO
            self.emit(f"LDM H, {lo_lbl}")
            self.emit(f"LDM G, {hi_lbl}")
            self.emit(f"LDR {dst}, G, H")
            return
        raise ValueError(f"Invalid mem address kind {addr.kind} at line {line}")

    def store_mem_u8_from(self, addr: Operand, src: str, line: int):
        self.reg_ok(src)
        if addr.kind == "num":
            self.emit(f"STM {self.const_u16(addr.value)}, {src}")
            return
        if addr.kind == "regpair":
            rp = addr.value
            self.regpair_ok(rp)
            hi, lo = rp[0], rp[1]
            self.emit(f"STR {hi}, {lo}, {src}")
            return
        if addr.kind == "var":
            lo_lbl, hi_lbl = self.varlabels_u16(addr.value, addr.line)
            self.emit(f"LDM H, {lo_lbl}")
            self.emit(f"LDM G, {hi_lbl}")
            self.emit(f"STR G, H, {src}")
            return
        raise ValueError(f"Invalid mem address kind {addr.kind} at line {line}")

    # ---------- compare + jump false ----------
    def emit_cond_jump_false(self, cond: Dict[str, Any], false_label: str):
        """
        Генерирует код проверки условия и прыжок на false_label, если условие ЛОЖНО.

        Поддерживает:
        - u8 сравнения: == != < > <= >=  (через A,B)
        - u16 сравнения: == != < > <= >= (через A,C и B,D)
          где A=Left_HI, C=Left_LO, B=Right_HI, D=Right_LO
        """
        left: Operand = cond["left"]
        right: Operand = cond["right"]
        op = cond["op"]
        line = cond["line"]

        # ---------- u16 path ----------
        if self.is_u16_operand(left) or self.is_u16_operand(right):
            # пока разрешаем только: u16 var, const num, regpair
            allowed = ("var", "num", "regpair")
            if left.kind not in allowed or right.kind not in allowed:
                raise ValueError(
                    f"u16 condition supports only u16 vars/regpairs/consts (line {line})"
                )

            # если var, он обязан быть u16
            if left.kind == "var" and self.vartype(left.value, left.line) != "u16":
                raise ValueError(f"Left operand must be u16 for u16 compare (line {line})")
            if right.kind == "var" and self.vartype(right.value, right.line) != "u16":
                raise ValueError(f"Right operand must be u16 for u16 compare (line {line})")

            self.emit_cond_jump_false_u16(cond, false_label)
            return

        # ---------- u8 path (старое поведение) ----------
        # load left into A, right into B
        self.load_u8_into(left, "A")
        self.load_u8_into(right, "B", avoid="A")
        self.emit("CMP A, B")

        if op == "==":
            self.emit(f"JNZ {false_label}")
        elif op == "!=":
            self.emit(f"JZ {false_label}")
        elif op == "<":
            self.emit(f"JNC {false_label}")
        elif op == ">=":
            self.emit(f"JC {false_label}")
        elif op == ">":
            # false if A < B OR A == B
            self.emit(f"JC {false_label}")
            self.emit(f"JZ {false_label}")
        elif op == "<=":
            # true if (A < B) OR (A == B); false otherwise
            true_label = self.new_label("cond_true")
            self.emit(f"JC {true_label}")
            self.emit(f"JZ {true_label}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{true_label}:")
        else:
            raise ValueError(f"Unsupported condition operator {op} at line {line}")

    # ---------- arithmetic/logic ----------
    def choose_temp(self, avoid: str) -> str:
        for r in ["B", "C", "D", "E", "F"]:
            if r != avoid:
                return r
        return "B"

    def apply_opassign_u8(self, target: Target, op: str, rhs: Operand):
        """
        target OP= rhs, where target is u8-like (reg single / var u8/char / mem byte)
        """
        # Handle shifts possibly by amount >1 (literal only)
        if op in ("<<=", ">>="):
            # amount must be num or bin
            amt = None
            if rhs.kind == "num":
                amt = int(rhs.value)
            elif rhs.kind == "char":
                raise ValueError(f"Shift amount cannot be char at line {rhs.line}")
            else:
                raise ValueError(f"Shift amount must be constant number at line {rhs.line}")
            amt = max(0, amt)
            if target.kind == "reg":
                r = target.value
                self.reg_ok(r)
                instr = "SHL" if op == "<<=" else "SHR"
                for _ in range(amt):
                    self.emit(f"{instr} {r}")
                return
            # non-reg: load into A, shift, store back
            self.load_u8_into(self.target_as_operand(target), "A")
            instr = "SHL" if op == "<<=" else "SHR"
            for _ in range(amt):
                self.emit(f"{instr} A")
            self.store_u8_from(target, "A")
            return

        # INC/DEC shortcuts if rhs is 1? we keep generic
        if target.kind == "reg":
            r = target.value
            self.reg_ok(r)
            tmp = self.choose_temp(avoid=r)
            self.load_u8_into(rhs, tmp, avoid=r)
            asm_op = {"+=": "ADD", "-=": "SUB", "&=": "AND", "|=": "OR", "^=": "XOR"}[op]
            self.emit(f"{asm_op} {r}, {tmp}")
            return

        # non-reg target: use A as accumulator
        self.load_u8_into(self.target_as_operand(target), "A")
        self.load_u8_into(rhs, "B", avoid="A")
        asm_op = {"+=": "ADD", "-=": "SUB", "&=": "AND", "|=": "OR", "^=": "XOR"}[op]
        self.emit(f"{asm_op} A, B")
        self.store_u8_from(target, "A")

    def target_as_operand(self, target: Target) -> Operand:
        if target.kind == "var":
            return Operand("var", target.value, target.line)
        if target.kind == "reg":
            return Operand("reg", target.value, target.line)
        if target.kind == "mem":
            return Operand("mem", target.value, target.line)
        raise ValueError(f"Cannot treat target {target.kind} as operand")

    def apply_postfix(self, target: Target, op: str):
        if op not in ("++", "--"):
            raise ValueError("Invalid postfix op")

        # ----------------------------
        # 1) 8-bit register: reg[A]++ / reg[B]--
        # ----------------------------
        if target.kind == "reg":
            r = target.value
            self.reg_ok(r)
            self.emit("INC " + r if op == "++" else "DEC " + r)
            return

        # ----------------------------
        # 2) 16-bit variable: cursor++ / cursor--
        # ----------------------------
        if target.kind == "var":
            name = target.value
            t = self.vartype(name, target.line)
            if t == "u16":
                lo_lbl, hi_lbl = self.varlabels_u16(name, target.line)

                # load u16 into A:HI, B:LO
                self.emit(f"LDM B, {lo_lbl}")
                self.emit(f"LDM A, {hi_lbl}")

                if op == "++":
                    # INC LO; if LO became 0 -> INC HI
                    done = self.new_label("u16_inc_done")
                    self.emit("INC B")
                    self.emit(f"JNZ {done}")
                    self.emit("INC A")
                    self.emit(f"{done}:")
                else:
                    # DEC: if LO==0 then HI--, then LO--
                    no_borrow = self.new_label("u16_dec_no_borrow")
                    self.emit("LDI C, 0")
                    self.emit("CMP B, C")
                    self.emit(f"JNZ {no_borrow}")
                    self.emit("DEC A")
                    self.emit(f"{no_borrow}:")
                    self.emit("DEC B")

                # store back (LO,HI)
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return

        # ----------------------------
        # 3) Everything else treated as u8 (var u8/char or mem[...])
        # ----------------------------
        instr = "INC" if op == "++" else "DEC"
        self.load_u8_into(self.target_as_operand(target), "A")
        self.emit(f"{instr} A")
        self.store_u8_from(target, "A")

    def apply_assign(self, target: Target, rhs: Operand):
        # If target is regpair or u16 var, only support u16 assign from const/var/regpair
        if target.kind == "regpair":
            rp = target.value
            self.regpair_ok(rp)
            hi, lo = rp[0], rp[1]
            if rhs.kind == "regpair":
                src = rhs.value
                self.regpair_ok(src)
                self.emit(f"MOV {hi}, {src[0]}")
                self.emit(f"MOV {lo}, {src[1]}")
                return
            if rhs.kind == "var":
                lo_lbl, hi_lbl = self.varlabels_u16(rhs.value, rhs.line)
                self.emit(f"LDM {lo}, {lo_lbl}")
                self.emit(f"LDM {hi}, {hi_lbl}")
                return
            if rhs.kind == "num":
                # easiest: use LDI16 with pair name (e.g. AB)
                self.emit(f"LDI16 {rp}, {self.const_u16(rhs.value)}")
                return
            raise ValueError(f"Cannot assign {rhs.kind} to regpair at line {target.line}")

        if target.kind == "var" and self.vartype(target.value, target.line) == "u16":
            # u16 var = regpair/var/num
            lo_lbl, hi_lbl = self.varlabels_u16(target.value, target.line)
            if rhs.kind == "regpair":
                src = rhs.value
                self.regpair_ok(src)
                # memory LO,HI
                self.emit(f"STM {lo_lbl}, {src[1]}")
                self.emit(f"STM {hi_lbl}, {src[0]}")
                return
            if rhs.kind == "var":
                src_lo, src_hi = self.varlabels_u16(rhs.value, rhs.line)
                # load into B/A and store; use B=LO, A=HI
                self.emit(f"LDM B, {src_lo}")
                self.emit(f"LDM A, {src_hi}")
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return
            if rhs.kind == "num":
                # load imm16 into AB then store
                self.emit(f"LDI16 AB, {self.const_u16(rhs.value)}")
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return
            raise ValueError(f"Cannot assign {rhs.kind} to u16 variable at line {target.line}")

        # otherwise treat as u8 assignment
        self.load_u8_into(rhs, "A")
        self.store_u8_from(target, "A")

    def apply_assign_not(self, target: Target, rhs: Operand):
        # u8 only
        self.load_u8_into(rhs, "A")
        self.emit("NOT A")
        self.store_u8_from(target, "A")

    def apply_out(self, port: Operand, val: Operand, line: int):
        # port must be constant (num/bin)
        if port.kind != "num":
            raise ValueError(f"out(port, ...) requires constant port at line {line}")
        p = port.value & 0xFF

        # if val is reg -> direct OUT
        if val.kind == "reg":
            self.reg_ok(val.value)
            self.emit(f"OUT {p}, {val.value}")
            return

        # else load into A then OUT
        self.load_u8_into(val, "A")
        self.emit(f"OUT {p}, A")

    # ---------- statement compilation ----------
    def compile_stmt_list(self, stmts: List[Stmt]):
        for st in stmts:
            self.compile_stmt(st)

    def compile_stmt(self, st: Stmt):
        if st.kind == "let":
            d: VarDecl = st.data
            self.declare_var(d.name, d.vtype, d.line)
            return

        if st.kind == "assign":
            self.apply_assign(st.data["target"], st.data["rhs"])
            return

        if st.kind == "assign_not":
            self.apply_assign_not(st.data["target"], st.data["rhs"])
            return

        if st.kind == "opassign":
            target: Target = st.data["target"]
            op: str = st.data["op"]
            rhs: Operand = st.data["rhs"]

            # decide u16? only allow +=/-= for u16 later; for now error
            if target.kind == "var" and target.value in self.vars and self.vars[target.value]["type"] == "u16":
                raise ValueError(f"u16 op-assign not implemented yet (line {st.line})")

            if target.kind == "regpair":
                raise ValueError(f"regpair op-assign not implemented yet (line {st.line})")

            self.apply_opassign_u8(target, op, rhs)
            return

        if st.kind == "postfix":
            self.apply_postfix(st.data["target"], st.data["op"])
            return

        if st.kind == "out":
            self.apply_out(st.data["port"], st.data["val"], st.line)
            return

        if st.kind == "if":
            cond = st.data["cond"]
            then_block = st.data["then"]
            else_block = st.data["else"]

            lbl_else = self.new_label("else")
            lbl_end = self.new_label("endif")

            if else_block is None:
                self.emit_cond_jump_false(cond, lbl_end)
                self.compile_stmt_list(then_block)
                self.emit(f"{lbl_end}:")
            else:
                self.emit_cond_jump_false(cond, lbl_else)
                self.compile_stmt_list(then_block)
                self.emit(f"JMP {lbl_end}")
                self.emit(f"{lbl_else}:")
                self.compile_stmt_list(else_block)
                self.emit(f"{lbl_end}:")
            return

        if st.kind == "while":
            cond = st.data["cond"]
            body = st.data["body"]

            lbl_begin = self.new_label("while_begin")
            lbl_end = self.new_label("while_end")

            self.emit(f"{lbl_begin}:")
            self.emit_cond_jump_false(cond, lbl_end)
            self.compile_stmt_list(body)
            self.emit(f"JMP {lbl_begin}")
            self.emit(f"{lbl_end}:")
            return

        raise ValueError(f"Unknown stmt kind {st.kind} at line {st.line}")

    def is_u16_operand(self, op: Operand) -> bool:
        # u16 — только переменная типа u16 или regpair (если ты захочешь сравнивать пары)
        if op.kind == "var":
            return self.vartype(op.value, op.line) == "u16"
        if op.kind == "regpair":
            return True
        return False

    def load_u16_into(self, op: Operand, hi_reg: str, lo_reg: str):
        self.reg_ok(hi_reg)
        self.reg_ok(lo_reg)

        if op.kind == "var":
            lo_lbl, hi_lbl = self.varlabels_u16(op.value, op.line)
            self.emit(f"LDM {lo_reg}, {lo_lbl}")  # LO
            self.emit(f"LDM {hi_reg}, {hi_lbl}")  # HI
            return

        if op.kind == "num":
            v = self.const_u16(op.value)
            lo = v & 0xFF
            hi = (v >> 8) & 0xFF
            self.emit(f"LDI {lo_reg}, {lo}")
            self.emit(f"LDI {hi_reg}, {hi}")
            return

        if op.kind == "regpair":
            rp = op.value
            self.regpair_ok(rp)
            # rp[0]=HI, rp[1]=LO
            if rp[0] != hi_reg:
                self.emit(f"MOV {hi_reg}, {rp[0]}")
            if rp[1] != lo_reg:
                self.emit(f"MOV {lo_reg}, {rp[1]}")
            return

        raise ValueError(f"Unsupported u16 operand {op.kind} at line {op.line}")

    def emit_cond_jump_false_u16(self, cond: dict, false_label: str):
        left: Operand = cond["left"]
        right: Operand = cond["right"]
        op = cond["op"]
        line = cond["line"]

        # Используем: A=Left_HI, C=Left_LO, B=Right_HI, D=Right_LO
        self.load_u16_into(left, hi_reg="A", lo_reg="C")
        self.load_u16_into(right, hi_reg="B", lo_reg="D")

        # Вспомогательные метки
        eq_hi = self.new_label("u16_eq_hi")
        cont = self.new_label("u16_true")

        if op == "==":
            self.emit("CMP A, B")
            self.emit(f"JNZ {false_label}")
            self.emit("CMP C, D")
            self.emit(f"JNZ {false_label}")
            return

        if op == "!=":
            # false, если равно
            self.emit("CMP A, B")
            self.emit(f"JNZ {cont}")
            self.emit("CMP C, D")
            self.emit(f"JNZ {cont}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{cont}:")
            return

        if op == "<":
            # false если NOT (L < R)
            # сравнить HI
            self.emit("CMP A, B")
            self.emit(f"JC {cont}")  # HI меньше -> true
            self.emit(f"JZ {eq_hi}")  # HI равны -> сравнить LO
            self.emit(f"JMP {false_label}")  # HI больше -> false
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JNC {false_label}")  # LO >= -> false
            self.emit(f"{cont}:")
            return

        if op == ">=":
            # false если L < R
            self.emit("CMP A, B")
            self.emit(f"JC {false_label}")  # HI меньше -> false
            self.emit(f"JZ {eq_hi}")  # HI равны -> сравнить LO
            self.emit(f"JMP {cont}")  # HI больше -> true
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JC {false_label}")  # LO меньше -> false
            self.emit(f"{cont}:")
            return

        if op == ">":
            # false если L <= R
            self.emit("CMP A, B")
            self.emit(f"JC {false_label}")  # HI меньше -> false
            self.emit(f"JZ {eq_hi}")  # HI равны -> сравнить LO
            self.emit(f"JMP {cont}")  # HI больше -> true
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JC {false_label}")  # LO меньше -> false
            self.emit(f"JZ {false_label}")  # LO равно  -> false
            self.emit(f"{cont}:")
            return

        if op == "<=":
            # false если L > R
            self.emit("CMP A, B")
            self.emit(f"JC {cont}")  # HI меньше -> true
            self.emit(f"JZ {eq_hi}")  # HI равны -> сравнить LO
            self.emit(f"JMP {false_label}")  # HI больше -> false
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JC {cont}")  # LO меньше -> true
            self.emit(f"JZ {cont}")  # LO равно  -> true
            self.emit(f"JMP {false_label}")  # LO больше -> false
            self.emit(f"{cont}:")
            return

        raise ValueError(f"Unsupported u16 condition operator {op} at line {line}")

    def render(self) -> str:
        out: List[str] = []
        out.append("; ===== GENERATED ASM (HighLang -> ASM) =====")
        out.append("")
        out.extend(self.asm)
        out.append("")
        out.append("HALT")
        out.append("; ===== DATA =====")
        out.append("")
        out.extend(self.data)
        out.append("")
        return "\n".join(out)

# =========================
# Compiler entry
# =========================
def compile_highlang_text(src_text: str) -> str:
    tokens = tokenize(src_text)
    parser = Parser(tokens)
    prog = parser.parse_program()

    cg = Codegen()
    cg.compile_stmt_list(prog)
    return cg.render()

def main():
    if len(sys.argv) < 3:
        print("Usage: python minic.py input.txt output.asm", file=sys.stderr)
        sys.exit(2)

    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])

    src = inp.read_text(encoding="utf-8")
    try:
        asm = compile_highlang_text(src)
    except Exception as e:
        print(f"Compile error: {e}", file=sys.stderr)
        sys.exit(1)

    outp.write_text(asm, encoding="utf-8")
    print(f"Wrote ASM: {outp} ({len(asm.splitlines())} lines)")

if __name__ == "__main__":
    main()
