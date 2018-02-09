# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import shutil
import tempfile
import time
import base64

class GaiaApp(object):

    def __init__(self, origin=None, name=None, frame=None, src=None):
        self.frame = frame
        self.frame_id = frame
        self.src = src
        self.name = name
        self.origin = origin

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class GaiaApps(object):

    def __init__(self, marionette):
        self.marionette = marionette
        js = os.path.abspath(os.path.join(__file__, os.path.pardir, 'atoms', "gaia_apps.js"))
        self.marionette.import_script(js)

    def get_permission(self, app_name, permission_name):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaApps.getPermission('%s', '%s')" % (app_name, permission_name))

    def set_permission(self, app_name, permission_name, value):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaApps.setPermission('%s', '%s', '%s')" %
                                                    (app_name, permission_name, value))

    def set_permission_by_url(self, manifest_url, permission_name, value):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaApps.setPermissionByUrl('%s', '%s', '%s')" %
                                                    (manifest_url, permission_name, value))

    def launch(self, name, manifest_url=None, entry_point=None, switch_to_frame=True, launch_timeout=None):
        self.marionette.switch_to_frame()

        if manifest_url:
            result = self.marionette.execute_async_script("GaiaApps.launchWithManifestURL('%s', %s)"
                                                          % (manifest_url, json.dumps(entry_point)), script_timeout=launch_timeout)
            assert result, "Failed to launch app with manifest_url '%s'" % manifest_url
        else:
            result = self.marionette.execute_async_script("GaiaApps.launchWithName('%s')" % name, script_timeout=launch_timeout)
            assert result, "Failed to launch app with name '%s'" % name
        app = GaiaApp(frame=result.get('frame'),
                      src=result.get('src'),
                      name=result.get('name'),
                      origin=result.get('origin'))
        if app.frame_id is None:
            raise Exception("App failed to launch; there is no app frame")
        if switch_to_frame:
            self.marionette.switch_to_frame(app.frame_id)
        return app

    @property
    def displayed_app(self):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_script('return GaiaApps.getDisplayedApp();')
        return GaiaApp(frame=result.get('frame'),
                       src=result.get('src'),
                       name=result.get('name'),
                       origin=result.get('origin'))

    def switch_to_displayed_app(self):
        self.marionette.switch_to_default_content()
        self.marionette.switch_to_frame(self.displayed_app.frame)

    def is_app_installed(self, app_name):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("GaiaApps.locateWithName('%s')" % app_name)

    def kill(self, app):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("GaiaApps.kill('%s');" % app.origin)
        assert result, "Failed to kill app with name '%s'" % app.name

    def kill_all(self):
        # First we attempt to kill the FTU, we treat it as a user app
        for app in self.running_apps(include_system_apps=True):
            if app.origin == 'app://ftu.gaiamobile.org':
                self.kill(app)
                break

        # Now kill the user apps
        self.marionette.switch_to_frame()
        self.marionette.execute_async_script("GaiaApps.killAll();")

    @property
    def installed_apps(self):
        apps = self.marionette.execute_async_script(
            'return GaiaApps.getInstalledApps();')
        result = []
        for app in [a for a in apps if not a['manifest'].get('role')]:
            entry_points = app['manifest'].get('entry_points')
            if entry_points:
                for ep in entry_points.values():
                    result.append(GaiaApp(
                        origin=app['origin'],
                        name=ep['name']))
            else:
                result.append(GaiaApp(
                    origin=app['origin'],
                    name=app['manifest']['name']))
        return result

    def running_apps(self, include_system_apps=False):
        '''  Returns a list of running apps
        Args:
            include_system_apps: Includes otherwise hidden System apps in the list
        Returns:
            A list of GaiaApp objects representing the running apps.
        '''
        include_system_apps = json.dumps(include_system_apps)
        self.marionette.switch_to_frame()
        apps = self.marionette.execute_script(
            "return GaiaApps.getRunningApps(%s);" % include_system_apps)
        result = []
        for app in [a[1] for a in apps.items()]:
            result.append(GaiaApp(origin=app['origin'], name=app['name']))
        return result


