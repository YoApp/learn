# -*- coding: utf-8 -*-

import os
import urllib2
import requests
from flask import request, Flask
import unicodecsv
import random


CSV_URL = os.environ.get('CSV_URL')
APP_ID = os.environ.get('APP_ID')
YO_API_TOKEN = os.environ.get('YO_API_TOKEN')
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


entries = {}

response = urllib2.urlopen(CSV_URL)
reader = unicodecsv.reader(response, encoding='utf-8')

for row in reader:

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


def send_a_question_to_all_users():
    question_text = random.choice(entries.keys())
    entry = entries[question_text]

    url = BASE_API_URL + '/apps/' + APP_ID + '/users/?api_token=' + YO_API_TOKEN
    response = requests.get(url)
    users = response.json().get('results')

    for user in users:
        username = user.get('username')
        response_pair = entry.left_button_text + '.' + entry.right_button_text
        params = {
            'text': question_text,
            'response_pair': response_pair,
            'username': username,
            'api_token': YO_API_TOKEN,
            'sound': 'silent'
        }
        response = requests.post('%s/yo/' % BASE_API_URL, json=params)

    print response, response.text
    return response.text


app = Flask(__name__)

@app.route("/trigger/", methods=['GET'])
def trigger():

    return send_a_question_to_all_users()


@app.route('/learn/reply/', methods=['POST'])
def incoming_reply():

    payload = request.get_json(force=True)
    username = payload.get('username')

    reply_object = payload.get('reply')
    reply_text = reply_object.get('text')

    reply_to_object = payload.get('reply_to')
    question_text = reply_to_object.get('text')
    entry = entries.get(question_text)

    if not entry and reply_text.startswith('Hit me again'):
        return send_a_question_to_all_users()

    if reply_text == entry.correct_button_text:
        follow_up_text = entry.correct_answer_followup_text
    else:
        follow_up_text = entry.incorrect_answer_followup_text

    response_pair = entry.followup_left_button_text + '.' + entry.followup_right_button_text

    params = {"api_token": YO_API_TOKEN,
              "response_pair": response_pair,
              "text": follow_up_text,
              "username": username}

    res = requests.post('https://api.justyo.co/yo/',
                        json=params)

    print res, res.text

    return res.text


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
