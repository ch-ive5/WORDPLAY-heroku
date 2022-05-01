from flask import Flask, render_template, request, url_for, redirect
from threading import Thread
from datetime import datetime
from pytz import timezone
import time
import smtplib
import os
import pickle
import find_connection
import find_opposite


# Copyright 2021 Johnathan Pennington | All rights reserved.


wordnet_index = None
wordnet_data = None
group_map = None
groups_without_opposites = None

wordnet_index_thread = None
wordnet_data_thread = None
group_map_thread = None
groups_without_opposites_thread = None


def tab_classes(active_tab=''):
    tab_class_dict = {'connect': '', 'opposite': '', 'about': ''}
    if active_tab in tab_class_dict:
        tab_class_dict[active_tab] = 'active-tab'
    else:
        'Passed invalid tab name to tab_classes()!'
    return tab_class_dict


def load_index():
    global wordnet_index
    with open('wordnet-index.pkl', 'rb') as file:
        wordnet_index = pickle.load(file)


def load_data():
    global wordnet_data
    with open('wordnet-data-0.pkl', 'rb') as file:
        wordnet_data = pickle.load(file)


def load_group_map():
    global group_map
    with open('group-map.pkl', 'rb') as file:
        group_map = pickle.load(file)


def load_groups_without_opposites():
    global groups_without_opposites
    with open('groups-without-opposites.pkl', 'rb') as file:
        groups_without_opposites = pickle.load(file)


def start_load_database_thread():
    global wordnet_data_thread
    global wordnet_index_thread
    global group_map_thread
    global groups_without_opposites_thread
    if wordnet_data_thread is None and wordnet_data is None:
        wordnet_data_thread = Thread(target=load_data)
        wordnet_data_thread.start()
    if wordnet_index_thread is None and wordnet_index is None:
        wordnet_index_thread = Thread(target=load_index)
        wordnet_index_thread.start()
    if group_map_thread is None and group_map is None:
        group_map_thread = Thread(target=load_group_map)
        group_map_thread.start()
    if groups_without_opposites_thread is None and groups_without_opposites is None:
        groups_without_opposites_thread = Thread(target=load_groups_without_opposites)
        groups_without_opposites_thread.start()


def join_thread(thread):
    if thread is not None:
        if thread.is_alive():
            thread.join(timeout=10.0)


SENDER = os.getenv("SENDER")
SENDER_PASS = os.getenv("SENDER_PASS")
RECIPIENT = os.getenv("RECIPIENT")


def admin_alert(subject, message):
    pacific_tz = timezone("US/Pacific")
    time_to_format = datetime.fromtimestamp(time.time(), tz=pacific_tz)
    second = round(float(time_to_format.strftime("%S.%f")), 2)
    formatted_datetime = time_to_format.strftime(f"%Y-%m-%d %H:%M:{second}")
    message = f'{formatted_datetime}\nWORDPLAY\n{message}\n{time.time()}'

    connection = smtplib.SMTP("smtp.mail.yahoo.com", port=587)  # or port=465
    connection.starttls()  # Make connection secure
    connection.login(user=SENDER, password=SENDER_PASS)
    connection.sendmail(
        from_addr=SENDER,
        to_addrs=RECIPIENT,
        msg=f"Subject: {subject}\n\n{message}"
    )
    connection.close()


def admin_alert_thread(subject, message):
    alert_args = [subject, message]
    alert_thread = Thread(target=admin_alert, args=alert_args)
    alert_thread.start()


start_load_database_thread()
app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
    error = 'That URL does not compute.'
    if request.path.startswith(url_for('about')):
        message_body = f'404 Redirect\n{request.url}\nPage not found. Rendered about.html.'
        admin_alert_thread('Web App - ERROR', message_body)
        tab_class = tab_classes('about')
        return render_template('about.html', tab_classes=tab_class), 404
    elif request.path.startswith(url_for('opposite')):
        message_body = f'404 Redirect\n{request.url}\nPage not found. Rendered opposite.html.'
        admin_alert_thread('Web App - ERROR', message_body)
        tab_class = tab_classes('opposite')
        return render_template('opposite.html', source='', error=error, tab_classes=tab_class), 404
    elif not request.path.startswith('/favicon.ico') and not request.path.startswith('/robots'):
        message_body = f'404 Redirect\n{request.url}\nPage not found. Rendered connect.html.'
        admin_alert_thread('Web App - ERROR', message_body)
        tab_class = tab_classes('connect')
        return render_template('connect.html', source='', target='', error=error, tab_classes=tab_class), 404


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/about')
def about():
    tab_class = tab_classes('about')
    return render_template('about.html', tab_classes=tab_class)


