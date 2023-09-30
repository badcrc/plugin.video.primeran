# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import sys
import json

import xbmc
import xbmcgui
import xbmcplugin

if sys.version_info[0] >= 3:
  import urllib.request as urllib2
  from urllib.parse import urlencode, parse_qsl, quote_plus
  unicode = str
else:
  import urllib2
  from urllib import urlencode, quote_plus
  from urlparse import parse_qsl

import xbmcaddon
import os.path

from .log import LOG
from .primeran import *
from .addon import *
from .gui import *

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

def get_url(**kwargs):
  for key, value in kwargs.items():
    if isinstance(value, unicode):
      kwargs[key] = value.encode('utf-8')
  return '{0}?{1}'.format(_url, urlencode(kwargs))

def play(params):
  LOG('play - params: {}'.format(params))

  item = p.get_item(params['slug'])

  import inputstreamhelper
  is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
  if not is_helper.check_inputstream():
    show_notification(addon.getLocalizedString(30202))
    return

  for stream in item['manifests']:
    if stream['drmConfig']['type'] == 'widevine':
      break

  url = 'https://primeran.site%s' % stream['manifestURL']
  license_url = 'https://primeran.site%s' % stream['drmConfig']['licenseAcquisitionURL']

  LOG('url: {} license_url: {}'.format(url, license_url))

  #headers = 'X-Profileid={}&X-Token={}'.format(p.get_account(),p.get_token())

  play_item = xbmcgui.ListItem(path=url)
  play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
  play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
  play_item.setProperty('inputstream.adaptive.license_key', '{}||R{{SSM}}|'.format(license_url))
  #play_item.setProperty('inputstream.adaptive.stream_headers', headers)
  play_item.setMimeType('application/dash+xml')
  play_item.setContentLookup(False)

  if sys.version_info[0] < 3:
    play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
  else:
    play_item.setProperty('inputstream', 'inputstream.adaptive')

  xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

  LOG("Playing: {}".format(url))
  from .player import MyPlayer
  player = MyPlayer()
  monitor = xbmc.Monitor()
  while not monitor.abortRequested() and player.running:
    monitor.waitForAbort(10)
  LOG('Playback finished')

def clear_session():
  p.delete_session_files()

def logout():
  clear_session()
  p.cache.remove_file('auth.key')

def login():
  def ask_credentials(email=''):
    email = input_window(addon.getLocalizedString(30163), email) # Username
    if email:
      password = input_window(addon.getLocalizedString(30164), hidden=True) # Password
      if password:
        return email, password
    return None, None

  email, password = ask_credentials()
  if email:
    success, _ = p.login(email, password)
    if success:
      clear_session()
    else:
      show_notification(addon.getLocalizedString(30166)) # Failed

def list_user():
  open_folder(addon.getLocalizedString(30160)) # Change user
  add_menu_option(addon.getLocalizedString(30183), get_url(action='login')) # Login with username
  add_menu_option(addon.getLocalizedString(30150), get_url(action='logout')) # Close session
  close_folder()

def list_profiles(params):
  LOG('list_profiles: {}'.format(params))
  profiles = p.get_profiles()
  if 'id' in params:
    if params['name'] == 'select':
      p.change_profile(profiles, params['id'])
    xbmc.executebuiltin("Container.Refresh")
    return

  current_profile = p.get_account()

  open_folder(addon.getLocalizedString(30180)) # Profiles
  for profile in profiles:
    name = profile['name']
    if profile['id'] == current_profile:
      name = '[B][COLOR blue]' + name + '[/COLOR][/B]'
    img_url = p.get_profile_image_url(profile['avatar'])
    art = {'icon': img_url} if img_url else None
    select_action = get_url(action='profiles', id=profile['id'], name='select')
    add_menu_option(name, select_action, art=art)
  close_folder(cacheToDisc=False)


def list_category(category):
  if category == 'movies':
    open_folder(addon.getLocalizedString(30105))
  elif category == 'documentaries':
    open_folder(addon.getLocalizedString(30120))
  elif category == 'kids':
    open_folder(addon.getLocalizedString(30121))
  elif category == 'tv-shows':
    open_folder(addon.getLocalizedString(30106))
  elif category == 'mylist':
    open_folder(addon.getLocalizedString(30102))
  else:
    open_folder(addon.getLocalizedString(30106))

  categories = p.get_categories(category)

  for cat in categories:
    name = cat['name'].encode('utf-8')
    add_menu_option(name, get_url(action='listing', type=category, name=name, id=cat['id']))
  close_folder()



