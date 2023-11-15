#!/env/python
from inspect import currentframe
from urllib.request import urlopen
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys

script_url = 'https://raw.githubusercontent.com/bjmckenz/rn-cli-fixup/main/reactnative-setup.py'

script_version = "1.4.1"

# This script is intended to be run from the root of a React Native project directory.

### TO DO
# TODO: Clean up filenames, envvars, file contents
# TODO: move data to a file
# TODO: give revised version of .bashrc/.zshrc
# TODO: test gitbash on win for shelltype, file PS vs command PS
#   PowerShell: ShellId = Microsoft.PowerShell
#   CMD, cygwin,gitbash: OS Windows_NT
#   cygwin,gitbsh: SHELL
#   gitbash and cygwin can handle \ in paths
# FIXME: https://stackoverflow.com/questions/70258316/how-to-fix-dexoptionsactiondexoptions-unit-is-deprecated-setting-dexopt
# FIXME: https://stackoverflow.com/questions/71365373/software-components-will-not-be-created-automatically-for-maven-publishing-from#:~:text=WARNING%3A%20Software%20Components%20will%20not,use%20the%20new%20publishing%20DSL.
# FIXME: When running a single thing, turn off modifications
# FIXME: release section should use proper file reading, not regex
# TODO: output number of tests and modifications

# ENVIRONMENTY STUFF

running_on_windows = platform.system() == 'Windows'
shell_is_unixy = os.environ.get('SHELL') != None

# path separator in commands and paths
# FIXME: Should this include "or shell_shell_is_unixy"? diff between commands we run and report a nd what we write in files

path_separator = '\\' if running_on_windows else '/'
cmd_argument_separator = '/' if shell_is_unixy else '\\'
path_variable_separator = ';' if running_on_windows else ':'

# From command-line Arguments
config = {}
# can be set to false if a test fails
ok_to_proceed_with_modifications = True

### vvvv BEGIN CUSTOMIZE vvvv ###

# Specify the path to bundletool.jar
bt_dir = 'C:{ps}Program Files{ps}'.format(ps=path_separator) \
    if running_on_windows \
    else '{home}{ps}Library{ps}'.format(
        home=os.environ.get('HOME'),ps=path_separator)


keystore_file = "my-release-key"
store_password = "12345678"
key_alias = "my-key-alias"
key_password = "12345678"

distinguished_name = "CN=MyName, OU=MyOrgUnit, O=MyOrg, L=MyCity, ST=MyStateOrProvince, C=MyCountry"

### ^^^^ END CUSTOMIZE ^^^^ ###


### vvv NOT INTENDED TO BE CUSTOMIZED (but fix it if needed) vvv ###


bt_jar = 'bundletool-all-1.15.6.jar'
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

# reanimated adds about 199 chars to the path, and the max length on Windows
# is 250.
max_windows_project_path_length = 45

