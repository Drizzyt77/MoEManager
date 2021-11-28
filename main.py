import configparser
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

import psutil
import pytz as pytz

from rcon import Client
from steam.client import SteamClient

import PySimpleGUIQt as sg

file_addition = r'/WindowsPrivateServer/MOE/Saved/Config/WindowsServer/GameUserSettings.ini'

server_status = ""
update_time = None
latest_update = None
last_backup = None


class Status(object):
    def __init__(self, interval=30):
        self.interval = interval
        thread = threading.Thread(target=self.check_server_status, args=())
        thread.daemon = True
        thread.start()

    def check_server_status(self):
        global server_status
        while True:
            if "MOEServer.exe" in (p.name() for p in psutil.process_iter()):
                server_status = 'Online'
            else:
                server_status = ''
            time.sleep(self.interval)


class Backup(object):
    def __init__(self):
        data = get_config()
        try:
            backuptime = data['backuptime']
        except KeyError:
            backuptime = 60
        try:
            install_dir = data['install']
        except KeyError:
            return
        self.interval = backuptime
        self.install_dir = install_dir
        thread = threading.Thread(target=self.do_backup, args=())
        thread.daemon = True
        thread.start()

    def do_backup(self):
        global last_backup
        while True:
            if os.path.exists(os.path.join(self.install_dir, '/WindowsPrivateServer/MOE/Saved/SaveGames/')):
                num = len(os.listdir(self.install_dir + '/WindowsPrivateServer/MOE/Saved/SaveGames/'))
                shutil.make_archive('MoEBackup-' + str(num) + '-'+str(datetime.now(pytz.timezone("America/Chicago"))),
                                    'zip', os.path.join(self.install_dir, '/WindowsPrivateServer/MOE/Saved/SaveGames/'),
                                    os.path.join(self.install_dir, '/Backups'))
            time.sleep(self.interval)


class Update(object):
    def __init__(self):
        data = get_config()
        try:
            updatetime = data['updatetime']
        except KeyError:
            updatetime = 60
        self.interval = updatetime
        thread = threading.Thread(target=self.check_for_updates, args=())
        thread.daemon = True
        thread.start()

    def check_for_updates(self):
        global update_time
        global latest_update
        while True:
            with open("appcfg.json", "r") as f:
                data = json.loads(f.read())
            buildid = data["buildid"]
            client = SteamClient()
            client.anonymous_login()
            info = SteamClient.get_product_info(client, apps=[1371580])
            x = info['apps'][1371580]['depots']['branches']['public']['buildid']
            if buildid != x:
                subprocess.Popen(["powershell.exe", "./MoEServerControl.ps1", "-option", "Shutdown"])
                time.sleep(30)
                with open("appcfg.json", "r") as f:
                    data = json.loads(f.read())
                folder = data["install"]
                with open(folder + file_addition, "w") as f:
                    config = configparser.ConfigParser()
                    config.read("tmpcfg.ini")
                    config.write(f)
                time.sleep(30)
                subprocess.Popen(["powershell.exe", "./MoEServerControl.ps1", "-option", "Start"])
                with open("appcfg.json", "w") as f:
                    data["buildid"] = str(x)
                    json.dump(data, f, indent=2)
                latest_update = datetime.now(pytz.timezone("America/Chicago"))
            update_time = datetime.now(pytz.timezone("America/Chicago"))
            time.sleep(60 * self.interval)


def get_ini(file: str):
    config = configparser.ConfigParser()
    config.read(file)

    return config


def get_config():
    try:
        with open("appcfg.json", "r") as f:
            data = json.loads(f.read())
    except:
        with open("appcfg.json", "w") as f:
            f.write('{}')
            data = {}

    return data


def get_saved_location():
    data = get_config()
    try:
        install = data['install']
    except:
        install = None
    if install is None:
        install = 'Select an Install Location'

    return install


def update_config(section, key, value, file):
    print(section, key, value, file)
    if file is None:
        return
    # file = file + file_addition
    print(file)
    config = get_ini(file)
    if not os.path.exists(file):
        print("Path Error")
        return
    if key is None:
        try:
            config.add_section(section)
            with open(file, 'w') as f:
                config.write(f)
        except Exception as e:
            print(e)
    elif value is None:
        try:
            config[section][key] = ''
            with open(file, 'w') as f:
                config.write(f)
        except Exception as e:
            print(e)
    else:
        try:
            config[section][key] = value
            with open(file, 'w') as f:
                config.write(f)
        except Exception as e:
            print(e)


