"""doomdumper.py: automated dumping and registration of writable game installation.

Requests the user to open their game, dumps with UWPDumper to a custom
location, uninstalls the encrypted game, and registers the writable game.

Copyright (c) 2021 SEWsam
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with UWP-DOOMdumper.  If not, see <https://www.gnu.org/licenses/>.
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import winreg
import zipfile
from json import JSONDecodeError

import psutil
from colorama import init

_updated = '2021-04-14'
_game_version = '1.0.5.0'

init(autoreset=True)
IMPORTANT = '[41m[30m'
INFO = '[44m[2m[37m'


def size_converter(bytesize):
    """Get human readable size from size in bytes."""
    units = ('Bytes', 'KB', 'MB', 'GB', 'TB', 'PB')
    value = float(bytesize)
    unit = 0
    while value >= 1024.00:
        value = value / 1024
        unit += 1

    return round(value, 2), units[unit]


def confirm(prompt):
    """Continue to ask for input until the user enters yes or no"""
    while True:
        confirmation = input(prompt + "[0m (yes/no): ")

        if confirmation.lower() in ('yes', 'y'):
            return True
        elif confirmation.lower() in ('no', 'n'):
            return False
        else:
            print("[33mPlease enter either 'yes' or 'no'")
            print()
            continue


def check_dumpable():
    """Check package info and return if game can be dumped"""
    print("Checking if DOOM Eternal is already 'moddable'...")

    p = subprocess.Popen(  # Get package info as json
        ['powershell.exe', 'Get-appxpackage -allusers *BethesdaSoftworks.DOOMEternal-PC* | ConvertTo-Json'],
        stdout=subprocess.PIPE
    )
    out, err = p.communicate()

    try:
        game_json = json.loads(out)
    except JSONDecodeError:
        print("[31mCouldn't check DOOM Eternal installation status. Is it not installed?")
        return False, None

    if game_json['Status'] != 0:
        print("[31mAn update is in progress for DOOM Eternal. Please update it first.")
        return False, None

    if game_json['Version'] != _game_version:
        print("[31mThe installed version of DOOM Eternal is not compatible with this version of DOOMdumper"
              " + EternalModInjector")
        return False, None

    if game_json['SignatureKind'] == 0:  # A SignatureKind of 0 means the game is sideloaded using developer mode.
        print("Game is already 'moddable'. The game does NOT need to be dumped.")
        return False, game_json['InstallLocation']
    else:
        print("Game is not 'moddable' yet. Proceeding.")
        return True, None


def get_pid():
    """Get process ID of DOOM Eternal. Loop until found."""
    proc_name = 'DOOMEternalx64vk.exe'
    while True:
        input("Please launch DOOM Eternal, then press enter . . .")

        for proc in psutil.process_iter():
            if proc.name() == proc_name:
                print("DOOM Eternal process detected!")
                print("[33mPlease do NOT close DOOM Eternal.\n")

                return proc.pid
        else:
            print("[33mDOOM Eternal is not running. Trying again.")
            print()


def check_path(path):
    """Check the validity of the given path, and create it if needed"""

    # make sure path is using backslashes and has a trailing slash
    path = path.replace('/', '\\')
    if not path.endswith('\\'):
        path += '\\'
    if ' ' in path:
        print("[33mPlease enter a path with NO spaces")
        return path, False, None

    drive_letter = os.path.splitdrive(path)[0]

    if drive_letter == '':  # Require an absolute path
        print("[33mNo drive letter specified.")
        return path, False, None
    if not os.path.exists(drive_letter):
        print(f"[33mInvalid Path: The drive letter given does not exist: '{drive_letter}'")
        return path, False, None

    if not os.path.isdir(path):
        os.makedirs(path)
    elif os.listdir(path):
        if 'doom_dumper' in os.listdir(path):  # If this blank file exists, doom must have been dumped there
            confirmation = confirm(
                "DOOM Eternal already installed in given directory. Do you want to delete it in order to proceed?"
            )
            if confirmation:
                shutil.rmtree(path)
                os.makedirs(path)
            else:
                return path, False, None
        else:
            print(f"[33mThe path given is not empty.")  # otherwise, just reject this path
            return path, False, None

    free_bytes = psutil.disk_usage(drive_letter).free
    free, unit = size_converter(free_bytes)
    disallowed = ('Bytes', 'KB', 'MB')
    if free > 75.00 and unit not in disallowed:
        valid = True
    else:
        print(f"[33mNot enough space in '{path}'({free} free, 75GB required)")
        valid = False

    return path, valid, str(free) + unit


def dump(pid, path):
    """Use UWPInjector to dump DOOM Eternal"""
    os.system("title DOOMdumper ^| Dumping game... do not close DOOM or this window")
    print(f"Copying game to new installation directory: '{path}]'")
    print(IMPORTANT + "STARTING DUMP. DO NOT CLOSE THIS APPLICATION")
    print(IMPORTANT + '=' * 44)

    p = subprocess.Popen(
        ['UWPInjector.exe', '-p', f'{pid}', '-d', f'{path[:-1]}']
    )
    p.wait()

    print(IMPORTANT + '=' * 44)
    print(IMPORTANT + "               DUMP COMPLETE                ")
    psutil.Process(pid).terminate()
    os.system('title DOOMdumper')
    with open(path + 'doom_dumper', 'w'):
        pass


def check_aborted():
    try:
        with open('aborted') as aborted:
            path = aborted.read()

        if os.path.isfile(path + 'doom_dumper'):
            print("Last time you ran this, you cancelled the re-installation process.")
            input("Press enter to resume this process, or CTRL+C to exit  . . . ")
            return path
        else:
            os.remove('aborted')
    except FileNotFoundError:
        pass

    return None


def extract_modinjector(dst):
    with zipfile.ZipFile('EternalModInjector-UWP.zip', 'r') as f:
        print(f"Extracting EternalModInjector-UWP to '{dst}'")
        f.extractall(dst)


def register(path):
    """Remove the original game installation and register the dumped/'moddable' version"""
    confirmation = confirm(IMPORTANT +
                           "Your old DOOM Eternal is about to be uninstalled; the new copy will be kept. "
                           "Continue?")
    if confirmation:
        p = subprocess.Popen(
            ['powershell', 'Get-appxpackage -allusers *BethesdaSoftworks.DOOMEternal-PC* | Remove-AppxPackage']
        )
        p.wait()
        print("Old installation removed")

        print("Setting up your new game installation")
        p = subprocess.Popen(
            ['powershell', f'Add-AppxPackage -Register {path}AppxManifest.xml']
        )
        p.wait()
    else:
        with open('aborted', 'w') as f:
            f.write(path)
        print(f"[33mYour original game was not uninstalled.\n"
              f"You can run this again to complete the process or delete the new copy '{path}'")
        sys.exit(0)


def enable_devmode():
    """Enables Development Mode for sideloading"""
    registry_key = winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AppModelUnlock", 0, winreg.KEY_WRITE
    )
    winreg.SetValueEx(registry_key, "AllowDevelopmentWithoutDevLicense", 0, winreg.REG_DWORD, 1)


def welcome():
    os.system('title DOOMdumper')
    print(INFO + ' ' * 53)
    print(INFO + "  UWP-DOOMdumper                                     ")
    print(INFO + f"    by SEWsam, updated {_updated}                    ")
    print(INFO + ' ' * 53)
    print(INFO + "    ALLOWS MODS ON GAME PASS                         ")
    print(INFO + ' ' * 53)
    print(INFO + "    A tool that grants full control over your UWP    ")
    print(INFO + "     DOOM Eternal installation, by reinstalling the  ")
    print(INFO + "    game to a custom location.                       ")
    print(INFO + ' ' * 53)
    print()

    print('[33m' +
          "This program will allow you to utilize EternalModInjector, with the\n"
          "gamepass/Windows Store version of DOOM Eternal.\n"
          "Your game will be copied to a location of your choosing, then removed\n"
          "from the original location. You'll need [31m75GB[33m free for this.\n"

          )
    input("Press enter to see update warning.")
    print()

    print('[33m' +
          "A WARNING ABOUT GAME UPDATES: Currently, there is no way to get updates\n"
          "through the Microsoft Store if your game is modded. To update, you will\n"
          "need to [31muninstall and reinstall[33m the game, then run the latest tools to\n"
          "use mods again.\n"
          )
    input("Press enter to proceed . . .")
    print()


def main():
    dumpable, current_path = check_dumpable()
    if dumpable:
        aborted_path = check_aborted()
        if aborted_path is None:
            while True:
                path = input("Please enter the path to where you would like to move your game to: ")
                path, valid, free = check_path(path)
                if not valid:
                    print()
                    continue

                confirmation = confirm(f"Are you sure you want to install your game to '{path}', with {free} free?")
                if confirmation:
                    break
                else:
                    print()
                    continue
            pid = get_pid()
            print("About to dump game. This can take [31m20-40[0m minutes depending on if you have a HDD or SSD")
            input("Press enter to proceed to dumping, or 'CTRL+C' to cancel . . .")
            dump(pid, path)
        else:
            path = aborted_path

        register(path)
        extract_modinjector(path)
        print(f"[32mComplete! Your game is installed at '{path}', alongside EternalModInjector")
        print("[33mOne last step. You need to install the main campaign/dlc licenses ")
        input("Press enter to open the Store. Once in, press the '<-' back button in the top left to go to the dlcs")
        os.system('start ms-windows-store://pdp/?productId=9NB788JLSR97')  # p2 <- <- back twice
        os.system('start ms-windows-store://pdp/?productId=9P2MSCGJPKJC')  # pt1 <- back once
        os.system('start ms-windows-store://pdp/?productId=9PC4V8W0VCWT')  # campaign
    else:
        if current_path is not None:
            print("Your game is already moddable; the included version of EternalModInjector is being extracted")
            extract_modinjector(current_path)


if __name__ == '__main__':
    try:
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            print("Administrator Mode required. Please re-run this program as Administrator.")
            sys.exit(1)

        welcome()
        enable_devmode()
        main()
    except KeyboardInterrupt:
        pass
    finally:
        input("\nPress enter to exit . . .")

# TODO:
#   If possible, in future releases allow the ?:\WindowsApps\MSIXVC\1605DD05-06F3-4181-A3CB-DEA5317B1291
#   file to be backed up, which can allow for file repair+faster updates.
#   THE ISSUE: All UWP volumes cannot normally be accessed even by an administrator.

# TODO: Maybe extract to current directory by default in the future?
# TODO: More ways to handle duplicate installations
