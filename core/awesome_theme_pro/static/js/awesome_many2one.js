odoo.define('awesome_theme_pro.many2one', function (require) {
    "use strict";

    var relational_fields = require('web.relational_fields');

    /**
     * extend to add the dropdown arrow
     */
    relational_fields.FieldMany2One.include({

        init: function () {
            this._super.apply(this, arguments);
            if (this.attrs.options && this.attrs.options.limit) {
                this.limit = this.attrs.options.limit
            }
        },

        /**
         * rotate the arrow when search
         */
        _onInputClick: function () {
            if (this.$input.autocomplete("widget").is(":visible")) {
                this.$input.autocomplete("close");
                this.$(".o_dropdown_arrow").addClass("awesome_reverse")
            } else if (this.floating) {
                this.$(".o_dropdown_arrow").removeClass("awesome_reverse")
                this.$input.autocomplete("search"); // search with the input's content
            } else {
                this.$(".o_dropdown_arrow").removeClass("awesome_reverse")
                this.$input.autocomplete("search", ''); // search with the empty string
            }
        },

        reinitialize: function (value) {
            var prom = this._super(value);
            this.$(".o_dropdown_arrow").addClass("awesome_reverse")
            return prom;
        },

         /**
         * @private
         */
        _bindAutoComplete: function () {
            var self = this;
            // avoid ignoring autocomplete="off" by obfuscating placeholder, see #30439
            if ($.browser.chrome && this.$input.attr('placeholder')) {
                this.$input.attr('placeholder', function (index, val) {
                    return val.split('').join('\ufeff');
                });
            }
            this.$input.autocomplete({
                source: function (req, resp) {
                    _.each(self._autocompleteSources, function (source) {
                        // Resets the results for this source
                        source.results = [];

                        // Check if this source should be used for the searched term
                        const search = req.term.trim();
                        if (!source.validation || source.validation.call(self, search)) {
                            source.loading = true;

                            // Wrap the returned value of the source.method with a promise
                            // So event if the returned value is not async, it will work
                            Promise.resolve(source.method.call(self, search)).then(function (results) {
                                source.results = results;
                                source.loading = false;
                                resp(self._concatenateAutocompleteResults());
                            });
                        }
                    });
                },
                select: function (event, ui) {
                    // we do not want the select event to trigger any additional
                    // effect, such as navigating to another field.
                    event.stopImmediatePropagation();
                    event.preventDefault();

                    var item = ui.item;
                    self.floating = false;
                    if (item.id) {
                        self.reinitialize({id: item.id, display_name: item.name});
                    } else if (item.action) {
                        item.action();
                    }
                    return false;
                },

                focus: function (event) {
                    event.preventDefault(); // don't automatically select values on focus
                },

                open: function (event) {
                    // hide the list when scroll
                    self._onScroll = function (ev) {
                        if (ev.target !== self.$input.get(0) && self.$input.hasClass('ui-autocomplete-input')) {
                            self.$input.autocomplete('close');
                        }
                    };
                    window.addEventListener('scroll', self._onScroll, true);
                },

                close: function (event) {
                    self.$(".o_dropdown_arrow").addClass("awesome_reverse")
                    // it is necessary to prevent ESC key from propagating to field
                    // root, to prevent unwanted discard operations.
                    if (event.which === $.ui.keyCode.ESCAPE) {
                        event.stopPropagation();
                    }
                    if (self._onScroll) {
                        window.removeEventListener('scroll', self._onScroll, true);
                    }
                },
                autoFocus: true,
                html: true,
                minLength: 0,
                delay: this.AUTOCOMPLETE_DELAY,
            });
            this.$input.autocomplete("option", "position", { my: "left top-110", at: "left bottom+110" });
            this.autocomplete_bound = true;
        }
    });
});