class GaiaData(object):

    def __init__(self, marionette, testvars=None):
        self.apps = GaiaApps(marionette)
        self.marionette = marionette
        self.testvars = testvars or {}
        js = os.path.abspath(os.path.join(__file__, os.path.pardir, 'atoms', "gaia_data_layer.js"))
        self.marionette.import_script(js)

        # TODO Bugs 1043562/1049489 To perform ContactsAPI scripts from the chrome context, we need
        # to import the js file into chrome context too
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        self.marionette.import_script(js)
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)

    def set_time(self, date_number):
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        self.marionette.execute_script("window.navigator.mozTime.set(%s);" % date_number)
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)

    @property
    def all_contacts(self):
        # TODO Bug 1049489 - In future, simplify executing scripts from the chrome context
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        result = self.marionette.execute_async_script('return GaiaDataLayer.getAllContacts();', special_powers=True)
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)
        return result

    @property
    def sim_contacts(self):
        # TODO Bug 1049489 - In future, simplify executing scripts from the chrome context
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        adn_contacts = self.marionette.execute_async_script('return GaiaDataLayer.getSIMContacts("adn");', special_powers=True)
        sdn_contacts = self.marionette.execute_async_script('return GaiaDataLayer.getSIMContacts("sdn");', special_powers=True)
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)
        return adn_contacts + sdn_contacts

    def insert_contact(self, contact):
        # TODO Bug 1049489 - In future, simplify executing scripts from the chrome context
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        mozcontact = contact.create_mozcontact()
        result = self.marionette.execute_async_script('return GaiaDataLayer.insertContact(%s);' % json.dumps(mozcontact), special_powers=True)
        assert result, 'Unable to insert contact %s' % contact
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)

    def insert_sim_contact(self, contact, contact_type='adn'):
        # TODO Bug 1049489 - In future, simplify executing scripts from the chrome context
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        mozcontact = contact.create_mozcontact()
        result = self.marionette.execute_async_script('return GaiaDataLayer.insertSIMContact("%s", %s);'
                                                      % (contact_type, json.dumps(mozcontact)), special_powers=True)
        assert result, 'Unable to insert SIM contact %s' % contact
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)
        return result

    def delete_sim_contact(self, moz_contact_id, contact_type='adn'):
        # TODO Bug 1049489 - In future, simplify executing scripts from the chrome context
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        result = self.marionette.execute_async_script('return GaiaDataLayer.deleteSIMContact("%s", "%s");'
                                                      % (contact_type, moz_contact_id), special_powers=True)
        assert result, 'Unable to insert SIM contact %s' % moz_contact_id
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)

    def remove_all_contacts(self):
        # TODO Bug 1049489 - In future, simplify executing scripts from the chrome context
        self.marionette.set_context(self.marionette.CONTEXT_CHROME)
        timeout = max(self.marionette.timeout or 60000, 1000 * len(self.all_contacts))
        result = self.marionette.execute_async_script('return GaiaDataLayer.removeAllContacts();', special_powers=True, script_timeout=timeout)
        assert result, 'Unable to remove all contacts'
        self.marionette.set_context(self.marionette.CONTEXT_CONTENT)

    def get_setting(self, name):
        return self.marionette.execute_async_script('return GaiaDataLayer.getSetting("%s")' % name)

    @property
    def all_settings(self):
        return self.get_setting('*')

    def set_setting(self, name, value):
        import json
        value = json.dumps(value)
        result = self.marionette.execute_async_script('return GaiaDataLayer.setSetting("%s", %s)' % (name, value))
        assert result, "Unable to change setting with name '%s' to '%s'" % (name, value)

    def _get_pref(self, datatype, name):
        self.marionette.switch_to_frame()
        pref = self.marionette.execute_script("return SpecialPowers.get%sPref('%s');" % (datatype, name), special_powers=True)
        return pref

    def _set_pref(self, datatype, name, value):
        value = json.dumps(value)
        self.marionette.switch_to_frame()
        self.marionette.execute_script("SpecialPowers.set%sPref('%s', %s);" % (datatype, name, value), special_powers=True)

    def get_bool_pref(self, name):
        """Returns the value of a Gecko boolean pref, which is different from a Gaia setting."""
        return self._get_pref('Bool', name)

    def set_bool_pref(self, name, value):
        """Sets the value of a Gecko boolean pref, which is different from a Gaia setting."""
        return self._set_pref('Bool', name, value)

    def get_int_pref(self, name):
        """Returns the value of a Gecko integer pref, which is different from a Gaia setting."""
        return self._get_pref('Int', name)

    def set_int_pref(self, name, value):
        """Sets the value of a Gecko integer pref, which is different from a Gaia setting."""
        return self._set_pref('Int', name, value)

    def get_char_pref(self, name):
        """Returns the value of a Gecko string pref, which is different from a Gaia setting."""
        return self._get_pref('Char', name)

    def set_char_pref(self, name, value):
        """Sets the value of a Gecko string pref, which is different from a Gaia setting."""
        return self._set_pref('Char', name, value)

    def set_volume(self, value):
        channels = ['alarm', 'content', 'notification']
        for channel in channels:
            self.set_setting('audio.volume.%s' % channel, value)

    def bluetooth_enable(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaDataLayer.enableBluetooth()")

    def bluetooth_disable(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaDataLayer.disableBluetooth()")

    @property
    def bluetooth_is_enabled(self):
        return self.marionette.execute_script("return window.navigator.mozBluetooth.enabled")

    @property
    def is_cell_data_enabled(self):
        return self.get_setting('ril.data.enabled')

    def connect_to_cell_data(self):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("return GaiaDataLayer.connectToCellData()", special_powers=True)
        assert result, 'Unable to connect to cell data'

    def disable_cell_data(self):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("return GaiaDataLayer.disableCellData()", special_powers=True)
        assert result, 'Unable to disable cell data'

    @property
    def is_cell_data_connected(self):
        return self.marionette.execute_script('return window.navigator.mozMobileConnections && ' +
                                              'window.navigator.mozMobileConnections[0].data.connected;')

    def enable_cell_roaming(self):
        self.set_setting('ril.data.roaming_enabled', True)

    def disable_cell_roaming(self):
        self.set_setting('ril.data.roaming_enabled', False)

    @property
    def is_wifi_enabled(self):
        return self.marionette.execute_script("return window.navigator.mozWifiManager && "
                                              "window.navigator.mozWifiManager.enabled;")

    def enable_wifi(self):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("return GaiaDataLayer.enableWiFi()", special_powers=True)
        assert result, 'Unable to enable WiFi'

    def disable_wifi(self):
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("return GaiaDataLayer.disableWiFi()", special_powers=True)
        assert result, 'Unable to disable WiFi'

    def connect_to_wifi(self, network=None):
        network = network or self.testvars.get('wifi')
        assert network, 'No WiFi network provided'
        self.enable_wifi()
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script("return GaiaDataLayer.connectToWiFi(%s)" % json.dumps(network),
                                                      script_timeout=max(self.marionette.timeout, 60000))
        assert result, 'Unable to connect to WiFi network'

    def forget_all_networks(self):
        self.marionette.switch_to_frame()
        self.marionette.execute_async_script('return GaiaDataLayer.forgetAllNetworks()')

    def is_wifi_connected(self, network=None):
        network = network or self.testvars.get('wifi')
        self.marionette.switch_to_frame()
        return self.marionette.execute_script("return GaiaDataLayer.isWiFiConnected(%s)" % json.dumps(network))

    @property
    def known_networks(self):
        known_networks = self.marionette.execute_async_script(
            'return GaiaDataLayer.getKnownNetworks()')
        return [n for n in known_networks if n]

    @property
    def active_telephony_state(self):
        # Returns the state of only the currently active call or None if no active call
        return self.marionette.execute_script("return GaiaDataLayer.getMozTelephonyState()")

    @property
    def is_antenna_available(self):
        return self.marionette.execute_script('return window.navigator.mozFMRadio.antennaAvailable')

    @property
    def is_fm_radio_enabled(self):
        return self.marionette.execute_script('return window.navigator.mozFMRadio.enabled')

    @property
    def fm_radio_frequency(self):
        return self.marionette.execute_script('return window.navigator.mozFMRadio.frequency')

    @property
    def media_files(self):
        result = []
        result.extend(self.music_files)
        result.extend(self.picture_files)
        result.extend(self.video_files)
        return result

    def delete_all_sms(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaDataLayer.deleteAllSms();", special_powers=True)

    def get_all_sms(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_async_script("return GaiaDataLayer.getAllSms();", special_powers=True)

    def delete_all_call_log_entries(self):
        """The call log needs to be open and focused in order for this to work."""
        self.marionette.execute_script('window.wrappedJSObject.RecentsDBManager.deleteAll();')

    def insert_call_entry(self, call):
        """The call log needs to be open and focused in order for this to work."""
        self.marionette.execute_script('window.wrappedJSObject.CallLogDBManager.add(%s);' % (json.dumps(call)))

        # TODO Replace with proper wait when possible
        import time
        time.sleep(1)

    def kill_active_call(self):
        self.marionette.execute_script("var telephony = window.navigator.mozTelephony; " +
                                       "if(telephony.active) telephony.active.hangUp();")

    def kill_conference_call(self):
        self.marionette.execute_script("""
        var callsToEnd = window.navigator.mozTelephony.conferenceGroup.calls;
        for (var i = (callsToEnd.length - 1); i >= 0; i--) {
            var call = callsToEnd[i];
            call.hangUp();
        }
        """)

    @property
    def music_files(self):
        return self.marionette.execute_async_script(
            'return GaiaDataLayer.getAllMusic();')

    @property
    def picture_files(self):
        return self.marionette.execute_async_script(
            'return GaiaDataLayer.getAllPictures();')

    @property
    def video_files(self):
        return self.marionette.execute_async_script(
            'return GaiaDataLayer.getAllVideos();')

    def sdcard_files(self, extension=''):
        files = self.marionette.execute_async_script(
            'return GaiaDataLayer.getAllSDCardFiles();')
        if len(extension):
            return [file for file in files if file['name'].endswith(extension)]
        return files

    def send_sms(self, number, message):
        self.marionette.switch_to_frame()
        import json
        number = json.dumps(number)
        message = json.dumps(message)
        result = self.marionette.execute_async_script('return GaiaDataLayer.sendSMS(%s, %s)' % (number, message), special_powers=True)
        assert result, 'Unable to send SMS to recipient %s with text %s' % (number, message)

    def add_notification(self, title, options=None):
        self.marionette.execute_script('new Notification("%s", %s);' % (title, json.dumps(options)))

    def clear_notifications(self):
        self.marionette.execute_script('window.wrappedJSObject.NotificationScreen.clearAll();')

    @property
    def current_audio_channel(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_script("return window.wrappedJSObject.soundManager.currentChannel;")


class Accessibility(object):

    def __init__(self, marionette):
        self.marionette = marionette
        js = os.path.abspath(os.path.join(__file__, os.path.pardir,
                                          'atoms', "accessibility.js"))
        self.marionette.import_script(js)

    def is_hidden(self, element):
        return self._run_async_script('isHidden', [element])

    def is_visible(self, element):
        return self._run_async_script('isVisible', [element])

    def is_disabled(self, element):
        return self._run_async_script('isDisabled', [element])

    def click(self, element):
        self._run_async_script('click', [element])

    def wheel(self, element, direction):
        self.marionette.execute_script('Accessibility.wheel.apply(Accessibility, arguments)', [
            element, direction])

    def get_name(self, element):
        return self._run_async_script('getName', [element])

    def get_role(self, element):
        return self._run_async_script('getRole', [element])

    def dispatchEvent(self):
        self.marionette.execute_script("window.wrappedJSObject.dispatchEvent(new CustomEvent(" +
                                       "'accessibility-action'));")

    def _run_async_script(self, func, args):
        result = self.marionette.execute_async_script(
            'return Accessibility.%s.apply(Accessibility, arguments)' % func,
            args, special_powers=True)

        if not result:
            return

        if result.has_key('error'):
            message = 'accessibility.js error: %s' % result['error']
            raise Exception(message)

        return result.get('result', None)


class GaiaDevice(object):

    def __init__(self, marionette, testvars=None, manager=None):
        self.manager = manager
        self.marionette = marionette
        self.testvars = testvars or {}

        if self.is_desktop_b2g:
            # Use a temporary directory for storage
            self.storage_path = tempfile.mkdtemp()
            self._set_storage_path()
        elif self.manager:
            # Use the device root for storage
            self.storage_path = self.manager.deviceRoot

        self.lockscreen_atom = os.path.abspath(
            os.path.join(__file__, os.path.pardir, 'atoms', "gaia_lock_screen.js"))

    def _set_storage_path(self):
        if self.is_desktop_b2g:
            # Override the storage location for desktop B2G. This will only
            # work if the B2G instance is running locally.
            GaiaData(self.marionette).set_char_pref(
                'device.storage.overrideRootDir', self.storage_path)

    @property
    def is_android_build(self):
        if self.testvars.get('is_android_build') is None:
            self.testvars['is_android_build'] = 'android' in self.marionette.session_capabilities['platformName'].lower()
        return self.testvars['is_android_build']

    @property
    def is_emulator(self):
        if not hasattr(self, '_is_emulator'):
            self._is_emulator = self.marionette.session_capabilities['device'] == 'qemu'
        return self._is_emulator

    @property
    def is_desktop_b2g(self):
        if self.testvars.get('is_desktop_b2g') is None:
            self.testvars['is_desktop_b2g'] = self.marionette.session_capabilities['device'] == 'desktop'
        return self.testvars['is_desktop_b2g']

    @property
    def is_online(self):
        # Returns true if the device has a network connection established (cell data, wifi, etc)
        return self.marionette.execute_script('return window.navigator.onLine;')

    @property
    def has_mobile_connection(self):
        return self.marionette.execute_script('return window.navigator.mozMobileConnections && ' +
                                              'window.navigator.mozMobileConnections[0].voice.network !== null')

    @property
    def has_wifi(self):
        if not hasattr(self, '_has_wifi'):
            self._has_wifi = self.marionette.execute_script('return window.navigator.mozWifiManager !== undefined')
        return self._has_wifi

    def restart_b2g(self):
        self.stop_b2g()
        time.sleep(2)
        self.start_b2g()

    def start_b2g(self, timeout=120):
        if self.marionette.instance:
            # launch the gecko instance attached to marionette
            self.marionette.instance.start()
        elif self.is_android_build:
            self.manager.shellCheckOutput(['start', 'b2g'])
        else:
            raise Exception('Unable to start B2G')
        self.marionette.wait_for_port()
        self.marionette.start_session()

        self.wait_for_b2g_ready(timeout)

        # Reset the storage path for desktop B2G
        self._set_storage_path()

    def wait_for_b2g_ready(self, timeout=120):
        # Wait for the homescreen to finish loading
        Wait(self.marionette, timeout).until(expected.element_present(
            By.CSS_SELECTOR, '#homescreen[loading-state=false]'))

        # Wait for logo to be hidden
        self.marionette.set_search_timeout(0)
        try:
            Wait(self.marionette, timeout, ignored_exceptions=StaleElementException).until(
                lambda m: not m.find_element(By.ID, 'os-logo').is_displayed())
        except NoSuchElementException:
            pass
        self.marionette.set_search_timeout(self.marionette.timeout or 10000)

    @property
    def is_b2g_running(self):
        return 'b2g' in self.manager.shellCheckOutput(['toolbox', 'ps'])

    def stop_b2g(self, timeout=5):
        if self.marionette.instance:
            # close the gecko instance attached to marionette
            self.marionette.instance.close()
        elif self.is_android_build:
            self.manager.shellCheckOutput(['stop', 'b2g'])
            Wait(self.marionette, timeout=timeout).until(
                lambda m: not self.is_b2g_running,
                message='b2g failed to stop.')
        else:
            raise Exception('Unable to stop B2G')
        self.marionette.client.close()
        self.marionette.session = None
        self.marionette.window = None

    def press_sleep_button(self):
        self.marionette.execute_script("""
            window.wrappedJSObject.dispatchEvent(new KeyboardEvent('mozbrowserbeforekeydown', {
              key: 'Power'
            }));""")
            
    def press_button(self, keyname): #goof
        env_predict = 'home/volumeup/volumedown/holdstar/holdhash';
        key_name_list = 'SoftLeft/SoftRight/Enter/ArrowLeft/ArrowRight/ArrowUp/ArrowDown/'
        if(env_predict.find(keyname)>=0):
            print "send event %s" % (keyname)
            cmd = "window.wrappedJSObject.dispatchEvent(new Event('%s'));" % (keyname)
            self.marionette.switch_to_frame()
            self.marionette.execute_script(cmd)#home/volumeup/volumedown/holdstar/holdhash can work.
        else:
            cmd = """
                window.wrappedJSObject.dispatchEvent(new KeyboardEvent('keydown', {
                  key: '""" + keyname + """'
                }));"""
            self.marionette.execute_script(cmd)
            cmd = """
                window.wrappedJSObject.dispatchEvent(new KeyboardEvent('keyup', {
                  key: '""" + keyname + """'
                }));"""
            self.marionette.execute_script(cmd)
        
        
    def press_release_volume_up_then_down_n_times(self, n_times):
        self.marionette.execute_script("""
            function sendEvent(key, aType) {
              var type = aType === 'press' ? 'mozbrowserafterkeydown' : 'mozbrowserafterkeyup';
              window.wrappedJSObject.dispatchEvent(new KeyboardEvent(type, {
                key: key
              }));
            }
            for (var i = 0; i < arguments[0]; ++i) {
              sendEvent('VolumeUp', 'press');
              sendEvent('VolumeUp', 'release');
              sendEvent('VolumeDown', 'press');
              sendEvent('VolumeDown', 'release');
            };""", script_args=[n_times])

    def turn_screen_off(self):
        self.marionette.execute_script("window.wrappedJSObject.ScreenManager.turnScreenOff(true)")

    def turn_screen_on(self):
        self.marionette.execute_script("window.wrappedJSObject.ScreenManager.turnScreenOn(true)")

    @property
    def is_screen_enabled(self):
        return self.marionette.execute_script('return window.wrappedJSObject.ScreenManager.screenEnabled')

    def touch_home_button(self):
        apps = GaiaApps(self.marionette)
        if apps.displayed_app.name.lower() != 'homescreen':
            # touching home button will return to homescreen
            self._dispatch_home_button_event()
            Wait(self.marionette).until(
                lambda m: apps.displayed_app.name.lower() == 'homescreen')
            apps.switch_to_displayed_app()
        else:
            apps.switch_to_displayed_app()
            mode = self.marionette.find_element(By.TAG_NAME, 'body').get_attribute('class')
            self._dispatch_home_button_event()
            apps.switch_to_displayed_app()
            if 'edit-mode' in mode:
                # touching home button will exit edit mode
                Wait(self.marionette).until(lambda m: m.find_element(
                    By.TAG_NAME, 'body').get_attribute('class') != mode)
            else:
                # touching home button inside homescreen will scroll it to the top
                Wait(self.marionette).until(lambda m: m.execute_script(
                    "return window.wrappedJSObject.scrollY") == 0)

    def _dispatch_home_button_event(self):
        self.marionette.switch_to_frame()
        self.marionette.execute_script("window.wrappedJSObject.dispatchEvent(new Event('home'));")

    def hold_home_button(self):
        self.marionette.switch_to_frame()
        self.marionette.execute_script("window.wrappedJSObject.dispatchEvent(new Event('holdhome'));")

    def hold_sleep_button(self):
        self.marionette.switch_to_frame()
        self.marionette.execute_script("window.wrappedJSObject.dispatchEvent(new Event('holdsleep'));")

    @property
    def is_locked(self):
        self.marionette.switch_to_frame()
        return self.marionette.execute_script('return window.wrappedJSObject.Service.locked')

    def lock(self):
        self.turn_screen_off()
        self.turn_screen_on()
        assert self.is_locked, 'The screen is not locked'
        Wait(self.marionette).until(lambda m: m.find_element(By.CSS_SELECTOR, 'div.lockScreenWindow.active'))

    def unlock(self):
        self.marionette.import_script(self.lockscreen_atom)
        self.marionette.switch_to_frame()
        result = self.marionette.execute_async_script('GaiaLockScreen.unlock()')
        assert result, 'Unable to unlock screen'

    def takeScreenshot(self):
        with self.marionette.using_context(self.marionette.CONTEXT_CHROME):
            return self.marionette.execute_script("""
            return (function takeScreenshot() {
              var canvas = document.createElementNS('http://www.w3.org/1999/xhtml',
                                                    'canvas');
              var width = window.innerWidth;
              var height = window.innerHeight;
              canvas.setAttribute('width', width);
              canvas.setAttribute('height', height);

              var context = canvas.getContext('2d');
              var flags =
                context.DRAWWINDOW_DRAW_CARET |
                context.DRAWWINDOW_DRAW_VIEW |
                context.DRAWWINDOW_USE_WIDGET_LAYERS;

              context.drawWindow(window, 0, 0, width, height,
                                 'rgb(255,255,255)', flags);

              return context.canvas.toDataURL('image/png');

            }.apply(this, arguments));
            """)
		
    def change_orientation(self, orientation):
        """  There are 4 orientation states which the phone can be passed in:
        portrait-primary(which is the default orientation), landscape-primary, portrait-secondary and landscape-secondary
        """
        self.marionette.execute_async_script("""
            if (arguments[0] === arguments[1]) {
              marionetteScriptFinished();
            }
            else {
              var expected = arguments[1];
              window.screen.onmozorientationchange = function(e) {
                console.log("Received 'onmozorientationchange' event.");
                waitFor(
                  function() {
                    window.screen.onmozorientationchange = null;
                    marionetteScriptFinished();
                  },
                  function() {
                    return window.screen.mozOrientation === expected;
                  }
                );
              };
              console.log("Changing orientation to '" + arguments[1] + "'.");
              window.screen.mozLockOrientation(arguments[1]);
            };""", script_args=[self.screen_orientation, orientation])

    @property
    def screen_width(self):
        return self.marionette.execute_script('return window.screen.width')

    @property
    def screen_orientation(self):
        return self.marionette.execute_script('return window.screen.mozOrientation')
