SECTIONS {
 .message 0x1722030 : { *(.message) }
 .selector 0x1811320 : { *(.selector) }
 .initialize 0x1811360 : { *(.initialize) }
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
message_return = 0x1722088;
barrier = 0x1b56978;
wrap_message = 0x1720f90;
boundary_build = 0x14ebf5c;
boundary_return = 0x14ebf80;

hg_capture_config = 0xb33600;
