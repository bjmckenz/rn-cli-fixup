#!/env/python
import re
import json
import os
import subprocess
import shutil
import sys
import platform
from urllib.request import urlopen

    
#  To do
#  Handle Mac


# This script is intended to be run from the root of a React Native project directory.

# ENVIRONMENTY STUFF

running_on_windows = platform.system() == 'Windows'
shell_is_unixy = os.environ.get('SHELL') != None

# path separator in commands and paths
path_separator = '\\' if running_on_windows else '/'
cmd_argument_separator = '/' if shell_is_unixy else '\\'
### vvvv BEGIN CUSTOMIZE vvvv ###

# Specify the path to bundletool.jar
bt = 'C:{ps}Program Files{ps}bundletool-all-1.15.4.jar'.format(ps=path_separator)

keystore_file = "my-release-key"
store_password = "12345678"
key_alias = "my-key-alias"
key_password = "12345678"

distinguished_name = "CN=MyName, OU=MyOrgUnit, O=MyOrg, L=MyCity, ST=MyStateOrProvince, C=MyCountry"

### ^^^^ END CUSTOMIZE ^^^^ ###


### vvv NOT INTENDED TO BE CUSTOMIZED (but fix it if needed) vvv ###

new_distribution_url = 'https{ps}://services.gradle.org/distributions/gradle-8.1-bin.zip'.format(ps=path_separator)

expected_java_version = "20.0.2"

jdk_path = "https://www.dropbox.com/scl/fi/hfwwy11wpskpzekh71ztg/jdk-20_windows-x64_bin.exe?rlkey=wkx4wfurf8l2valcqaawztvun"

bt_loc = 'https://github.com/google/bundletool'

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
    'MYAPP_RELEASE_STORE_FILE={keystore_file}.jks'.format(keystore_file=keystore_file),
    'MYAPP_RELEASE_KEY_ALIAS={key_alias}'.format(key_alias=key_alias),
    'MYAPP_RELEASE_STORE_PASSWORD={store_password}'.format(store_password=store_password),
    'MYAPP_RELEASE_KEY_PASSWORD={key_password}'.format(key_password=key_password),
]


app_tsx_path = 'App.tsx'  # Expected for new projects
app_tsx_original_length = 2605

package_json_path = 'package.json'
universal_json_path = 'android{ps}universal.json'.format(ps=path_separator) # created to specify which apk to extract from apks file
gradle_properties_path = 'android{ps}gradle.properties'.format(ps=path_separator)
build_gradle_path = 'android{ps}app{ps}build.gradle'.format(ps=path_separator)
gradle_wrapper_properties_path = 'android{ps}gradle{ps}wrapper{ps}gradle-wrapper.properties'.format(ps=path_separator)


