#include "runtime.cpp"
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <thread>

namespace {
std::mutex pause_mutex;
std::condition_variable pause_cv;
bool worker_inside=false,release_worker=false,callback_returned=false;
std::atomic<unsigned>guard_calls{0};
}
extern "C" bool hg_page_guard_ready(){
 if(guard_calls.fetch_add(1)==0){
  std::unique_lock<std::mutex>lock(pause_mutex);worker_inside=true;pause_cv.notify_all();
  pause_cv.wait(lock,[]{return release_worker;});
 }
 return false;
}
extern "C" int hg_apply_batch(const hg_patch*,size_t){assert(false);return -1;}
extern "C" int hg_install_native_hook(void*,void*,void**){assert(false);return -1;}
extern "C" void hg_install_resources(){assert(false);}
namespace hg {
bool image_layout(const char*,std::vector<Elf64_Phdr>&,uint64_t&,std::string&){assert(false);return false;}
bool resolve_program(const char*,uintptr_t,const Program&,Resolved&,bool){assert(false);return false;}
uintptr_t adapter_address(const Resolved&,uint32_t){assert(false);return 0;}
bool install_material_hooks(uintptr_t,const Program&,const Resolved&){assert(false);return false;}
bool install_backdrop_stream_hooks(){assert(false);return false;}
void queue_material_target(unsigned,unsigned,unsigned){assert(false);}
uintptr_t image_peer(uintptr_t,uintptr_t){assert(false);return 0;}
bool crop_export_image(uintptr_t,unsigned,unsigned,unsigned,unsigned){assert(false);return false;}
}
int main(){
 using namespace std::chrono_literals;
 Layout layout;Elf64_Phdr code{};code.p_type=PT_LOAD;code.p_flags=PF_R|PF_X;code.p_vaddr=0x1000;code.p_filesz=0x3000;layout.segments.push_back(code);
 std::vector<Mapping>split={{0x11000,0x12000,0,"/target.apk","r-xp"},{0x12000,0x13000,0,"/target.apk","--xp"},{0x13000,0x14000,0,"/target.apk","r-xp"}};
 assert(executable_mapping(0x10000,"/target.apk",layout,split));
 auto incomplete=split;incomplete.erase(incomplete.begin()+1);assert(!executable_mapping(0x10000,"/target.apk",layout,incomplete));
 incomplete=split;incomplete[1].permission="r--p";assert(!executable_mapping(0x10000,"/target.apk",layout,incomplete));
 incomplete=split;incomplete[1].path="/other.apk";assert(!executable_mapping(0x10000,"/target.apk",layout,incomplete));
 std::thread worker([]{assert(hg_runtime_tick("watch")==0);});
 {std::unique_lock<std::mutex>lock(pause_mutex);assert(pause_cv.wait_for(lock,2s,[]{return worker_inside;}));}
 // The callback represents a thread holding the loader lock. It must return
 // while the worker owns the runtime gate and is waiting on that loader.
 std::thread callback([]{
  assert(hg_runtime_tick("library-loaded")==0);
  std::lock_guard<std::mutex>lock(pause_mutex);callback_returned=true;pause_cv.notify_all();
 });
 {std::unique_lock<std::mutex>lock(pause_mutex);assert(pause_cv.wait_for(lock,2s,[]{return callback_returned;}));
  assert(guard_calls.load()==1);release_worker=true;pause_cv.notify_all();}
 callback.join();worker.join();
 assert(hg_runtime_tick("watch-retry")==0&&guard_calls.load()==2);
 puts("PASS split executable mappings retain ELF identity and complete coverage; loader callback never waits for the worker runtime gate and deferred work retries");
}
