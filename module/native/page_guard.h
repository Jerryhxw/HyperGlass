#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
bool hg_page_guard_ready(void);
bool hg_protect_range(uintptr_t address, size_t size);
#ifdef __cplusplus
}
#endif
