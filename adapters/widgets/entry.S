.section .xml_transform,"ax"
.global parse_original
parse_original:
 stp x29,x30,[sp,#-96]!
 bl outlined_save
 b parse_continue
