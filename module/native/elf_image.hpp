#pragma once
#include <elf.h>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
namespace hg {
struct Symbol { uint64_t value,size; std::string name; };
class ElfImage {
 public:
  bool load(const char *path,std::string &error);
  const uint8_t *at(uint64_t address,size_t size) const;
  std::vector<Symbol> named(const char *name) const;
  uint64_t symbol_end(const Symbol &symbol) const;
  const std::vector<Symbol> &symbols()const{return symbols_;}
  const std::vector<Elf64_Phdr> &segments()const{return segments_;}
  bool executable(uint64_t address,size_t size)const;
  uint64_t import_stub(const char *name) const;
  uint32_t word(uint64_t address)const;
  uint64_t span()const{return span_;}
 private:
  bool parse_symbols(const std::vector<uint8_t>&data,std::string &error);
  std::vector<uint8_t> data_;
  std::vector<Elf64_Phdr> segments_;
  std::vector<Symbol> symbols_;
  uint64_t span_=0;
};
bool image_layout(const char *path,std::vector<Elf64_Phdr>&segments,uint64_t &archive_offset,std::string &error);
uint32_t instruction_mask(uint32_t instruction,bool frames);
uint64_t branch_target(uint32_t instruction,uint64_t pc);
int64_t instruction_immediate(uint32_t instruction,bool *valid=nullptr);
}
