import time
import tkinter as tk
from threading import Thread


class CPU8Bit:
    def __init__(self, program=None):
        self.program = program or []
        self.pc = 0
        self.registers = [0b00000000] * 10
        if len(self.program) > 256:
            raise ValueError("Ошибка: Программа больше 256 байт!")
        self.memory = self.program + [0b00000000] * (256 - len(self.program))

        self.console_window = None
        self.console_text = None
        self.running = False

        self.CHAR_MAP = {
            # --- Спецсимволы ---
            0: " ", 1: ":", 2: "!",
            3: "?", 4: "*", 5: "-",
            6: "+", 7: "/", 8: ",",
            9: ".",

            # --- Английские буквы (A–Z + W) ---
            10: "A", 11: "B", 12: "C",
            13: "D", 14: "E", 15: "F",
            16: "G", 17: "H", 18: "I",
            19: "J", 20: "K", 21: "L",
            22: "M", 23: "N", 24: "O",
            25: "P", 26: "Q", 27: "R",
            28: "S", 29: "T", 30: "U",
            31: "V", 32: "W", 33: "X",
            34: "Y", 35: "Z",

            # --- Русские буквы ---
            36: "Б", 37: "Г", 38: "Д",
            39: "Ж", 40: "З", 41: "И",
            42: "Л", 43: "П", 44: "Ф",
            45: "Ц", 46: "Ч", 47: "Ш",
            48: "Щ", 49: "Ъ", 50: "Ы",
            51: "Ь", 52: "Э", 53: "Ю",
            54: "Я",

            # --- Цифры ---
            55: "0", 56: "1", 57: "2",
            58: "3", 59: "4", 60: "5",
            61: "6", 62: "7", 63: "8",
            64: "9", 65: "=", 66: "(",
            67: ")", 68: "_", 69: "&",
            70: "@", 71: "%", 72: "$",
            73: "~", 74: "|", 75: "<",
            76: ">", 77: ";", 78: "✡",
            79:"^", 80: "#", 81: "[",
            82: "]", 83: "{", 84: "}",

        }

    # --- GUI консоль ---
    def start_console(self):
        def run_console():
            self.console_window = tk.Tk()

            self.console_window.title("8-bit Console Output")
            self.console_window.geometry("400x150")
            self.console_text = tk.Text(self.console_window, font=("Consolas", 30), bg="black", fg="lime")
            self.console_text.pack(fill="both", expand=True)
            self.console_window.mainloop()

        t = Thread(target=run_console, daemon=False)
        t.start()

    def update_console(self):
        if self.console_text:
            text = ''.join(self.CHAR_MAP[self.memory[-16 + i]] for i in range(16))
            self.console_text.delete("1.0", tk.END)
            self.console_text.insert(tk.END, text)

    def run(self):

        self.start_console()
        self.running = True
        self.pc = 0
        print("=" * 50)
        print("Запуск программы 8-битного эмулятора")
        print(f"Общий вес программы: {len(self.program)} Байт")
        if len(self.program) >= 256:
            raise ValueError("Ошибка: Программа больше 256 Байт!")
        print("=" * 50)

        while self.pc < len(self.memory):
            opcode = self.memory[self.pc]

            if opcode == 0b11111111:  # HALT
                print("=" * 50)
                print(f"[PC={self.pc:03}] Выполнение программы завершено")
                break

            # LDI
            if opcode == 0b00000001:
                reg = self.memory[self.pc + 1]
                val = self.memory[self.pc + 2] & 0xFF
                self.registers[reg] = val
                print(f"[PC={self.pc:03}] LDI: Загружено {val} (0b{val:08b}) в регистр R{reg}")
                self.pc += 3

            # LD
            elif opcode == 0b00000010:
                reg = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                val = self.memory[addr] & 0xFF
                self.registers[reg] = val
                print(f"[PC={self.pc:03}] LD: Загружено {val} (0b{val:08b}) из памяти[{addr}] в R{reg}")
                self.pc += 3

            # ST
            elif opcode == 0b00000011:
                reg = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                val = self.registers[reg] & 0xFF
                self.memory[addr] = val
                print(f"[PC={self.pc:03}] ST: Сохранено {val} (0b{val:08b}) из R{reg} в память[{addr}]")
                self.pc += 3

            # MOV
            elif opcode == 0b00000100:
                regA = self.memory[self.pc + 1]
                regB = self.memory[self.pc + 2]
                val = self.registers[regB] & 0xFF
                self.registers[regA] = val
                print(f"[PC={self.pc:03}] MOV: R{regA} <- R{regB} ({val})")
                self.pc += 3

            # ADD
            elif opcode == 0b00000101:
                regA = self.memory[self.pc + 1]
                regB = self.memory[self.pc + 2]
                result = (self.registers[regA] + self.registers[regB]) & 0xFF
                self.registers[regA] = result
                print(f"[PC={self.pc:03}] ADD: R{regA} = R{regA} + R{regB} = {result}")
                self.pc += 3

            # ADDI
            elif opcode == 0b00000110:
                reg = self.memory[self.pc + 1]
                val = self.memory[self.pc + 2]
                result = (self.registers[reg] + val) & 0xFF
                self.registers[reg] = result
                print(f"[PC={self.pc:03}] ADDI: R{reg} = R{reg} + {val} = {result}")
                self.pc += 3

            # SUB
            elif opcode == 0b00000111:
                regA = self.memory[self.pc + 1]
                regB = self.memory[self.pc + 2]
                result = (self.registers[regA] - self.registers[regB]) & 0xFF
                self.registers[regA] = result
                print(f"[PC={self.pc:03}] SUB: R{regA} = R{regA} - R{regB} = {result}")
                self.pc += 3

            # SUBI
            elif opcode == 0b00001000:
                reg = self.memory[self.pc + 1]
                val = self.memory[self.pc + 2]
                result = (self.registers[reg] - val) & 0xFF
                self.registers[reg] = result
                print(f"[PC={self.pc:03}] SUBI: R{reg} = R{reg} - {val} = {result}")
                self.pc += 3

            # DIV
            elif opcode == 0b00001001:
                regA = self.memory[self.pc + 1]
                regB = self.memory[self.pc + 2]
                divisor = self.registers[regB]
                if divisor == 0:
                    print(f"[PC={self.pc:03}] DIV: Деление на ноль! R{regB}=0 — пропуск операции")
                else:
                    result = (self.registers[regA] // divisor) & 0xFF
                    self.registers[regA] = result
                    print(f"[PC={self.pc:03}] DIV: R{regA} = R{regA} // R{regB} = {result}")
                self.pc += 3

            # MOD
            elif opcode == 0b00001010:
                regA = self.memory[self.pc + 1]
                regB = self.memory[self.pc + 2]
                divisor = self.registers[regB]
                if divisor == 0:
                    print(f"[PC={self.pc:03}] MOD: Деление на ноль! R{regB}=0 — пропуск операции")
                else:
                    result = (self.registers[regA] % divisor) & 0xFF
                    self.registers[regA] = result
                    print(f"[PC={self.pc:03}] MOD: R{regA} = R{regA} % R{regB} = {result}")
                self.pc += 3


            # INC
            elif opcode == 0b00001011:
                reg = self.memory[self.pc + 1]
                self.registers[reg] = (self.registers[reg] + 1) & 0xFF
                print(f"[PC={self.pc:03}] INC: R{reg} = R{reg} + 1 -> {self.registers[reg]}")
                self.pc += 2

            # DEC
            elif opcode == 0b00001100:
                reg = self.memory[self.pc + 1]
                self.registers[reg] = (self.registers[reg] - 1) & 0xFF
                print(f"[PC={self.pc:03}] DEC: R{reg} = R{reg} - 1 -> {self.registers[reg]}")
                self.pc += 2


            # JMP
            elif opcode == 0b00001101:
                addr = self.memory[self.pc + 1]
                print(f"[PC={self.pc:03}] JMP Переход на адрес {addr}")
                self.pc = addr

            # JZ
            elif opcode == 0b00001110:
                reg = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                if self.registers[reg] == 0:
                    print(f"[PC={self.pc:03}] JZ: R{reg} == 0 → Переход на {addr}")
                    self.pc = addr
                else:
                    print(f"[PC={self.pc:03}] JZ: R{reg} != 0 → Переход не выполнен")
                    self.pc += 3

            # JNZ
            elif opcode == 0b00001111:
                reg = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                if self.registers[reg] != 0:
                    print(f"[PC={self.pc:03}] JNZ: R{reg} != 0 → Переход на {addr}")
                    self.pc = addr
                else:
                    print(f"[PC={self.pc:03}] JNZ: R{reg} == 0 → Переход не выполнен")
                    self.pc += 3

            # STI
            elif opcode == 0b00010000:
                reg_src = self.memory[self.pc + 1]
                reg_addr = self.memory[self.pc + 2]
                addr = self.registers[reg_addr] & 0xFF
                val = self.registers[reg_src] & 0xFF
                self.memory[addr] = val
                print(f"[PC={self.pc:03}] STI: MEM[R{reg_addr}] <- R{reg_src} ({val})")
                self.pc += 3
            # MUL
            elif opcode == 0b00010001:
                regA = self.memory[self.pc + 1]
                regB = self.memory[self.pc + 2]
                result = (self.registers[regA] * self.registers[regB]) & 0xFF
                self.registers[regA] = result
                print(f"[PC={self.pc:03}] MUL: R{regA} = R{regA} * R{regB} = {result}")
                self.pc += 3

            else:
                self.pc += 1

            self.update_console()

            print("Регистры: ", end="")
            for i, val in enumerate(self.registers):
                print(f"R{i}={val} (0b{val:08b}) ", end="")
            print("\n")
            time.sleep(0.03)


# Пример программы
cpu = CPU8Bit(
    [
        0b00000001, 0b00000000, 0b01001110, 0b00000001, 0b00000001, 0b00000000, 0b00000001, 0b00000010, 0b00000101,
        0b00000011, 0b00000010, 0b11110001, 0b00000001, 0b00000100, 0b01100100, 0b00000001, 0b00000101, 0b00001010,
        0b00000001, 0b00000111, 0b01100100, 0b00000001, 0b00000111, 0b01100100, 0b00000001, 0b00000111, 0b01100100,
        0b00000001, 0b00000111, 0b01100100, 0b00000001, 0b00000111, 0b01100100, 0b00000011, 0b00000001, 0b11110000,
        0b00000100, 0b00000011, 0b00000001, 0b00001001, 0b00000011, 0b00000100, 0b00000110, 0b00000011, 0b00110111,
        0b00000011, 0b00000011, 0b11110010, 0b00000100, 0b00000011, 0b00000001, 0b00001010, 0b00000011, 0b00000100,
        0b00001001, 0b00000011, 0b00000101, 0b00000110, 0b00000011, 0b00110111, 0b00000011, 0b00000011, 0b11110011,
        0b00000100, 0b00000011, 0b00000001, 0b00001010, 0b00000011, 0b00000101, 0b00000110, 0b00000011, 0b00110111,
        0b00000011, 0b00000011, 0b11110100, 0b00001100, 0b00000000, 0b00001011, 0b00000001, 0b00001111, 0b00000000,
        0b00010010, 0b00001101, 0b01010100, 0b00000011, 0b00000001, 0b11110000, 0b11111111

    ])
cpu.run()
