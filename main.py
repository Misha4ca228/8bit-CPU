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
            79: "^", 80: "#", 81: "[",
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
        self.all_opcode_count = 0

        print("=" * 50)
        print("Запуск 8-битного эмулятора")
        print(f"Размер программы: {len(self.program)} байт")
        print("=" * 50)

        while self.pc < len(self.memory):
            opcode = self.memory[self.pc]

            # ====================================================
            # 1️⃣ Работа с памятью и регистрами
            # ====================================================
            if opcode == 0b00000001:  # LDI
                r = self.memory[self.pc + 1]
                val = self.memory[self.pc + 2] & 0xFF
                self.registers[r] = val
                print(f"[PC={self.pc:03}] LDI: R{r} <- {val}")
                self.pc += 3

            elif opcode == 0b00000010:  # LD
                r = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                self.registers[r] = self.memory[addr] & 0xFF
                print(f"[PC={self.pc:03}] LD: R{r} <- MEM[{addr}] ({self.registers[r]})")
                self.pc += 3

            elif opcode == 0b00000011:  # ST
                r = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                self.memory[addr] = self.registers[r] & 0xFF
                print(f"[PC={self.pc:03}] ST: MEM[{addr}] <- R{r} ({self.registers[r]})")
                self.pc += 3

            elif opcode == 0b00000100:  # MOV
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] = self.registers[rB] & 0xFF
                print(f"[PC={self.pc:03}] MOV: R{rA} <- R{rB} ({self.registers[rB]})")
                self.pc += 3

            elif opcode == 0b00000101:  # STI
                r_src = self.memory[self.pc + 1]
                r_addr = self.memory[self.pc + 2]
                addr = self.registers[r_addr] & 0xFF
                self.memory[addr] = self.registers[r_src] & 0xFF
                print(f"[PC={self.pc:03}] STI: MEM[R{r_addr}] <- R{r_src}")
                self.pc += 3

            # ====================================================
            # 2️⃣ Арифметические операции
            # ====================================================
            elif opcode == 0b00001000:  # ADD
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] = (self.registers[rA] + self.registers[rB]) & 0xFF
                print(f"[PC={self.pc:03}] ADD: R{rA} = R{rA} + R{rB}")
                self.pc += 3

            elif opcode == 0b00001001:  # ADDI
                r = self.memory[self.pc + 1]
                val = self.memory[self.pc + 2]
                self.registers[r] = (self.registers[r] + val) & 0xFF
                print(f"[PC={self.pc:03}] ADDI: R{r} += {val}")
                self.pc += 3

            elif opcode == 0b00001010:  # SUB
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] = (self.registers[rA] - self.registers[rB]) & 0xFF
                print(f"[PC={self.pc:03}] SUB: R{rA} = R{rA} - R{rB}")
                self.pc += 3

            elif opcode == 0b00001011:  # SUBI
                r = self.memory[self.pc + 1]
                val = self.memory[self.pc + 2]
                self.registers[r] = (self.registers[r] - val) & 0xFF
                print(f"[PC={self.pc:03}] SUBI: R{r} -= {val}")
                self.pc += 3

            elif opcode == 0b00001100:  # MUL
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] = (self.registers[rA] * self.registers[rB]) & 0xFF
                print(f"[PC={self.pc:03}] MUL: R{rA} = R{rA} * R{rB}")
                self.pc += 3

            elif opcode == 0b00001101:  # DIV
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                divisor = self.registers[rB]
                if divisor == 0:
                    print(f"[PC={self.pc:03}] DIV: Деление на ноль! Пропуск.")
                else:
                    self.registers[rA] = (self.registers[rA] // divisor) & 0xFF
                    print(f"[PC={self.pc:03}] DIV: R{rA} = R{rA} // R{rB}")
                self.pc += 3

            elif opcode == 0b00001110:  # MOD
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                divisor = self.registers[rB]
                if divisor == 0:
                    print(f"[PC={self.pc:03}] MOD: Деление на ноль! Пропуск.")
                else:
                    self.registers[rA] = (self.registers[rA] % divisor) & 0xFF
                    print(f"[PC={self.pc:03}] MOD: R{rA} = R{rA} % R{rB}")
                self.pc += 3

            elif opcode == 0b00001111:  # INC
                r = self.memory[self.pc + 1]
                self.registers[r] = (self.registers[r] + 1) & 0xFF
                print(f"[PC={self.pc:03}] INC: R{r}++")
                self.pc += 2

            elif opcode == 0b00010000:  # DEC
                r = self.memory[self.pc + 1]
                self.registers[r] = (self.registers[r] - 1) & 0xFF
                print(f"[PC={self.pc:03}] DEC: R{r}--")
                self.pc += 2

            # ====================================================
            # 3️⃣ Логические операции
            # ====================================================
            elif opcode == 0b00010001:  # AND
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] &= self.registers[rB]
                print(f"[PC={self.pc:03}] AND: R{rA} = R{rA} AND R{rB}")
                self.pc += 3

            elif opcode == 0b00010010:  # OR
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] |= self.registers[rB]
                print(f"[PC={self.pc:03}] OR: R{rA} = R{rA} OR R{rB}")
                self.pc += 3

            elif opcode == 0b00010011:  # XOR
                rA = self.memory[self.pc + 1]
                rB = self.memory[self.pc + 2]
                self.registers[rA] ^= self.registers[rB]
                print(f"[PC={self.pc:03}] XOR: R{rA} = R{rA} XOR R{rB}")
                self.pc += 3

            elif opcode == 0b00010100:  # NOT
                r = self.memory[self.pc + 1]
                self.registers[r] = (~self.registers[r]) & 0xFF
                print(f"[PC={self.pc:03}] NOT: R{r} = NOT R{r}")
                self.pc += 2

            # ====================================================
            # 4️⃣ Условия и переходы
            # ====================================================
            elif opcode == 0b00011000:  # JMP
                addr = self.memory[self.pc + 1]
                print(f"[PC={self.pc:03}] JMP -> {addr}")
                self.pc = addr

            elif opcode == 0b00011001:  # JZ
                r = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                if self.registers[r] == 0:
                    print(f"[PC={self.pc:03}] JZ: R{r}=0 -> {addr}")
                    self.pc = addr
                else:
                    print(f"[PC={self.pc:03}] JZ: R{r}!=0 -> skip")
                    self.pc += 3

            elif opcode == 0b00011010:  # JNZ
                r = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                if self.registers[r] != 0:
                    print(f"[PC={self.pc:03}] JNZ: R{r}!=0 -> {addr}")
                    self.pc = addr
                else:
                    print(f"[PC={self.pc:03}] JNZ: R{r}=0 -> skip")
                    self.pc += 3

            # ====================================================
            # 5️⃣ Остановка
            # ====================================================
            elif opcode == 0b11111111:  # HALT
                print(f"[PC={self.pc:03}] HALT: Программа завершена.")
                break

            else:
                print(f"[PC={self.pc:03}] Неизвестная команда: {opcode}")
                self.pc += 1

            self.update_console()
            self.all_opcode_count = self.all_opcode_count + 1
            print("Регистры: ", end="")
            for i, val in enumerate(self.registers):
                print(f"R{i}={val} (0b{val:08b}) ", end="")
            print("\n")
        return self.all_opcode_count


