.section .message,"ax"
.global message
message:
 stp x29,x30,[x15,#-16]!
 mov x29,x15
 sub x15,x15,#8
 stur x1,[x29,#-8]
 b call
post_store:
 ldur w2,[x0,#-1]
 ubfx w2,w2,#12,#20
#ifdef HG_ADAPTIVE
 adrp x16,hg_capture_config
 ldr w16,[x16,:lo12:hg_capture_config+20]
#else
 mov w16,#0x1e11
#endif
 cmp w2,w16
 b.ne done
 ldur w2,[x1,#0x23]
 tbnz w2,#4,need_message
 ldur w2,[x1,#0x1f]
 tbz w2,#4,need_message
done:
 mov x0,x22
 mov x15,x29
 ldp x29,x30,[x15],#16
 ret
need_message:
 b call
.org 0x50
call:
 ldur x1,[x29,#-8]
 bl choose_wrapper
 ldur x1,[x29,#-8]
 stur w0,[x1,#0xb]
 ldurb w16,[x1,#-1]
 ldurb w17,[x0,#-1]
 and x16,x17,x16,lsr #2
 tst x16,x28,lsr #32
 b.eq post_store
 bl barrier
 b post_store
.section .selector,"ax"
.global choose_wrapper
choose_wrapper:
 ldur w2,[x1,#0xb]
 add x2,x2,x28,lsl #32
 ldur w16,[x2,#-1]
 ubfx w16,w16,#12,#20
#ifdef HG_ADAPTIVE
 adrp x17,hg_capture_config
 ldr w17,[x17,:lo12:hg_capture_config+20]
#else
 mov w17,#0x1e11
#endif
 cmp w16,w17
#ifdef HG_ADAPTIVE
 b.ne selector_boundary
 b wrap_message
selector_boundary:
 b boundary_build
#else
 b.eq wrap_message
 b boundary_build
#endif
.section .initialize,"ax"
.global initialize
initialize:
 ldr x16,[x29,#8]
#ifdef HG_ADAPTIVE
 adrp x17,message_return
 add x17,x17,:lo12:message_return
#else
 adr x17,message_return
#endif
 cmp x16,x17
 b.ne replay
 ldr x16,[x29]
 ldur x16,[x16,#-8]
 ldur w16,[x16,#0x2b]
 add x16,x16,x28,lsl #32
#ifdef HG_ADAPTIVE
 adrp x17,hg_capture_config
 ldr w17,[x17,:lo12:hg_capture_config+24]
#else
 mov x17,#0x14b
#endif
 ldr w16,[x16,x17]
 stur w16,[x0,#7]
replay:
 stur w1,[x0,#0xb]
 b boundary_return
