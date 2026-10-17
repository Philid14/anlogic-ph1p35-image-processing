//======================================================================
// osd_layout.vh - latency OSD character buffer layout
//
// GENERATED FILE - do not edit by hand.
//   generator : scripts/gen_osd_layout.py
//   model     : work/models/latency_osd_model.py
//
// The template holds the static text of the panel; '#' field positions are
// rewritten every frame by latency_osd.v. Byte 0 of the buffer is the most
// significant byte of OSD_TEMPLATE.
//======================================================================
localparam integer OSD_COLS = 16;
localparam integer OSD_ROWS = 3;
localparam [383:0] OSD_BUF_BITS = 384'd48;
localparam [383:0] OSD_TEMPLATE = 384'h4C41542D46202323232323234D5320204C41542D50202323232323234D53202046524D20232323232323232320452320;

localparam [5:0] OSD_FLD_LAT_FRAME = 6'd6;  // row 0 latency field, 6 characters
localparam [5:0] OSD_FLD_LAT_PIPE = 6'd22;  // row 1 pipeline field, 6 characters
localparam [5:0] OSD_FLD_FRAME = 6'd36;  // row 2 frame counter, 8 characters
localparam [5:0] OSD_FLD_ERR = 6'd46;  // row 2 sticky error nibble, 1 character
localparam [5:0] OSD_FLD_LAT_LEN = 6'd6;  // latency field length
localparam [5:0] OSD_FLD_FRAME_LEN = 6'd8;  // frame field length
localparam [5:0] OSD_FLD_ERR_LEN = 6'd1;  // error field length

// template rows: "LAT-F ######MS  " "LAT-P ######MS  " "FRM ######## E# "
