import signal
import os
import time
import telnetlib
import sys

from subprocess import Popen, PIPE, call
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice


SDK = "/Users/tarek/.mozbuild/android-sdk-macosx"
ADB = os.path.join(SDK, "platform-tools", "adb")
os.environ["ANDROID_SDK_ROOT"] = SDK
AVD = "mozemulator-x86-7.0"
emulator = os.path.join(SDK, "emulator", "emulator")
os.environ["ANDROID_AVD_HOME"] = "/Users/tarek/.mozbuild/android-device/avd"

def lprint(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()


class CTelnet(telnetlib.Telnet):
    def write_until(self, command):
        self.write('%s\n' % command)
        return self.read_until('OK', 10)


def verify_emulator():
    telnet_ok = False
    tn = None
    while not telnet_ok:
        try:
            tn = CTelnet('localhost', 5554)
            tn.read_until('OK', 10)
            tn.write_until('avd status')
            tn.write_until('redir list')
            tn.write_until('network status')
            tn.write('quit\n')
            tn.read_all()
            telnet_ok = True
        except Exception:
            raise
        finally:
            if tn is not None:
                tn.close()
        if not telnet_ok:
            lprint("+")
            time.sleep(1.)
    return telnet_ok


def adb(*args):
    cmd = [ADB] + list(args)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    return output, p.returncode


def check_for_device(name="emulator-5554", wait=True):
    def get_devices():
        return adb("devices")[0]
    if not wait:
        return name in get_devices()
    while wait:
        devices = get_devices()
        if name in devices:
            while adb("shell",  "getprop", "sys.boot_completed")[1] != 0:
                lprint(".")
                time.sleep(1.)
            verify_emulator()
            print("")
            return True
        time.sleep(1.)
    print("")
    return False


def dump_log(filename, reset=True):
    logs = device.shell("logcat -d")
    if logs is None:
        logs = 'None'
    f = open("emulator.log", "w")
    try:
        f.write(logs.encode("utf-8"))
    finally:
        f.close()
    if reset:
        device.shell('logcat -c')


cmd = [emulator, '-avd', AVD, '-gpu', 'on', '-skip-adb-auth', '-verbose',
        '-show-kernel', '-ranchu', '-selinux', 'permissive', '-memory', '3072',
        '-cores', '4']

# emulator running ?
if not check_for_device(wait=False):
    kill_it = True
    print("starting the emulator")
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    print("Waiting for its readiness")
    check_for_device(wait=True)
    print("Ready!")
else:
    kill_it = False

app = "org.mozilla.fenix.nightly"
activity = "org.mozilla.fenix.IntentReceiverActivity"

print("starting")
device = MonkeyRunner.waitForConnection(5, 'emulator-5554')
apk = device.shell('pm path %s' % app)

if apk.startswith('package:'):
    print("Nightly already installed")
else:
  print("installing fenix on the emulator")
  device.installPackage('firefox.apk')

device.shell('logcat -c')
print "launching fenix..."
extras = {"args": "-marionette"}
device.startActivity(component="%s/%s" % (app, activity), extras=extras)

# make marionette available locally
adb("reverse", "tcp:2828", "tcp:2828")

# here, need to wait for the browser to be ready by calling the marionette
# port until its responsive
time.sleep(5)

dump_log("fenix_start.log")

# now we can start the browsing here
import pdb; pdb.set_trace()

if kill_it:
    print("Closing emulator")
    adb("-s", "emulator-5554", "emu", "kill")


print("done")
