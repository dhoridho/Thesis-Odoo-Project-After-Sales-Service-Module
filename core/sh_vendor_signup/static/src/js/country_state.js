odoo.define("sh_vendor_signup.sh_vendor_signup", function (require) {			
    var concurrency = require("web.concurrency");
    var core = require("web.core");
    var publicWidget = require("web.public.widget");


    publicWidget.registry.js_cls_sh_vendor_signup_country_state_wrapper = publicWidget.Widget.extend({
		selector: ".js_cls_sh_vendor_signup_country_state_wrapper",
		events: {
	        'change select[name="country_id"]': '_onChangeCountry',
	    },


	/**
     * @private
     * @param {Event} ev
     */
    _onChangeCountry: function (ev) {
		var self = this;
		if (!$(ev.currentTarget).val()){
			return;
		}
		
        this._rpc({
            route: "/vendor_sign_up/" + $(ev.currentTarget).val()
        }).then(function (data) {
            // populate states and display
            var selectStates = self.$el.find("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                if (data.states.length || data.state_required) {
                    selectStates.html('');
                    _.each(data.states, function (x) {
                        var opt = $('<option>').text(x[1])
                            .attr('value', x[0])
                            .attr('data-code', x[2]);
                        selectStates.append(opt);
                    });
                    selectStates.parent('div').show();
                } else {
                    selectStates.val('').parent('div').hide();
                }
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }
        });		
		

    },


	
	});
});
