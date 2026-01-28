import time
import tkinter as tk
from threading import Thread


class CPU8Bit:
    def __init__(self, program=None):
        self.program = program or []
        if len(self.program) > 65536:
            raise ValueError("Программа больше 64К")

        self.memory = self.program + [0] * (65536 - len(self.program))

        self.PC = 0

        # Stack (32 bytes)
        self.STACK_START = 0xFFD0
        self.STACK_END = 0xFFEF
        self.SC = self.STACK_END

        # 8 registers, 16-bit unsigned
        self.reg = [0] * 8

        # Flags
        self.Z = 0
        self.C = 0

        self.ports = [0] * 8

        self.console_window = None
        self.console_text = None
        self.CHAR_MAP = {
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

    # ---------------- GUI ----------------
    def start_console(self):
        def run():
            self.console_window = tk.Tk()
            self.console_window.title("CPU Output + Keyboard")
            self.console_window.geometry("1020x640")

            # ================= экран =================
            self.console_text = tk.Text(
                self.console_window,
                font=("Consolas", 30),
                bg="black",
                fg="lime",
                height=2
            )
            self.console_text.pack(fill="x", padx=6, pady=6)

            # ================= клавиатурный порт =================
            KEYBOARD_PORT = 0

            def press_code(code: int):
                # НЕ очищаем порт автоматически
                self.ports[KEYBOARD_PORT] = code & 0xFF

            def code_of(ch: str) -> int:
                for k, v in self.CHAR_MAP.items():
                    if v == ch:
                        return k
                return 0  # 0 = "ничего"

            # ================= SHIFT переключатель (LAT↔RUS) =================
            shift_var = tk.IntVar(value=0)  # 0=LAT, 1=RUS

            # ================= UI верхняя панель =================
            topbar = tk.Frame(self.console_window, bg="gray10")
            topbar.pack(fill="x", padx=6, pady=(0, 6))

            tk.Label(
                topbar,
                text="SHIFT (LAT / RUS)",
                fg="white",
                bg="gray10",
                font=("Consolas", 12)
            ).pack(side="left", padx=(6, 6))

            tk.Checkbutton(
                topbar,
                variable=shift_var,
                onvalue=1,
                offvalue=0,
                bg="gray10",
                activebackground="gray10",
                command=lambda: rebuild_labels()  # обновим подписи при переключении
            ).pack(side="left")

            port_label = tk.Label(
                topbar,
                text=f"PORT[{KEYBOARD_PORT}] = 0",
                fg="white",
                bg="gray10",
                font=("Consolas", 12)
            )
            port_label.pack(side="right", padx=10)

            def refresh_port():
                port_label.config(text=f"PORT[{KEYBOARD_PORT}] = {self.ports[KEYBOARD_PORT]}")
                self.console_window.after(100, refresh_port)

            refresh_port()

            # ================= раскладка: 2 символа на клавишу =================
            # Формат: phys -> (normal, shift)
            # normal = что вводится без SHIFT (LAT),
            # shift  = что вводится с SHIFT (RUS), может быть "" (пустая клавиша)
            KEYMAP = {}

            # 1) Цифры: обычные / со "shift-знаками"
            digit_shift = {
                "1": "!", "2": "?", "3": "*", "4": "-", "5": "+",
                "6": "/", "7": ",", "8": ".", "9": "(", "0": ")",
            }
            for d in "1234567890":
                KEYMAP[d] = (d, digit_shift.get(d, d))

            # 2) Буквы: LAT / RUS (пустые допускаются)
            RUS_MAP = {
                # верхний ряд
                "Q": "", "W": "Ц", "E": "", "R": "", "T": "",
                "Y": "", "U": "Г", "I": "Ш", "O": "Щ", "P": "З",

                # средний ряд
                "A": "Ф", "S": "Ы", "D": "", "F": "", "G": "П",
                "H": "", "J": "", "K": "Л", "L": "Д",

                # нижний ряд
                "Z": "Я", "X": "Ч", "C": "", "V": "", "B": "И",
                "N": "", "M": "Ь",
            }
            for ch in "QWERTYUIOPASDFGHJKLZXCVBNM":
                KEYMAP[ch] = (ch, RUS_MAP.get(ch, ""))

            # 3) Доп. символы (отдельный ряд): normal/shift пары
            SYM_KEYS = [
                (":", ";"),
                ("=", "_"),
                ("@", "#"),
                ("&", "%"),
                ("$", "~"),
                ("|", "^"),
                ("<", ">"),
                ("[", "]"),
                ("{", "}"),
                ("✡", "✡"),
            ]

            # ================= построение кнопок =================
            kb = tk.Frame(self.console_window, bg="gray15")
            kb.pack(fill="both", expand=True, padx=6, pady=6)

            buttons = {}  # phys -> (Button, normal, shifted)

            def label_for(phys: str, normal: str, shifted: str) -> str:
                if phys == "SPACE":
                    return "SPACE"
                if phys == "ENTER":
                    return "ENTER\n255"
                if phys == "BACK":
                    return "BACK\n254"

                # Пустая русская буква: показываем только латиницу
                if shifted == "" or shifted is None:
                    return f"{normal}"

                # если совпадает — тоже один
                if shifted == normal:
                    return f"{normal}"

                # стандарт: верх = shift, низ = normal
                return f"{shifted}\n{normal}"

            def press_phys(phys: str, normal: str, shifted: str):
                if phys == "ENTER":
                    press_code(255)
                    return
                if phys == "BACK":
                    press_code(254)
                    return
                if phys == "SPACE":
                    press_code(code_of(" "))
                    return

                sym = shifted if shift_var.get() == 1 else normal
                if not sym:
                    press_code(0)
                    return

                press_code(code_of(sym))

            def rebuild_labels():
                for phys, (btn, normal, shifted) in buttons.items():
                    btn.config(text=label_for(phys, normal, shifted))

            # ----- ряды как на клавиатуре -----
            physical_rows = [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "BACK"],
                list("QWERTYUIOP"),
                list("ASDFGHJKL") + ["ENTER"],
                list("ZXCVBNM"),
                ["SPACE"],
            ]

            for row in physical_rows:
                row_frame = tk.Frame(kb, bg="gray15")
                row_frame.pack(fill="x", pady=4)

                for phys in row:
                    if phys == "SPACE":
                        normal, shifted = " ", " "
                        w, h = 60, 3
                    elif phys == "ENTER":
                        normal, shifted = "", ""
                        w, h = 10, 3
                    elif phys == "BACK":
                        normal, shifted = "", ""
                        w, h = 10, 3
                    else:
                        normal, shifted = KEYMAP.get(phys, ("", ""))
                        w, h = 6, 3

                    btn = tk.Button(
                        row_frame,
                        text=label_for(phys, normal, shifted),
                        width=w,
                        height=h,
                        command=lambda p=phys, n=normal, s=shifted: press_phys(p, n, s)
                    )
                    btn.pack(side="left", padx=3)
                    buttons[phys] = (btn, normal, shifted)

            # ----- ряд доп. символов -----
            sym_frame = tk.Frame(kb, bg="gray15")
            sym_frame.pack(fill="x", pady=(10, 4))

            tk.Label(
                sym_frame, text="SYMBOLS:", fg="white", bg="gray15", font=("Consolas", 12)
            ).pack(side="left", padx=(6, 10))

            for normal, shifted in SYM_KEYS:
                phys = f"{normal}|{shifted}"
                btn = tk.Button(
                    sym_frame,
                    text=label_for(phys, normal, shifted),
                    width=6,
                    height=3,
                    command=lambda p=phys, n=normal, s=shifted: press_phys(p, n, s)
                )
                btn.pack(side="left", padx=3)
                buttons[phys] = (btn, normal, shifted)

            rebuild_labels()
            self.console_window.mainloop()

        Thread(target=run, daemon=False).start()

    def update_console(self):
        if not self.console_text:
            return

        text = ""
        for i in range(16):
            code = self.memory[-16 + i] & 0xFF
            text += self.CHAR_MAP.get(code, "?")

        self.console_text.delete("1.0", tk.END)
        self.console_text.insert(tk.END, text)

    def dump_state(self, msg):
        print(f"[PC={self.PC}] {msg}")
        regs = " ".join(
            f"R{i}={self.reg[i]:3d}({self.reg[i]:08b})"
            for i in range(8)
        )
        sc = f"SC={self.SC:3d}({self.SC:08b})"
        flags = f"Z={self.Z}({self.Z:01b}) C={self.C}({self.C:01b})"

        print(f"   {regs} | {sc} | {flags}")

    # ---------------- RUN ------------------
    def run(self):
        self.start_console()
        count = 0

        while self.PC < 65536:
            op = self.memory[self.PC]
            # ==========================================================
            # Память
            # ==========================================================

            if op == 0b00000001:  # LDI reg imm8
                r = self.memory[self.PC + 1]
                imm8 = self.memory[self.PC + 2]
                self.reg[r] = imm8 & 0xFF
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"LDI: R{r} <- {imm8}({imm8:08b})")

            elif op == 0b00000010:  # LDI16
                hi = self.memory[self.PC + 1]
                lo = self.memory[self.PC + 2]
                imm_lo = self.memory[self.PC + 3]
                imm_hi = self.memory[self.PC + 4]
                self.reg[hi] = imm_hi & 0xFF
                self.reg[lo] = imm_lo & 0xFF
                self.PC = (self.PC + 5) & 0xFFFF
                imm16 = (imm_hi << 8) | imm_lo
                self.dump_state(f"LDI16 R{hi}R{lo} <-{imm16}({imm16:016b})")

            elif op == 0b00000011:  # MOV
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                self.reg[r1] = self.reg[r2] & 0xFF
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"MOV R{r1} <- R{r2}")

            elif op == 0b00000100:  # LDM r, addr16
                r = self.memory[self.PC + 1]
                addr_lo = self.memory[self.PC + 2]
                addr_hi = self.memory[self.PC + 3]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF
                val = self.memory[addr] & 0xFF
                self.reg[r] = val
                self.PC = (self.PC + 4) & 0xFFFF
                self.dump_state(
                    f"LDM R{r} <- mem[{addr_hi:02X}:{addr_lo:02X}] "
                    f"= {val}({val:08b})  addr={addr}({addr:016b})"
                )

            elif op == 0b00000101:  # STM addr16, r
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                r = self.memory[self.PC + 3]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF
                val = self.reg[r] & 0xFF
                self.memory[addr] = val
                self.PC = (self.PC + 4) & 0xFFFF
                self.dump_state(
                    f"STM mem[{addr_hi:02X}:{addr_lo:02X}] <- R{r} "
                    f"= {val}({val:08b})  addr={addr}({addr:016b})"
                )

            elif op == 0b00000110:  # LDR r, HI, LO
                r = self.memory[self.PC + 1]
                hi = self.memory[self.PC + 2]
                lo = self.memory[self.PC + 3]

                addr = ((self.reg[hi] << 8) | self.reg[lo]) & 0xFFFF
                val = self.memory[addr] & 0xFF

                self.reg[r] = val
                self.PC = (self.PC + 4) & 0xFFFF

                self.dump_state(
                    f"LDR R{r} <- mem[R{hi}:R{lo}] "
                    f"(addr={addr}({addr:016b})) = {val}({val:08b})"
                )

            elif op == 0b00000111:  # STR HI, LO, r
                hi = self.memory[self.PC + 1]
                lo = self.memory[self.PC + 2]
                r = self.memory[self.PC + 3]

                addr = ((self.reg[hi] << 8) | self.reg[lo]) & 0xFFFF
                val = self.reg[r] & 0xFF

                self.memory[addr] = val
                self.PC = (self.PC + 4) & 0xFFFF

                self.dump_state(
                    f"STR mem[R{hi}:R{lo}] (addr={addr}({addr:016b})) <- "
                    f"R{r} = {val}({val:08b})"
                )

            # ==========================================================
            # Арифметика
            # ==========================================================

            elif op == 0b00001000:  # ADD r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = self.reg[r1] + self.reg[r2]
                self.C = 1 if res > 0xFF else 0
                res &= 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"ADD R{r1}, R{r2}")

            elif op == 0b00001001:  # ADC r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = self.reg[r1] + self.reg[r2] + self.C
                self.C = 1 if res > 0xFF else 0
                res &= 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"ADC R{r1}, R{r2}")

            elif op == 0b00001010:  # SUB r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = self.reg[r1] - self.reg[r2]
                self.C = 1 if res < 0 else 0
                res &= 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"SUB R{r1}, R{r2}")

            elif op == 0b00001011:  # SBC r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = self.reg[r1] - self.reg[r2] - self.C
                self.C = 1 if res < 0 else 0
                res &= 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"SBC R{r1}, R{r2}")

            elif op == 0b00001100:  # INC r
                r = self.memory[self.PC + 1]
                res = self.reg[r] + 1
                self.C = 1 if res > 0xFF else 0
                res &= 0xFF
                self.reg[r] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"INC R{r}")

            elif op == 0b00001101:  # DEC r
                r = self.memory[self.PC + 1]
                res = self.reg[r] - 1
                self.C = 1 if res < 0 else 0
                res &= 0xFF
                self.reg[r] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"DEC R{r}")

            elif op == 0b00001110:  # CMP r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = self.reg[r1] - self.reg[r2]
                self.C = 1 if res < 0 else 0
                res &= 0xFF
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"CMP R{r1}, R{r2}")

            # ==========================================================
            # Логика
            # ==========================================================

            elif op == 0b00001111:  # AND r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = (self.reg[r1] & self.reg[r2]) & 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"AND R{r1}, R{r2}")

            elif op == 0b00010000:  # OR r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = (self.reg[r1] | self.reg[r2]) & 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"OR R{r1}, R{r2}")

            elif op == 0b00010001:  # XOR r1, r2
                r1 = self.memory[self.PC + 1]
                r2 = self.memory[self.PC + 2]
                res = (self.reg[r1] ^ self.reg[r2]) & 0xFF
                self.reg[r1] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(f"XOR R{r1}, R{r2}")

            elif op == 0b00010010:  # NOT r
                r = self.memory[self.PC + 1]
                res = (~self.reg[r]) & 0xFF
                self.reg[r] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"NOT R{r}")

            elif op == 0b00010011:  # SHL r
                r = self.memory[self.PC + 1]
                old = self.reg[r] & 0xFF
                self.C = (old >> 7) & 1
                res = (old << 1) & 0xFF
                self.reg[r] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"SHL R{r}")

            elif op == 0b00010100:  # SHR r
                r = self.memory[self.PC + 1]
                old = self.reg[r] & 0xFF
                self.C = old & 1
                res = (old >> 1) & 0xFF
                self.reg[r] = res
                self.Z = 1 if res == 0 else 0
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"SHR R{r}")

            # ==========================================================
            # Переходы
            # ==========================================================

            elif op == 0b00010101:  # JMP addr16
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF

                self.PC = addr
                self.dump_state(f"JMP {addr}({addr:016b})")

            elif op == 0b00010110:  # JZ addr16
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF
                if self.Z == 1:
                    self.PC = addr
                    self.dump_state(f"JZ TAKEN -> {addr}")
                else:
                    self.PC = (self.PC + 3) & 0xFFFF
                    self.dump_state("JZ NOT TAKEN")

            elif op == 0b00010111:  # JNZ addr16
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF

                if self.Z == 0:
                    self.PC = addr
                    self.dump_state(f"JNZ TAKEN -> {addr}")
                else:
                    self.PC = (self.PC + 3) & 0xFFFF
                    self.dump_state("JNZ NOT TAKEN")

            elif op == 0b00011000:  # JC addr16
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF

                if self.C == 1:
                    self.PC = addr
                    self.dump_state(f"JC TAKEN -> {addr}")
                else:
                    self.PC = (self.PC + 3) & 0xFFFF
                    self.dump_state("JC NOT TAKEN")

            elif op == 0b00011001:  # JNC addr16
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                addr = ((addr_hi << 8) | addr_lo) & 0xFFFF

                if self.C == 0:
                    self.PC = addr
                    self.dump_state(f"JNC TAKEN -> {addr}")
                else:
                    self.PC = (self.PC + 3) & 0xFFFF
                    self.dump_state("JNC NOT TAKEN")

            # ==========================================================
            # Стек
            # ==========================================================

            elif op == 0b00011010:  # PUSH r
                r = self.memory[self.PC + 1]
                val = self.reg[r] & 0xFF
                if self.SC <= self.STACK_START:
                    raise RuntimeError("Stack overflow")
                self.SC = (self.SC - 1) & 0xFFFF
                self.memory[self.SC] = val
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"PUSH R{r}={val}({val:08b})  SP={self.SC}({self.SC:016b})")

            elif op == 0b00011011:  # POP r
                r = self.memory[self.PC + 1]
                if self.SC >= self.STACK_END:
                    raise RuntimeError("Stack underflow")
                val = self.memory[self.SC] & 0xFF
                self.SC = (self.SC + 1) & 0xFFFF
                self.reg[r] = val
                self.PC = (self.PC + 2) & 0xFFFF
                self.dump_state(f"POP R{r}<-{val}({val:08b})  SP={self.SC}({self.SC:016b})")

            elif op == 0b00011100:  # PUSH16 HI, LO
                hi_r = self.memory[self.PC + 1]
                lo_r = self.memory[self.PC + 2]
                hi = self.reg[hi_r] & 0xFF
                lo = self.reg[lo_r] & 0xFF
                value16 = ((hi << 8) | lo) & 0xFFFF
                if self.SC <= self.STACK_START:
                    raise RuntimeError("Stack overflow")
                self.SC = (self.SC - 1) & 0xFFFF
                self.memory[self.SC] = hi
                if self.SC <= self.STACK_START:
                    raise RuntimeError("Stack overflow")
                self.SC = (self.SC - 1) & 0xFFFF
                self.memory[self.SC] = lo
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(
                    f"PUSH16 R{hi_r}:R{lo_r}={value16}({value16:016b})  SP={self.SC}({self.SC:016b})"
                )


            elif op == 0b00011101:  # POP16 HI, LO
                hi_r = self.memory[self.PC + 1]
                lo_r = self.memory[self.PC + 2]
                if self.SC >= self.STACK_END:
                    raise RuntimeError("Stack underflow")
                lo = self.memory[self.SC] & 0xFF
                self.SC = (self.SC + 1) & 0xFFFF
                if self.SC >= self.STACK_END:
                    raise RuntimeError("Stack underflow")
                hi = self.memory[self.SC] & 0xFF
                self.SC = (self.SC + 1) & 0xFFFF
                self.reg[hi_r] = hi
                self.reg[lo_r] = lo
                value16 = ((hi << 8) | lo) & 0xFFFF
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(
                    f"POP16 R{hi_r}:R{lo_r}<-{value16}({value16:016b})  SP={self.SC}({self.SC:016b})"
                )

            elif op == 0b00011110:  # CALL addr16
                addr_lo = self.memory[self.PC + 1]
                addr_hi = self.memory[self.PC + 2]
                target = ((addr_hi << 8) | addr_lo) & 0xFFFF
                ret_addr = (self.PC + 3) & 0xFFFF
                ret_hi = (ret_addr >> 8) & 0xFF
                ret_lo = ret_addr & 0xFF
                if self.SC <= self.STACK_START:
                    raise RuntimeError("Stack overflow")
                self.SC = (self.SC - 1) & 0xFFFF
                self.memory[self.SC] = ret_hi
                if self.SC <= self.STACK_START:
                    raise RuntimeError("Stack overflow")
                self.SC = (self.SC - 1) & 0xFFFF
                self.memory[self.SC] = ret_lo
                self.PC = target
                self.dump_state(
                    f"CALL {target}({target:016b})  push RET={ret_addr}({ret_addr:016b})  SP={self.SC}({self.SC:016b})"
                )

            elif op == 0b00011111:  # RET
                if self.SC >= self.STACK_END:
                    raise RuntimeError("Stack underflow")
                ret_lo = self.memory[self.SC] & 0xFF
                self.SC = (self.SC + 1) & 0xFFFF
                if self.SC >= self.STACK_END:
                    raise RuntimeError("Stack underflow")
                ret_hi = self.memory[self.SC] & 0xFF
                self.SC = (self.SC + 1) & 0xFFFF
                ret_addr = ((ret_hi << 8) | ret_lo) & 0xFFFF
                self.PC = ret_addr
                self.dump_state(f"RET -> {ret_addr}({ret_addr:016b})  SP={self.SC}({self.SC:016b})")

            # ==========================================================
            # I/O Ввод/Вывод
            # ==========================================================

            elif op == 0b00100000:  # IN r, port
                r = self.memory[self.PC + 1]
                port = self.memory[self.PC + 2]
                if port < 0 or port >= len(self.ports):
                    raise RuntimeError(f"Invalid port number: {port}")
                val = self.ports[port] & 0xFF
                self.reg[r] = val
                self.Z = 1 if val == 0 else 0
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(
                    f"IN R{r} <- PORT[{port}] = {val}({val:08b})"
                )

            elif op == 0b00100001:  # OUT port, r
                port = self.memory[self.PC + 1]
                r = self.memory[self.PC + 2]
                if port < 0 or port >= len(self.ports):
                    raise RuntimeError(f"Invalid port number: {port}")
                val = self.reg[r] & 0xFF
                self.ports[port] = val
                self.PC = (self.PC + 3) & 0xFFFF
                self.dump_state(
                    f"OUT PORT[{port}] <- R{r} = {val}({val:08b})"
                )


            # ==========================================================
            # Системные
            # ==========================================================
            elif op == 0b11111111:  # HALT
                self.dump_state(msg="HALT: Программа завершена")
                break

            else:
                print(f"[PC={self.PC}] Unknown opcode: {op:08b}")
                self.PC = (self.PC + 1) & 0xFFFF

            self.update_console()
            count += 1
            time.sleep(0.02)

        return count


cpu = CPU8Bit(
    [])
cpu.run()
