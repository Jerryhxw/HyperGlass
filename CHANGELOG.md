# HyperGlass 1.0.1

使用 finall release 证书签名，支持覆盖升级。

- 修复从抽屉顶部最近应用打开 App 后，返回动画中目标图标消失的问题。
- 按当前桌面的推荐区来源标识选择图标控制器，保留普通列表与桌面的原有查找路径。
- 保持玻璃材质、动态图标、圆角裁剪和通知角标行为。
- 增加来源标签、用户 ID、Dart 调用帧及不同桌面布局的 ARM64 回归验证。

作用域为系统桌面，需要支持 HyperOS Runtime 的 LSPosed / Vector、Modern API 102 和 native API 2。覆盖安装后重新加载系统桌面生效。