@app.route('/opposite')
def opposite():
    if 'word' in request.args:
        word = request.args['word']
    else:
        word = ''
    tab_class = tab_classes('opposite')
    return render_template('opposite.html', source=word, error='', tab_classes=tab_class)


@app.route('/opposite/random')
def opposite_random():
    global wordnet_data_thread
    global wordnet_data
    join_thread(wordnet_data_thread)
    word = find_connection.random_main_group_word(wordnet_data)
    destination = url_for('opposite', word=word)
    admin_alert_thread('Web App - Log', f'Opposite page random button click.\n'
                                        f'Request: {request.url}\nRedirect to: {request.url_root}{destination[1:]}\n'
                                        f'WORD: {word}')
    return redirect(destination)


@app.route('/opposite/query')
def opposite_result():

    global wordnet_index_thread
    global wordnet_index
    global wordnet_data_thread
    global wordnet_data
    global group_map_thread
    global group_map
    global groups_without_opposites_thread
    global groups_without_opposites

    if 'synset' in request.args:
        synset = request.args['synset']
    else:
        synset = ''
    if 'word' in request.args:
        word = request.args['word']
    else:
        word = ''

    join_thread(groups_without_opposites_thread)
    join_thread(wordnet_index_thread)
    join_thread(wordnet_data_thread)
    data = find_opposite.web_app_inquiry(wordnet_data, wordnet_index, groups_without_opposites, word, synset)

    if data['status'] == 'error':
        tab_class = tab_classes('opposite')
        admin_alert_thread('Web App - ERROR',
                           f'{request.url}\nWORD: {word}\nSYNSET: {synset}\n{data["message"]}')
        return render_template('opposite.html', source=word, error=data['message'], tab_classes=tab_class)
    else:
        tab_class = tab_classes()
        cleaned_word = find_connection.remove_non_wordnet_chars(word)
        if data['status'] == 'choose_synset':
            admin_alert_thread('Web App - Log',
                               f'{request.url}\nRendered opposite choose-synset page.\nWORD: {word}\nSYNSET: {synset}')
            return render_template('choose_synset.html', source=cleaned_word, synsets=data['data'],
                                   message=data['message'], tab_classes=tab_class)
        else:
            admin_alert_thread('Web App - Log',
                               f'{request.url}\nRendered opposite result page.\nWORD: {word}\nSYNSET: {synset}')
            return render_template('opposite_result.html', source=cleaned_word, info=data['message'],
                                   paths=data['data'], tab_classes=tab_class)


@app.route('/')
def connect():
    if 'source' in request.args:
        source = request.args['source']
    else:
        source = ''
    if 'target' in request.args:
        target = request.args['target']
    else:
        target = ''
    tab_class = tab_classes('connect')
    return render_template('connect.html', source=source, target=target, error='', tab_classes=tab_class)


@app.route('/connect/random')
def connect_random():
    global wordnet_data_thread
    global wordnet_data
    join_thread(wordnet_data_thread)
    source = find_connection.random_main_group_word(wordnet_data)
    target = find_connection.random_main_group_word(wordnet_data)
    destination = url_for('connect', source=source, target=target)
    admin_alert_thread('Web App - Log', f'Connect page random button click.\n'
                                        f'Request: {request.url}\nRedirect to: {request.url_root}{destination[1:]}\n'
                                        f'START: {source}\nTARGET: {target}')
    return redirect(destination)


@app.route('/connect/query')
def connect_result():

    global wordnet_index_thread
    global wordnet_index
    global wordnet_data_thread
    global wordnet_data
    global group_map_thread
    global group_map

    if 'source' in request.args:
        source = request.args['source']
    else:
        source = ''
    if 'target' in request.args:
        target = request.args['target']
    else:
        target = ''

    join_thread(group_map_thread)
    join_thread(wordnet_index_thread)
    join_thread(wordnet_data_thread)
    data = find_connection.web_app_inquiry(wordnet_data, wordnet_index, group_map, source, target)

    if data['status'] == 'error':
        admin_alert_thread('Web App - ERROR',
                           f'{request.url}\nSTART: {source}\nTARGET: {target}\n{data["message"]}')
        tab_class = tab_classes('connect')
        return render_template('connect.html', source=source, target=target,
                               error=data['message'], tab_classes=tab_class)
    else:
        admin_alert_thread('Web App - Log',
                           f'{request.url}\nRendered connect result page.\nSTART: {source}\nTARGET: {target}')
        tab_class = tab_classes()
        return render_template('connect_result.html', source=source, target=target,
                               info=data['message'], paths=data['data'], tab_classes=tab_class)


if __name__ == '__main__':
    app.run()
