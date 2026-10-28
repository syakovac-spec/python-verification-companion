`timescale 1ns/1ps
module apb_peripheral #(parameter integer WAIT_CYCLES = 0, MUTANT = 0) (
    input wire PCLK, PRESETn, PSEL, PENABLE, PWRITE,
    input wire [31:0] PADDR, PWDATA,
    output wire PREADY,
    output reg [31:0] PRDATA,
    output wire PSLVERR
);
    reg [31:0] scratch;
    reg sticky;
    reg stale_valid = 0;
    reg [31:0] stale_data = 0;
    localparam integer EFFECTIVE_WAIT = (MUTANT == 6 && WAIT_CYCLES > 0) ? WAIT_CYCLES-1 : WAIT_CYCLES;
    integer remaining;
    wire mapped = (PADDR == 0 || PADDR == 4 || PADDR == 8 || PADDR == 12);
    wire invalid = !mapped || (PWRITE && PADDR == 0);
    assign PREADY = PRESETn && PSEL && PENABLE && (remaining == 0);
    assign PSLVERR = PREADY && invalid && !(MUTANT == 4 && !mapped && PADDR[1:0] == 0);
    always @* begin
        case (PADDR)
            0: PRDATA = 32'h43564301;
            4: PRDATA = scratch;
            8: PRDATA = {31'b0, sticky};
            default: PRDATA = 0;
        endcase
    end
    always @(posedge PCLK or negedge PRESETn) begin
        if (!PRESETn) begin
            scratch <= 0;
            if (MUTANT == 5 && PSEL && PWRITE && PADDR == 4) begin
                stale_valid <= 1;
                stale_data <= PWDATA;
            end else stale_valid <= 0;
            sticky <= 0;
            remaining <= EFFECTIVE_WAIT;
        end else begin
            if (MUTANT == 5 && stale_valid) begin
                scratch <= stale_data;
                stale_valid <= 0;
            end
            if (!PSEL || !PENABLE) remaining <= EFFECTIVE_WAIT;
            else if (remaining > 0) remaining <= remaining - 1;
            if (PSEL && PENABLE && (PREADY || (MUTANT == 2 && remaining == 1)) && PWRITE && !invalid) begin
                case (PADDR)
                    4: scratch <= MUTANT == 1 ? (PWDATA & 32'h7fffffff) : PWDATA;
                    8: if (PWDATA[0] || MUTANT == 3) sticky <= 0;
                    12: if (PWDATA[0]) sticky <= 1;
                endcase
            end
        end
    end
endmodule
