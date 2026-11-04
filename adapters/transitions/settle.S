.text
.global settle_schedule
settle_schedule:
 mov x2,#0
 mov x0,x25
 add x1,sp,#0x100
 bl post_delayed_task
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop
