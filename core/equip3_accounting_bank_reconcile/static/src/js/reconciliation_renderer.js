odoo.define('equip3_accounting_bank_reconcile.ReconciliationRenderer', function (require) {
    'use strict';

    var LineRenderer = require('account.ReconciliationRenderer').LineRenderer;

    var core = require("web.core");
    var qweb = core.qweb;

    LineRenderer.include({
        /**
         * @override
         * @param {Object} prop
         * @returns {Boolean}
         */
        update: function (state) {
            var self = this;
            // IsValid
            var to_check_checked = Boolean(state.to_check);
            this.$("caption .o_buttons button.o_validate").toggleClass(
                "d-none",
                Boolean(state.balance.type) && !to_check_checked
            );
            this.$("caption .o_buttons button.o_reconcile").toggleClass(
                "d-none",
                state.balance.type <= 0 || to_check_checked
            );
            this.$("caption .o_buttons .o_no_valid").toggleClass(
                "d-none",
                state.balance.type >= 0 || to_check_checked
            );
            self.$("caption .o_buttons button.o_validate").toggleClass(
                "text-warning",
                to_check_checked
            );

            // Partner_id
            this._makePartnerRecord(
                state.st_line.partner_id,
                state.st_line.partner_name
            ).then(function (recordID) {
                self.fields.partner_id.reset(self.model.get(recordID));
                self.$el.attr("data-partner", state.st_line.partner_id);
            });

            // Mode
            this.$el.data("mode", state.mode).attr("data-mode", state.mode);
            this.$(".o_notebook li a").attr("aria-selected", false);
            this.$(".o_notebook li a").removeClass("active");
            this.$(".o_notebook .tab-content .tab-pane").removeClass("active");
            this.$('.o_notebook li a[href*="notebook_page_' + state.mode + '"]').attr(
                "aria-selected",
                true
            );
            this.$(
                '.o_notebook li a[href*="notebook_page_' + state.mode + '"]'
            ).addClass("active");
            this.$(
                '.o_notebook .tab-content .tab-pane[id*="notebook_page_' +
                    state.mode +
                    '"]'
            ).addClass("active");
            this.$(".create, .match").each(function () {
                $(this).removeAttr("style");
            });

            // Reconciliation_proposition
            var $props = this.$(".accounting_view tbody").empty();

            // Search propositions that could be a partial credit/debit.
            var props = [];
            _.each(state.reconciliation_proposition, function (prop) {
                if (prop.display) {
                    props.push(prop);
                }
            });

            _.each(props, function (line) {
                var $line = $(
                    qweb.render("reconciliation.line.mv_line", {
                        line: line,
                        state: state,
                        proposition: true,
                    })
                );
                if (!isNaN(line.id)) {
                    $('<span class="line_info_button fa fa-info-circle"/>')
                        .appendTo($line.find(".cell_info_popover"))
                        .attr(
                            "data-content",
                            qweb.render("reconciliation.line.mv_line.details", {
                                line: line,
                            })
                        );
                }
                $props.append($line);
            });

            // Mv_lines
            var matching_modes = self.model.modes.filter((x) => x.startsWith("match"));
            for (let i = 0; i < matching_modes.length; i++) {
                var stateMvLines = state["mv_lines_" + matching_modes[i]] || [];
                var remaining = state["remaining_" + matching_modes[i]];
                var $mv_lines = this.$(
                    'div[id*="notebook_page_' +
                        matching_modes[i] +
                        '"] .match table tbody'
                ).empty();
                this.$(
                    '.o_notebook li a[href*="notebook_page_' + matching_modes[i] + '"]'
                )
                    .parent()
                    .toggleClass(
                        "d-none",
                        stateMvLines.length === 0 &&
                            !state["filter_" + matching_modes[i]]
                    );

                _.each(stateMvLines, function (line) {
                    var $line = $(
                        qweb.render("reconciliation.line.mv_line", {
                            line: line,
                            state: state,
                        })
                    );
                    if (!isNaN(line.id)) {
                        $('<span class="line_info_button fa fa-info-circle"/>')
                            .appendTo($line.find(".cell_info_popover"))
                            .attr(
                                "data-content",
                                qweb.render("reconciliation.line.mv_line.details", {
                                    line: line,
                                })
                            );
                    }
                    $mv_lines.append($line);
                });
                this.$(
                    'div[id*="notebook_page_' +
                        matching_modes[i] +
                        '"] .match div.load-more'
                ).toggle(remaining > 0);
                this.$(
                    'div[id*="notebook_page_' +
                        matching_modes[i] +
                        '"] .match div.load-more span'
                ).text(remaining);
            }

            // Balance
            this.$(".popover").remove();
            this.$("table tfoot").html(
                qweb.render("reconciliation.line.balance", {state: state})
            );

            // Create form
            if (state.createForm) {
                var createPromise = Promise.resolve();
                if (!this.fields.account_id) {
                    createPromise = this._renderCreate(state);
                }
                createPromise.then(function () {
                    var data = self.model.get(self.handleCreateRecord).data;
                    return self.model
                        .notifyChanges(self.handleCreateRecord, state.createForm)
                        .then(function () {
                            // FIXME can't it directly written REPLACE_WITH ids=state.createForm.analytic_tag_ids
                            return self.model.notifyChanges(self.handleCreateRecord, {
                                analytic_tag_ids: {operation: "REPLACE_WITH", ids: []},
                            });
                        })
                        .then(function () {
                            var defs = [];
                            _.each(state.createForm.analytic_tag_ids, function (tag) {
                                defs.push(
                                    self.model.notifyChanges(self.handleCreateRecord, {
                                        analytic_tag_ids: {
                                            operation: "ADD_M2M",
                                            ids: tag,
                                        },
                                    })
                                );
                            });
                            return Promise.all(defs);
                        })
                        .then(function () {
                            return self.model.notifyChanges(self.handleCreateRecord, {
                                tax_ids: {operation: "REPLACE_WITH", ids: []},
                            });
                        })
                        .then(function () {
                            var defs = [];
                            _.each(state.createForm.tax_ids, function (tag) {
                                defs.push(
                                    self.model.notifyChanges(self.handleCreateRecord, {
                                        tax_ids: {operation: "ADD_M2M", ids: tag},
                                    })
                                );
                            });
                            return Promise.all(defs);
                        })
                        .then(function () {
                            var record = self.model.get(self.handleCreateRecord);
                            _.each(self.fields, function (field, fieldName) {
                                if (self._avoidFieldUpdate[fieldName]) return;
                                if (fieldName === "partner_id") return;
                                if (
                                    (data[fieldName] || state.createForm[fieldName]) &&
                                    !_.isEqual(
                                        state.createForm[fieldName],
                                        data[fieldName]
                                    )
                                ) {
                                    field.reset(record);
                                }
                                if (fieldName === "tax_ids") {
                                    if (
                                        !state.createForm[fieldName].length ||
                                        state.createForm[fieldName].length > 1
                                    ) {
                                        $(".create_force_tax_included").addClass(
                                            "d-none"
                                        );
                                    } else {
                                        $(".create_force_tax_included").removeClass(
                                            "d-none"
                                        );
                                        var price_include =
                                            state.createForm[fieldName][0]
                                                .price_include;
                                        var force_tax_included =
                                            state.createForm[fieldName][0]
                                                .force_tax_included;
                                        self.$(".create_force_tax_included input").prop(
                                            "checked",
                                            force_tax_included
                                        );
                                        self.$(".create_force_tax_included input").prop(
                                            "disabled",
                                            price_include
                                        );
                                    }
                                }
                            });
                            if (state.to_check) {
                                // Set the to_check field to true if global to_check is set
                                self.$(".create_to_check input")
                                    .prop("checked", state.to_check)
                                    .change();
                            }
                            return true;
                        });
                });
            }
            this.$(".create .add_line").toggle(Boolean(state.balance.amount_currency));

            // Set color if table body is empty
            $('table.accounting_view').each(function() {
                var $table = $(this);
                var $tableBody = $table.find('tbody');
                // Check if the table body is empty
                if ($tableBody.children().length === 0) {
                    $table.find('thead td').css('background-color', '#ebe1b6');
                } else {
                    $table.find('thead td').css('background-color', '#f0f0f0');
                }
            });
        },
    });
});