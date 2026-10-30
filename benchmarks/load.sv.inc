    // Synthetic scalable synchronous RTL activity, independent of traffic.
    // Every lane contributes to a visible checksum checked by Python.
    reg [31:0] load_state [0:LANES-1];
    reg [31:0] load_steps = 0;
    reg [31:0] load_checksum;
    integer j;
    always @(posedge clock) begin
        if (!reset_n) load_steps <= 0;
        else load_steps <= load_steps + 1;
        for (integer i = 0; i < LANES; i = i + 1) begin
            if (!reset_n) load_state[i] <= 0;
            else load_state[i] <= load_state[i] + i + 1;
        end
    end
    always @* begin
        load_checksum = 0;
        for (integer k = 0; k < LANES; k = k + 1)
            load_checksum = load_checksum + load_state[k];
    end
