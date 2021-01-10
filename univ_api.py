#! /usr/bin/python3
import requests
import re


def login_session(login: str, password: str):
    univses = requests.session()

    regex = """<input type="hidden" name="execution" value="([a-zA-Z0-9_=-]+)"/>"""
    response = univses.get("https://cas.univ-rouen.fr/login")

    execution_token = re.findall(regex, response.text)

    if execution_token == None:
        raise Exception("login page return invalid content")

    execution_token = execution_token[0]

    post_data = "username={}&password={}&execution={}&_eventId=submit&geolocation=".format(login, password, execution_token)
    custom_header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = univses.post("https://cas.univ-rouen.fr/login", data=post_data, headers=custom_header)

    # Login the cas session to universitice

    univses.get("https://universitice.univ-rouen.fr/login/index.php?authCAS=CAS")
    response = univses.get("https://cas.univ-rouen.fr/login?service=https%3A%2F%2Fwebtv.univ-rouen.fr%2Flogin%2Fiframe%2F%3Fnext%3D%252Fpermalink%252Fv125f75c6c428x7iwl0w%252Fiframe%252F")

    return univses