def listing(type, name, id):
  LOG('listing: type: {} name: {} id: {}'.format(type, name, id))

  if type == 'movies':
    items = p.get_categories(type,id)
    xbmcplugin.setPluginCategory(_handle, 'movies')
    xbmcplugin.setContent(_handle, 'movies')
    mediatype = 'movie'
  elif type == 'documentaries':
    items = p.get_categories(type,id)
    xbmcplugin.setPluginCategory(_handle, 'movies')
    xbmcplugin.setContent(_handle, 'movies')
    mediatype = 'movie'
  elif type == 'tv-shows':
    items = p.get_categories(type,id)
    xbmcplugin.setPluginCategory(_handle, 'tvshows')
    xbmcplugin.setContent(_handle, 'tvshows')
    mediatype = 'tvshow'
  elif type == 'kids':
    items = p.get_categories(type,id)
    xbmcplugin.setPluginCategory(_handle, 'movies')
    xbmcplugin.setContent(_handle, 'movies')
    mediatype = 'movie'
  elif type == 'seasons':
    items = p.get_seasons(id)
    xbmcplugin.setPluginCategory(_handle, 'seasons')
    xbmcplugin.setContent(_handle, 'seasons')
    mediatype = 'season'
  elif type == 'episodes':
    items = p.get_episodes(id,name)
    xbmcplugin.setPluginCategory(_handle, 'episodes')
    xbmcplugin.setContent(_handle, 'episodes')
    mediatype = 'episode'
  elif type == 'continue-watching':
    items = p.get_continue_watching()
    xbmcplugin.setPluginCategory(_handle, 'movies')
    xbmcplugin.setContent(_handle, 'movies')
    mediatype = 'movie'
  elif type == 'my-list':
    items = p.get_my_list()
    xbmcplugin.setPluginCategory(_handle, 'movies')
    xbmcplugin.setContent(_handle, 'movies')
    mediatype = 'movie'
  else:
    xbmcplugin.setPluginCategory(_handle, 'movies')
    xbmcplugin.setContent(_handle, 'movies')
    mediatype = 'movie'


  for item in items:
    name = item['title'].encode('utf-8')
    try:
      slug = slug='/media/%s' % item['media_id']
    except:
      slug = slug='/media/%s' % item['slug']
    list_item = xbmcgui.ListItem(label=name)
    if item['collection'] == 'media':
      list_item.setProperty('IsPlayable', 'true')

    try:
      year = item['production_year']
    except:
      year = ''

    try:
      plot = item['description']
    except:
      plot = ''

    try:
      duration = item['duration']
    except:
      duration = '0'

    info = {'mediatype': mediatype,
            'title': name,
            'plot': plot,
            'duration': duration,
            'year': year
    }
    list_item.setInfo('video', info)

    try:
      thumb_file = ''
      fanart_file = ''
      for img in item['images']:
        if type == 'episodes':
          if img['format'] == 3:
              thumb_file = img['file']
        else:
          if img['format'] == 2:
                thumb_file = img['file']

        if img['format'] == 1:
              fanart_file = img['file']

      list_item.setArt({
          'thumb': thumb_file,
          'fanart': fanart_file,
          })
    except Exception as e:
      LOG('Error: ' + str(e))
      pass

    if item['collection'] == 'media':
      xbmcplugin.addDirectoryItem(_handle, get_url(action='play', slug=slug), list_item, False)
    elif item['collection'] == 'seasons':
      xbmcplugin.addDirectoryItem(_handle, get_url(action='listing', type='episodes', name=name, id=slug), list_item, True)
    else:
      xbmcplugin.addDirectoryItem(_handle, get_url(action='listing', type='seasons', name=name, id=slug), list_item, True)

  xbmcplugin.endOfDirectory(_handle)



def router(paramstring):
  """
  Router function that calls other functions
  depending on the provided paramstring
  :param paramstring: URL encoded plugin paramstring
  :type paramstring: str
  """

  params = dict(parse_qsl(paramstring))
  LOG('params: {}'.format(params))
  if params:
    if params['action'] == 'play':
      play(params)
    elif params['action'] == 'continue':
      listing('continue-watching', 'continue-watching', 'continue-watching')
    elif params['action'] == 'list':
      listing('my-list', 'my-list', 'my-list')
    elif params['action'] == 'tv-shows':
      list_category('tv-shows')
    elif params['action'] == 'movies':
      list_category('movies')
    elif params['action'] == 'kids':
      list_category('kids')
    elif params['action'] == 'docs':
      list_category('documentaries')
    elif params['action'] == 'profiles':
      list_profiles(params)
    elif params['action'] == 'login':
      login()
    elif params['action'] == 'user':
      list_user()
    elif params['action'] == 'logout':
      logout()
    elif params['action'] == 'listing':
      listing(params['type'], params['name'], params['id'])
  else:
    # Main
    open_folder(addon.getLocalizedString(30101)) # Menu
    xbmcplugin.setContent(_handle, 'files')

    if p.logged:
      add_menu_option(addon.getLocalizedString(30122), get_url(action='continue'))
      add_menu_option(addon.getLocalizedString(30102), get_url(action='list'))
      add_menu_option(addon.getLocalizedString(30106), get_url(action='tv-shows'))
      add_menu_option(addon.getLocalizedString(30105), get_url(action='movies'))
      add_menu_option(addon.getLocalizedString(30121), get_url(action='kids'))
      add_menu_option(addon.getLocalizedString(30120), get_url(action='docs'))
      add_menu_option(addon.getLocalizedString(30180), get_url(action='profiles'))
      add_menu_option(addon.getLocalizedString(30160), get_url(action='user')) # Accounts
    else:
      add_menu_option(addon.getLocalizedString(30183), get_url(action='login')) # Login with username
    close_folder(cacheToDisc=False)


def run():
  global p
  LOG('profile_dir: {}'.format(profile_dir))
  p = Primeran(profile_dir)

  # Clear cache
  LOG('Cleaning cache. {} files removed.'.format(p.cache.clear_cache()))
  # Call the router function and pass the plugin call parameters to it.
  # We use string slicing to trim the leading '?' from the plugin call paramstring
  params = sys.argv[2][1:]
  router(params)
