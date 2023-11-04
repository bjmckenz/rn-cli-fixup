#!/env/python
import re
import json
import os
import subprocess
import shutil
import sys
import platform
import argparse
from urllib.request import urlopen
from inspect import currentframe
import json

script_version = "1.2"

# This script is intended to be run from the root of a React Native project directory.

### TO DO
# TODO: Handle Mac/Linux
# https://blog.logrocket.com/react-native-vector-icons-fonts-react-native-app-ui/
# https://stackoverflow.com/questions/69079963/how-to-set-compilejava-task-11-and-compilekotlin-task-1-8-jvm-target-com
# Add decorator for test type/mod
# Better version of how to fix. Perhaps for each test?
# ability to disable/ignore/skip each test?
# Clean up filenames, envvars, file contents    

# ENVIRONMENTY STUFF

running_on_windows = platform.system() == 'Windows'
print(running_on_windows)
shell_is_unixy = os.environ.get('SHELL') != None

# path separator in commands and paths
# FIXME: Should this include "or shell_shell_is_unixy"? diff between commands we run and report a nd what we write in files

path_separator = '\\' if running_on_windows else '/'
cmd_argument_separator = '/' if shell_is_unixy else '\\'
path_variable_separator = ';' if running_on_windows else ':'

# From command-line Arguments
config = {}

### vvvv BEGIN CUSTOMIZE vvvv ###

# Specify the path to bundletool.jar
bt_dir = 'C:{ps}Program Files{ps}'.format(ps=path_separator) if running_on_windows \
    else '{home}{ps}Library{ps}'.format(home=os.environ.get('HOME'),ps=path_separator)



keystore_file = "my-release-key"
store_password = "12345678"
key_alias = "my-key-alias"
key_password = "12345678"

distinguished_name = "CN=MyName, OU=MyOrgUnit, O=MyOrg, L=MyCity, ST=MyStateOrProvince, C=MyCountry"

### ^^^^ END CUSTOMIZE ^^^^ ###


### vvv NOT INTENDED TO BE CUSTOMIZED (but fix it if needed) vvv ###


bt_jar = 'bundletool-all-1.15.5.jar'
bt_loc = 'https://github.com/google/bundletool'

new_distribution_url = 'https://services.gradle.org/distributions/gradle-8.1-bin.zip'.format(
    ps=path_separator)

expected_java_version = "20.0.2"

jdk_download_path = "https://jdk.java.net/archive/"

signing_config_text = '''
    release {{
        storeFile file('{keystore_file}')
        storePassword '{store_password}'
        keyAlias '{key_alias}'
        keyPassword '{key_password}'
    }}
'''.format(
    keystore_file=keystore_file,
    store_password=store_password,
    key_alias=key_alias,
    key_password=key_password
)

gradle_properties_to_add = [
    'MYAPP_RELEASE_STORE_FILE={keystore_file}.jks'.format(
        keystore_file=keystore_file),
    'MYAPP_RELEASE_KEY_ALIAS={key_alias}'.format(key_alias=key_alias),
    'MYAPP_RELEASE_STORE_PASSWORD={store_password}'.format(
        store_password=store_password),
    'MYAPP_RELEASE_KEY_PASSWORD={key_password}'.format(
        key_password=key_password),
]


app_tsx_path = 'App.tsx'  # Expected for new projects
app_tsx_original_length = 2605

package_json_path = 'package.json'
# created to specify which apk to extract from apks file
universal_json_path = 'android{ps}universal.json'.format(ps=path_separator)
gradle_properties_path = 'android{ps}gradle.properties'.format(
    ps=path_separator)
build_gradle_path = 'android{ps}build.gradle'.format(ps=path_separator)
app_build_gradle_path = 'android{ps}app{ps}build.gradle'.format(ps=path_separator)
gradle_wrapper_properties_path = 'android{ps}gradle{ps}wrapper{ps}gradle-wrapper.properties'.format(
    ps=path_separator)

script_output_file = 'reactnative-fixup.txt'

kotlinVersion = "1.7.10"

dependencies_to_add = {
    "@react-native-masked-view/masked-view": "^0.3.0",
    "@react-navigation/drawer": "^6.6.4",
    "@react-navigation/native": "^6.1.8",
    "@react-navigation/native-stack": "^6.9.14",
    "@react-navigation/stack": "^6.3.18",
    "react-native-asset": "^2.1.1",
    "react": "18.2.0",
    "react-native": "0.72.6",
    "react-native-gesture-handler": "^2.13.2",
    "react-native-reanimated": "^3.5.4",
    "react-native-safe-area-context": "^4.7.2",
    "react-native-screens": "^3.25.0"
}

