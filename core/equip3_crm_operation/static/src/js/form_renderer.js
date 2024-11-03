odoo.define('equip3_crm_operation.FormRenderer', function (require) {
"use strict";

    var FormRenderer = require('web.FormRenderer');
    var core = require('web.core');

    var _t = core._t;
    var qweb = core.qweb;

    function errorFunction(err) {
        alert("Allow get location to this site");
    }

    FormRenderer.include({
        events: _.extend({}, FormRenderer.prototype.events, {
            'click .click_sign_in': '_onClickSignIn',
            'click .click_sign_out': '_onClickSignOut',
        }),
        _updateView: function ($newContent) {
            this._super.apply(this, arguments);
            if (this.mode === "readonly") {
                this.$el.find('#einstein_score').append($(qweb.render('EinsteinScore', {score: this.state.data.einstein_score})));
                this.$el.find('#einstein_score').append(this.state.data.einstein_score_text);
            }
        },
        _onClickSignIn: function(ev) {
            this.getLocation(this.state.res_id, 'sign_in');
        },
        _onClickSignOut: function(ev) {
            this.getLocation(this.state.res_id, 'sign_out');
        },
        getLocation: function (event_id, sign_in_out) {
            var self = this;
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    if (sign_in_out == "sign_in"){
                        self._rpc({
                            model: 'calendar.event',
                            method: 'get_sign_in_location',
                            args: [event_id, {'lat': position.coords.latitude, 'lng': position.coords.longitude}],
                        }).then(function (result){
                            window.location.reload();
                        });
                     }
                     if (sign_in_out == "sign_out"){
                        self._rpc({
                            model: 'calendar.event',
                            method: 'get_sign_out_location',
                            args: [event_id, {'lat': position.coords.latitude, 'lng': position.coords.longitude}],
                        }).then(function (result){
                            window.location.reload();
                        });
                     }
                    }, errorFunction);
            } else {
                alert("Geolocation is not supported by this browser!");
            }
        }
    })

});