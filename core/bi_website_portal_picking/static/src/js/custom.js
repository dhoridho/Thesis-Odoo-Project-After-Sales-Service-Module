odoo.define('bi_website_support_ticket.custom', function(require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;

var PortalChatter = require('portal.chatter').PortalChatter;

/**
 * Extends Frontend Chatter to handle rating
 */
ajax.loadXML('/bi_website_portal_picking/static/src/xml/website_portal_chatter.xml', qweb);

PortalChatter.include({
    init: function(parent, options){
    	this._super.apply(this, arguments);
        this.set('attachments', []);
    }
});

});


