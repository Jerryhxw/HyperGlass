"""Pinned Android build tools for local macOS and Linux CI."""
import os
from pathlib import Path
import sys
SDK=Path(os.environ.get('ANDROID_HOME',Path.home()/'Library/Android/sdk'))
HOST='darwin-x86_64'if sys.platform=='darwin'else'linux-x86_64'
TOOLCHAIN=SDK/'ndk/29.0.14206865/toolchains/llvm/prebuilt'/HOST/'bin'
CLANG=TOOLCHAIN/'aarch64-linux-android35-clang'
BUILD_TOOLS=SDK/'build-tools/36.0.0'
ANDROID_JAR=SDK/'platforms'/os.environ.get('HYPERGLASS_ANDROID_PLATFORM','android-37.0')/'android.jar'