dependencies_to_add = {
    "@react-native-masked-view/masked-view": "^0.3.0",
    "@react-navigation/drawer": "^6.6.6",
    "@react-navigation/native": "^6.1.9",
    "@react-navigation/native-stack": "^6.9.17",
    "@react-navigation/stack": "^6.3.20",
    "react-native-asset": "^2.1.1",
    "react": "18.2.0",
    "react-native": "0.72.7",
    "react-native-gesture-handler": "^2.13.4",
    "react-native-reanimated": "^3.5.4",
    "react-native-safe-area-context": "^4.7.4",
    "react-native-screens": "^3.27.0"
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

*FOR IOS Before* your first build (or after you install a new NPM package) you must:

$ sudo gem update cocoapods --pre
$ npx pod-install
$ cd ios && pod update && cd ..

$ npx react-native run-android *(or)* run-ios

[to build an APK]

$ npx react-native-asset

$ cd android && .{ps}gradlew build && .{ps}gradlew bundleRelease
$ {build_apks_cmd}

$ {extract_apk_cmd}

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
sound_assets_dir = 'assets/audio'
react_native_config_path = 'react-native.config.js'
react_native_config_contents = '''
module.exports = {
    assets: ['./assets/fonts', './assets/audio'],
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
    'info': 0,
    'debug': 0,
    'howto': 0
}


def print_counts():
    print('*** ({ver}) Message type counts: {fatal} fatal, {warn} warn, {error} error, {info} info, {howto} fixes'.format(
        fatal=counts['fatal'],
        warn=counts['warn'],
        error=counts['error'],
        info=counts['info'],
        howto=counts['howto'],
        ver=script_version))


def report(type, message, include_line=True):
    counts[type.lower()] += 1

    if config['quiet'] and type.lower() == 'info':
        return

    if not config['debug'] and type.lower() == 'debug':
        return

    caller_line = currentframe().f_back.f_lineno

    if type.lower() == 'howto':
        print("vvvvvv HOW TO FIX vvvvvv\n{message}\n^^^^^^ HOW TO FIX ^^^^^".format(message=message.strip()))
        return

    message += ' [{ln}]'.format(ln=caller_line) if include_line else ''
    print('{type}: {message}'.format(type=type.upper(), message=message))

def current_version_of_script():
    try:
        for line in urlopen(script_url).read().decode('utf-8').splitlines():
            if line.strip().startswith('script_version'):
                return line.split('=')[1].strip().strip('"')
        report('error','Could not determine current version of script.')
    except Exception as e:
        report('error','Could not read current version of script.')
        print(e)
        pass
    return None

def versiontuple(v):
    return tuple(map(int, (v.split("."))))

#### Decorators and such that automatically collect operations to run

operations_in_order = []
operation_named = {}

def operation_prereqs_met(operation):
    if config['ignore_prerequisites']:
        return True
    for prereq_name in operation['prereqs']:
        # if we didn't run it, or we did and it failed
        if operation_named[prereq_name]['result'] != True:
            return False
    return True

def add_operation(func,attrs):
    func_name = func.__name__
    new_op = {
        'func_name': func_name,
        'prereqs': [],
        # Default true for all except show_newest_script_version
        'to_run': func_name != 'show_newest_script_version',
        'index': len(operations_in_order),
        'result': None,
        **attrs}
    operation_named[func_name] = new_op
    operations_in_order.append(new_op)
    return new_op

def operation(attrs={}):
    def decorator_internal(func):
        op = add_operation(func,attrs)
        def if_prereqs_met(*args, **kwargs):
            return func(*args, **kwargs) \
                    if operation_prereqs_met(op) \
                    else None
        op['func'] = if_prereqs_met
        return if_prereqs_met
    return decorator_internal

def system_test(attrs={}):
    return operation({'scope':'system','type':'test', **attrs})

def project_test(attrs={}):
    return operation({'scope':'project','type':'test', **attrs})

def project_modification(attrs={}):
    return operation({'scope':'project','type':'modification', **attrs})

##### end decorators for operations

# decorator to wrap a function to be executed only once
def do_once(func):
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return func(*args, **kwargs)
    wrapper.has_run = False
    return wrapper

def parse_command_line_arguments():

    @do_once
    def clear_list_of_tests_to_run():
        for op in operations_in_order:
            if op['type'] == 'test':
                op['to_run'] = False

    @do_once
    def clear_list_of_modifications_to_run():
        for op in operations_in_order:
            if op['type'] == 'modification':
                op['to_run'] = False

    class DoTestModule(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            ok_to_proceed_with_modifications = False
            clear_list_of_tests_to_run()
            operation_named[self.dest]['to_run'] = True

    class DoModificationtModule(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            clear_list_of_modifications_to_run()
            operation_named[self.dest]['to_run'] = True

    class SkipModule(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            operation_named[self.dest]['to_run'] = False

    class NoTests(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            clear_list_of_tests_to_run()

    class NoMods(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            clear_list_of_modifications_to_run()

    class NoProject(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            for op in operations_in_order:
                if op['scope'] == 'project':
                    op['to_run'] = False

    class NoSystem(argparse.Action):
        def __call__(self, parse, namespace, values, option_string=None):
            for op in operations_in_order:
                if op['scope'] == 'system':
                    op['to_run'] = False

    parser = argparse.ArgumentParser(description="React-Native CLI Fixer-Upper",
                                    formatter_class=argparse.
                                    ArgumentDefaultsHelpFormatter,
                                    epilog="v{ver} Contact bjmckenz@gmail.com with bugs, questions, and suggestions.".format(ver=script_version))

    parser.add_argument("-q", "--quiet", action=argparse.BooleanOptionalAction,
                        default=False, help="Shhh! No INFO messages")

    parser.add_argument("--debug", action=argparse.BooleanOptionalAction,
                        default=False, help="Show Debug Messages")

    parser.add_argument("-f", "--force", action=argparse.BooleanOptionalAction,
                        default=False,
                        help="continue even if after an error")

    parser.add_argument("--simulate-modifications", action=argparse.BooleanOptionalAction,
                        default=False, dest='simulate',
                        help="simulate modifications, don't actually do them")

    parser.add_argument("--show-header-and-trailer", action=argparse.BooleanOptionalAction,
                        default=not safe_exists(script_output_file),
                        dest='show-header-and-trailer',
                        help="display annoying header and trailer every time")

    parser.add_argument("--ignore-prerequisites", action='store_true',
                        default=False,
                        help="run tests regardless of prerequisites")

    parser.add_argument("--no-tests", action=NoTests, nargs=0,
                        help="skip all tests")

    parser.add_argument("--no-project", action=NoProject, nargs=0,
                        help="skip project-level tests")

    parser.add_argument("--no-system", action=NoSystem, nargs=0,
                        help="skip system-level tests")

    parser.add_argument("--no-mods","--no-modifications", action=NoMods, nargs=0,
                        help="skip modifications")

    for op in operations_in_order:
        parser.add_argument("--do-"+op['func_name'],
                            action=DoTestModule if op['type'] == 'test' else DoModificationtModule,
                            dest=op['func_name'], nargs=0,
                            help="run "+op['func_name'])

        parser.add_argument("--skip-"+op['func_name'],
                            action=SkipModule, nargs=0,
                            dest=op['func_name'],
                            help="(don't) "+op['func_name'])

    config = vars(parser.parse_args())

    return config

def safe_exists(path):
    return os.path.exists(os.path.normcase(path))


def paths_equal(path1, path2):
    #print("comparing {p1} to {p2}".format(p1=path1,p2=path2))
    return os.path.normcase(path1) == os.path.normcase(path2)

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



# BEGIN TESTS

@operation({'scope':'meta','type':'debug'})
def print_stats():
    report('debug',"*** CONFIG ***")
    report('debug',json.dumps(config, indent=4, sort_keys=True))
    report('debug',"*** OPERATIONS ***")
    report('debug',json.dumps(list(map(lambda x: {**x, 'func':'<func>'},operations_in_order)), indent=4))
    return True


@operation({'scope':'meta','type':'meta'})
def script_version_check():
    current_vers = current_version_of_script()
    if current_vers is None:
        report('fatal','Could not determine current version of script.')
        for op in operations_in_order:
            op['to_run'] = False
        return False

    #report('info',"Current version of script is {cv}, this version is {dv}".format(cv=current_vers,dv=script_version))

    if versiontuple(current_vers) > versiontuple(script_version):
        report('fatal','This script (v{dv}) is out of date. Please pull the latest version (v{cv}) from github'.format(dv=script_version,cv=current_vers))
        sys.exit()

    report('info', 'Script is current version ({cv})'.format(cv=current_vers))
    return True


@operation({'scope':'meta','type':'meta'})
def show_newest_script_version():
    current_vers = current_version_of_script()
    if current_vers is None:
        report('error','Could not determine current version of script.')
        sys.exit()

    report('info','Your version of this script is {this}. Current version on github is {vers}'.format(
            vers=current_vers, this=script_version))

    sys.exit()

@system_test()
def is_npm_installed():
    if shutil.which('npx') != None:
        report('info', 'Found npm.')
        return True

    report('fatal', 'Node.js is not installed (or is not in your PATH).')
    return False

@system_test()
def is_java_home_valid():
    if not java_home:
        report('fatal', 'JAVA_HOME is not defined. Set it in your environment.')
        report('info',
                'If needed, download and install JDK\n\n     {jv}\n\nfrom\n\n     {jdp}\n\nand make sure it is in your path, and that JAVA_HOME is set in environment variables.'.format(
                    jv=expected_java_version, jdp=jdk_download_path))
        return False

    report('info', 'JAVA_HOME is set to {jhp}'.format(
        jhp=java_home))

    if safe_exists(java_home):
        report('info', 'JAVA_HOME points to an existing directory.')
        return True

    report('fatal', 'JAVA_HOME set, but does not point to an existing directory.')
    return False


@system_test()
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

@system_test({'prereqs':['is_java_in_path']})
def is_correct_version_of_java_installed():
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

    report('error', 'Go download and install JDK {jv}, and make sure it is in your path.'.format(
        jv=expected_java_version))

    report('info', 'Download link: {jdk_download_path}'.format(
        jdk_download_path=jdk_download_path))
    return False


@system_test({'prereqs':['is_java_in_path','is_java_home_valid']})
def is_java_from_path_from_java_home():
    # Java under the jdk dir
    java_executable_location = shutil.which('java')

    if java_executable_location.startswith(java_home):
        report('info', 'java executable location matches up with JAVA_HOME.')
        return True

    report('fatal', 'java executable location does not match up with JAVA_HOME. Fix JAVA_HOME in your environment.')
    return False



@system_test()
def is_android_sdk_installed():
    if not android_sdk_root:
        report('fatal', 'ANDROID_HOME and ANDROID_SDK_ROOT are not defined. Set at least one in your environment.')
        report('info', "This may indicate you haven't downloaded the ANDROID SDK yet.")
        report(
            'info', 'Download the Android SDK from https://developer.android.com/studio')
        return False

    report('info', 'Environment var(s) point to an Android SDK location {asdk}.'.format(
        asdk=android_sdk_root))

    if safe_exists(android_sdk_root):
        report('info', 'Android SDK appears to exist.')
        return True

    report('fatal', 'ANDROID_SDK_ROOT variable is set but directory does not exist. Set it CORRECTLY in your environment.')
    return False

@system_test({'prereqs':['is_android_sdk_installed']})
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

@system_test()
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


##################################

@project_test()
def is_project_under_git():
    if safe_exists('.git'):
        report('info', 'Project is git-controlled.')
        return True

    if subprocess.run(
            ["git", "rev-parse"], stderr=subprocess.DEVNULL).returncode == 0:
        report('info', 'Project is git-controlled.')
        return True

    report('fatal', 'This project is NOT under git management (!)')
    report('howto', "$ git init\n$ git add .\n$ git commit -m\'Initial commit\'")
    return False

@project_test({'prereqs':['is_npm_installed']})
def is_npm_project():
    if safe_exists(package_json_path):
        report('info', 'We are in an NPM project.')
        return True
    report('fatal', 'package.json does not exist. Run this from an initialized project directory.')
    report('howto','''
* Open a terminal/cmd window in a directory where you keep all your projects.
$ npx react-native@latest init MyProject
* Open that folder in VS Code.
''')
    return False

@project_test()
def is_project_path_too_long():
    if running_on_windows and len(os.getcwd()) > max_windows_project_path_length:
        report('fatal', 'Project path is too long. Move it to a shorter path.')
        report('howto','''
* Move this directory to a shorter path, such as C:\SOURCE
* Be sure to move rn-cli-fixup to the same directory.
''')
        return False
    return True

@project_test()
def is_react_native_project():
    if safe_exists("android"):
        report('info', 'We are really in a React-native project.')
        return True
    report('fatal', '"android" does not exist. This does not appear to be a React-Native project dir.')
    return False

@project_test({'prereqs':['is_react_native_project']})
def is_react_native_cli_project():
    with open(package_json_path, 'r') as package_json_file:
        package_json_data = json.load(package_json_file)
        dependencies = package_json_data.get("dependencies", {})
        if dependencies.get("expo", None) == None:
            report('info', 'Confirmed: this is a CLI project.')
            return True
        report('fatal', 'expo is a dependency. This appears to be an expo project, not a React-Native CLI project dir.')
        return False

@project_test({'prereqs':['is_npm_project']})
def is_not_formerly_expo_project():
    with open(package_json_path, 'r') as package_json_file:
        package_json_data = json.load(package_json_file)
        dependencies = package_json_data.get("dependencies", {})
        if dependencies.get("expo-splash-screen", None) == None:
            report('info', 'Confirmed: this is not an expo rebuild/exported project.')
            return True
        report('fatal', 'expo-splash-screen is a dependency. This appears to be an exported (prebuild) expo project, not a true CLI project.')
        return False

@project_test()
def is_cocoapods_present():
    if running_on_windows:
        report('info','(Cocoapods is not required on Windows.)')
        return True

    if brew_recipe_installed('cocoapods'):
        report('info', 'Found cocoapods.')
        return True

    report('fatal', 'cocoapods not found.')
    report('howto', '$ brew install cocoapods')

    return False

@system_test()
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
    report('howto','$ sudo xcode-select -s /Applications/Xcode.app')

    return False

@system_test()
def is_watchman_present():
    if running_on_windows:
        report('info','(Watchman is not required on Windows.)')
        return True

    if shutil.which('watchman'):
        report('info', 'Found watchman.')
        return True

    report('fatal', 'watchman command not found. Set it in your path).')
    report('howto','$ brew install watchman')

    return False

@system_test()
def is_ios_deploy_present():
    if running_on_windows:
        report('info','(ios-deploy is not required on Windows.)')
        return True

    if shutil.which('ios-deploy'):
        report('info', 'Found ios-deploy.')
        return True

    report('fatal', 'ios-deploy command not found. Set it in your path).')
    report('howto','$ brew install ios-deploy')

    return False

@system_test()
def is_adb_present():
    if shutil.which(adb_command):
        report('info', 'Found adb.')
        return True

    report('fatal', 'adb command not found. Set it in your path (install platform-tools if needed).')
    if not running_on_windows:
        report('howto','$ brew install android-platform-tools')
    return False

@system_test({'prereqs':['is_java_in_path']})
def is_keytool_present():
    if shutil.which('keytool') != None:
        report('info', 'keytool is in path.')
        return True

    report('fatal', 'keytool command not found. Set it in your path.')
    report('info', 'This is usually in {jdk}{ps}bin'.format(
        jdk=java_home, ps=path_separator))
    return True

@system_test()
def is_emulator_present():
    if shutil.which(emu) != None:
        report('info', 'Found emulator.')
        return True

    report('warn', 'Emulator not found. Did you intend to install it?')
    return False

@system_test()
def is_bundletool_installed():
    if not safe_exists(bt_dir):
        report('fatal', 'Expected location of bundletool ({bt_dir}) does not exist.. Please specify the correct path to it or create it.'.format(
            bt_dir=bt_dir
        ))
        return False

    report('info','bundletool destination folder of {bt_dir} exists.'.format(bt_dir=bt_dir))

    if safe_exists(bt_dir+bt_jar):
        report('info', 'Found current version of bundletool.')
        return True

    report('fatal', 'Current version of bundletool.jar does not exist. Please specify the correct path to it.')
    report('info', 'The current (known) version is {bt_jar}'.format(bt_jar=bt_jar))
    report('howto', '''
* Browse to {bt_loc}
* Click on 'Releases'
* Click on '{bt_jar}'
* Save it in Downloads
* Copy it to {bt_dir}
'''.format(bt_jar=bt_jar,bt_dir=bt_dir,bt_loc=bt_loc))
    return False

@system_test({'prereqs':['is_npm_installed']})
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
    return True

@system_test({'prereqs':['is_android_sdk_installed']})
def are_command_line_tools_in_path():
    if safe_exists(os.path.join(android_sdk_root, cmdline_tools_path)):
        report('info', 'Command-line tools are in path.')
        return True
    report('fatal', 'Command-line tools (latest) are not installed in Android SDK.')
    return False

@system_test({'prereqs':['is_android_sdk_installed']})
def is_correct_ndk_installed():
    if safe_exists(os.path.join(android_sdk_root, 'ndk', ndk_version)):
        report('info', 'Correct NDK is installed.')
        return True

    report('fatal', 'Android SDK NDK version {ndk_version} not installed.'.format(
        ndk_version=ndk_version))
    return False

@system_test({'prereqs':['is_android_sdk_installed']})
def are_all_build_tools_versions_present():
    missing = 0
    for btv in build_tools_versions:
        if safe_exists(os.path.join(android_sdk_root, 'build-tools', btv)):
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

@system_test()
def is_mac_java_version_set():
    if running_on_windows:
        report('info','(JAVA_VERSION is not needed for Windows)')
        return True

    if os.environ.get('JAVA_VERSION') == expected_java_version:
        report('info','JAVA_VERSION is set correctly.')
        return True

    report('FATAL','Environment var JAVA_VERSION must be set to {jv} (probably in ~/.zshrc)'.format(jv=expected_java_version))
    report('howto','''
* Add this line to ~/.zshrc (or ~/.bashrc)
----
export JAVA_VERSION=20.0.2
----
* Restart Terminal and VS Code.
''')
    return False

# BEGIN MODIFICATIONS

@project_modification()
def add_kotlin_version_to_build_gradle():
    bg = read_gradle_file(build_gradle_path)

    # Find buildscript.ext, ensure there is a kotlinVersion
    # and that it has the correct version

    buildscript = list(filter(lambda x: 'key' in x and x['key'] == 'buildscript', bg))[0]
    ext = list(filter(lambda x: 'key' in x and x['key'] == 'ext', buildscript['contents']))[0]

    kvs = list(filter(lambda x: 'line' in x and x['line'].startswith('kotlinVersion'), ext['contents']))
    if len(kvs) and 'line' in kvs[0] and kotlinVersion not in kvs[0]['line']:
        report('warn', "build.gradle has unexpected "+kvs[0]['line'])

    ext['contents'] = list(filter(lambda x: 'line' not in x or not x['line'].startswith('kotlinVersion'), ext['contents']))
    ext['contents'].append({'line':'kotlinVersion = "{kv}"'.format(kv=kotlinVersion)})

    with open(build_gradle_path, 'w') as gradle_file:
        gradle_file.write(gradle_config_as_str(bg))

    report('info', "build.gradle file updated successfully with kotlinVersion {kv}.".format(kv=kotlinVersion))
    return True

@project_modification()
def add_signing_config_to_app_build_gradle():
    with open(app_build_gradle_path, 'r') as app_build_gradle_file:
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
    with open(app_build_gradle_path, 'w') as app_build_gradle_file:
        app_build_gradle_file.write(modified_content)

    report('info', "app/build.gradle file updated successfully with signingConfigs.")
    return True

@project_modification()
def add_keys_to_gradle_properties():
    with open(gradle_properties_path, 'r') as properties_file:
        properties_content = properties_file.read()

        # Check if each property already exists in the file
        for prop in gradle_properties_to_add:
            if prop not in properties_content:
                properties_content += f"{prop}\n"

    # Write the modified content back to the file
    with open(gradle_properties_path, 'w') as properties_file:
        properties_file.write(properties_content)

    report('info', "gradle.properties file updated successfully with keys.")
    return True

@project_modification()
def modify_gradle_properties_release_section():
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

    report('info', "gradle.properties file updated successfully with release section.")
    return True

@project_modification()
def modify_gradle_wrapper_distribution_url():
    with open(gradle_wrapper_properties_path, 'r') as wrapper_properties_file:
        wrapper_properties_content = wrapper_properties_file.readlines()

    for i, line in enumerate(wrapper_properties_content):
        if line.startswith("distributionUrl="):
            wrapper_properties_content[i] = f"distributionUrl={new_distribution_url}\n"
            break

    with open(gradle_wrapper_properties_path, 'w') as wrapper_properties_file:
        wrapper_properties_file.writelines(wrapper_properties_content)

    report('info', "Gradle wrapper distributionUrl updated successfully.")
    return True

@project_modification()
def add_gradle_java_home():
    actual_java_home_path = osified_java_home_path
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
    return True

@project_modification()
def add_universal_json_file():
    if safe_exists(universal_json_path):
        report(
            'info', f"{universal_json_path} file already exists. (not modifying it)")
        return True

    with open(universal_json_path, 'w') as universal_json_file:
        json.dump(universal_json_contents, universal_json_file, indent=4)

    report('info', f"{universal_json_path} file created with contents.")
    return True

@project_modification()
def remove_tsx_and_create_app_js():
    if safe_exists(app_tsx_path):
        if os.path.getsize(app_tsx_path) != app_tsx_original_length:
            report(
                'warn', f"{app_tsx_path} has been modified. Is this intentional?")
            report('info', f"{app_tsx_path} not overwritten.")
            return True

        os.remove(app_tsx_path)
        report(
            'info', f"{app_tsx_path} removed (it was the default version).")

    if safe_exists(app_js_path):
        report('info', f"{app_js_path} exists and has not been modified.")
        return True

    # Create a new App.js file with the specified contents
    with open(app_js_path, 'w') as app_js_file:
        app_js_file.write(app_js_content)

    report('info', f"{app_js_path} created.")
    return True

@project_modification()
def modify_package_json_dependencies():
    json_path = package_json_path

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
        return True

    package_json_file_bak = json_path + '.bak'
    report('info', "Backing up {jp} to {jpb}".format(
        jp=json_path, jpb=package_json_file_bak))

    if safe_exists(package_json_file_bak):
        report('warn', "Removing existing {jpb} file".format(
            jpb=package_json_file_bak))
        os.remove(package_json_file_bak)

    os.rename(json_path, package_json_file_bak)

    # Write the modified content back to the file
    with open(json_path, 'w') as package_json_file:
        json.dump(package_json_data, package_json_file,
                indent=2, sort_keys=True)

    report('info', "package.json file adjusted successfully.")
    return True

@project_modification()
def create_assets_config():
    if safe_exists(font_assets_dir):
        report('info',f'{font_assets_dir} dir exists already')
    else:
        os.makedirs(font_assets_dir)
        report('info',f'{font_assets_dir} dir created')

    created_sound_dir = False
    if safe_exists(sound_assets_dir):
        report('info',f'{sound_assets_dir} dir exists already')
    else:
        created_sound_dir = True
        os.makedirs(sound_assets_dir)
        report('info',f'{sound_assets_dir} dir created')

    if safe_exists(react_native_config_path):
        report('info',f'{react_native_config_path} exists already; not overwritten')
        if created_sound_dir:
            report('warn',f'You may need to add {sound_assets_dir} to {react_native_config_path}')
        return True

    with open(react_native_config_path, 'w') as config_file:
        config_file.write(react_native_config_contents)

    report('info', f"{react_native_config_path} created.")
    return True

@project_modification()
def create_keystore():
    if safe_exists(keystore_path):
        report('info', "Keystore already exists. (not overwriting it)")
        return True

    as_args = re.split(r'  +', keystore_create_cmd)
    subprocess.check_output(as_args, stderr=subprocess.STDOUT, text=True)
    report('info', "Keystore generated successfully.")
    return True

@project_modification()
def create_prettierrc():
    if safe_exists(".prettierrc") or \
        safe_exists(".prettierrc.js"):
            report('info', 'Found existing .prettierrc or .prettierrc.js, so not modifying it.')
            return True

    with open('.prettierrc', 'w') as rc_file:
        rc_file.write(prettier_rc)

    report('info', ".prettierrc file created.")
    return True

def execute_operations():
    global ok_to_proceed_with_modifications
    overall_success = True
    for operation in operations_in_order:
        fn = operation['func_name']
        if not operation['to_run']:
            report('info',"(Skipping {fn})".format(fn=fn))
            continue
        if operation['type'] == 'modification':
            if not ok_to_proceed_with_modifications:
                report('info',"Skipping {fn} ('{typ}' filtered out; previous test failure)".format(
                    fn=fn,
                    typ=operation['type'])
                )
                continue
            if config['simulate']:
                report('info',"(Simulating {fn})".format(fn=fn))
                continue
        try:
            result = operation['func']()
            operation['result'] = result
            report('debug',"op {fn} returned {r}".format(fn=fn,r=result))
        except Exception as e:
            report('error','module {fn} raised {e}'.format(
                fn=fn,
                e=e
            ))
            report('error','please report to BJM ASAP')
            operation['result'] = False
            overall_success = False

            if not config['force']:
                break

        if not operation['result'] and not config['force']:
            ok_to_proceed_with_modifications = False

    return overall_success or config['force']

if __name__ == "__main__":

    # note that this is done after operations_in_order is created
    config = parse_command_line_arguments()

    sys.stdout = Logger()

    new_ops = list(map(lambda x: {**x,'func':'<>'}, operations_in_order))

    if config['show-header-and-trailer']:
        report('info', welcome_message, include_line=False)

    success = execute_operations()

    if success and config['show-header-and-trailer']:
        report('info', 'Be sure to:\n{pcs}\n'.format(
            pcs=post_config_steps), include_line=False)

    print_counts()
