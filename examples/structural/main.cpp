#include "Vprobe.h"
#include "verilated.h"
#include "verilated_cov.h"
#include <cstdlib>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    VerilatedContext context;
    Vprobe dut{&context};
    const int selections = std::atoi(argv[1]);
    if (selections < 1 || selections > 4) return 2;
    dut.clk = 0; dut.reset = 1; dut.select = 0; dut.eval();
    context.coveragep()->zero();
    dut.clk = 1; dut.eval();
    if (dut.value != 0) return 1;
    dut.reset = 0;
    for (int repeat = 0; repeat < 3; ++repeat) {
        for (int select = 0; select < selections; ++select) {
            dut.clk = 0; dut.select = select; dut.eval();
            dut.clk = 1; dut.eval();
            if (dut.value != 0x11 * (select + 1)) {
                std::cerr << "RTL output mismatch\n";
                return 1;
            }
        }
    }
    dut.final();
    context.coveragep()->write(argv[2]);
    return 0;
}
