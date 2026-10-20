//======================================================================
// osd_layout.vh - latency_view panel layout (GENERATED, do not edit)
//   generator: model/gen_osd_layout.py
//   model    : model/latency_model.py
//   rows     : LAT / AGE / CAP fps / DSP fps / FRM + alarm nibble
//======================================================================
localparam integer OSD_COLS = 16;
localparam integer OSD_ROWS = 5;
localparam [639:0] OSD_TEMPLATE = 640'h4C415420202323232323234D5320202041474520202323232323234D53202020434150202020232323232346505320204453502020202323232323465053202046524D20232323232323232320452320;

localparam [6:0] OSD_FLD_LAT = 7'd5;  // row0 latency, 6 chars
localparam [6:0] OSD_FLD_AGE = 7'd21;  // row1 image age, 6 chars
localparam [6:0] OSD_FLD_CAP = 7'd38;  // row2 capture fps, 5 chars
localparam [6:0] OSD_FLD_DSP = 7'd54;  // row3 display fps, 5 chars
localparam [6:0] OSD_FLD_FRM = 7'd68;  // row4 frame counter, 8 chars
localparam [6:0] OSD_FLD_ERR = 7'd78;  // row4 alarm nibble, 1 char
localparam [6:0] OSD_LEN_MS = 7'd6;  // 
localparam [6:0] OSD_LEN_FPS = 7'd5;  // 
localparam [6:0] OSD_LEN_FRM = 7'd8;  // 

// row 0: "LAT  ######MS   "
// row 1: "AGE  ######MS   "
// row 2: "CAP   #####FPS  "
// row 3: "DSP   #####FPS  "
// row 4: "FRM ######## E# "
