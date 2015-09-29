# -*- coding: utf-8 -*-

import os
import urllib2

import pymongo
import requests
from flask import request, Flask
import unicodecsv
import random


client = pymongo.MongoClient(os.environ.get('MONGO_URL'))
db = client['push-learn']


BASE_API_URL = 'https://api.justyo.co'


class Entry(object):

    def __init__(self):

        self.question_text = None

        self.left_button_text = None
        self.right_button_text = None

        self.correct_button_text = None

        self.correct_answer_followup_text = None
        self.incorrect_answer_followup_text = None

        self.followup_left_button_text = None
        self.followup_right_button_text = None


apps = db.apps.find()
all_apps_entries = {}

for app in apps:
    entries = {}

    response = urllib2.urlopen(app.get('csv_url'))
    reader = unicodecsv.reader(response, encoding='utf-8')

    for row in reader:

        if row[0] == 'question':
            continue  # header row

        entry = Entry()
        entry.question_text = row[0]
        entry.left_button_text = row[1]
        entry.right_button_text = row[2]
        entry.correct_button_text = row[3]
        entry.correct_answer_followup_text = row[4]
        entry.incorrect_answer_followup_text = row[5]
        entry.followup_left_button_text = row[6]
        entry.followup_right_button_text = row[7]

        entries[entry.question_text] = entry

    all_apps_entries[app.get('app_username')] = entries


def send_question_to_user(app, username, entry):
    response_pair = entry.left_button_text + '.' + entry.right_button_text
    params = {
        'text': entry.question_text,
        'response_pair': response_pair,
        'username': username,
        'api_token': app.get('api_token'),
        'sound': 'silent'
    }
    res = requests.post('%s/yo/' % BASE_API_URL, json=params)
    return res


def send_a_question_to_all_users(app):
    entries = all_apps_entries[app.get('app_username')]
    question_text = random.choice(entries.keys())
    entry = entries[question_text]

    url = BASE_API_URL + '/apps/' + str(app.get('_id')) + '/users/?api_token=' + app.get('api_token')
    response = requests.get(url)
    users = response.json().get('results')

    for user in users:
        send_question_to_user(app, user.get('username'), entry)

    return 'OK'


flask_app = Flask(__name__)


@flask_app.route("/trigger/", methods=['GET'])
def trigger():
    apps = db.apps.find()
    for app in apps:
        send_a_question_to_all_users(app)


@flask_app.route("/demo/<app_username>/", methods=['POST'])
def demo(app_username):

    app = db.apps.find_one({'app_username': app_username.upper()})

    username = request.json.get('username')

    entries = all_apps_entries[app.get('app_username')]
    question_text = random.choice(entries.keys())
    entry = entries[question_text]
    response_pair = entry.left_button_text + '.' + entry.right_button_text
    params = {
        'text': question_text,
        'response_pair': response_pair,
        'username': username,
        'api_token': app.get('api_token'),
        'sound': 'silent'
    }
    response = requests.post('%s/yo/' % BASE_API_URL, json=params)

    print response, response.text
    return response.text


@flask_app.route('/learn/<app_username>/reply/', methods=['POST'])
def incoming_reply(app_username):

    app = db.apps.find_one({'app_username': app_username.upper()})

    payload = request.get_json(force=True)
    username = payload.get('username')

    reply_object = payload.get('reply')
    reply_text = reply_object.get('text')

    reply_to_object = payload.get('reply_to')
    question_text = reply_to_object.get('text')
    entries = all_apps_entries[app.get('app_username')]
    entry = entries.get(question_text)

    if not entry and reply_text.startswith('Hit me again'):
        question_text = random.choice(entries.keys())
        entry = entries[question_text]
        return send_question_to_user(app, username, entry)

    if reply_text == entry.correct_button_text:
        follow_up_text = entry.correct_answer_followup_text
    else:
        follow_up_text = entry.incorrect_answer_followup_text

    response_pair = entry.followup_left_button_text + '.' + entry.followup_right_button_text

    params = {"api_token": app.get('api_token'),
              "response_pair": response_pair,
              "text": follow_up_text,
              "username": username,
              'sound': 'silent'}

    res = requests.post('https://api.justyo.co/yo/',
                        json=params)

    print res, res.text

    return res.text


if __name__ == "__main__":
    flask_app.debug = True
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
