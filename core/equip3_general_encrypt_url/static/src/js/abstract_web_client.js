odoo.define('equip3_general_encrypt_url.AbstractWebClient', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var Widget = require('web.Widget');
var AbstractWebClient = require('web.AbstractWebClient');

const env = require('web.env');


    AbstractWebClient.include({

        do_push_state: function (state) {

            if (!state.menu_id && this.menu) { 
                state.menu_id = this.menu.getCurrentPrimaryMenu();
            }
            if ('title' in state) {
                this.set_title(state.title);
                delete state.title;
            }
            if(state.id) {
                var encrypt_id = btoa(state.id);
                encrypt_id = encrypt_id.replace('=','!')
                state.hashcode = encrypt_id
                 delete state.id;
            }

            var url = '#' + $.param(state);
            this._current_state = $.deparam($.param(state), false); 
            $.bbq.pushState(url);
            this.trigger('state_pushed', state);
           
            
        },
    });

});