# Define the contents for universal.json
universal_json_contents = {
    "supportedAbis": ["armeabi-v7a", "arm64-v8a", "x86", "x86_64"],
    "supportedLocales": ["en", "fr", "de", "es", "it", "ja", "ko", "pt", "ru", "zh-rCN", "zh-rTW"],
    "screenDensity": 160,
    "sdkVersion": 21
}

release_section_text = """
    release {{
        signingConfig signingConfigs.release
        minifyEnabled enableProguardInReleaseBuilds
        proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
    }}
"""

prettier_rc = """
{
  "arrowParens": "avoid",
  "bracketSameLine": true,
  "bracketSpacing": false,
  "singleQuote": true,
  "trailingComma": "all"
}
"""

welcome_message = """
*******
This script MAY help you. You *should* have run "npx react-native doctor"
and fixed the issues first. This may help you with issues there if you can't figure out why doctor is failing.
      
BUT DO NOT try to run-android without BOTH "doctor" and this script reporting success.
      
Note that "WARN:" does not mean "Error", it means "be sure this is correct."

All output from this script will be logged to {of}
*********** 
      
""".format(of=script_output_file)

# This is the Hello-Worldiest of Hello-World apps.
app_js_path = 'App.js'  # we create this if we remove App.tsx
app_js_content = """
import React from 'react';
import {
  Text,
  SafeAreaView,
} from 'react-native';
import {SafeAreaProvider} from 'react-native-safe-area-context';

const App = () => {
  return (
    <SafeAreaProvider>
      <SafeAreaView>
        <Text>Hello World</Text>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

export default App;
"""

keystore_path = 'android/app/{keystore_file}.jks'.format(
    keystore_file=keystore_file
)

# Note - this is split into lines so we can split into command-line arguments later. One arg per line!
keystore_create_cmd = 'keytool \
  -genkeypair \
  -v \
  -storetype \
  PKCS12 \
  -keystore \
  {keystore_path} \
  -keyalg \
  RSA \
  -keysize \
  2048 \
  -validity \
  10000 \
  -alias \
  {key_alias} \
  -dname \
  {distinguished_name} \
  -storepass \
  {store_password} \
  -keypass \
  {key_password}'.format(
    keystore_path=keystore_path,
    store_password=store_password,
    key_alias=key_alias,
    key_password=key_password,
    distinguished_name=distinguished_name
)

build_apks_cmd = re.sub(r' +', ' ',
                        'java -jar "{bt_dir}{bt_jar}" \
    build-apks \
    --bundle=app{ps}build{ps}outputs{ps}bundle{ps}release{ps}app-release.aab \
    --output=app{ps}build{ps}outputs{ps}apk{ps}release{ps}app-release.apks \
    --mode=universal \
    --ks=..{ps}{keystore_path} \
    --ks-pass=pass:{store_password} \
    --ks-key-alias={key_alias} \
    --key-pass=pass:{key_password}'.format(
                            bt_dir=bt_dir,
                            bt_jar=bt_jar,
                            keystore_path=keystore_path,
                            store_password=store_password,
                            key_alias=key_alias,
                            key_password=key_password,
                            ps=cmd_argument_separator))

extract_apk_cmd = re.sub(r' +', ' ',
                         'java -jar "{bt_dir}{bt_jar}" \
  extract-apks \
    --apks=app{ps}build{ps}outputs{ps}apk{ps}release{ps}app-release.apks \
    --output-dir=app{ps}build{ps}outputs{ps}apk{ps}release{ps} \
    --device-spec=..{ps}{universal_json_path}'.format(
                             bt_dir=bt_dir,
                             bt_jar=bt_jar,
                             universal_json_path=universal_json_path,
                             ps=cmd_argument_separator
                         ))

post_config_steps = '''

$ npm install
$ npx react-native-asset

[Then...]
*sigh* 
[to run on simulator or connected device]

$ npx react-native run-android

[to build an APK]

$ npx react-native-asset

$ cd android && .{ps}gradlew build && .{ps}gradlew bundleRelease
$ {build_apks_cmd}

$ {extract_apk_cmd}

[to build on Mac for IOS]

*Before* your first build (or after you install a new NPM package) you must:

$ sudo gem update cocoapods --pre
$ npx pod-install
$ cd ios && pod update && cd ..

'''.format(
    extract_apk_cmd=extract_apk_cmd,
    build_apks_cmd=build_apks_cmd,
    ps=cmd_argument_separator
)

clean_repo_cmd = 'rnc clean --include "android,metro,npm,watchman,yarn"'

# ideal way to find
android_home = os.environ.get('ANDROID_HOME')
android_sdk_root = android_home if android_home else os.environ.get(
    'ANDROID_SDK_ROOT')

    
font_assets_dir = 'assets/fonts'
react_native_config_path = 'react-native.config.js'
react_native_config_contents = '''
module.exports = {
    assets: ['./assets/fonts'],
    dependencies: {
        'react-native-vector-icons': {
            platforms: {
                ios: null,
            },
        },
    },
};
'''