dependencies_to_add = {
  "@react-native-masked-view/masked-view": "^0.2.9",
  "@react-navigation/drawer": "^6.6.4",
  "@react-navigation/native": "^6.1.8",
  "@react-navigation/native-stack": "^6.9.14",
  "@react-navigation/stack": "^6.3.18",
  "react": "18.2.0",
  "react-native": "0.72.5",
  "react-native-gesture-handler": "^2.13.1",
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


# This is the Hello-Worldiest of Hello-World apps.
app_js_path = 'App.js' # we create this if we remove App.tsx
app_js_content = """
import React from 'react';
import {
  Text,
  View,
} from 'react-native';

const App = () => {
  return (
    <View ><Text>Hello World</Text></View>
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

build_apks_cmd = re.sub(r' +',' ',
  'java -jar "{bt}" \
    build-apks \
    --bundle=app{ps}build{ps}outputs{ps}bundle{ps}release{ps}app-release.aab \
    --output=app{ps}build{ps}outputs{ps}apk{ps}release{ps}app-release.apks \
    --mode=universal \
    --ks=..{ps}{keystore_path} \
    --ks-pass=pass:{store_password} \
    --ks-key-alias={key_alias} \
    --key-pass=pass:{key_password}'.format(
    bt=bt, 
    keystore_path=keystore_path, 
    store_password=store_password,
    key_alias=key_alias,
    key_password=key_password,
    ps=cmd_argument_separator))

extract_apk_cmd = re.sub(r' +',' ',
  'java -jar "{bt}" \
  extract-apks \
    --apks=app{ps}build{ps}outputs{ps}apk{ps}release{ps}app-release.apks \
    --output-dir=app{ps}build{ps}outputs{ps}apk{ps}release{ps} \
    --device-spec=..{ps}{universal_json_path}'.format(
    bt=bt, 
    universal_json_path=universal_json_path,
    ps=cmd_argument_separator
 ))

post_config_steps = '''
1. npm install
2a. git init
2b. git add .
2c. git commit -m"initial version"

Once this is done, you can either/both:

[to run on simulator or connected device]

$ npx react-native run-android

[to build an APK]

$ cd android && .{ps}gradlew build && .{ps}gradlew bundleRelease
$ {build_apks_cmd}

$ {extract_apk_cmd}'''.format(
    extract_apk_cmd=extract_apk_cmd,
    build_apks_cmd=build_apks_cmd,
    ps=cmd_argument_separator
 )

clean_repo_cmd = 'rnc clean --include "android,metro,npm,watchman,yarn"'

output_file = 'reactnative-fixup.txt'

# ideal way to find
android_home = os.environ.get('ANDROID_HOME')
android_sdk_root = os.environ.get('ANDROID_SDK_ROOT')

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

### ^^^ NOT INTENDED TO BE CUSTOMIZED ^^^ ###

def npm_installed():
    return shutil.which('npx') != None

def add_signing_config_to_build_gradle(file_path):
    try:
        with open(file_path, 'r') as build_gradle_file:
            build_gradle_content = build_gradle_file.read()

            # Check if the signingConfigs section already exists
            if 'signingConfigs {' in build_gradle_content:
                # If it exists, append the signing_config_text to it
                modified_content = re.sub(r'(signingConfigs \{[^\}]*\})', r'\1' + signing_config_text, build_gradle_content, flags=re.DOTALL)
            else:
                # If it doesn't exist, add the entire signingConfig section
                modified_content = re.sub(r'(buildTypes \{[^\}]*\})', r'signingConfigs {\n' + signing_config_text + r'\1', build_gradle_content, flags=re.DOTALL)

        # Write the modified content back to the file
        with open(file_path, 'w') as build_gradle_file:
            build_gradle_file.write(modified_content)

        print("INFO: Build.gradle file updated successfully.")
    except Exception as e:
        print(f"ERROR: {e}")





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

        print("INFO: gradle.properties file updated successfully.")
    except Exception as e:
        print(f"ERROR: {e}")





def update_build_gradle_release_section(gradle_properties_path):
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

        print("INFO: gradle.properties file updated successfully.")
    except Exception as e:
        print(f"ERROR: {e}")





def change_gradle_wrapper_distribution_url(prop_path, new_distribution_url):
    try:
        with open(prop_path, 'r') as wrapper_properties_file:
            wrapper_properties_content = wrapper_properties_file.readlines()

        for i, line in enumerate(wrapper_properties_content):
            if line.startswith("distributionUrl="):
                wrapper_properties_content[i] = f"distributionUrl={new_distribution_url}\n"
                break

        with open(prop_path, 'w') as wrapper_properties_file:
            wrapper_properties_file.writelines(wrapper_properties_content)

        print("INFO: Gradle wrapper distributionUrl updated successfully.")
    except Exception as e:
        print(f"ERROR: {e}")





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

        print("INFO: org.gradle.java.home added or updated in gradle.properties.")
    except Exception as e:
        print(f"ERROR: {e}")

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
    else:
        return path1 == path2



def create_universal_json(universal_json_path, contents):
    try:
        if not exists_insensitive(universal_json_path):
            with open(universal_json_path, 'w') as universal_json_file:
                json.dump(contents, universal_json_file, indent=4)

            print(f"INFO: {universal_json_path} file created with contents.")
        else:
            print(f"WARN: {universal_json_path} file already exists.")
    except Exception as e:
        print(f"ERROR: {e}")


def errors_in_java_home_and_path():
    errors_occurred = False
    java_loc = shutil.which('java')
    if not java_loc:
        print('FATAL: java is not in your path. Set it in your environment.')
        errors_occurred = True

    java_home_path = os.environ.get('JAVA_HOME')
    if not java_home_path:
        print('FATAL: JAVA_HOME is not defined. Set it in your environment.')
        errors_occurred = True 
    
    if not errors_occurred:
        # both need to exist, and path must be parent of loc
        # Java in the /bin under the jdk dir
        actual_java_install_path = os.path.dirname(os.path.dirname(java_loc))
        if not paths_equal(actual_java_install_path, java_home_path):
            print('FATAL: java executable location does not match up with JAVA_HOME. Fix JAVA_HOME in your environment.')
            errors_occurred = True
    
    return errors_occurred

def correct_version_of_java_installed(version_desired):
    try:
        # Run the "java -version" command and capture the output
        java_version_output = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT, text=True)

        # Check if the output contains "java version" followed by "20" (exact match)
        match = re.search(r'"([\d.]+)"',java_version_output)
        if not match:
            return False
        installed_version = match.group()
        print("INFO: Detected version ",installed_version," of Java.")
        if version_desired in installed_version:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        # The "java" command returned a non-zero exit status, indicating Java is not installed or not recognized.
        return False


def remove_tsx_and_create_app_js():
    try:
        if exists_insensitive(app_tsx_path):

            if os.path.getsize(app_tsx_path) != app_tsx_original_length:
                print(f"WARN: {app_tsx_path} has been modified. Is this intentional?")
                print(f"INFO: {app_tsx_path} not overwritten.")
                return
            
            # Remove the existing App.tsx file if it exists
            os.remove(app_tsx_path)

            # Create a new App.js file with the specified contents
            with open(app_js_path, 'w') as app_js_file:
                app_js_file.write(app_js_content)

            print(f"INFO: {app_tsx_path} removed and {app_js_path} created.")
        else:
            print(f"WARN: {app_tsx_path} does not exist.")
            print(f"INFO: {app_js_path} not modified.")
    except Exception as e:
        print(f"ERROR: {e}")


def adjust_package_json(json_path):
    try:
        with open(json_path, 'r') as package_json_file:
            package_json_data = json.load(package_json_file)

            # Create a new dictionary for dependencies
            updated_dependencies = {}

            # Add the specified keys in the desired order
            for key in dependencies_to_add:
                if key in package_json_data.get("dependencies", {}):
                    updated_dependencies[key] = package_json_data["dependencies"][key]
                else:
                    updated_dependencies[key] = dependencies_to_add[key]

            # Merge the new dependencies with existing ones
            package_json_data["dependencies"] = updated_dependencies

        # Write the modified content back to the file
        with open(json_path, 'w') as package_json_file:
            json.dump(package_json_data, package_json_file, indent=2, sort_keys=True)

        print("INFO: package.json file adjusted successfully.")
    except Exception as e:
        print(f"WARN: {e}")

def generate_keystore():
    if exists_insensitive(keystore_path):
      print("WARN: Keystore already exists. (Overwriting it)")
      os.remove(keystore_path)

    try:
      as_args = re.split(r'  +',keystore_create_cmd)
      subprocess.check_output(as_args, stderr=subprocess.STDOUT, text=True)
      print("INFO: Keystore generated successfully.")

      return True
    except subprocess.CalledProcessError:
      print("ERROR: Keystore generated failed.")
      return False

def npm_package_version(pkg):
    url = 'https://unpkg.com/{pkg}/package.json'.format(pkg=pkg)
    response = urlopen(url)
    package_json = json.loads(response.read())
    return package_json['version']

def compare_expected_npm_package_versions_to_latest_available():
    print("INFO: Checking [newest published] npm package versions...")
    any_changes = False
    for p in dependencies_to_add.keys():
        compare_to = npm_package_version(p)
        if dependencies_to_add[p][0] == '^':
            compare_to = '^' + compare_to

        if compare_to != dependencies_to_add[p]:
            print('WARN: Expecting version {v} of {p} but found {v2}'.format(v=dependencies_to_add[p], p=p, v2=compare_to))
            any_changes = True

        #print(p,' ',npm_package_version(p))

    if any_changes:
        print("INFO: (Tell BJM or write an issue against this script on GitHub)")

    print("INFO: ...Done checking npm package versions.")

def keytool_missing(java_home_path):
    if exists_insensitive(os.path.join(java_home_path,'bin','keytool.exe')):
        return False
    
    print('FATAL: keytool command not found. Set it in your path.')
    print('INFO: This is usually in {jdk}{ps}bin'.format(jdk=java_home_path,ps=path_separator))
    return True

def path_inspected_and_confirmed(java_home,android_sdk_root):
    existing_path = os.environ.get('PATH').split(';')
    found_platform_tools = False
    found_tools = False
    found_java_bin = False
    found_another_java_bin = False

    for p in existing_path:
        lcp = p.lower()
        if paths_equal(p,os.path.join(android_sdk_root,'platform-tools')):
            found_platform_tools = True
        elif paths_equal(p,os.path.join(android_sdk_root,'tools')):
            found_tools = True
        elif paths_equal(p,os.path.join(java_home,'bin')):
            found_java_bin = True
        elif 'oracle' in lcp:
            # trying to catch Java's router to installed versions
            found_another_java_bin = True
        elif 'jdk' in lcp:
            # trying to catch windows version
            found_another_java_bin = True
        elif 'jbr' in lcp:
            # trying to catch IntelliJ version
            found_another_java_bin = True
            
        if found_platform_tools and found_tools and found_java_bin:
            break

    if found_another_java_bin:
        print('FATAL: Another Java bin directory is in your ahead of the proper JDK.');
    
    if not found_java_bin:
        print('FATAL: Ensure that {java_home}{ps}bin is at the top of your {emphasis}path.'.
              format(java_home=java_home,
                     ps=path_separator,
                     emphasis='SYSTEM ' if running_on_windows else ''))
        
    if not found_platform_tools:
        print('FATAL: Ensure that {android_sdk_root}{ps}platform-tools is at the top of your {emphasis}path.'.
              format(android_sdk_root=android_sdk_root,
                     ps=path_separator,
                     emphasis='SYSTEM ' if running_on_windows else ''))
        
    if not found_platform_tools:
        print('FATAL: Ensure that {android_sdk_root}{ps}tools is at the top of your {emphasis}path.'.
              format(android_sdk_root=android_sdk_root,
                     ps=path_separator,
                     emphasis='SYSTEM ' if running_on_windows else ''))
        
    return found_platform_tools and \
        found_tools and \
        found_java_bin and \
        not found_another_java_bin


print("*********")
print('INFO: All output from this script will be logged to {output_file}'.format(output_file=output_file))
print("*********")

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open(output_file, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        self.log.flush()

sys.stdout = Logger()

print("""
*******
This script MAY help you. You *should* have run "npx react-native doctor"
and fixed the issues first. This may help you with issues there if you can't figure out why doctor is failing.
      
BUT DO NOT try to run-android without BOTH "doctor" and this script reporting success.
      
Note that "WARN:" does not mean "Error", it means "be sure this is correct."
*********** 
      
            """)

if not npm_installed():
    print('FATAL: Node.js is not installed (os is not in your PATH).')
    print('FATAL: Exiting...')
    exit()
   
if errors_in_java_home_and_path():
    print('INFO: If needed, download and install JDK\n\n     {jv}\n\nfrom\n\n     {jdk_path}\n\nand make sure it is in your path, and that JAVA_HOME is set.'.format(jv=expected_java_version,jdk_path=jdk_path))

    print('FATAL: Exiting...')
    exit()


if android_home is None and android_sdk_root is None:
    print('FATAL: ANDROID_HOME and ANDROID_SDK_ROOT are not defined. Set at least one in your environment.')
    print("INFO: This may indicate you haven't downloaded the ANDROID SDK yet." )
    print('INFO: Download the Android SDK from https://developer.android.com/studio')
    print('FATAL: Exiting...')
    exit()

canonical_java_home_path = os.environ.get('JAVA_HOME')
osified_java_home_path = canonical_java_home_path.replace('\\','\\\\')

android_sdk_root = android_home if android_home else android_sdk_root

if not exists_insensitive(android_sdk_root):
    print('FATAL: ANDROID_SDK_ROOT variable is set but directory does not exist. Set it CORRECTLY in your environment.')
    print('FATAL: Exiting...')
    exit()

if not path_inspected_and_confirmed(canonical_java_home_path,android_sdk_root):
    print('FATAL: Exiting...')
    exit()

error_count = 0

if not exists_insensitive(bt):
    print('FATAL: bundletool.jar does not exist. Please specify the correct path to it.')
    print('INFO: Download it from {bt_loc}'.format(bt_loc=bt_loc))
    print('INFO: And ideally copy it to {bt}'.format(bt=bt))
    error_count += 1

if not exists_insensitive(package_json_path):
    print('FATAL: package.json does not exist. Run this from an initialized project directory.')
    error_count += 1

if not exists_insensitive("android"):
    print('FATAL: "android" does not exist. This does not appear to be a React-Native project dir.')
    error_count += 1

if not exists_insensitive(os.path.join(android_sdk_root,cmdline_tools_path)):
    print(os.path.join(android_sdk_root,cmdline_tools_path))
    print('FATAL: Command-line tools (latest) are not installed in Android SDK.')
    error_count += 1

if not exists_insensitive(os.path.join(android_sdk_root,'ndk',ndk_version)):
    print('FATAL: Android SDK NDK version {ndk_version} not installed.'.format(ndk_version=ndk_version))
    error_count += 1

for btv in build_tools_versions:
    if not exists_insensitive(os.path.join(android_sdk_root,'build-tools',btv)):
        print('FATAL: Android SDK build-tools version {btv} not installed.'.format(btv=btv))
        error_count += 1

if not shutil.which(adb_command):
    print('FATAL: adb command not found. Set it in your path (install platform-tools if needed).')
    error_count += 1

if error_count > 0:
    print('FATAL: Exiting...')
    exit()

if not shutil.which(emu):
    print('WARN: Emulator not found. Did you intend to install it?')

# Call the function to check if Java 20 is installed
if correct_version_of_java_installed(expected_java_version):
    print("INFO: Correct version of java installed.")
else:
    print('ERROR: Go download and install JDK {jv}, and make sure it is in your path.'.format(jv=expected_java_version))

    print('INFO: Download link: {jdk_path}'.format(jdk_path=jdk_path))

compare_expected_npm_package_versions_to_latest_available()

adjust_package_json(package_json_path)

remove_tsx_and_create_app_js()

if not exists_insensitive(".prettierrc"):
    with open('.prettierrc', 'w') as rc_file:
        rc_file.write(prettier_rc)

    print("INFO: .prettierrc file created.")

add_gradle_java_home(gradle_properties_path, osified_java_home_path)

add_keys_to_gradle_properties(gradle_properties_path)

create_universal_json(universal_json_path, universal_json_contents)

change_gradle_wrapper_distribution_url(gradle_wrapper_properties_path, new_distribution_url)

add_signing_config_to_build_gradle(build_gradle_path)

update_build_gradle_release_section(gradle_properties_path)

if keytool_missing(osified_java_home_path):
    print('FATAL: Exiting...')
    exit()
 
generate_keystore()

print("\nINFO: Be sure to:",post_config_steps)
print('\nINFO: Remember: output from this script is in {output_file}'.format(output_file=output_file))
