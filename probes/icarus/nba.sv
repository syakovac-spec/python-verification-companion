`timescale 1ns/1ps
module nba;
  reg clk = 0;
  reg [7:0] q = 0;
  reg [7:0] sampled_q = 0;
  always #5 clk = ~clk;
  always @(posedge clk) begin
    sampled_q <= q;
    q <= q + 1;
  end
endmodule
