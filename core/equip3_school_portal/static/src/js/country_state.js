odoo.define("equip3_school_portal.school_admission_register", function (require) {          
    var concurrency = require("web.concurrency");
    var core = require("web.core");
    var publicWidget = require("web.public.widget");


    publicWidget.registry.js_cls_student_signup_country_state_wrapper = publicWidget.Widget.extend({
        selector: ".js_cls_student_signup_country_state_wrapper",
        events: {
            'change select[name="country_id"]': '_onChangeCountry',
            'change select[data-name="country_id"]': '_onChangeParentCountry'
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
            route: "/student/admission/" + $(ev.currentTarget).val()
        }).then(function (data) {
            // populate states and display
            var selectStates = $("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                selectStates.html('');
                _.each(data.states, function (x) {
                    var opt = $('<option>').text(x[1])
                        .attr('value', x[0])
                        .attr('data-code', x[2]);
                    selectStates.append(opt);
                });
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }
        });
    },
    _onChangeParentCountry: function (ev) {
        var self = this;
        if (!$(ev.currentTarget).val()){
            return;
        }
        
        this._rpc({
            route: "/student/admission/" + $(ev.currentTarget).val()
        }).then(function (data) {
            // populate states and display
            var selectStates = $(ev.currentTarget).closest('tr').find('select[data-name="state_id"]');
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                selectStates.html('');
                _.each(data.states, function (x) {
                    var opt = $('<option>').text(x[1])
                        .attr('value', x[0])
                        .attr('data-code', x[2]);
                    selectStates.append(opt);
                });
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }
        });
    },
    });
});
