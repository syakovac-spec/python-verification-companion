`timescale 1ns/1ps
// Test harness only. Fault inputs perturb the observed response, not DUT source.
module apb_top #(parameter integer WAIT_CYCLES = 0, MUTANT = 0);
    reg PCLK = 0, PRESETn = 0;
    reg PSEL = 0, PENABLE = 0, PWRITE = 0;
    reg [31:0] PADDR = 0, PWDATA = 0;
    reg fault_stall = 0, fault_read = 0, reset_at_edge = 0;
    wire dut_ready, dut_error;
    wire [31:0] dut_data;
    wire PREADY = dut_ready && !fault_stall;
    wire PSLVERR = dut_error;
    wire [31:0] PRDATA = dut_data ^ (fault_read ? 32'h1 : 32'h0);
    apb_peripheral #(.WAIT_CYCLES(WAIT_CYCLES), .MUTANT(MUTANT)) dut (
        .PCLK(PCLK), .PRESETn(PRESETn), .PSEL(PSEL), .PENABLE(PENABLE),
        .PWRITE(PWRITE), .PADDR(PADDR), .PWDATA(PWDATA),
        .PREADY(dut_ready), .PSLVERR(dut_error), .PRDATA(dut_data)
    );
    // Reset assignment precedes the clock assignment in one HDL process. This
    // defines the same-timestamp reset test without a Python/HDL drive race.
    always begin
        #5;
        if (!PCLK && reset_at_edge) PRESETn = 0;
        PCLK = ~PCLK;
    end
    // Passive snapshot of acceptance values, before sequential NBA updates.
    reg s_reset, s_sel, s_enable, s_write, s_ready, s_error;
    reg [31:0] s_addr, s_wdata, s_rdata;
    always @(posedge PCLK) begin
        s_reset <= PRESETn; s_sel <= PSEL; s_enable <= PENABLE;
        s_write <= PWRITE; s_ready <= PREADY; s_error <= PSLVERR;
        s_addr <= PADDR; s_wdata <= PWDATA; s_rdata <= PRDATA;
    end
    reg [2047:0] wavefile;
    initial begin
        if ($value$plusargs("wavefile=%s", wavefile)) begin
            $dumpfile(wavefile);
            $dumpvars(0, apb_top);
        end
    end
endmodule
