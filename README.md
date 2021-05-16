# Fuzzing WebkitGTK++ with Favocado

This is an example how to to setup and fuzz webkitgtk++ by favocado in context-dependent mode.

#### Config

To do context-dependent fuzzing on webkitgtk, we need to setup a [Logger](https://github.com/favocado/favocado/blob/webkit-gtk/Generator/Core/Core_Config.js#L24), In this repo we used [window.confirm](https://github.com/favocado/favocado/blob/webkit-gtk/Generator/Run/fuzz.html#L23)
 as a Logger.

We [patched](https://github.com/favocado/webkitgtk-fuzz/blob/master/patches/patch-2.28.3.diff#L27) this `window.confirm` to write out the fuzzing code which is generated when fuzzing in context-dependent mode.



# Install
0. install docker
1. adjust your webkitgtk version in [build.sh](https://github.com/favocado/webkitgtk-fuzz/blob/master/build.sh#L8)
2. run  `./build.sh`