def refresh_players():
    try:
        with Client('127.0.0.1', 5778, passwd='123456', timeout=15.0) as client:
            response = client.run('GetPlayers')
            print("Response: ", response)
    except Exception as e:
        print("Exception: ", e)
        response = e

    return response


def get_update_refresh():
    data = get_config()
    try:
        updatetime = data['updatetime']
    except KeyError:
        updatetime = 60
    return updatetime


def get_backup_refresh():
    data = get_config()
    try:
        backuptime = data['backuptime']
    except KeyError:
        backuptime = 60
    return backuptime


def manager_settings_window():
    slider = [
        [
            sg.Text(f"Check for Updates every {get_update_refresh()} minute(s)", key='-UPDATE_CHECK-')
        ],
        [
            sg.Slider((1, 120), tooltip='How often to check for updates',
                      orientation='horizontal', resolution=10, key='-SLIDER-',
                      enable_events=True, default_value=get_update_refresh())
        ]
    ]
    slider2 = [
        [
            sg.Text(f"Backup save every {get_backup_refresh()} minutes(s)", key='-BACKUP_CHECK-')
        ],
        [
            sg.Slider((1, 120), tooltip='How often to backup your save',
                      orientation='horizontal', resolution=10, key='-SLIDER2-',
                      enable_events=True, default_value=get_backup_refresh())
        ]
    ]
    layout = [
        [
            sg.Column(slider)
        ],
        [
            sg.HSeperator()
        ],
        [
            sg.Column(slider2)
        ],
        [
            sg.HSeperator()
        ],
        [
            sg.Button("Save", key='-SAVE-', enable_events=True),
            sg.Button("Cancel", key='-CANCEL-', enable_events=True)
        ]
    ]
    win = sg.Window("MoE Manager Settings", keep_on_top=True, layout=layout, icon='Images/moe.ico')
    config = get_config()
    while True:
        event, values = win.read()
        if event is None:
            win.close()
            break
        elif event == '-SAVE-':
            config['updatetime'] = values['-SLIDER-']
            config['backuptime'] = values['-SLIDER2-']
            with open('appcfg.json', 'w') as f:
                json.dump(config, f, indent=2)
            sg.popup_quick_message("Settings Saved!", no_titlebar=True, keep_on_top=True,
                                   auto_close_duration=2, background_color='green', text_color='white')
            win.close()
            break
        elif event == '-SLIDER-':
            win['-UPDATE_CHECK-'].update(f"Check for Updates every {values['-SLIDER-']} minute(s)")
        elif event == '-SLIDER2-':
            win['-BACKUP_CHECK-'].update(f"Backup save every {values['-SLIDER2-']} minute(s)")
        elif event == sg.WINDOW_CLOSED or event == '-CANCEL-':
            win.close()
            break