# tests command-line tools
cmdline_tools_path = 'cmdline-tools/latest/bin'
# tests NDK
ndk_version = '23.1.7779620'
# tests buildtools
build_tools_versions = ['30.0.3', '33.0.0', '34.0.0']
# platform-tools
adb_command = 'adb'
# tests tools dir
emu = 'emulator'

java_home = os.environ.get('JAVA_HOME')
osified_java_home_path = java_home.replace('\\', '\\\\') if java_home \
    else None


### ^^^ NOT INTENDED TO BE CUSTOMIZED ^^^ ###

# BEGIN UTILITIES

counts = {
    'fatal': 0,
    'warn': 0,
    'error': 0,
    'info': 0
}


def print_counts():
    print('*** ({ver}) Message type counts: {fatal} fatal, {warn} warn, {error} error, {info} info'.format(
          fatal=counts['fatal'],
          warn=counts['warn'],
          error=counts['error'],
          info=counts['info'],
          ver=script_version))


def report(type, message, include_line=True):
    counts[type.lower()] += 1

    if config['quiet'] and type.lower() == 'info':
        return

    caller_line = currentframe().f_back.f_lineno

    message += ' [{ln}]'.format(ln=caller_line) if include_line else ''
    print('{type}: {message}'.format(type=type.upper(), message=message))


#  https://stackoverflow.com/questions/319426/how-do-i-do-a-case-insensitive-string-comparison
def getfile_insensitive(path):
    directory, filename = os.path.split(path)
    directory, filename = (directory or '.'), filename.lower()
    for f in os.listdir(directory):
        newpath = os.path.join(directory, f)
        if os.path.exists(newpath) and f.lower() == filename:
            return newpath


def exists_insensitive(path):
    return getfile_insensitive(path) is not None


def paths_equal(path1, path2):
    if running_on_windows:
        return path1.lower() == path2.lower()
    return path1 == path2


def current_version_of_npm_package(pkg):
    url = 'https://unpkg.com/{pkg}/package.json'.format(pkg=pkg)
    response = urlopen(url)
    package_json = json.loads(response.read())
    return package_json['version']

def brew_recipe_installed(item):
    brew_output = subprocess.check_output(
            ["brew", "info", item], stderr=subprocess.STDOUT, text=True)

    return 'Not installed' not in brew_output

def read_gradle_file(file_path):
    try:
        with open(file_path, 'r') as gradle_config:
            content = gradle_config.read()
            objstack = [ [] ]
            for line in map(str.strip, content.splitlines()):
                if line == '}':
                    objstack.pop()
                elif len(line) and (line[0] == '*' or line.startswith('/*') or line.startswith('//')):
                    # hack for comments -- not really very good but hopefully adequate
                    objstack[len(objstack)-1].append({'line':line})
                elif line.endswith('{'):
                    sub = { 'key': line.split(' ')[0], 'contents':[] }
                    objstack[len(objstack)-1].append(sub)
                    objstack.append(sub['contents'])
                else:
                    objstack[len(objstack)-1].append({'line':line})
        return objstack[0]

    except Exception as e:
        report('error', f"{e}")

def gradle_config_as_str(contents,level=0):
    lines = []
    for element in contents:
        if 'line' in element:
            lines.append(('    '* level + element['line']).rstrip())
        else:
            lines.append(('    '*level + element['key'] + ' {').rstrip() )
            lines.append(gradle_config_as_str(element['contents'],level+1))
            lines.append('    '*level + '}')

    return '\n'.join(lines) + ('\n' if level==0 else '')

# Logger Class tees all output to output file


