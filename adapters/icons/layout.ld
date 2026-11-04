SECTIONS {
 .text.helper 0x8f9120 : { *(.text.color) *(.text.blend) *(.text.distance) *(.text.finish) *(.text.OUTLINED_FUNCTION*) }
 .text 0x18c78c4 : { *(.text) *(.text.clear_content) }
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
