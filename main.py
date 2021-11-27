import base64
import configparser
import json
import os
import subprocess
import threading
import time

from rcon import Client
from steam.client import SteamClient

import PySimpleGUIQt as sg

file_addition = r'/WindowsPrivateServer/MOE/Saved/Config/WindowsServer/GameUserSettings.ini'


class Update(object):
    def __init__(self, interval=30):
        self.interval = interval
        thread = threading.Thread(target=self.check_for_updates, args=())
        thread.daemon = True
        thread.start()

    def check_for_updates(self):
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
                time.sleep(60)
                subprocess.Popen(["powershell.exe", "./MoEServerControl.ps1", "-option", "Start"])
                with open("appcfg.json", "w") as f:
                    data["buildid"] = str(x)
                    json.dump(data, f, indent=2)
            time.sleep(60*self.interval)


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
    if file is None:
        return
    file = file + file_addition
    config = get_ini(file)
    if not os.path.exists(file):
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


def main():
    test = Update()
    install = [
        [
            sg.In(default_text=get_saved_location(), size=(25, 1), enable_events=True, key="-FOLDER-", disabled=True),
            sg.FolderBrowse(initial_folder=get_saved_location())
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
    window = sg.Window("MoE Setting Manager", layout, icon='Images\moe.ico')
    cur_selection = None
    cur_key = None
    folder = None
    while True:
        event, values = window.read(timeout=1000, timeout_key='-REFRESH-')
        data = get_config()
        if event is None:
            continue
        else:
            if not data:
                pass
            else:
                if data['install'] != '':
                    folder = data['install']
                    try:
                        file_list = os.listdir(folder + file_addition[:-20])
                    except:
                        file_list = []
                    filename = None
                    for f in file_list:
                        if os.path.isfile(
                                os.path.join(
                                    folder + file_addition[:-20], f)) \
                                and f.lower() == 'gameusersettings.ini':
                            filename = f
                    if filename is None:
                        pass
                    else:
                        config = get_ini(folder + file_addition)
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
                config = get_ini(folder + file_addition)
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
                config = get_ini(folder + file_addition)
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
                    update_config(cur_selection, cur_key, values["-EDITS-"], folder)
                    sg.popup_quick_message('Setting Saved!', background_color='green',
                                           text_color='white', keep_on_top=True, auto_close_duration=1)
        elif event == '-ADD_SECTION_BUTTON-':
            if values['-ADD_SECTION-'] != '':
                if folder is None:
                    continue
                update_config(values['-ADD_SECTION-'], None, '', folder)
                config = get_ini(folder + file_addition)
                window['-OPTIONS-'].update(config.keys())
                window['-EDITS-'].update('')
                window['-VALUES-'].update('')
                window['-ADD_KEY-'].update('')
        elif event == '-ADD_KEY_BUTTON-':
            if values['-ADD_KEY-'] != '':
                if folder is None:
                    continue
                update_config(cur_selection, values['-ADD_KEY-'], '', folder)
                config = get_ini(folder + file_addition)
                window['-VALUES-'].update(config[cur_selection])
                window['-EDITS-'].update('')
                window['-ADD_KEY-'].update('')
        elif event == '-REMOVE_SECTION_BUTTON-':
            if cur_selection is not None:
                if folder is None:
                    continue
                config = get_ini(folder + file_addition)
                config.remove_section(cur_selection)
                with open(folder + file_addition, 'w') as f:
                    config.write(f)
                config = get_ini(folder + file_addition)
                window['-OPTIONS-'].update(config.keys())
                window['-EDITS-'].update('')
                window['-VALUES-'].update('')
                window['-ADD_KEY-'].update('')
                window['-ADD_SECTION-'].update('')
        elif event == '-REMOVE_KEY_BUTTON-':
            if cur_key is not None:
                if folder is None:
                    continue
                config = get_ini(folder + file_addition)
                config.remove_option(cur_selection, cur_key)
                with open(folder + file_addition, 'w') as f:
                    config.write(f)
                config = get_ini(folder + file_addition)
                window['-VALUES-'].update(config[cur_selection])
                window['-EDITS-'].update('')
                window['-ADD_KEY-'].update('')
        elif event == '-REFRESH-':
            continue
        elif event == "OK" or event == sg.WIN_CLOSED:
            break

    window.close()


if __name__ == '__main__':
    main()
