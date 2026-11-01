module probe(input logic clk, reset, input logic [1:0] select,
             output logic [7:0] value);
  always_ff @(posedge clk) begin
    if (reset) value <= 0;
    else if (select == 0) value <= 8'h11;
    else if (select == 1) value <= 8'h22;
    else if (select == 2) value <= 8'h33;
    else value <= 8'h44;
  end
endmodule
