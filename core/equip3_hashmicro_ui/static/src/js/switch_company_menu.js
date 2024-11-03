odoo.define('equip3_hashmicro_ui.SwitchCompanyMenu', function (require) {
    "use strict";

    var AppsMenu = require('web.AppsMenu');
    var SwitchCompanyMenu = require('web.SwitchCompanyMenu');
    var session = require('web.session');

    SwitchCompanyMenu.include({
        events: _.extend({}, SwitchCompanyMenu.prototype.events, {
            'click div.toggle_all_companies': '_onToggleAllCompaniesClick',
            'click #apply_company': '_onClickApplyCompany',
        }),

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                var active_company_ids = session.user_context.allowed_company_ids;
                var allowed_company_ids = session.user_companies.allowed_companies;

                if (active_company_ids.length == allowed_company_ids.length) {
                    self.is_all_companies = true;
                } else {
                    self.is_all_companies = false;
                }
            });
        },

        _onClickApplyCompany: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            var allowed_company_ids = [];
            var current_company_id = this.allowed_company_ids[0];
            var allDropdownItem = this.$('.dropdown-item[data-menu]');

            allDropdownItem.each(function(index, element) {
                if ($(this).find('.fa-check-square').length) {
                    var companyID = $(this).attr('data-company-id');
                    allowed_company_ids.push(parseInt(companyID));
                }
            });
            
            session.setCompanies(current_company_id, allowed_company_ids);
            window.location.reload();
        },

        _onToggleAllCompaniesClick: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            var dropdownItem = $(ev.currentTarget).parent();
            var allowed_company_ids = this.allowed_company_ids;
            var allDropdownItem = this.$('.dropdown-item[data-menu]');

            if (dropdownItem.find('.fa-square-o').length) {
                allDropdownItem.each(function(index, element) {
                    if ($(this).find('.fa-square-o').length) {
                        $(this).find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                    }
                });
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            } else {
                allDropdownItem.each(function(index, element) {
                    if ($(this).find('.fa-check-square').length) {
                        $(this).find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                    }
                });
                dropdownItem.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
            }
        },

        _onToggleCompanyClick: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            var dropdownItem = $(ev.currentTarget).parent();
            var companyID = dropdownItem.data('company-id');
            var allowed_company_ids = this.allowed_company_ids;
            if (dropdownItem.find('.fa-square-o').length) {
                allowed_company_ids.push(companyID);
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                $(ev.currentTarget).attr('aria-checked', 'true');
            } else {
                allowed_company_ids.splice(allowed_company_ids.indexOf(companyID), 1);
                dropdownItem.find('.fa-check-square').addClass('fa-square-o').removeClass('fa-check-square');
                $(ev.currentTarget).attr('aria-checked', 'false');
            }
        },
    });

    var AppsMenu = AppsMenu.include({

        start: function(){
            var self = this;
            this.SwitchCompanyMenu = new SwitchCompanyMenu();
            return this._super.apply(this, arguments).then(function() {
                self.SwitchCompanyMenu.appendTo('.o_switch_company_container').then(function(){
                    self.$el.find('.o_switch_company_menu').removeClass('d-none');
                });
            });
        }
    });
    return AppsMenu;

});