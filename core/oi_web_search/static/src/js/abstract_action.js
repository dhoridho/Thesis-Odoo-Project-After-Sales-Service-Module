odoo.define('oi_web_search.AbstractAction', function (require) {
	"use strict";

	const AbstractAction = require("web.AbstractAction");
	const MyControlPanel = require("oi_web_search.ControlPanel");

	
	AbstractAction.include({
		config: _.extend({}, AbstractAction.prototype.config, {
			ControlPanel: MyControlPanel,
		})
	});
		
	return AbstractAction;
});

odoo.define('oi_web_search.abstract_Field_fix', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    AbstractField.include({
        isFocusable: function () {
            var $focusable = this.getFocusableElement();
            if ($focusable){
            	return this._super.apply(this, arguments);
            	// return $focusable.length && $focusable.is(':visible');
            }
        },
    });
    return AbstractField
});