def main():
    global server_status
    global update_time
    global latest_update
    test = Update()
    test2 = Status()
    test3 = Backup()
    install = [
        [
            sg.Button("Manager Settings", key='-MSETTINGS-', enable_events=True)
        ],
        [
            sg.In(default_text=get_saved_location(), size=(25, 1), enable_events=True, key="-FOLDER-", disabled=True),
            sg.FolderBrowse(initial_folder=get_saved_location())
        ],
        [
            sg.HSeperator()
        ],
        [
            sg.Text("Server Status:"),
            sg.Text("Offline", key="-STATUS-")
        ],
        [
            sg.Text("Latest update Check:"),
            sg.Text("---", key='-UPDATE_TIME-')
        ],
        [
            sg.Text("Next update Check:"),
            sg.Text("---", key='-NEXT_UPDATE_TIME-')
        ],
        [
            sg.Text("Last Update:"),
            sg.Text("---", key='-LATEST_UPDATE-')
        ],
        [
            sg.HSeperator()
        ],
        [
            sg.Button("Start Server", key='-START_SERVER-'),
            sg.Button("Reboot Sever", key='-REBOOT_SERVER-'),
            sg.Button("Shutdown Server", key='-SHUTDOWN_SERVER-')
        ]
    ]
    options = [
        [
            sg.Text("INI Options")
        ],
        [
            sg.Listbox(values=[], size=(40, 20), enable_events=True, key="-OPTIONS-")

        ],
        [
            sg.In(size=(20, 2), key="-ADD_SECTION-"),
            sg.Button('Add', key="-ADD_SECTION_BUTTON-"),
            sg.Button('Remove', key="-REMOVE_SECTION_BUTTON-")
        ]
    ]

    editor = [
        [
            sg.Text("Keys")
        ],
        [
            sg.Listbox(values=[], size=(40, 20), enable_events=True, key="-VALUES-")
        ],
        [
            sg.In(size=(20, 2), key="-ADD_KEY-"),
            sg.Button('Add', key="-ADD_KEY_BUTTON-"),
            sg.Button('Remove', key="-REMOVE_KEY_BUTTON-")
        ]
    ]
    edit_values = [
        [
            sg.Text("Values")
        ],
        [
            sg.In(size=(20, 1), key="-EDITS-")
        ],
        [
            sg.Button(button_text='Save', key="-SAVE-")
        ]
    ]
    layout = [
        [
            sg.Column(install),
            sg.Column(options),
            sg.VSeperator(),
            sg.Column(editor),
            sg.Column(edit_values)
        ]
    ]
    window = sg.Window("MoE Server Manager", layout, icon='Images\moe.ico')
    cur_selection = None
    cur_key = None
    folder = None
    data = get_config()
    try:
        install_location = data['install']
    except KeyError:
        install_location = os.curdir
    folder = install_location
    shutil.copy(install_location + file_addition, "./tmpcfg.ini")
    while True:
        event, values = window.read(timeout=1000, timeout_key='-REFRESH-')
        data = get_config()
        if not data:
            pass
        else:
            config = get_ini("tmpcfg.ini")
            try:
                window["-OPTIONS-"].update(config.keys())
            except (IndexError, KeyError):
                pass
        if event == "-FOLDER-":
            with open('appcfg.json', 'w') as f:
                data['install'] = values['-FOLDER-']
                json.dump(data, f, indent=2)
            folder = values["-FOLDER-"]
            try:
                # Get list of files in folder
                file_list = os.listdir(folder + file_addition[:-20])
            except:
                file_list = []

            filename = None
            for f in file_list:
                if os.path.isfile(
                        os.path.join(
                            folder + file_addition[:-20], f)) \
                        and f.lower() == 'GameUserSettings.ini':
                    filename = f
            if filename is None:
                continue
            config = get_ini(folder + file_addition)
            try:
                window["-OPTIONS-"].update(config.keys())
            except (IndexError, KeyError):
                pass
        elif event == "-OPTIONS-":
            if values["-OPTIONS-"]:
                folder = values["-FOLDER-"]
                config = get_ini("tmpcfg.ini")
                try:
                    cur_selection = str(values['-OPTIONS-'][0])
                except (IndexError, KeyError):
                    cur_selection = None
                try:
                    window["-VALUES-"].update(config[values['-OPTIONS-'][0]])
                    window['-ADD_SECTION-'].update(cur_selection)
                    window['-ADD_KEY-'].update('')
                    window['-EDITS-'].update('')
                except (IndexError, KeyError):
                    pass

        elif event == '-VALUES-':
            if cur_selection is not None:
                folder = values["-FOLDER-"]
                try:
                    # Get list of files in folder
                    file_list = os.listdir(folder + file_addition[:-20])
                except:
                    file_list = []

                filename = None
                for f in file_list:
                    if os.path.isfile(
                            os.path.join(
                                folder + file_addition[:-20], f)) \
                            and f.lower() == 'GameUserSettings.ini':
                        filename = f
                config = get_ini("tmpcfg.ini")
                try:
                    cur_key = values['-VALUES-'][0]
                except (IndexError, KeyError):
                    cur_key = None
                try:
                    window["-EDITS-"].update(config[cur_selection][values['-VALUES-'][0]])
                    window['-ADD_KEY-'].update(cur_key)
                except (IndexError, KeyError):
                    pass
        elif event == '-SAVE-':
            if cur_key is not None:
                if values["-EDITS-"] != '':
                    update_config(cur_selection, cur_key, values["-EDITS-"], "tmpcfg.ini")
                    sg.popup_quick_message('Setting Saved!', background_color='green',
                                           text_color='white', keep_on_top=True, auto_close_duration=1)
        elif event == '-ADD_SECTION_BUTTON-':
            if values['-ADD_SECTION-'] != '':
                if folder is None:
                    continue
                update_config(values['-ADD_SECTION-'], None, '', "tmpcfg.ini")
                config = get_ini("tmpcfg.ini")
                window['-OPTIONS-'].update(config.keys())
                window['-EDITS-'].update('')
                window['-VALUES-'].update('')
                window['-ADD_KEY-'].update('')
        elif event == '-ADD_KEY_BUTTON-':
            if values['-ADD_KEY-'] != '':
                if folder is None:
                    continue
                update_config(cur_selection, values['-ADD_KEY-'], '', "tmpcfg.ini")
                config = get_ini("tmpcfg.ini")
                window['-VALUES-'].update(config[cur_selection])
                window['-EDITS-'].update('')
                window['-ADD_KEY-'].update('')
        elif event == '-REMOVE_SECTION_BUTTON-':
            if cur_selection is not None:
                if folder is None:
                    continue
                config = get_ini("tmpcfg.ini")
                config.remove_section(cur_selection)
                with open("tmpcfg.ini", 'w') as f:
                    config.write(f)
                window['-OPTIONS-'].update(config.keys())
                window['-EDITS-'].update('')
                window['-VALUES-'].update('')
                window['-ADD_KEY-'].update('')
                window['-ADD_SECTION-'].update('')
        elif event == '-REMOVE_KEY_BUTTON-':
            if cur_key is not None:
                if folder is None:
                    continue
                config = get_ini("tmpcfg.ini")
                config.remove_option(cur_selection, cur_key)
                with open("tmpcfg.ini", 'w') as f:
                    config.write(f)
                window['-VALUES-'].update(config[cur_selection])
                window['-EDITS-'].update('')
                window['-ADD_KEY-'].update('')
        elif event == '-START_SERVER-':
            with open(folder + file_addition, "w") as f:
                config = configparser.ConfigParser()
                config.read("tmpcfg.ini")
                config.write(f)

            subprocess.Popen(['powershell.exe', './MoEServerControl.ps1', '-option', 'Start'])
        elif event == '-REBOOT_SERVER-':
            subprocess.Popen(['powershell.exe', './MoEServerControl.ps1', '-option', 'Shutdown'])
            time.sleep(15)
            with open(folder + file_addition, "w") as f:
                config = configparser.ConfigParser()
                config.read("tmpcfg.ini")
                config.write(f)
            time.sleep(15)
            subprocess.Popen(['powershell.exe', './MoEServerControl.ps1', '-option', 'Start'])
        elif event == '-SHUTDOWN_SERVER-':
            subprocess.Popen(['powershell.exe', './MoEServerControl.ps1', '-option', 'Shutdown'])
        elif event == '-MSETTINGS-':
            manager_settings_window()
        elif event == '-REFRESH-':
            if server_status == "":
                window['-STATUS-'].update('Offline ❌')
            else:
                window['-STATUS-'].update('Online ✅')
            try:
                utime = update_time.strftime('%m/%d at %I:%M%p')
            except AttributeError:
                utime = '---'
            try:
                next_time = update_time + timedelta(minutes=30)
                ntime = next_time.strftime('%m/%d at %I:%M%p')
            except TypeError:
                ntime = '---'
            try:
                last_update = latest_update.strftime('%m/%d at %I:%M%p')
            except AttributeError:
                last_update = '---'
            window['-UPDATE_TIME-'].update(str(utime))
            window['-NEXT_UPDATE_TIME-'].update(str(ntime))
            window['-LATEST_UPDATE-'].update(str(last_update))
            window.refresh()
            continue
        elif event is None:
            window.close()
            sys.exit()

    window.close()


if __name__ == '__main__':
    main()