# Пример программы
cpu = CPU8Bit(
    [
        0b00000001, 0b00000000, 0b00010001, 0b00000011, 0b00000000, 0b11110000, 0b00000001, 0b00000000, 0b00001110,
        0b00000011, 0b00000000, 0b11110001, 0b00000001, 0b00000000, 0b00010101, 0b00000011, 0b00000000, 0b11110010,
        0b00000001, 0b00000000, 0b00010101, 0b00000011, 0b00000000, 0b11110011, 0b00000001, 0b00000000, 0b00011000,
        0b00000011, 0b00000000, 0b11110100, 0b00000001, 0b00000000, 0b00000000, 0b00000011, 0b00000000, 0b11110101,
        0b00000001, 0b00000000, 0b00100000, 0b00000011, 0b00000000, 0b11110110, 0b00000001, 0b00000000, 0b00011000,
        0b00000011, 0b00000000, 0b11110111, 0b00000001, 0b00000000, 0b00011011, 0b00000011, 0b00000000, 0b11111000,
        0b00000001, 0b00000000, 0b00010101, 0b00000011, 0b00000000, 0b11111001, 0b00000001, 0b00000000, 0b00001101,
        0b00000011, 0b00000000, 0b11111010, 0b00000001, 0b00000000, 0b00000010, 0b00000011, 0b00000000, 0b11111011,
        0b11111111

    ])
start_time = time.time()
all_opcode = cpu.run()

end_time = time.time()

duration = end_time - start_time
ops_per_second = all_opcode / duration

print(f"Всего операций: {all_opcode}")
print(f"Время выполнения: {duration:.4f} секунд")
print(f"Операций в секунду: {ops_per_second:.2f}")
