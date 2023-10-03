# rn-cli-fixup
Initializing a project as of react-native 0.72.5 does not guarantee happiness. This project promotes peace and love.

This is a script that you can run on a freshly-created ("npx react-native@latest init fooooo") that makes sure things are present and configured.

This does not remove the need for (react-native) doctor. That needs to be solid too.

Download the script run it from the root of the project directory.

    $ npx react-native@latest init foobar
    $ cd foobar
    $ npx react-native doctor
    ...Output: All green - no errors!
    $ python somewhere/reactnative-setup.py

Issues and PRs welcome!

