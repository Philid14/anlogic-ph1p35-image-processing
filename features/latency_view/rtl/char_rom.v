//======================================================================
// char_rom.v - 95 x 8 bit character ROM for the latency/OSD text overlay
//
// GENERATED FILE - do not edit by hand.
//   generator: scripts/gen_char_rom.py
//   font     : work/models/third_party/font8x8_basic.h (public domain)
//   mirror   : work/models/font8x8_public_domain.py (Python golden model)
//
// char_code : ASCII 0x20..0x7E. Any other code selects a blank cell.
// row       : 0 = top scanline of the glyph cell.
// bits      : bit 0 = leftmost pixel, bit 7 = rightmost pixel.
//
// Eight row bytes are packed into one 64-bit constant per character and
// sliced with a variable part-select, so the ROM contains no divider and
// no per-row case duplication.
//======================================================================
`timescale 1ns/1ps

module char_rom (
    input  wire [6:0] char_code,  // ASCII 0x20..0x7E
    input  wire [2:0] row,        // 0 = top row
    output wire [7:0] bits        // bit 0 = leftmost pixel
);
    reg [63:0] glyph;

    always @(*) begin
        case (char_code)
            7'h20: glyph = 64'h0000000000000000;  // 'space'
            7'h21: glyph = 64'h183C3C1818001800;  // '!'
            7'h22: glyph = 64'h3636000000000000;  // '"'
            7'h23: glyph = 64'h36367F367F363600;  // '#'
            7'h24: glyph = 64'h0C3E031E301F0C00;  // '$'
            7'h25: glyph = 64'h006333180C666300;  // '%'
            7'h26: glyph = 64'h1C361C6E3B336E00;  // '&'
            7'h27: glyph = 64'h0606030000000000;  // '''
            7'h28: glyph = 64'h180C0606060C1800;  // '('
            7'h29: glyph = 64'h060C1818180C0600;  // ')'
            7'h2A: glyph = 64'h00663CFF3C660000;  // '*'
            7'h2B: glyph = 64'h000C0C3F0C0C0000;  // '+'
            7'h2C: glyph = 64'h00000000000C0C06;  // ','
            7'h2D: glyph = 64'h0000003F00000000;  // '-'
            7'h2E: glyph = 64'h00000000000C0C00;  // '.'
            7'h2F: glyph = 64'h6030180C06030100;  // '/'
            7'h30: glyph = 64'h3E63737B6F673E00;  // '0'
            7'h31: glyph = 64'h0C0E0C0C0C0C3F00;  // '1'
            7'h32: glyph = 64'h1E33301C06333F00;  // '2'
            7'h33: glyph = 64'h1E33301C30331E00;  // '3'
            7'h34: glyph = 64'h383C36337F307800;  // '4'
            7'h35: glyph = 64'h3F031F3030331E00;  // '5'
            7'h36: glyph = 64'h1C06031F33331E00;  // '6'
            7'h37: glyph = 64'h3F3330180C0C0C00;  // '7'
            7'h38: glyph = 64'h1E33331E33331E00;  // '8'
            7'h39: glyph = 64'h1E33333E30180E00;  // '9'
            7'h3A: glyph = 64'h000C0C00000C0C00;  // ':'
            7'h3B: glyph = 64'h000C0C00000C0C06;  // ';'
            7'h3C: glyph = 64'h180C0603060C1800;  // '<'
            7'h3D: glyph = 64'h00003F00003F0000;  // '='
            7'h3E: glyph = 64'h060C1830180C0600;  // '>'
            7'h3F: glyph = 64'h1E3330180C000C00;  // '?'
            7'h40: glyph = 64'h3E637B7B7B031E00;  // '@'
            7'h41: glyph = 64'h0C1E33333F333300;  // 'A'
            7'h42: glyph = 64'h3F66663E66663F00;  // 'B'
            7'h43: glyph = 64'h3C66030303663C00;  // 'C'
            7'h44: glyph = 64'h1F36666666361F00;  // 'D'
            7'h45: glyph = 64'h7F46161E16467F00;  // 'E'
            7'h46: glyph = 64'h7F46161E16060F00;  // 'F'
            7'h47: glyph = 64'h3C66030373667C00;  // 'G'
            7'h48: glyph = 64'h3333333F33333300;  // 'H'
            7'h49: glyph = 64'h1E0C0C0C0C0C1E00;  // 'I'
            7'h4A: glyph = 64'h7830303033331E00;  // 'J'
            7'h4B: glyph = 64'h6766361E36666700;  // 'K'
            7'h4C: glyph = 64'h0F06060646667F00;  // 'L'
            7'h4D: glyph = 64'h63777F7F6B636300;  // 'M'
            7'h4E: glyph = 64'h63676F7B73636300;  // 'N'
            7'h4F: glyph = 64'h1C36636363361C00;  // 'O'
            7'h50: glyph = 64'h3F66663E06060F00;  // 'P'
            7'h51: glyph = 64'h1E3333333B1E3800;  // 'Q'
            7'h52: glyph = 64'h3F66663E36666700;  // 'R'
            7'h53: glyph = 64'h1E33070E38331E00;  // 'S'
            7'h54: glyph = 64'h3F2D0C0C0C0C1E00;  // 'T'
            7'h55: glyph = 64'h3333333333333F00;  // 'U'
            7'h56: glyph = 64'h33333333331E0C00;  // 'V'
            7'h57: glyph = 64'h6363636B7F776300;  // 'W'
            7'h58: glyph = 64'h6363361C1C366300;  // 'X'
            7'h59: glyph = 64'h3333331E0C0C1E00;  // 'Y'
            7'h5A: glyph = 64'h7F6331184C667F00;  // 'Z'
            7'h5B: glyph = 64'h1E06060606061E00;  // '['
            7'h5C: glyph = 64'h03060C1830604000;  // '\'
            7'h5D: glyph = 64'h1E18181818181E00;  // ']'
            7'h5E: glyph = 64'h081C366300000000;  // '^'
            7'h5F: glyph = 64'h00000000000000FF;  // '_'
            7'h60: glyph = 64'h0C0C180000000000;  // '`'
            7'h61: glyph = 64'h00001E303E336E00;  // 'a'
            7'h62: glyph = 64'h0706063E66663B00;  // 'b'
            7'h63: glyph = 64'h00001E3303331E00;  // 'c'
            7'h64: glyph = 64'h3830303E33336E00;  // 'd'
            7'h65: glyph = 64'h00001E333F031E00;  // 'e'
            7'h66: glyph = 64'h1C36060F06060F00;  // 'f'
            7'h67: glyph = 64'h00006E33333E301F;  // 'g'
            7'h68: glyph = 64'h0706366E66666700;  // 'h'
            7'h69: glyph = 64'h0C000E0C0C0C1E00;  // 'i'
            7'h6A: glyph = 64'h300030303033331E;  // 'j'
            7'h6B: glyph = 64'h070666361E366700;  // 'k'
            7'h6C: glyph = 64'h0E0C0C0C0C0C1E00;  // 'l'
            7'h6D: glyph = 64'h0000337F7F6B6300;  // 'm'
            7'h6E: glyph = 64'h00001F3333333300;  // 'n'
            7'h6F: glyph = 64'h00001E3333331E00;  // 'o'
            7'h70: glyph = 64'h00003B66663E060F;  // 'p'
            7'h71: glyph = 64'h00006E33333E3078;  // 'q'
            7'h72: glyph = 64'h00003B6E66060F00;  // 'r'
            7'h73: glyph = 64'h00003E031E301F00;  // 's'
            7'h74: glyph = 64'h080C3E0C0C2C1800;  // 't'
            7'h75: glyph = 64'h0000333333336E00;  // 'u'
            7'h76: glyph = 64'h00003333331E0C00;  // 'v'
            7'h77: glyph = 64'h0000636B7F7F3600;  // 'w'
            7'h78: glyph = 64'h000063361C366300;  // 'x'
            7'h79: glyph = 64'h00003333333E301F;  // 'y'
            7'h7A: glyph = 64'h00003F190C263F00;  // 'z'
            7'h7B: glyph = 64'h380C0C070C0C3800;  // '{'
            7'h7C: glyph = 64'h1818180018181800;  // '|'
            7'h7D: glyph = 64'h070C0C380C0C0700;  // '}'
            7'h7E: glyph = 64'h6E3B000000000000;  // '~'
            default: glyph = 64'h0;  // blank for codes outside 0x20..0x7E
        endcase
    end

    assign bits = glyph[(7 - row) * 8 +: 8];

endmodule
