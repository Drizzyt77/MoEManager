import json
import subprocess
import requests
import urllib.request
from time import sleep
import PySimpleGUI as sg

pbar = None
downloaded = None
size = None


def check_update():
    column_to_be_centered = [[sg.Text('Checking for Updates...', k='-TEXT-')]]

    layout = [[sg.Text(key='-EXPAND-', font='ANY 1', pad=(0, 0))],  # the thing that expands from top
              [sg.Text('', pad=(0, 0), key='-EXPAND2-'),  # the thing that expands from left
               sg.Column(column_to_be_centered, vertical_alignment='center', justification='center', k='-C-')]]

    window = sg.Window('Window Title', layout, resizable=True, finalize=True, no_titlebar=True, size=(250, 100))
    window['-C-'].expand(True, True, True)
    window['-EXPAND-'].expand(True, True, True)
    window['-EXPAND2-'].expand(True, False, True)
    window.Refresh()
    sleep(1)
    with open("appcfg.json", "r") as f:
        data = json.loads(f.read())
    version = data["version"]
    window['-TEXT-'].update(f"Current version {version} found")
    window.Refresh()
    sleep(.5)
    response = requests.get("https://api.github.com/repos/Drizzyt77/workout/releases/latest")

    latest_version = response.json()['name']
    window['-TEXT-'].update(f"Latest version {latest_version} found")
    window.Refresh()
    sleep(.5)

    if float(version) < float(latest_version):
        window['-TEXT-'].update("Starting update...")
        window.Refresh()
        url = f'https://github.com/Drizzyt77/workout/releases/download/{latest_version}/main.exe'
        filename = 'Workout App.exe'
        urllib.request.urlretrieve(url, filename)
        data["version"] = latest_version
        with open("appcfg.json", "w") as f:
            json.dump(data, f, indent=2)
        window['-TEXT-'].update("Update completed!")
        window.Refresh()
        sleep(2)
        subprocess.Popen(['Workout App.exe'])
    else:
        window['-TEXT-'].update("Up to date, running program!")
        window.Refresh()
        sleep(2)
        subprocess.Popen(['Workout App.exe'])


if __name__ == '__main__':
    check_update()
