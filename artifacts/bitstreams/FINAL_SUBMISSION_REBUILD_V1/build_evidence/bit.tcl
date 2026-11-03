source ./settings.cfg
import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
import_db {D:/p35check/FINAL_SUBMISSION_V1_1/in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display_pr.db}
commit_param -step bitgen
bitgen -bit {D:/p35check/FINAL_SUBMISSION_V1_1/dist/local_build/20261103_233153/camera_to_dsi_display.bit}
puts "BIT_COMPLETE"
exit
