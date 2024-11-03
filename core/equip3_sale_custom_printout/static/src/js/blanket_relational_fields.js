odoo.define('equip3_sale_custom_printout.blanket_relational_fields', function (require) {
    "use strict";
    
        var FieldRadio = require('web.relational_fields').FieldRadio;
    
        FieldRadio.include({
            _setValues: function () {
                this._super.apply(this, arguments);
                if (this.model !== undefined &&
                    this.model === "blanket.printout.editor" &&
                    this.name !== undefined &&
                    this.name === 'orientation') {
                    if (this.value === 'potrait') {
                        $('.o_preview_iframe_wrapper').addClass('potrait');
                        $('.o_preview_iframe_wrapper').removeClass('landscape');
                    } else {
                        $('.o_preview_iframe_wrapper').addClass('landscape');
                        $('.o_preview_iframe_wrapper').removeClass('potrait');
                    }
                }
            },
            _onInputClick: function (event) {
                this._super.apply(this, arguments);
                if (this.model !== undefined &&
                    this.model === "blanket.printout.editor" &&
                    this.name !== undefined &&
                    this.name === 'orientation') {
                    var index = $(event.target).data('index');
                    var value = this.values[index];
                    if (value[0] === 'potrait') {
                        $('.o_preview_iframe_wrapper').addClass('potrait');
                        $('.o_preview_iframe_wrapper').removeClass('landscape');
                    } else {
                        $('.o_preview_iframe_wrapper').addClass('landscape');
                        $('.o_preview_iframe_wrapper').removeClass('potrait');
                    }
                }
            },
        });
    
    });