class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open(script_output_file, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.log.flush()


def set_up_config():
    parser = argparse.ArgumentParser(description="React-Native CLI Fixer-Upper",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-f", "--force", action="store_true",
                        help="continue even if after FATAL error")
    parser.add_argument("-q", "--quiet", action='store_true',
                        default=False, help="Shhh! No INFO messages")
    config = vars(parser.parse_args())
    return config


# BEGIN TESTS

def is_npm_installed():
    if shutil.which('npx') != None:
        report('info', 'Found npm.')
        return True

    report('fatal', 'Node.js is not installed (or is not in your PATH).')
    return False


def is_project_under_git():
    if os.path.exists('.git'):
        report('info', 'Project is git-controlled.')
        return True

    report('fatal', 'This project is NOT under git management (!)')
    report('info', 'do "git init", "git add ." and "git commit -m\'Initial commit\'"')
    return False


def is_npm_project():
    if exists_insensitive(package_json_path):
        report('info', 'We are in an NPM project.')
        return True
    report('fatal', 'package.json does not exist. Run this from an initialized project directory.')
    return False


def is_react_native_project():
    if exists_insensitive("android"):
        report('info', 'We are really in a React-native project.')
        return True
    report('fatal', '"android" does not exist. This does not appear to be a React-Native project dir.')
    return False


def is_react_native_cli_project():
    with open(package_json_path, 'r') as package_json_file:
        package_json_data = json.load(package_json_file)
        dependencies = package_json_data.get("dependencies", {})
        if dependencies.get("expo", None) == None:
            report('info', 'Confirmed: this is a CLI project.')
            return True
        report('fatal', 'expo is a dependency. This appears to be an expo project, not a React-Native CLI project dir.')
        return False

def is_homebrew_installed():
    if running_on_windows:
        report('info','(homebrew is not required on Windows)');
        return True

    if shutil.which('brew') != None:
        report('info','brew exists.');
        return True
    
    report('fatal','Brew is necessary for Mac development but is not installed.')
    report('info','Install it as shown at https://brew.sh/')
    return False

def is_not_formerly_expo_project():
    with open(package_json_path, 'r') as package_json_file:
        package_json_data = json.load(package_json_file)
        dependencies = package_json_data.get("dependencies", {})
        if dependencies.get("expo-splash-screen", None) == None:
            report('info', 'Confirmed: this is not an expo rebuild/exported project.')
            return True
        report('fatal', 'expo-splash-screen is a dependency. This appears to be an exported (prebuild) expo project, not a true CLI project.')
        return False


def is_cocoapods_present():
    if running_on_windows:
        report('info','(Cocoapods is not required on Windows.)')
        return True
    
    if brew_recipe_installed('cocoapods'):
        report('info', 'Found cocoapods.')
        return True
    
    report('fatal', 'cocoapods not found.')
    report('info','Install it via: brew install cocoapods')
    
    return False

def is_xcode_selected():
    if running_on_windows:
        report('info','(xcode-select is not required on Windows.)')
        return True
    
    xcode_sel_output = subprocess.check_output(
            ["xcode-select", "--print-path"], stderr=subprocess.STDOUT, text=True)

    if xcode_sel_output and '/' in xcode_sel_output:
        report('info','Xcode has been selected.')
        return True

    report('fatal', 'It does not appear that Xcode is selected.')
    report('info','Select it via: sudo xcode-select -s /Applications/Xcode.app')
    
    return False

def is_watchman_present():
    if running_on_windows:
        report('info','(Watchman is not required on Windows.)')
        return True
    
    if shutil.which('watchman'):
        report('info', 'Found watchman.')
        return True
    
    report('fatal', 'watchman command not found. Set it in your path).')
    report('info','It is easiest to do: brew install watchman (and make sure /opt/homebrew/bin is in your PATH)')
    
    return False

def is_ios_deploy_present():
    if running_on_windows:
        report('info','(ios-deploy is not required on Windows.)')
        return True
    
    if shutil.which('ios-deploy'):
        report('info', 'Found ios-deploy.')
        return True
    
    report('fatal', 'ios-deploy command not found. Set it in your path).')
    report('info','It is easiest to do: brew install ios-deploy (and make sure /opt/homebrew/bin is in your PATH)')
    
    return False


def is_adb_present():
    if shutil.which(adb_command):
        report('info', 'Found adb.')
        return True
    
    report('fatal', 'adb command not found. Set it in your path (install platform-tools if needed).')
    if not running_on_windows:
        report('info','On Mac, it is easiest to do: brew install android-platform-tools (and make sure /opt/homebrew/bin is in your PATH)')
    return False

def is_keytool_present():
    if shutil.which('keytool') != None:
        report('info', 'keytool is in path.')
        return True

    report('fatal', 'keytool command not found. Set it in your path.')
    report('info', 'This is usually in {jdk}{ps}bin'.format(
        jdk=java_home, ps=path_separator))
    return True


def is_emulator_installed():
    return shutil.which(emu) != None


def check_for_emulator():
    if is_emulator_installed():
        report('info', 'Found emulator.')
        return True

    report('warn', 'Emulator not found. Did you intend to install it?')
    return False


def is_bundletool_installed():
    if not os.path.exists(bt_dir):
        report('fatal', 'Expected location of bundletool ({bt_dir}) does not exist.. Please specify the correct path to it or create it.'.format(
            bt_dir=bt_dir
        ))
        return False

    report('info','bundletool destination folder of {bt_dir} exists.'.format(bt_dir=bt_dir))
    
    if exists_insensitive(bt_dir+bt_jar):
        report('info', 'Found current version of bundletool.')
        return True

    report('fatal', 'Current version of bundletool.jar does not exist. Please specify the correct path to it.')
    report('info', 'The current (known) version is {bt_jar}'.format(bt_jar=bt_jar))
    report('info', 'Download it from {bt_loc}'.format(bt_loc=bt_loc))
    report('info', 'And copy it to {bt_dir}'.format(bt_dir=bt_dir))
    return False


def is_java_in_path():
    if shutil.which('java') != None:
        report('info', 'java is in your path.')
        return True

    report('fatal', 'java is not in your path. Set it in your environment.')
    report('info', 'If needed, download and install JDK\n\n     {jv}\n\nfrom\n\n     {jdp}\n\nand make sure it is in your path, and that JAVA_HOME is set.'.format(
        jv=expected_java_version, jdp=jdk_download_path))
    if not running_on_windows:
        report('warn','on Mac, JAVA_HOME is not the location of the JDK, but the /Contents/Home directory under it.')

    return False


def is_java_home_valid():
    if not java_home:
        report('fatal', 'JAVA_HOME is not defined. Set it in your environment.')
        report('info',
               'If needed, download and install JDK\n\n     {jv}\n\nfrom\n\n     {jdp}\n\nand make sure it is in your path, and that JAVA_HOME is set in environment variables.'.format(
                   jv=expected_java_version, jdp=jdk_download_path))
        return False

    report('info', 'JAVA_HOME is set to {jhp}'.format(
        jhp=java_home))

    if os.path.exists(java_home):
        report('info', 'JAVA_HOME points to an existing directory.')
        return True

    report('fatal', 'JAVA_HOME set, but does not point to an existing directory.')
    return False


def is_java_from_path_from_java_home():
    # Java under the jdk dir
    java_executable_location = shutil.which('java')

    if java_executable_location.startswith(java_home):
        report('info', 'java executable location matches up with JAVA_HOME.')
        return True

    report('fatal', 'java executable location does not match up with JAVA_HOME. Fix JAVA_HOME in your environment.')
    return False


def are_paths_valid():
    existing_path = os.environ.get('PATH').split(path_variable_separator)
    found_platform_tools = False
    found_tools = False
    path_is_good = True

    for p in existing_path:
        lcp = p.lower()
        if paths_equal(p, os.path.join(android_sdk_root, 'platform-tools')):
            found_platform_tools = True
        elif paths_equal(p, os.path.join(android_sdk_root, 'tools')):
            found_tools = True

        if found_platform_tools and found_tools:
            break

    if not found_platform_tools:
        report('fatal', 'Ensure that {android_sdk_root}{ps}platform-tools is at the top of your {emphasis}path.'.
               format(android_sdk_root=android_sdk_root,
                      ps=path_separator,
                      emphasis='SYSTEM ' if running_on_windows else ''))
        path_is_good = False

    if not found_tools:
        report('fatal', 'Ensure that {android_sdk_root}{ps}tools is at the top of your {emphasis}path.'.
               format(android_sdk_root=android_sdk_root,
                      ps=path_separator,
                      emphasis='SYSTEM ' if running_on_windows else ''))
        path_is_good = False

    if path_is_good:
        report('info', 'SDK and JDK paths appear to be good.')

    return path_is_good


def is_correct_version_of_java_installed():
    try:
        # Run the "java -version" command and capture the output
        java_version_output = subprocess.check_output(
            ["java", "-version"], stderr=subprocess.STDOUT, text=True)

        # Check if the output contains "java version" followed by "20" (exact match)
        match = re.search(r'"([\d.]+)"', java_version_output)
        if not match:
            return False
        installed_version = match.group()

        report('info', 'Detected version {iv} of Java.'.format(
            iv=installed_version))

        if expected_java_version in installed_version:
            report('info', "Java version is correct.")
            return True

    except subprocess.CalledProcessError:
        # The "java" command returned a non-zero exit status, indicating Java is not installed or not recognized.
        pass

    report('error', 'Go download and install JDK {jv}, and make sure it is in your path.'.format(
        jv=expected_java_version))

    report('info', 'Download link: {jdk_download_path}'.format(
        jdk_download_path=jdk_download_path))
    return False


def compare_expected_current_version_of_npm_packages_to_latest_available():
    report('info', "Checking [newest published] npm package versions...")
    any_changes = False
    for p in dependencies_to_add.keys():
        compare_to = current_version_of_npm_package(p)
        if dependencies_to_add[p][0] == '^':
            compare_to = '^' + compare_to

        if compare_to != dependencies_to_add[p]:
            report('warn', 'Expecting version {v} of {p} but found {v2}'.format(
                v=dependencies_to_add[p], p=p, v2=compare_to))
            any_changes = True

        # print(p,' ',current_version_of_npm_package(p))

    if any_changes:
        report('info', "(Tell BJM or write an issue against this script on GitHub)")

    report('info', "...Done checking npm package versions.")


def is_android_sdk_installed():
    if not android_sdk_root:
        report('fatal', 'ANDROID_HOME and ANDROID_SDK_ROOT are not defined. Set at least one in your environment.')
        report('info', "This may indicate you haven't downloaded the ANDROID SDK yet.")
        report(
            'info', 'Download the Android SDK from https://developer.android.com/studio')
        return False

    report('info', 'Environment var(s) point to an Android SDK location {asdk}.'.format(
        asdk=android_sdk_root))

    if exists_insensitive(android_sdk_root):
        report('info', 'Android SDK appears to exist.')
        return True

    report('fatal', 'ANDROID_SDK_ROOT variable is set but directory does not exist. Set it CORRECTLY in your environment.')
    return False


def are_command_line_tools_in_path():
    if exists_insensitive(os.path.join(android_sdk_root, cmdline_tools_path)):
        report('info', 'Command-line tools are in path.')
        return True
    report('fatal', 'Command-line tools (latest) are not installed in Android SDK.')
    return False


def is_correct_ndk_installed():
    try:
        if exists_insensitive(os.path.join(android_sdk_root, 'ndk', ndk_version)):
            report('info', 'Correct NDK is installed.')
            return True
    except :
        pass
    
    report('fatal', 'Android SDK NDK version {ndk_version} not installed.'.format(
        ndk_version=ndk_version))
    return False


def are_all_build_tools_versions_present():
    missing = 0
    for btv in build_tools_versions:
        if exists_insensitive(os.path.join(android_sdk_root, 'build-tools', btv)):
            report(
                'info', 'Android SDK build-tools version {btv} exists.'.format(btv=btv))
            continue
        report(
            'fatal', 'Android SDK build-tools version {btv} not installed.'.format(btv=btv))
        missing += 1

    if missing == 0:
        report('info', '(All build-tools versions exist)')
        return True

    report('fatal', '{count} versions of build tools are not installed.'.format(
        count=missing))
    return False

def is_mac_java_version_set():
    if running_on_windows:
        report('info','(JAVA_VERSION is not needed for Windows)')
        return True
    
    if os.environ.get('JAVA_VERSION') == expected_java_version:
        report('info','JAVA_VERSION is set correctly.')
        return True

    report('FATAL','Environment var JAVA_VERSION must be set to {jv} (probably in ~/.zshrc)'.format(jv=expected_java_version))
    return False

# BEGIN MODIFICATIONS

def add_kotlin_version_to_build_gradle(file_path):
    try:
        bg = read_gradle_file(file_path)

        # Find buildscript.ext, ensure there is a kotlinVersion
        # and that it has the correct version

        buildscript = list(filter(lambda x: 'key' in x and x['key'] == 'buildscript', bg))[0]
        ext = list(filter(lambda x: 'key' in x and x['key'] == 'ext', buildscript['contents']))[0]

        kvs = list(filter(lambda x: 'line' in x and x['line'].startswith('kotlinVersion'), ext['contents']))
        if len(kvs) and 'line' in kvs[0] and kotlinVersion not in kvs[0]['line']:
            report('warn', "build.gradle has unexpected "+kvs[0]['line'])

        ext['contents'] = list(filter(lambda x: 'line' not in x or not x['line'].startswith('kotlinVersion'), ext['contents']))
        ext['contents'].append({'line':'kotlinVersion = "{kv}"'.format(kv=kotlinVersion)})

        with open(file_path, 'w') as gradle_file:
            gradle_file.write(gradle_config_as_str(bg))

        report('info', "build.gradle file updated successfully with kotlinVersion.")
    except Exception as e:
        report('error', f"{e}")


def add_signing_config_to_app_build_gradle(file_path):
    try:
        with open(file_path, 'r') as app_build_gradle_file:
            build_gradle_content = app_build_gradle_file.read()

            # Check if the signingConfigs section already exists
            if 'signingConfigs {' in build_gradle_content:
                # If it exists, append the signing_config_text to it
                modified_content = re.sub(
                    r'(signingConfigs \{[^\}]*\})', r'\1' + signing_config_text, build_gradle_content, flags=re.DOTALL)
            else:
                # If it doesn't exist, add the entire signingConfig section
                modified_content = re.sub(
                    r'(buildTypes \{[^\}]*\})', r'signingConfigs {\n' + signing_config_text + r'\1', build_gradle_content, flags=re.DOTALL)

        # Write the modified content back to the file
        with open(file_path, 'w') as app_build_gradle_file:
            app_build_gradle_file.write(modified_content)

        report('info', "app/build.gradle file updated successfully with signingConfigs.")
    except Exception as e:
        report('error', f"{e}")


def add_keys_to_gradle_properties(properties_file_path):
    try:
        with open(properties_file_path, 'r') as properties_file:
            properties_content = properties_file.read()

            # Check if each property already exists in the file
            for prop in gradle_properties_to_add:
                if prop not in properties_content:
                    properties_content += f"{prop}\n"

        # Write the modified content back to the file
        with open(properties_file_path, 'w') as properties_file:
            properties_file.write(properties_content)

        report('info', "gradle.properties file updated successfully.")
    except Exception as e:
        report('error', f"{e}")


def modify_gradle_properties(gradle_properties_path):
    try:
        with open(gradle_properties_path, 'r') as gradle_properties_file:
            gradle_properties_content = gradle_properties_file.read()

            # Update the release section text
            gradle_properties_content = re.sub(
                r'(\s*release\s*\{[^\}]*\})',
                release_section_text,
                gradle_properties_content,
                flags=re.DOTALL
            )

        # Write the modified content back to the file
        with open(gradle_properties_path, 'w') as gradle_properties_file:
            gradle_properties_file.write(gradle_properties_content)

        report('info', "gradle.properties file updated successfully.")
    except Exception as e:
        report('error', f"{e}")


def modify_gradle_wrapper_distribution_url(prop_path, new_distribution_url):
    try:
        with open(prop_path, 'r') as wrapper_properties_file:
            wrapper_properties_content = wrapper_properties_file.readlines()

        for i, line in enumerate(wrapper_properties_content):
            if line.startswith("distributionUrl="):
                wrapper_properties_content[i] = f"distributionUrl={new_distribution_url}\n"
                break

        with open(prop_path, 'w') as wrapper_properties_file:
            wrapper_properties_file.writelines(wrapper_properties_content)

        report('info', "Gradle wrapper distributionUrl updated successfully.")
    except Exception as e:
        report('error', f"{e}")


def add_gradle_java_home(gradle_properties_path, actual_java_home_path):
    try:
        with open(gradle_properties_path, 'r') as gradle_properties_file:
            gradle_properties_content = gradle_properties_file.readlines()

        java_home_line = f"org.gradle.java.home={actual_java_home_path}/\n"
        java_home_exists = False

        for i, line in enumerate(gradle_properties_content):
            if line.startswith("org.gradle.java.home="):
                gradle_properties_content[i] = java_home_line
                java_home_exists = True
                break

        if not java_home_exists:
            gradle_properties_content.append(java_home_line)

        with open(gradle_properties_path, 'w') as gradle_properties_file:
            gradle_properties_file.writelines(gradle_properties_content)

        report('info', "org.gradle.java.home added or updated in gradle.properties.")
    except Exception as e:
        report('error', f"{e}")


def add_universal_json_file(universal_json_path, contents):
    try:
        if exists_insensitive(universal_json_path):
            report(
                'info', f"{universal_json_path} file already exists. (not modifying it)")
            return

        with open(universal_json_path, 'w') as universal_json_file:
            json.dump(contents, universal_json_file, indent=4)

        report('info', f"{universal_json_path} file created with contents.")
    except Exception as e:
        report('error', f"{e}")


def remove_tsx_and_create_app_js():
    try:
        if exists_insensitive(app_tsx_path):
            if os.path.getsize(app_tsx_path) != app_tsx_original_length:
                report(
                    'warn', f"{app_tsx_path} has been modified. Is this intentional?")
                report('info', f"{app_tsx_path} not overwritten.")
                return

            os.remove(app_tsx_path)
            report(
                'info', f"{app_tsx_path} removed (it was the default version).")

        if exists_insensitive(app_js_path):
            report('info', f"{app_js_path} exists and has not been modified.")
            return

        # Create a new App.js file with the specified contents
        with open(app_js_path, 'w') as app_js_file:
            app_js_file.write(app_js_content)

        report('info', f"{app_js_path} created.")
    except Exception as e:
        report('error', f"{e}")


def modify_package_json_dependencies(json_path):
    try:
        with open(json_path, 'r') as package_json_file:
            package_json_data = json.load(package_json_file)
            dependencies_to_update = package_json_data.get("dependencies", {})

            count_of_dependencies_changed = 0

            # Add the specified keys in the desired order
            for key in dependencies_to_add:
                if key not in dependencies_to_update:
                    report('info', f"Adding {key} {dependencies_to_add[key]}")
                    dependencies_to_update[key] = dependencies_to_add[key]
                    count_of_dependencies_changed += 1
                    continue

                if dependencies_to_add[key] != dependencies_to_update[key]:
                    report(
                        'warn', f"Updating {key} from {dependencies_to_update[key]} to {dependencies_to_add[key]}")
                    dependencies_to_update[key] = dependencies_to_add[key]
                    count_of_dependencies_changed += 1
                    continue

                report('info', "{key} ({cd}) is present and up to date".format(
                    key=key, cd=dependencies_to_update[key]))

            # Merge the new dependencies with existing ones
            package_json_data["dependencies"] = dependencies_to_update

        if count_of_dependencies_changed == 0:
            report('info', "No package.json dependencies changed.")
            return

        package_json_file_bak = json_path + '.bak'
        report('info', "Backing up {jp} to {jpb}".format(
            jp=json_path, jpb=package_json_file_bak))

        if os.path.exists(package_json_file_bak):
            report('warn', "Removing existing {jpb} file".format(
                jpb=package_json_file_bak))
            os.remove(package_json_file_bak)

        os.rename(json_path, package_json_file_bak)

        # Write the modified content back to the file
        with open(json_path, 'w') as package_json_file:
            json.dump(package_json_data, package_json_file,
                      indent=2, sort_keys=True)

        report('info', "package.json file adjusted successfully.")
    except Exception as e:
        report('error', f"{e}")

def create_assets_config():
    if os.path.exists(font_assets_dir):
        report('info',f'{font_assets_dir} dir exists already')
    else:
        os.makedirs(font_assets_dir)
        report('info',f'{font_assets_dir} dir created')

    if os.path.exists(react_native_config_path):
        report('info',f'{react_native_config_path} exists already; not overwritten')
        return True
    
    try:
        with open(react_native_config_path, 'w') as config_file:
            config_file.write(react_native_config_contents)

        report('info', f"{react_native_config_path} created.")
        return True
    except Exception as e:
        report('error', f"{e}") 
        return False

def create_keystore():
    if exists_insensitive(keystore_path):
        report('info', "Keystore already exists. (not overwriting it)")
        return

    try:
        as_args = re.split(r'  +', keystore_create_cmd)
        subprocess.check_output(as_args, stderr=subprocess.STDOUT, text=True)
        report('info', "Keystore generated successfully.")
    except subprocess.CalledProcessError:
        report('error', "Keystore generated failed.")


def create_prettierrc():
    if exists_insensitive(".prettierrc"):
        report('info', 'Found existing .prettierrc, so not modifying it.')
        return

    with open('.prettierrc', 'w') as rc_file:
        rc_file.write(prettier_rc)

    report('info', ".prettierrc file created.")

# OVERALL ORCHESTRATION of TESTS that ALL MUST PASS (in order) before proceeding
# True for success, False for failure


def tests_of_essentials():
    tests = [is_npm_installed, is_java_home_valid,
             is_java_in_path, is_correct_version_of_java_installed,
             is_java_from_path_from_java_home, are_paths_valid,
             is_android_sdk_installed,is_homebrew_installed]

    all_successful = True
    for test in tests:
        if test():
            continue
        if not config['force']:
            return False
        all_successful = False
    return all_successful


# OVERALL ORCHESTRATION of TESTS that are INDEPENDENT of each other:
# failure of one does not prevent others from running
# True for success, False for failure
def tests_independent_of_each_other():
    tests = [is_project_under_git, is_npm_project,
             is_react_native_project, is_react_native_cli_project, 
             is_not_formerly_expo_project, is_adb_present,
             is_watchman_present, is_ios_deploy_present, is_cocoapods_present, is_xcode_selected,
             is_keytool_present, check_for_emulator,
             is_bundletool_installed, is_correct_ndk_installed,
             are_command_line_tools_in_path, is_mac_java_version_set,
             are_all_build_tools_versions_present]
    all_successful = True
    for test in tests:
        if not test():
            all_successful = False
    return all_successful


# OVERALL ORCHESTRATION of MODIFICATIONS
def modify_project_files():
    compare_expected_current_version_of_npm_packages_to_latest_available()

    modify_package_json_dependencies(package_json_path)

    remove_tsx_and_create_app_js()

    create_prettierrc()

    create_assets_config()

    add_gradle_java_home(gradle_properties_path, osified_java_home_path)

    add_keys_to_gradle_properties(gradle_properties_path)

    add_universal_json_file(universal_json_path, universal_json_contents)

    modify_gradle_wrapper_distribution_url(
        gradle_wrapper_properties_path, new_distribution_url)

    add_kotlin_version_to_build_gradle(build_gradle_path)

    add_signing_config_to_app_build_gradle(app_build_gradle_path)

    modify_gradle_properties(gradle_properties_path)

    create_keystore()


if __name__ == "__main__":

    config = set_up_config()

    sys.stdout = Logger()

    report('info', welcome_message, include_line=False)

    if not tests_of_essentials():
        if not config['force']:
            report('info', 'Exiting...')
            print_counts()
            sys.exit(1)

    if not tests_independent_of_each_other():
        if not config['force']:
            report('info', 'Exiting...')
            print_counts()
            sys.exit(1)

    try:
        modify_project_files()
    except Exception as e:
        report('error', f"{e}")
        report('fatal', 'Exiting...')
        print_counts()
        sys.exit(1)

    report('info', 'Be sure to:\n{pcs}\n'.format(
        pcs=post_config_steps), include_line=False)

    print_counts()
