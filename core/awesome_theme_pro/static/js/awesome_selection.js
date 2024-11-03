odoo.define('awesome_theme_pro.selection', function (require) {
    "use strict";

    var Fields = require("web.relational_fields")
    var special_fields = require("web.special_fields")

    var core = require('web.core');
    var _lt = core._lt;

    Fields.FieldSelection.include({
        template: 'awesome_theme_pro.selection',

        start: function () {
            var self = this;
            this._super.apply(this, arguments)
            if (this.description.toString() == _lt('Selection').toString()) {
                setTimeout(() => {
                    try {
                        if (self.mode === 'edit') {
                            if (self.attrs.placeholder) {
                                self.$el.select2({
                                    id: false,
                                    text: self.attrs.placeholder,
                                    minimumResultsForSearch: 'Infinity'
                                });
                            } else {
                                self.$el.select2({
                                    minimumResultsForSearch: 'Infinity'
                                });
                            }
                        }
                    } catch (error) {
                        console.log(error);
                    }
                }, 0);
            }
        },
    });

    special_fields.FieldTimezoneMismatch.include({
        template: 'awesome_theme_pro.selection',

        start: function () {
            var self = this;
            this._super.apply(this, arguments)
            setTimeout(() => {
                try {
                    if (self.mode === 'edit') {
                        if (self.attrs.placeholder) {
                            self.$el.first().select2({
                                id: false,
                                text: self.attrs.placeholder,
                                minimumResultsForSearch: 'Infinity'
                            });
                        } else {
                            self.$el.first().select2({
                                minimumResultsForSearch: 'Infinity'
                            });
                        }
                    }
                } catch (error) {
                    console.log(error)
                }
            }, 0);
        }
    })
});