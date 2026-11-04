package dev.hyperglass.lsposed;
import io.github.libxposed.api.XposedModule;
public final class ModuleMain extends XposedModule {
 @Override public void onModuleLoaded(ModuleLoadedParam param) {
  if ("com.miui.home".equals(param.getProcessName())) System.loadLibrary("hyperglass");
 }
}
