`timescale 1ns/1ps
// Bounded two-request demonstration: transform data, return second ID first.
module tagged_top #(parameter integer CORRUPT=0, DROP=0);
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, tx_valid=0;
    reg [7:0] tx_data=0;
    reg [3:0] tx_id=0;
    reg [7:0] data0=0, data1=0;
    reg [3:0] id0=0, id1=0;
    reg [2:0] phase=0;
    wire tx_ready = rst_n && phase < 2;
    wire rx_valid = rst_n && (phase == 2 || (phase == 3 && !DROP));
    wire [3:0] rx_id = phase == 2 ? id1 : id0;
    wire [7:0] rx_data = (phase == 2 ? data1 : data0) ^ 8'h5a ^ (CORRUPT ? 8'h01 : 8'h00);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin phase<=0; data0<=0; data1<=0; id0<=0; id1<=0; end
        else if (tx_valid && tx_ready) begin
            if (phase == 0) begin data0<=tx_data; id0<=tx_id; end
            else begin data1<=tx_data; id1<=tx_id; end
            phase<=phase+1;
        end else if (phase == 2 || phase == 3) phase<=phase+1;
    end
    // Qualified acceptance snapshots; Python reads these after ReadOnly.
    reg s_reset, s_tx_valid, s_tx_ready, s_rx_valid;
    reg [7:0] s_tx_data, s_rx_data;
    reg [3:0] s_tx_id, s_rx_id;
    always @(posedge clk) begin
        s_reset<=rst_n;
        s_tx_valid<=tx_valid; s_tx_ready<=tx_ready; s_tx_data<=tx_data; s_tx_id<=tx_id;
        s_rx_valid<=rx_valid; s_rx_data<=rx_data; s_rx_id<=rx_id;
    end
endmodule
