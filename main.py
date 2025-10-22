import time


class CPU8Bit:
    def __init__(self):
        self.pc = 1
        self.registers = [0b00000000] * 8
        self.memory = [0b00000000] * 256

    def run(self):
        self.pc = 0
        print("=" * 50)
        print("Запуск программы 8-битного эмулятора")
        print(f"Общий вес программы: {len(self.memory)} Байт")
        if len(self.memory) >= 256:
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

            # INC
            elif opcode == 0b00001001:
                reg = self.memory[self.pc + 1]
                self.registers[reg] = (self.registers[reg] + 1) & 0xFF
                print(f"[PC={self.pc:03}] INC: R{reg} = R{reg} + 1 -> {self.registers[reg]}")
                self.pc += 2

            # DEC
            elif opcode == 0b00001010:
                reg = self.memory[self.pc + 1]
                self.registers[reg] = (self.registers[reg] - 1) & 0xFF
                print(f"[PC={self.pc:03}] DEC: R{reg} = R{reg} - 1 -> {self.registers[reg]}")
                self.pc += 2

            # JMP
            elif opcode == 0b00001011:
                addr = self.memory[self.pc + 1]
                print(f"[PC={self.pc:03}] JMP Переход на адрес {addr}")
                self.pc = addr

            # JZ
            elif opcode == 0b00001100:
                reg = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                if self.registers[reg] == 0:
                    print(f"[PC={self.pc:03}] JZ: R{reg} == 0 → Переход на {addr}")
                    self.pc = addr
                else:
                    print(f"[PC={self.pc:03}] JZ: R{reg} != 0 → Переход не выполнен")
                    self.pc += 3

            # JNZ
            elif opcode == 0b00001101:
                reg = self.memory[self.pc + 1]
                addr = self.memory[self.pc + 2]
                if self.registers[reg] != 0:
                    print(f"[PC={self.pc:03}] JNZ: R{reg} != 0 → Переход на {addr}")
                    self.pc = addr
                else:
                    print(f"[PC={self.pc:03}] JNZ: R{reg} == 0 → Переход не выполнен")
                    self.pc += 3

            # OUT
            elif opcode == 0b00001110:
                reg = self.memory[self.pc + 1]
                value = self.registers[reg]
                print("#" * 50)
                print(f"# Вывод регистра R{reg}: {value} (0b{value:08b})" + " " * (50 - len(str(value)) - 35) + "#")
                print("#" * 50)
                self.pc += 2

            else:
                self.pc += 1

            print("Регистры: ", end="")
            for i, val in enumerate(self.registers):
                print(f"R{i}={val} (0b{val:08b}) ", end="")
            print("\n")
            time.sleep(0.2)


# Пример программы
cpu = CPU8Bit()
cpu.memory = [


]
cpu.run()
