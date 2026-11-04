#pragma once
#include "resolver.hpp"
namespace hg {
void queue_material_target(unsigned kind,unsigned x,unsigned y);
bool install_material_hooks(uintptr_t base,const Program&program,const Resolved&result);
bool install_backdrop_stream_hooks();
bool crop_export_image(uintptr_t peer,unsigned x,unsigned y,unsigned width,unsigned height);
uintptr_t image_peer(uintptr_t image,uintptr_t heap);
}
