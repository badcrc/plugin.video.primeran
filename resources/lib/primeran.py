# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import sys
import json
import requests
import io
import os
import time
import re
from datetime import datetime

from .endpoints import endpoints
from .log import LOG, print_json
from .network import Network
from .cache import Cache

class Primeran(object):
    account = {'username': '', 'password': '',
                'account': '',
                'id': None,
                'profile_id': '0',
                'ui_language': 'eus',
                'token': ''}


    def __init__(self, config_directory):
        self.logged = False

        # Network
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'
        }

        self.net = Network()
        self.net.headers = headers

        # Cache
        self.cache = Cache(config_directory)
        if not os.path.exists(config_directory + 'cache'):
            os.makedirs(config_directory + 'cache')

        self.endpoints = endpoints

        # Tokens
        content = self.cache.load_file('auth.key')
        if content:
            data = json.loads(content)
            if 'token' in data:
                self.account['token'] = data['token']
                try:
                    self.account['username'] = data['account_name']
                except:
                    self.account['username'] = data['username']
                self.account['account'] = data['account']
                if data['id'] == None:
                    self.account['profile_id'] = data['profile_id']
                else:
                    self.account['profile_id'] = data['id']
                if data['ui_language'] == 1:
                    self.account['ui_language'] = 'es'
                elif data['ui_language'] == 2:
                    self.account['ui_language'] = 'eus'
                self.logged = True

    def get_token(self):
        return self.account['token']

    def get_account(self):
        return self.account['profile_id']

    def change_profile(self, profiles, profile_id):
        for profile in profiles:
            if profile['id'] == profile_id:
                self.account['username'] = profile['name']
                self.account['profile_id'] = profile['id']
                if profile['ui_language'] == 1:
                    self.account['ui_language'] = 'es'
                elif profile['ui_language'] == 2:
                    self.account['ui_language'] = 'eus'
                self.save_token_file(self.account)
                return True


    def get_profile_image_url(self, avatar_id):
        headers = self.net.headers.copy()
        avatar = ''

        params = {'token': self.account['token']}

        url = self.endpoints['avatars']
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')
        try:
            d = json.loads(content)
            for avatar in d:
                if avatar['id'] == avatar_id:
                    avatar = avatar['image']
                    break
        except Exception as e:
            LOG('Error: ' + str(e))
            pass
        return avatar

    def get_profiles(self):
        headers = self.net.headers.copy()
        profiles = []

        params = {'token': self.account['token']}

        url = self.endpoints['profiles']
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')

        try:
            d = json.loads(content)
            for profile in d:
                profiles.append(profile)
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        return profiles

    def get_item(self, slug):
        headers = self.net.headers.copy()
        item = {}

        params = {'token': self.account['token'], 'profileid': self.account['profile_id']}

        url = self.endpoints['media'] + '/' + slug
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')

        try:
            d = json.loads(content)
            if 'title' in d:
                item = d
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        return item

    def get_continue_watching(self):
        headers = self.net.headers.copy()
        items = []

        params = {'token': self.account['token'], 'profileid': self.account['profile_id']}

        url = self.endpoints['continue_watching']
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')

        try:
            d = json.loads(content)
            for item in d:
                if 'data' in item:
                    if item['collection'] == 'series':
                        item['data']['slug'] = item['media_id']
                    item['data']['collection'] = 'media'
                    items.append(item['data'])
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        return items

    def get_my_list(self):
        headers = self.net.headers.copy()
        items = []

        params = {'token': self.account['token'], 'profileid': self.account['profile_id']}

        url = self.endpoints['mylist']
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')
        try:
            d = json.loads(content)
            for item in d:
                if 'data' in item:
                    item['data']['collection'] = item['collection']
                    items.append(item['data'])
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        return items

    def get_seasons(self, slug):
        headers = self.net.headers.copy()
        seasons = []

        params = {'token': self.account['token'], 'profileid': self.account['profile_id']}

        real_slug = slug.split('/')[-1]

        url = self.endpoints['series'] + '/' + real_slug
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')

        try:
            d = json.loads(content)
            if 'seasons' in d:
                for season in d['seasons']:
                    season_data = {}
                    season_data['id'] = season['id']
                    season_data['number'] = season['number']
                    season_data['title'] = season['title']
                    season_data['slug'] = real_slug
                    season_data['episodes'] = len(season['episodes'])
                    season_data['collection'] = 'seasons'
                    seasons.append(season_data)
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        if len(seasons) == 1:
            return self.get_episodes(slug,seasons[0]['title'])

        return seasons

    def get_episodes(self, slug,name):
        headers = self.net.headers.copy()
        episodes = []

        params = {'token': self.account['token'], 'profileid': self.account['profile_id']}

        real_slug = slug.split('/')[-1]

        url = self.endpoints['series'] + '/' + real_slug
        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')

        try:
            d = json.loads(content)
            if 'seasons' in d:
                for season in d['seasons']:
                    if name != season['title']:
                        continue

                    for episode in season['episodes']:
                        episodes.append(episode)
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        return episodes

    def get_categories(self, type, id=''):
        headers = self.net.headers.copy()
        categories = []

        params = {'token': self.account['token'], 'profileid': self.account['profile_id']}
        if type == 'movies':
            url = self.endpoints['movies_%s' % self.account['ui_language']]
        elif type == 'tv-shows':
            url = self.endpoints['tv-shows_%s' % self.account['ui_language']]
        elif type == 'kids':
            url = self.endpoints['kids_%s' % self.account['ui_language']]
        elif type == 'documentaries':
            url = self.endpoints['documentaries_%s' % self.account['ui_language']]
        else:
            url = self.endpoints['movies_%s' % self.account['ui_language']]

        response = self.net.session.get(url, headers=headers, params = params)
        content = response.content.decode('utf-8')

        try:
            d = json.loads(content)
            if 'children' in d:
                for child in d['children']:
                    if 'name' in child:
                        try:
                            if 'slider' in child['name'].lower():
                                continue
                        except:
                            pass
                        if id == '':
                            categories.append(child)
                        elif int(id) == int(child['id']):
                            categories = child['children']
                            break
        except Exception as e:
            LOG('Error: ' + str(e))
            pass

        return categories

    def get_movie_category(self, children):
        headers = self.net.headers.copy()
        movies = []

        for movie in children:
            if 'title' in movie:
                movies.append(movie)
        return movies

    def login(self, email, password):
        headers = self.net.headers.copy()

        data = {
            'email': email,
            'password': password
        }

        url = self.endpoints['login']
        response = self.net.session.post(url, headers=headers, data=json.dumps(data))
        content = response.content.decode('utf-8')
        success = False
        try:
            d = json.loads(content)
            if 'token' in d:
                success = True
                self.save_token_file(d)
        except:
            pass

        return success, content

    def save_token_file(self, d):
        self.cache.save_file('auth.key', json.dumps(d, ensure_ascii=False))

    def delete_session_files(self):
        for f in ['access_token.conf', 'account.json','profile_id.conf', 'tokens.json']:
            self.cache.remove_file(f)
