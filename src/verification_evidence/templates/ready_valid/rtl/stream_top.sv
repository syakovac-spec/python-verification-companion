`timescale 1ns/1ps
// One-entry elastic buffer; no protocol-specific evidence logic in the DUT.
module stream_top #(parameter integer CORRUPT = 0);
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg tx_valid = 0, rx_ready = 0;
    reg [7:0] tx_data = 0;
    wire tx_ready, rx_valid;
    wire [7:0] rx_data;
    reg full = 0;
    reg [7:0] stored = 0;
    assign tx_ready = rst_n && (!full || rx_ready);
    assign rx_valid = rst_n && full;
    assign rx_data = stored ^ (CORRUPT ? 8'h01 : 8'h00);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin full <= 0; stored <= 0; end
        else if (tx_ready) begin
            full <= tx_valid;
            if (tx_valid) stored <= tx_data;
        end
    end
    // Test-only scheduling oracle for qualifying Python's pre-NBA sample.
    reg s_tx_valid, s_tx_ready, s_rx_valid, s_rx_ready, s_reset;
    reg [7:0] s_tx_data, s_rx_data;
    always @(posedge clk) begin
        s_reset <= rst_n;
        s_tx_valid <= tx_valid; s_tx_ready <= tx_ready; s_tx_data <= tx_data;
        s_rx_valid <= rx_valid; s_rx_ready <= rx_ready; s_rx_data <= rx_data;
    end
endmodule
