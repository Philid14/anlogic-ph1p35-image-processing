import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project {D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.prj} -noanalyze
import_db {D:/anlogic_formal_project/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display_pr.db}
analyze_clock -detail
exit
