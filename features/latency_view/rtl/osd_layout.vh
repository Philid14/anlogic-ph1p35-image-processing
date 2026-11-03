//======================================================================
// osd_layout.vh - latency_view panel layout (GENERATED, do not edit)
//   generator: model/gen_osd_layout.py
//   model    : model/latency_model.py
//   rows     : LAT / AGE / CAP fps / DSP fps / FRM + alarm nibble
//======================================================================
localparam integer OSD_COLS = 16;
localparam integer OSD_ROWS = 8;
localparam [1023:0] OSD_TEMPLATE = 1024'h4C415420202323232323234D5320202041564720202323232323234D5320202041474520202323232323234D53202020434150202023232323234650532020204453502020232323232346505320202046524D20232323232323232320452320434E5420232323232323232320202020414C4D20232023232323232323232020;

localparam [6:0] OSD_FLD_LAT = 7'd5;  // row0 latency, 6 chars
localparam [6:0] OSD_FLD_AVG = 7'd21;  // row1 average latency, 6 chars
localparam [6:0] OSD_FLD_AGE = 7'd37;  // row2 image age, 6 chars
localparam [6:0] OSD_FLD_CAP = 7'd53;  // row3 capture fps, 5 chars
localparam [6:0] OSD_FLD_DSP = 7'd69;  // row4 display fps, 5 chars
localparam [6:0] OSD_FLD_FRM = 7'd84;  // row5 frame counter, 8 chars
localparam [6:0] OSD_FLD_ERR = 7'd94;  // row5 alarm nibble, 1 char
localparam [6:0] OSD_FLD_CNT = 7'd100;  // row6 first display count, 8 chars
localparam [6:0] OSD_FLD_ALM_NIB = 7'd116;  // row7 alarm nibble, 1 char
localparam [6:0] OSD_FLD_ALM_TXT = 7'd118;  // row7 alarm word, 8 chars
localparam [6:0] OSD_LEN_MS = 7'd6;  // 
localparam [6:0] OSD_LEN_FPS = 7'd5;  // 
localparam [6:0] OSD_LEN_FRM = 7'd8;  // 
localparam [6:0] OSD_LEN_CNT = 7'd8;  // 
localparam [6:0] OSD_LEN_ALM = 7'd8;  // 

// row 0: "LAT  ######MS   "
// row 1: "AVG  ######MS   "
// row 2: "AGE  ######MS   "
// row 3: "CAP  #####FPS   "
// row 4: "DSP  #####FPS   "
// row 5: "FRM ######## E# "
// row 6: "CNT ########    "
// row 7: "ALM # ########  "
