odoo.define('equip3_construction_accessright_setting.construction_security', function (require) {
    'use strict';

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        // to add invisible to base.module_category_services_project
        _renderInnerGroup: function (node) {
            if (this.state.model === "res.users") {
                var self = this;
                var $result = $('<table/>', {class: 'o_group o_inner_group'});
                var $tbody = $('<tbody />').appendTo($result);
                this._handleAttributes($result, node);
                this._registerModifiers(node, this.state, $result);

                var col = parseInt(node.attrs.col, 10) || this.INNER_GROUP_COL;

                if (node.attrs.string) {
                    var $sep = $('<tr><td colspan="' + col + '" style="width: 100%;"><div class="o_horizontal_separator">' + node.attrs.string + '</div></td></tr>');
                    if ($sep[0].innerHTML.includes("Services")) {
                        $result = $("<table style='display:None;'/>", {class: 'o_group o_inner_group'});
                        $tbody = $('<tbody />').appendTo($result);
                        this._handleAttributes($result, node);
                        this._registerModifiers(node, this.state, $result);
                    }else{
                        $result.append($sep);
                    }
                }

                var rows = [];
                var $currentRow = $('<tr/>');
                var currentColspan = 0;
                node.children.forEach(function (child) {
                    if (child.tag === 'newline') {
                        rows.push($currentRow);
                        $currentRow = $('<tr/>');
                        currentColspan = 0;
                        return;
                    }

                    var colspan = parseInt(child.attrs.colspan, 10);
                    var isLabeledField = (child.tag === 'field' && child.attrs.nolabel !== '1');
                    if (!colspan) {
                        if (isLabeledField) {
                            colspan = 2;
                        } else {
                            colspan = 1;
                        }
                    }
                    var finalColspan = colspan - (isLabeledField ? 1 : 0);
                    currentColspan += colspan;

                    if (currentColspan > col) {
                        rows.push($currentRow);
                        $currentRow = $('<tr/>');
                        currentColspan = colspan;
                    }

                    var $tds;
                    if (child.tag === 'field') {
                        $tds = self._renderInnerGroupField(child);
                    } else if (child.tag === 'label') {
                        $tds = self._renderInnerGroupLabel(child);
                    } else {
                        var $td = $('<td/>');
                        var $child = self._renderNode(child);
                        if ($child.hasClass('o_td_label')) { // transfer classname to outer td for css reasons
                            $td.addClass('o_td_label');
                            $child.removeClass('o_td_label');
                        }
                        $tds = $td.append($child);
                    }
                    if (finalColspan > 1) {
                        $tds.last().attr('colspan', finalColspan);
                    }
                    $currentRow.append($tds);
                });
                // console.log('currentRow', $currentRow)
                rows.push($currentRow);

                _.each(rows, function ($tr) {
                    var nonLabelColSize = 100 / (col - $tr.children('.o_td_label').length);
                    _.each($tr.children(':not(.o_td_label)'), function (el) {
                        var $el = $(el);
                        $el.css('width', ((parseInt($el.attr('colspan'), 10) || 1) * nonLabelColSize) + '%');
                    });
                    $tbody.append($tr);
                });

                return $result;
            }
            else{
                return this._super.apply(this, arguments);
            }
        },

    })

});