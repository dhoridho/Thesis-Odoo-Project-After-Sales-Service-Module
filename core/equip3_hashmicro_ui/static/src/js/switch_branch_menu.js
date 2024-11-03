odoo.define('equip3_hashmicro_ui.SwitchBranchMenu', function (require) {
    "use strict";

    var SwitchBranchMenu = require('equip3_general_setting.SwitchBranchMenu');
    var session = require('web.session');

    SwitchBranchMenu.include({
        events: _.extend({}, SwitchBranchMenu.prototype.events, {
            'click div.toggle_all_branches': '_onToggleAllBranchesClick',
            'click #apply_branch': '_onClickApplyBranch',
        }),

        willStart: function () {
            var self = this;
            this.allowed_branch_ids = session.user_context.allowed_branch_ids
            this.current_branch = this.allowed_branch_ids[0];
            return this._super.apply(this, arguments).then(function() {
                var active_branch_ids = session.user_context.allowed_branch_ids;
                var allowed_branch_ids = self.user_branches;
                var current_branch = self.current_branch;

                if (active_branch_ids.length == allowed_branch_ids.length) {
                    self.is_all_branches = true;
                } else {
                    self.is_all_branches = false;
                }
            });
        },

        _onClickApplyBranch: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            var allowed_branch_ids = [];
            var current_branch_id = this.allowed_branch_ids[0];
            var allDropdownItem = this.$('.dropdown-item[data-menu]');

            
            allDropdownItem.each(function(index, element) {
                if ($(this).find('.fa-check-square').length) {
                    var branchID = $(this).attr('data-branch-id');
                    allowed_branch_ids.push(parseInt(branchID));
                }
            });
            
            session.setBranches(current_branch_id, allowed_branch_ids);
        },

        _onToggleAllBranchesClick: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            var dropdownItem = $(ev.currentTarget).parent();
            var allDropdownItem = this.$('.dropdown-item[data-menu]');

            if (dropdownItem.find('.fa-square-o').length) {
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                allDropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square')
                $(allDropdownItem).find('.toggle_branch').attr('aria-checked', 'true');
            } else {
                dropdownItem.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                allDropdownItem.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                $(allDropdownItem).find('.toggle_branch').attr('aria-checked', 'false');
            }
        },

        _onToggleBranchClick: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            var dropdownItem = $(ev.currentTarget).parent();
            var branchID = dropdownItem.data('branch-id');
            var allowed_branch_ids = this.allowed_branch_ids;
            var current_branch_id = allowed_branch_ids[0];
            var shouldSetBranch = true;
            if (dropdownItem.find('.fa-square-o').length) {
                allowed_branch_ids.push(branchID);
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                $(ev.currentTarget).attr('aria-checked', 'true');
            } else {
                if (allowed_branch_ids.length > 1){
                    allowed_branch_ids.splice(allowed_branch_ids.indexOf(branchID), 1);
                    dropdownItem.find('.fa-check-square').addClass('fa-square-o').removeClass('fa-check-square');
                    $(ev.currentTarget).attr('aria-checked', 'false');
                } else {
                    shouldSetBranch = false;
                }
            }
            // if (shouldSetBranch){
            //     session.setBranches(current_branch_id, allowed_branch_ids);
            // }
        },
    });
});