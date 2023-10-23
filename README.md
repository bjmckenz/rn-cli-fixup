# rn-cli-fixup
Initializing a project as of react-native 0.72.5 CLI does not guarantee happiness. This project promotes peace and love.

This is a script that you can run on a freshly-created ("npx react-native@latest init fooooo") that makes sure things are present and configured.

This does not remove the need for (react-native) doctor. That needs to be solid too.

If doctor is NOT green, this script may point the way to fixing those issues (all except "you don't have a device or simulator connected").

**It is safe and perhaps helpful to run it BEFORE running doctor.**

Download the script run it from the root of the project directory.

    $ npx react-native@latest init foobar
    $ cd foobar
    $ npx react-native doctor <--- if you like
    $ python somewhere/reactnative-setup.py
    ...Output: does things. leaves copy of messages in **reactnative-fixup.txt**
    $ npx react-native doctor <--- at least once, verify it is ALL GREEN
    $ npx react-native run-android

Issues and PRs welcome!

# **When it reports ERROR or FATAL**

Many of those errors require you to restart your shell / command prompt. If you are using VSCode's Terminal ***you must completely restart VSCode*** not just starting a new terminal. 
