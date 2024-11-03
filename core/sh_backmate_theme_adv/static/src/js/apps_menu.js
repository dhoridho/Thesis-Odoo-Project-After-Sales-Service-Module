odoo.define('backmate_backend_theme.AppsMenu', function (require) {
	"use strict";

	var Widget = require('web.Widget');
	var AppsMenu = require('web.AppsMenu');
	var session = require('web.session');
	var rpc = require('web.rpc')
	var icon_style = 'standard';

	rpc.query({
		model: 'sh.back.theme.config.settings',
		method: 'search_read',
		args: [[], ['icon_style']],
	}, { async: false }).then(function (output) {
		if (output) {
			var i;
			for (i = 0; i < output.length; i++) {
				if (output[i]['icon_style'] == '2d') {
					icon_style = '2d';
				}

			}
		}
	});



	var AppsMenu = AppsMenu.include({

		//--------------------------------------------------------------------------
		// Handlers
		//--------------------------------------------------------------------------

		/**
		 * Called when clicking on an item in the apps menu.
		 *
		 * @private
		 * @param {MouseEvent} ev
		 */
		init: function (parent, menuData) {
			this._super.apply(this, arguments);
			this._activeApp = undefined;
			this.sidebar_style = '9';
			this.icon_style = icon_style;
			this.allowed_company_ids = String(session.user_context.allowed_company_ids)
				.split(',')
				.map(function (id) { return parseInt(id); });
			this.user_companies = session.user_companies.allowed_companies;
			this.current_company = this.allowed_company_ids[0];
			this._apps = _.map(menuData.children, function (appMenuData) {
				return {
					actionID: parseInt(appMenuData.action.split(',')[1]),
					menuID: appMenuData.id,
					name: appMenuData.name,
					xmlID: appMenuData.xmlid,
					parent: appMenuData.parent_id,
					children: appMenuData.children,
					appdata: appMenuData,
				};
			});

		},
		_openApp: function (app) {
			this._setActiveApp(app);
			this.trigger_up('app_clicked', {
				action_id: app.actionID,
				menu_id: app.menuID,
			});
		},
		/**
		 * @private
		 * @param {Object} app
		 */
		_setActiveApp: function (app) {

			var $oldActiveApp = this.$('.o_app.active');
			$oldActiveApp.removeClass('active');
			var $newActiveApp = this.$('.o_app[data-action-id="' + app.actionID + '"]');
			$newActiveApp.addClass('active');
		},



	});

	return AppsMenu;


});
