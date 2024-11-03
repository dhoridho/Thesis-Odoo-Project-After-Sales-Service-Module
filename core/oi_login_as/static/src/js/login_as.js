odoo.define('login_as', function (require) {
    'use strict';

    var core = require('web.core');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var _t = core._t;
    

    var LoginAs = Widget.extend({
        template: 'LoginAs',
        events: {
            'click a#login_as': 'login_as',
        },
        login_as: function() {                        
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Login as'),
                views: [[false, 'form']],
                res_model: 'login.as',
                target: 'new',
            });
        }
    });
    
    var LoginBack = Widget.extend({
        template: 'LoginBack',
        events: {
            'click a#login_back': 'login_back',
        },
        login_back: function() {                        
            this.do_action({
                type: 'ir.actions.act_url',
                url: '/web/login_back',
                target: 'self'
            });
        }
    });
                
    if (odoo.debug && session.is_system)
    	SystrayMenu.Items.push(LoginAs);
    
    if (session.impersonate)
    	SystrayMenu.Items.push(LoginBack);

});
