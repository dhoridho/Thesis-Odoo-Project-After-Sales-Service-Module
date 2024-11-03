odoo.define('backmate_backend_theme.UserMenu', function (require) {
"use strict";

	var UserMenu = require('web.UserMenu');
	var UserMenu = UserMenu.include({
		 /**
	     * @override
	     */
	    init: function () {
	        this._super.apply(this, arguments);
	        var session = this.getSession();
	        this.sidebar_style = 9;
	        this.outOfOfficeMessage = session.out_of_office_message;
	    },
		
	});
	return UserMenu;

});

		
		