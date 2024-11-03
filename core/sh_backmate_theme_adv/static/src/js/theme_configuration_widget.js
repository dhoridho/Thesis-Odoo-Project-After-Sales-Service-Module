odoo.define('sh_backmate_theme_adv.theme_configuration_widget', function (require) {
	"use strict";
	
	var config = require('web.config');
	var ajax = require('web.ajax');
	var core = require('web.core');
	var dom = require('web.dom');
	var Widget = require('web.Widget');
	
	var _t = core._t;
	
	ajax.loadXML('/sh_backmate_theme_adv/static/src/xml/theme_config.xml', core.qweb)
	
	var ThemeSettingWidget = Widget.extend({
		template: 'ThemeConfiguration',
		custom_events: {
	       // field_changed: '_onFieldChanged',
	    },
		willStart: function () {
	        return this._super.apply(this, arguments).then(function () {
	        })
	    },
	});
	return ThemeSettingWidget;
});;