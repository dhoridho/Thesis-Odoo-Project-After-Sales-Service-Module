odoo.define('equip3_purchase_masterdata.wa_fields', function (require) {
    "use strict";    
    var smsFields = require('sms.fields');
    var core = require('web.core');
    var session = require('web.session');
    var _t = core._t;


    var waFields = smsFields.include({
        _onClickWA: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            var context = session.user_context;
            context = _.extend({}, context, {
                default_res_model: this.model,
                default_res_id: parseInt(this.res_id),
                default_number_field_name: this.name,
                default_composition_mode: 'comment',
            });
            var self = this;
            return this.do_action({
                title: _t('Send Whatsapp Message'),
                name: _t('Send Whatsapp Message'),
                type: 'ir.actions.act_window',
                res_model: 'sms.composer',
                target: 'new',
                views: [[false, 'form']],
                context: context,
            }, {
            on_close: function () {
                self.trigger_up('reload');
            }});
        },

        _renderReadonly: function () {
            var def = this._super.apply(this, arguments);
            if (this.enableSMS && this.value) {
                var $composerButton = $('<a>', {
                    title: _t('Send Whatsapp Message'),
                    href: '',
                    class: 'ml-3 d-inline-flex align-items-center o_field_phone_sms',
                    html: $('<small>', {class: 'font-weight-bold ml-1', html: 'Whatsapp'}),
                });
                $composerButton.prepend($('<i>', {class: 'fa fa-mobile'}));
                $composerButton.on('click', this._onClickWA.bind(this));
                this.$el = this.$el.prevObject;
                this.$el = this.$el.add($composerButton);
            }

            return def;
        },
    
    })
    return waFields
})