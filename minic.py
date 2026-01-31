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
  | (?P<FUNC>\bfunc\b)
  | (?P<RETURN>\breturn\b)
  | (?P<CALL>\bcall\b)
  | (?P<COLON>:)
   | (?P<HALT>\bhalt\b)
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
            newlines = text.count("\n")
            if newlines:
                line += newlines
                col = 1 + len(text) - (text.rfind("\n") + 1)
            else:
                col += len(text)
            i = m.end()
            continue
        out.append(Token(kind, text, line, col))
        col += len(text)
        i = m.end()
    return out

# =========================
# AST nodes
# =========================
@dataclass
class VarDecl:
    name: str
    vtype: str
    line: int

@dataclass
class Operand:
    # kind: 'num','char','var','reg','regpair','mem','in','call'
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

@dataclass
class Param:
    name: str
    ptype: str
    line: int

@dataclass
class FuncDef:
    name: str
    params: List[Param]
    body: List[Stmt]     # statements excluding return (parser enforces)
    ret: Stmt            # Stmt(kind='return', data=Operand)
    line: int

@dataclass
class Program:
    funcs: List[FuncDef]
    main: List[Stmt]

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

    def parse_program(self) -> Program:
        funcs: List[FuncDef] = []
        main: List[Stmt] = []
        while self.peek():
            if self.peek().kind == "FUNC":
                funcs.append(self.parse_funcdef())
            else:
                main.append(self.parse_stmt(allow_return=False))
        return Program(funcs=funcs, main=main)

    def parse_funcdef(self) -> FuncDef:
        f_tok = self.expect("FUNC")
        name_tok = self.expect("IDENT")
        self.expect("LPAREN")
        params: List[Param] = []
        if not self.accept("RPAREN"):
            while True:
                p_name = self.expect("IDENT")
                self.expect("COLON")
                p_type = self.expect("TYPE")
                params.append(Param(name=p_name.text, ptype=p_type.text, line=p_name.line))
                if self.accept("COMMA"):
                    continue
                self.expect("RPAREN")
                break

        # function block
        self.expect("LBRACE")
        body: List[Stmt] = []
        ret_stmt: Optional[Stmt] = None

        while True:
            if self.accept("RBRACE"):
                break
            if not self.peek():
                raise SyntaxError(f"Unclosed function block for {name_tok.text}: missing '}}'")

            # return is mandatory, v1: single return
            if self.peek().kind == "RETURN":
                if ret_stmt is not None:
                    raise SyntaxError(f"Multiple return not allowed (v1) in function {name_tok.text} at line {self.peek().line}")
                ret_stmt = self.parse_return_stmt()
                # After return, we still allow only '}' (no more statements)
                # But we won't hard-enforce here; we can allow empty lines/comments already removed.
                continue

            if ret_stmt is not None:
                raise SyntaxError(f"Statements after return are not allowed in function {name_tok.text} (line {self.peek().line})")

            body.append(self.parse_stmt(allow_return=False))

        if ret_stmt is None:
            raise SyntaxError(f"Function {name_tok.text} must have return (line {f_tok.line})")

        return FuncDef(name=name_tok.text, params=params, body=body, ret=ret_stmt, line=f_tok.line)

    def parse_block(self) -> List[Stmt]:
        self.expect("LBRACE")
        stmts: List[Stmt] = []
        while True:
            if self.accept("RBRACE"):
                break
            if not self.peek():
                raise SyntaxError("Unclosed block: missing '}'")
            stmts.append(self.parse_stmt(allow_return=False))
        return stmts

    def parse_stmt(self, allow_return: bool) -> Stmt:
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
        if t.kind == "RETURN":
            if not allow_return:
                raise SyntaxError(f"'return' not allowed here (line {t.line})")
            return self.parse_return_stmt()
        if t.kind == "HALT":
            ht = self.expect("HALT")
            return Stmt("halt", None, ht.line)

        return self.parse_assignment_like()

    def parse_return_stmt(self) -> Stmt:
        r_tok = self.expect("RETURN")
        expr = self.parse_operand()
        return Stmt("return", expr, r_tok.line)

    def parse_let(self) -> Stmt:
        let_tok = self.expect("LET")
        name = self.expect("IDENT").text
        op = self.expect("OP")
        if op.text != "=":
            raise SyntaxError(f"Expected '=' in let, got {op.text} (line {op.line})")
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
        target = self.parse_target()

        nxt = self.peek()
        if nxt and nxt.kind == "OP" and nxt.text in ("++", "--"):
            op = self.expect("OP").text
            return Stmt("postfix", {"target": target, "op": op}, target.line)

        op_tok = self.expect("OP")
        op = op_tok.text

        if op == "=":
            if self.peek() and self.peek().kind == "NOT":
                self.expect("NOT")
                rhs = self.parse_operand()
                return Stmt("assign_not", {"target": target, "rhs": rhs}, op_tok.line)
            rhs = self.parse_operand()
            return Stmt("assign", {"target": target, "rhs": rhs}, op_tok.line)

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

        if t.kind == "MEM":
            mem_tok = self.expect("MEM")
            self.expect("LBRACK")
            addr = self.parse_address()
            self.expect("RBRACK")
            return Target("mem", addr, mem_tok.line)

        if t.kind == "IDENT":
            tok = self.expect("IDENT")
            return Target("var", tok.text, tok.line)

        raise SyntaxError(f"Invalid target at line {t.line}")

    def parse_address(self) -> Operand:
        t = self.peek()
        if not t:
            raise SyntaxError("Unexpected EOF in address")

        if t.kind in ("NUM", "BIN"):
            return self.parse_operand()

        if t.kind == "IDENT":
            tok = self.expect("IDENT")
            name = tok.text.upper()
            if len(name) == 2 and all(ch in "ABCDEFGHIJKLMNOP" for ch in name):
                return Operand("regpair", name, tok.line)
            return Operand("var", tok.text, tok.line)

        if t.kind == "REG":
            raise SyntaxError(f"Use mem[GH] not mem[reg[GH]] at line {t.line}")

        raise SyntaxError(f"Invalid address at line {t.line}")

    def parse_operand(self) -> Operand:
        t = self.peek()
        if not t:
            raise SyntaxError("Unexpected EOF in operand")

        # call foo(...)
        if t.kind == "CALL":
            call_tok = self.expect("CALL")
            fname = self.expect("IDENT").text
            self.expect("LPAREN")
            args: List[Operand] = []
            if not self.accept("RPAREN"):
                while True:
                    args.append(self.parse_operand())
                    if self.accept("COMMA"):
                        continue
                    self.expect("RPAREN")
                    break
            return Operand("call", {"name": fname, "args": args}, call_tok.line)

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
            ch = tok.text[1]
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
        # stacked scopes: each scope maps source var name -> varinfo dict
        self.scopes: List[Dict[str, Dict[str, Any]]] = [dict()]  # global scope
        self.current_func: Optional[str] = None

        self.main_asm: List[str] = []
        self.func_asm: List[str] = []
        self.data: List[str] = []

        self.lbl_id = 0

        # function table
        # name -> {params:[{name, type}], ret_width:8|16}
        self.funcs: Dict[str, Dict[str, Any]] = {}

    # ---------- utilities ----------
    def new_label(self, prefix: str) -> str:
        s = f"{prefix}_{self.lbl_id}"
        self.lbl_id += 1
        return s

    def emit(self, line: str):
        if self.current_func is None:
            self.main_asm.append(line)
        else:
            self.func_asm.append(line)

    def emit_data(self, line: str):
        self.data.append(line)

    # ---------- scope ----------
    def push_scope(self):
        self.scopes.append(dict())

    def pop_scope(self):
        if len(self.scopes) <= 1:
            raise RuntimeError("Internal: pop global scope")
        self.scopes.pop()

    def lookup_var(self, name: str) -> Optional[Dict[str, Any]]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

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
        if self.lookup_var(name) is not None and name in self.scopes[-1]:
            raise ValueError(f"Variable {name} redeclared in same scope at line {line}")

        if vtype not in ("u8", "u16", "char"):
            raise ValueError(f"Unknown type {vtype} at line {line}")

        # mangle inside functions to avoid collisions
        if self.current_func is None:
            base = name
        else:
            base = f"__{self.current_func}__{name}"

        if vtype in ("u8", "char"):
            info = {"type": vtype, "labels": {"byte": base}}
            self.emit_data(f"{base}: $ 0")
        else:
            lo = f"{base}_lo"
            hi = f"{base}_hi"
            info = {"type": vtype, "labels": {"lo": lo, "hi": hi}}
            self.emit_data(f"{lo}: $ 0")
            self.emit_data(f"{hi}: $ 0")

        self.scopes[-1][name] = info

    def vartype(self, name: str, line: int) -> str:
        info = self.lookup_var(name)
        if info is None:
            raise ValueError(f"Unknown variable {name} at line {line}")
        return info["type"]

    def varlabel_u8(self, name: str, line: int) -> str:
        t = self.vartype(name, line)
        if t not in ("u8", "char"):
            raise ValueError(f"Variable {name} is {t}, expected u8/char at line {line}")
        info = self.lookup_var(name)
        return info["labels"]["byte"]

    def varlabels_u16(self, name: str, line: int) -> Tuple[str, str]:
        t = self.vartype(name, line)
        if t != "u16":
            raise ValueError(f"Variable {name} is {t}, expected u16 at line {line}")
        info = self.lookup_var(name)
        return info["labels"]["lo"], info["labels"]["hi"]

    # ---------- type helpers ----------
    def is_u16_operand(self, op: Operand) -> bool:
        if op.kind == "var":
            return self.vartype(op.value, op.line) == "u16"
        if op.kind == "regpair":
            return True
        if op.kind == "num":
            return int(op.value) > 0xFF
        return False

    def width_of_operand(self, op: Operand) -> int:
        # returns 8 or 16
        return 16 if self.is_u16_operand(op) else 8

    def width_of_target(self, target: Target) -> int:
        if target.kind == "reg":
            return 8
        if target.kind == "regpair":
            return 16
        if target.kind == "var":
            return 16 if self.vartype(target.value, target.line) == "u16" else 8
        if target.kind == "mem":
            # memory is byte-addressed here -> u8 store
            return 8
        raise ValueError(f"Unknown target kind {target.kind}")

    # ---------- load/store u8 ----------
    def load_u8_into(self, op: Operand, dst: str, avoid: Optional[str] = None):
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
            port = op.value
            if port.kind == "num":
                self.emit(f"IN {dst}, {port.value & 0xFF}")
            else:
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
            lo_lbl, hi_lbl = self.varlabels_u16(addr.value, addr.line)
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

    # ---------- u16 load ----------
    def load_u16_into(self, op: Operand, hi_reg: str, lo_reg: str):
        self.reg_ok(hi_reg)
        self.reg_ok(lo_reg)

        if op.kind == "var":
            lo_lbl, hi_lbl = self.varlabels_u16(op.value, op.line)
            self.emit(f"LDM {lo_reg}, {lo_lbl}")
            self.emit(f"LDM {hi_reg}, {hi_lbl}")
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
            if rp[0] != hi_reg:
                self.emit(f"MOV {hi_reg}, {rp[0]}")
            if rp[1] != lo_reg:
                self.emit(f"MOV {lo_reg}, {rp[1]}")
            return

        raise ValueError(f"Unsupported u16 operand {op.kind} at line {op.line}")

    # ---------- compare + jump false ----------
    def emit_cond_jump_false(self, cond: Dict[str, Any], false_label: str):
        left: Operand = cond["left"]
        right: Operand = cond["right"]
        op = cond["op"]
        line = cond["line"]

        if self.is_u16_operand(left) or self.is_u16_operand(right):
            allowed = ("var", "num", "regpair")
            if left.kind not in allowed or right.kind not in allowed:
                raise ValueError(f"u16 condition supports only u16 vars/regpairs/consts (line {line})")

            if left.kind == "var" and self.vartype(left.value, left.line) != "u16":
                raise ValueError(f"Left operand must be u16 for u16 compare (line {line})")
            if right.kind == "var" and self.vartype(right.value, right.line) != "u16":
                raise ValueError(f"Right operand must be u16 for u16 compare (line {line})")

            self.emit_cond_jump_false_u16(cond, false_label)
            return

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
            self.emit(f"JC {false_label}")
            self.emit(f"JZ {false_label}")
        elif op == "<=":
            true_label = self.new_label("cond_true")
            self.emit(f"JC {true_label}")
            self.emit(f"JZ {true_label}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{true_label}:")
        else:
            raise ValueError(f"Unsupported condition operator {op} at line {line}")

    def emit_cond_jump_false_u16(self, cond: dict, false_label: str):
        left: Operand = cond["left"]
        right: Operand = cond["right"]
        op = cond["op"]
        line = cond["line"]

        # A=Left_HI, C=Left_LO, B=Right_HI, D=Right_LO
        self.load_u16_into(left, hi_reg="A", lo_reg="C")
        self.load_u16_into(right, hi_reg="B", lo_reg="D")

        eq_hi = self.new_label("u16_eq_hi")
        cont = self.new_label("u16_true")

        if op == "==":
            self.emit("CMP A, B")
            self.emit(f"JNZ {false_label}")
            self.emit("CMP C, D")
            self.emit(f"JNZ {false_label}")
            return

        if op == "!=":
            self.emit("CMP A, B")
            self.emit(f"JNZ {cont}")
            self.emit("CMP C, D")
            self.emit(f"JNZ {cont}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{cont}:")
            return

        if op == "<":
            self.emit("CMP A, B")
            self.emit(f"JC {cont}")
            self.emit(f"JZ {eq_hi}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JNC {false_label}")
            self.emit(f"{cont}:")
            return

        if op == ">=":
            self.emit("CMP A, B")
            self.emit(f"JC {false_label}")
            self.emit(f"JZ {eq_hi}")
            self.emit(f"JMP {cont}")
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JC {false_label}")
            self.emit(f"{cont}:")
            return

        if op == ">":
            self.emit("CMP A, B")
            self.emit(f"JC {false_label}")
            self.emit(f"JZ {eq_hi}")
            self.emit(f"JMP {cont}")
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JC {false_label}")
            self.emit(f"JZ {false_label}")
            self.emit(f"{cont}:")
            return

        if op == "<=":
            self.emit("CMP A, B")
            self.emit(f"JC {cont}")
            self.emit(f"JZ {eq_hi}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{eq_hi}:")
            self.emit("CMP C, D")
            self.emit(f"JC {cont}")
            self.emit(f"JZ {cont}")
            self.emit(f"JMP {false_label}")
            self.emit(f"{cont}:")
            return

        raise ValueError(f"Unsupported u16 condition operator {op} at line {line}")

    # ---------- arithmetic/logic ----------
    def choose_temp(self, avoid: str) -> str:
        for r in ["B", "C", "D", "E", "F"]:
            if r != avoid:
                return r
        return "B"

    def target_as_operand(self, target: Target) -> Operand:
        if target.kind == "var":
            return Operand("var", target.value, target.line)
        if target.kind == "reg":
            return Operand("reg", target.value, target.line)
        if target.kind == "mem":
            return Operand("mem", target.value, target.line)
        raise ValueError(f"Cannot treat target {target.kind} as operand")

    def apply_opassign_u8(self, target: Target, op: str, rhs: Operand):
        if op in ("<<=", ">>="):
            if rhs.kind != "num":
                raise ValueError(f"Shift amount must be constant number at line {rhs.line}")
            amt = max(0, int(rhs.value))
            instr = "SHL" if op == "<<=" else "SHR"

            if target.kind == "reg":
                r = target.value
                self.reg_ok(r)
                for _ in range(amt):
                    self.emit(f"{instr} {r}")
                return

            self.load_u8_into(self.target_as_operand(target), "A")
            for _ in range(amt):
                self.emit(f"{instr} A")
            self.store_u8_from(target, "A")
            return

        if target.kind == "reg":
            r = target.value
            self.reg_ok(r)
            tmp = self.choose_temp(avoid=r)
            self.load_u8_into(rhs, tmp, avoid=r)
            asm_op = {"+=": "ADD", "-=": "SUB", "&=": "AND", "|=": "OR", "^=": "XOR"}[op]
            self.emit(f"{asm_op} {r}, {tmp}")
            return

        self.load_u8_into(self.target_as_operand(target), "A")
        self.load_u8_into(rhs, "B", avoid="A")
        asm_op = {"+=": "ADD", "-=": "SUB", "&=": "AND", "|=": "OR", "^=": "XOR"}[op]
        self.emit(f"{asm_op} A, B")
        self.store_u8_from(target, "A")

    def apply_postfix(self, target: Target, op: str):
        if op not in ("++", "--"):
            raise ValueError("Invalid postfix op")

        if target.kind == "reg":
            r = target.value
            self.reg_ok(r)
            self.emit("INC " + r if op == "++" else "DEC " + r)
            return

        if target.kind == "var":
            name = target.value
            t = self.vartype(name, target.line)
            if t == "u16":
                lo_lbl, hi_lbl = self.varlabels_u16(name, target.line)

                self.emit(f"LDM B, {lo_lbl}")
                self.emit(f"LDM A, {hi_lbl}")

                if op == "++":
                    done = self.new_label("u16_inc_done")
                    self.emit("INC B")
                    self.emit(f"JNZ {done}")
                    self.emit("INC A")
                    self.emit(f"{done}:")
                else:
                    no_borrow = self.new_label("u16_dec_no_borrow")
                    self.emit("LDI C, 0")
                    self.emit("CMP B, C")
                    self.emit(f"JNZ {no_borrow}")
                    self.emit("DEC A")
                    self.emit(f"{no_borrow}:")
                    self.emit("DEC B")

                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return

        instr = "INC" if op == "++" else "DEC"
        self.load_u8_into(self.target_as_operand(target), "A")
        self.emit(f"{instr} A")
        self.store_u8_from(target, "A")

    # ---------- CALL / RET convention ----------
    def emit_push_arg(self, arg_op: Operand, arg_type: str):
        if arg_type in ("u8", "char"):
            self.load_u8_into(arg_op, "A")
            self.emit("PUSH A")
            return
        if arg_type == "u16":
            # use AB: A=HI, B=LO
            self.load_u16_into(arg_op, hi_reg="A", lo_reg="B")
            self.emit("PUSH16 AB")
            return
        raise ValueError(f"Invalid arg type {arg_type}")

    def compile_call_and_pop(self, call: Operand, expected_width: int) -> Tuple[int, str, str]:
        """
        Emits:
          PUSH args (right-to-left, sized by function signature)
          CALL foo
          POP or POP16 into (A) or (A,B)
        Returns: (ret_width, hi_reg, lo_reg) where for 8-bit lo_reg is ''.
        """
        info = self.funcs.get(call.value["name"])
        if info is None:
            raise ValueError(f"Unknown function {call.value['name']} at line {call.line}")

        fname = call.value["name"]
        args: List[Operand] = call.value["args"]
        params = info["params"]

        if len(args) != len(params):
            raise ValueError(f"Function {fname} expects {len(params)} args, got {len(args)} (line {call.line})")

        # push right-to-left
        for arg_op, p in zip(reversed(args), reversed(params)):
            self.emit_push_arg(arg_op, p["type"])

        self.emit(f"CALL {fname}")

        retw = info["ret_width"]
        if expected_width != retw:
            raise ValueError(
                f"Call {fname} returns {retw}-bit, but assignment expects {expected_width}-bit (line {call.line})"
            )

        if retw == 8:
            self.emit("POP A")
            return retw, "A", ""
        else:
            self.emit("POP16 AB")  # A=HI, B=LO after POP16
            return retw, "A", "B"

    # ---------- assignment ----------
    def apply_assign(self, target: Target, rhs: Operand):
        # call expression
        if rhs.kind == "call":
            expected = self.width_of_target(target)
            self.compile_call_and_pop(rhs, expected_width=expected)

            if expected == 8:
                # result in A
                self.store_u8_from(target, "A")
                return

            # expected 16: result in A(hi), B(lo)
            if target.kind == "regpair":
                rp = target.value
                self.regpair_ok(rp)
                self.emit(f"MOV {rp[0]}, A")
                self.emit(f"MOV {rp[1]}, B")
                return

            if target.kind == "var" and self.vartype(target.value, target.line) == "u16":
                lo_lbl, hi_lbl = self.varlabels_u16(target.value, target.line)
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return

            raise ValueError(f"Cannot assign 16-bit return value into {target.kind} (line {target.line})")

        # normal assigns
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
                self.emit(f"LDI16 {rp}, {self.const_u16(rhs.value)}")
                return
            raise ValueError(f"Cannot assign {rhs.kind} to regpair at line {target.line}")

        if target.kind == "var" and self.vartype(target.value, target.line) == "u16":
            lo_lbl, hi_lbl = self.varlabels_u16(target.value, target.line)
            if rhs.kind == "regpair":
                src = rhs.value
                self.regpair_ok(src)
                self.emit(f"STM {lo_lbl}, {src[1]}")
                self.emit(f"STM {hi_lbl}, {src[0]}")
                return
            if rhs.kind == "var":
                src_lo, src_hi = self.varlabels_u16(rhs.value, rhs.line)
                self.emit(f"LDM B, {src_lo}")
                self.emit(f"LDM A, {src_hi}")
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return
            if rhs.kind == "num":
                self.emit(f"LDI16 AB, {self.const_u16(rhs.value)}")
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
                return
            raise ValueError(f"Cannot assign {rhs.kind} to u16 variable at line {target.line}")

        # otherwise treat as u8 assignment
        self.load_u8_into(rhs, "A")
        self.store_u8_from(target, "A")

    def apply_assign_not(self, target: Target, rhs: Operand):
        self.load_u8_into(rhs, "A")
        self.emit("NOT A")
        self.store_u8_from(target, "A")

    def apply_out(self, port: Operand, val: Operand, line: int):
        if port.kind != "num":
            raise ValueError(f"out(port, ...) requires constant port at line {line}")
        p = port.value & 0xFF
        if val.kind == "reg":
            self.reg_ok(val.value)
            self.emit(f"OUT {p}, {val.value}")
            return
        self.load_u8_into(val, "A")
        self.emit(f"OUT {p}, A")

    # ---------- statements ----------
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

        if st.kind == "halt":
            self.emit("HALT")
            return

        if st.kind == "assign_not":
            self.apply_assign_not(st.data["target"], st.data["rhs"])
            return

        if st.kind == "opassign":
            target: Target = st.data["target"]
            op: str = st.data["op"]
            rhs: Operand = st.data["rhs"]

            if target.kind == "var" and self.vartype(target.value, target.line) == "u16":
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

    # ---------- functions ----------
    def register_funcs(self, funcs: List[FuncDef]):
        for f in funcs:
            if f.name in self.funcs:
                raise ValueError(f"Function {f.name} redeclared (line {f.line})")
            self.funcs[f.name] = {
                "params": [{"name": p.name, "type": p.ptype, "line": p.line} for p in f.params],
                "ret_width": None,
                "line": f.line,
            }

    def compile_func(self, f: FuncDef):
        self.current_func = f.name
        self.push_scope()

        # function label
        self.emit(f"{f.name}:")
        # prologue: pop return address
        self.emit("POP16 OP")

        # declare params as variables in current scope (so body can use them as vars)
        for p in f.params:
            self.declare_var(p.name, p.ptype, p.line)

        # pop args left-to-right (arg1 first after retaddr removed)
        for p in f.params:
            if p.ptype in ("u8", "char"):
                self.emit("POP A")
                lbl = self.varlabel_u8(p.name, p.line)
                self.emit(f"STM {lbl}, A")
            elif p.ptype == "u16":
                self.emit("POP16 AB")  # A=HI, B=LO
                lo_lbl, hi_lbl = self.varlabels_u16(p.name, p.line)
                self.emit(f"STM {lo_lbl}, B")
                self.emit(f"STM {hi_lbl}, A")
            else:
                raise ValueError(f"Invalid param type {p.ptype} in {f.name} (line {p.line})")

        # compile body statements
        self.compile_stmt_list(f.body)

        # return (mandatory, single)
        ret_op: Operand = f.ret.data
        retw = self.width_of_operand(ret_op)

        # record return width for callers
        self.funcs[f.name]["ret_width"] = retw

        if retw == 8:
            self.load_u8_into(ret_op, "A")
            self.emit("PUSH A")
        else:
            self.load_u16_into(ret_op, hi_reg="A", lo_reg="B")
            self.emit("PUSH16 AB")

        # restore return address and ret
        self.emit("PUSH16 OP")
        self.emit("RET")

        self.pop_scope()
        self.current_func = None

    def compile_program(self, prog: Program):
        # First pass: collect function signatures
        self.register_funcs(prog.funcs)

        # Second: compile functions and infer return widths
        for f in prog.funcs:
            self.compile_func(f)

        # Validate all funcs got ret_width (should)
        for name, info in self.funcs.items():
            if info["ret_width"] is None:
                raise ValueError(f"Internal: function {name} missing return width")

        # Compile main (global scope)
        self.current_func = None
        self.compile_stmt_list(prog.main)

    def render(self) -> str:
        out: List[str] = []
        out.append("; ===== GENERATED ASM (HighLang -> ASM) =====")
        out.append("")
        start_lbl = "__start"
        out.append(f"JMP {start_lbl}")
        out.append("")
        out.append("; ===== FUNCTIONS =====")
        out.extend(self.func_asm)
        out.append("")
        out.append("; ===== MAIN =====")
        out.append(f"{start_lbl}:")
        out.extend(self.main_asm)
        out.append("")
        out.append("HALT")
        out.append("")
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
    cg.compile_program(prog)
    return cg.render()

def main():
    if len(sys.argv) < 3:
        print("Usage: python highlang_compiler.py input.txt output.asm", file=sys.stderr)
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
