`timescale 1ns/1ps
module concurrent;
  reg clk = 0;
  reg req = 0;
  reg ack = 0;
  integer mode;
  always #5 clk = ~clk;
  // Single-cycle non-overlapped implication; deliberate negative case below.
  response: assert property (@(posedge clk) req |=> ack)
    else $fatal(1, "CONCURRENT_FAIL");
  initial begin
    if (!$value$plusargs("mode=%d", mode)) mode = 0;
    @(negedge clk); req = 1;
    @(negedge clk); req = 0; ack = (mode == 0);
    @(negedge clk); ack = 0;
    @(negedge clk); $display("PROBE_COMPLETE"); $finish;
  end
endmodule
