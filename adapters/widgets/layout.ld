SECTIONS {
 .xml_helpers 0x33b00c : { *(.xml_helpers) }
 .xml_attrs 0x4156f8 : { *(.xml_attrs) *(.rodata*) }
 .xml_transform 0x33bd70 : { *(.xml_transform) *(.text*) }
 .xml_data 0x416a70 : { *(.xml_data) }
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
malloc = 0x649d10;
free = 0x6499f0;
outlined_save = 0x5e7230;
parse_continue = 0x5182ec;
