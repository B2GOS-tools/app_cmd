'use strict';

const MODIFIER = 0x0000;

var keyboardEventHandler = {

  pressKeypad: function(aType, aKeyName, aKeyCode, aCharCode) {

       // requires higher privilege by providing sandbox = 'system' in execute_script
       let domWindowUtils = window.QueryInterface(Components.interfaces.nsIInterfaceRequestor)
                     .getInterface(Components.interfaces.nsIDOMWindowUtils);
       domWindowUtils.sendKeyEventByKeyName(aType, aKeyName, aKeyCode, aCharCode, MODIFIER)
   }
};
