module immediate;
  integer mode;
  reg value;
  initial begin
    if (!$value$plusargs("mode=%d", mode)) mode = 0;
    case (mode)
      0: value = 1'b1;
      1: value = 1'b0;
      2: value = 1'bx;
      3: value = 1'bz;
    endcase
    assert (value) $display("ASSERT_PASS");
      else $fatal(1, "ASSERT_FAIL mode=%0d", mode);
    $display("PROBE_COMPLETE");
    $finish;
  end
endmodule
