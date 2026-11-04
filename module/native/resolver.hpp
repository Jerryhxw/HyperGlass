#pragma once
#include "elf_image.hpp"
#include "runtime.h"
#include <string>
#include <vector>
namespace hg {
struct Anchor {
 const char *owner;
 uint32_t source;
 uint8_t before,count,mode;
 int32_t dependency,qualifier;
 const char *callee;
 int32_t delta;
 const uint32_t *values,*masks;
};
struct Target { uint32_t source; int32_t anchor; uint8_t kind; };
struct Relocation { uint16_t offset; uint8_t kind; Target target; uint32_t original; };
struct Unit {
 const char *label;uint32_t source,size;int32_t anchor;uint8_t group,shadow;
 const uint8_t *bytes;const Relocation *relocations;uint16_t relocation_count;
};
struct Config { uint8_t slot,kind;int16_t subtract_slot;int32_t anchor;uint32_t source_tag; };
struct Constraint { uint32_t group;int32_t left,right;int32_t delta; };
struct Program {
 const char *image;const Anchor *anchors;size_t anchor_count;
 const Unit *units;size_t unit_count;
 const Config *config;size_t config_count;uint32_t config_source;
 const uint32_t *groups;size_t group_count;
 const Constraint *constraints;size_t constraint_count;
};
using Patch = hg_patch;
struct Resolved {
 std::vector<Patch> patches;
 uintptr_t shadow=0;size_t shadow_size=0;uint32_t ready=0;
 std::vector<uint32_t> addresses;
 std::vector<std::pair<uint32_t,uintptr_t>> adapter_pages;
 std::string diagnostic;
};
class Locator {
 public:
  Locator(const ElfImage &image,const Program &program):image_(image),program_(program),resolved_(program.anchor_count,-1),candidates_(program.anchor_count,0){}
  uint32_t resolve(size_t index);
  unsigned candidates(size_t index)const{return candidates_[index];}
 private:
  const ElfImage &image_;const Program &program_;
  std::vector<int64_t> resolved_;std::vector<unsigned>candidates_;
  void scan(const Anchor &anchor,uint64_t begin,uint64_t end,std::vector<uint32_t>&exact,std::vector<uint32_t>&elastic);
};
uintptr_t adapter_address(const Resolved &result,uint32_t source);
bool resolve_program(const char *path,uintptr_t live_base,const Program &program,Resolved &out,bool allocate_shadow=true);
}
