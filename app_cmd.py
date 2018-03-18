#Goof create
import sys
import gaia
import base64

from marionette_driver import By
from marionette_driver import Wait
from marionette import Marionette
#from marionette_driver.marionette import Marionette

SPLIT_SYM = "="

def main(argv):

    if len(argv) == 3:
        cmd = argv[1]
        name = argv[2]
    else :
        print "parameters format not correct!"
        print """Synopsis:   
            %s command[run/capture/press/getpref/getsettings/setsettings] [app_name/file_name/key_name/settings_name]
example:
            %s run camera
            %s capture screenshot.png
            %s press home
            %s getprop/setprop [key%s(value)]
            %s getsetting/setsetting [key%s(value)]
                    """%(argv[0],argv[0],argv[0],argv[0],argv[0],SPLIT_SYM,argv[0],SPLIT_SYM)
        exit()

    print "open port"
    client = Marionette('localhost', port=2828)#defined in setup.py
    client.start_session()
    
    app_manager = gaia.GaiaApps(client)
    dev_manager = gaia.GaiaDevice(client)
    data_manager = gaia.GaiaData(client)
	
    if(cmd == "run"):
        print 'start testing'
        dev_manager.turn_screen_on()
        #dev_manager.touch_home_button()
        print 'current orientation:', dev_manager.screen_orientation
        dev_manager.change_orientation("portrait-primary");

        # may need to unlock screen before this command
        print 'launching application: ', str(name)
        print app_manager.launch(str(name))
        print app_manager.running_apps()
        app_manager.switch_to_displayed_app()
        print app_manager.displayed_app.frame, app_manager.displayed_app.name, "is running!"
        
        ###debug,dev_manager.change_orientation("landscape-primary");
    elif(cmd == "capture"):
        width = dev_manager.screen_width
        print 'screen size:', width
        png_base64 = dev_manager.takeScreenshot()
        ###png_base64 = client.screenshot(app_manager.displayed_app.frame)
        #client.switch_to_frame()
        png_base64 = png_base64[png_base64.find(",")+1:]
        ###print png_base64
        ###print len(png_base64)
        
        png = base64.b64decode(png_base64)
        file_object = open(name,'wb')
        try:
            file_object.write(png)
        finally:
            file_object.close()
    elif(cmd == "press"):
        dev_manager.turn_screen_on()
        print app_manager.displayed_app.frame, app_manager.displayed_app.name, "is running!"
        app_manager.switch_to_displayed_app()
        dev_manager.press_button(name);
    elif(cmd == "getpref"):
        pref = client.get_pref(name)
        print "%s%s%s" % (name,SPLIT_SYM,pref);
    elif(cmd == "setpref"):
        pref, value = map(str, name.split(SPLIT_SYM))
        if(value == "true"): value = true
        if(value == "false"): value = false
        if(value.isdigit()): value = int(value)
        client.set_pref(pref, value)
        prefs = client.get_pref(pref)
        if(value == prefs): print "%s successful change to %s" % (pref,value)
        else: print "failed#### %s:%s" % (pref,prefs)
    elif(cmd == "getsettings"):
        settings = data_manager.get_setting(name)
        print "%s%s%s" % (name,SPLIT_SYM,settings);
    elif(cmd == "setsettings"):
        setting, value = map(str, name.split(SPLIT_SYM))
        data_manager.set_setting(setting, value)
        settings = data_manager.get_setting(setting)
        if(value == settings): print "%s successful change to %s" % (setting,value)
        else: print "failed#### %s" % setting
    elif(cmd == "getallsettings"):
        settings = data_manager.all_settings()
        print "all: %s" % settings;
#complete session
    client.delete_session()

if __name__ == "__main__":
   main(sys.argv)
