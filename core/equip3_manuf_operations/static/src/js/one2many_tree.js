odoo.define('equip3_manuf_operations.FieldOne2manyTree', function(require){
    "use strict";

    var relational_fields = require('web.relational_fields');
    var registry = require('web.field_registry');
    var ListRenderer = require('web.ListRenderer');

    var ListRendererTree = ListRenderer.extend({
        events: _.extend({}, ListRenderer.prototype.events, {
            'click .o_tree_collapse': '_onClickCollapse'
        }),

        custom_events: _.extend({}, ListRenderer.prototype.custom_events, {
            toggle_tree: '_onToggleTree'
        }),

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.rowExpand = {};
        },

        _getNumberOfCols: function () {
            var n = this._super.apply(this, arguments);
            var maxLevel = Math.max.apply(Math, _.map(this.state.data, record => record.data ? record.data.level : 1));
            if (isFinite(maxLevel)){
                n += maxLevel + 1;
            }
            return n;
        },

        _renderHeader: function () {
            var $thead = this._super.apply(this, arguments);
            var $tr = $thead.find('tr');
            var maxLevel = Math.max.apply(Math, _.map(this.state.data, record => record.data ? record.data.level : 1));
            if (maxLevel > 0){
                maxLevel++;
                $tr.prepend('<th class="o_tree_level_head" colspan="'+ maxLevel +'"></th>');
            }
            return $thead;
        },

        _renderBodyCell: function (record, node, colIndex, options) {
            var $td = this._super.apply(this, arguments);
            if (node.attrs.name === 'product_id' && this.maxLevel > 0){
                let colspan = this.maxLevel + 1 - record.data.level;
                $td.attr('colspan', colspan);
            }
            return $td;
        },

        _renderRow: function (record) {
            var $tr = this._super.apply(this, arguments);
            if (record.data){
                let klass;
                if (record.data.parent_id === 0){
                    klass = 'o_line_parent';
                } else {
                    klass = 'o_line_child';
                    $tr.find('td.o_list_record_remove').find('button[name="delete"]').remove();
                }
                $tr.addClass(klass);
                $tr.attr('data-line-id', record.data.line_id);
                $tr.attr('data-parent-id', record.data.parent_id);
                $tr.attr('data-expand', this.rowExpand[record.id] === undefined ? record.data.parent_id === 0 : this.rowExpand[record.id]);
                if (!record.data.bom_id && record.data.parent_id !== 0){
                    $tr.addClass('d-none o_no_bom');
                }
            }

            if (this.maxLevel > 0){
                for (let level=record.data.level + 1; level > 0; level--){
                    $tr.prepend('<td class="o_tree_level" data-level="'+ (level - 1) +'"></td>');
                }
            }
            return $tr;
        },

        _renderRows: function(){
            var self = this;

            var records = this.state.data;
            this.maxLevel = Math.max.apply(Math, _.map(records, record => record.data ? record.data.level : 1));
            var $rows = this._super.apply(this, arguments);

            function hideRows($tr){
                if ($tr.data('expand') === false){
                    let $trChildren = _.filter($rows, $o => $o.data('parent-id') === $tr.data('line-id') && !$o.is($tr));
                    _.each($trChildren, function($trChild){
                        $trChild.addClass('d-none');
                        hideRows($trChild);
                    });
                }
            }

            _.each($rows, function($row){
                hideRows($row);
            });

            let n = records.length;

            for (let i=0; i < n; i++){
                let $row = $rows[i];
                let parent = records[i];
                let $parentTd = $row.find('td.o_tree_level[data-level="'+ parent.data.level +'"]');
                let childIds = _.map(_.filter(records, o => o.data.parent_id === parent.data.line_id && !!o.data.bom_id), o => o.data.line_id);

                if (childIds.length){
                    if ($row.data('expand')){
                        $parentTd.append('<span class="o_tree_line o_line_bottom o_with_icon"></span>');
                    } else {
                        $parentTd.append('<span class="o_tree_line o_line_bottom o_with_icon d-none"></span>');
                    }

                    for (let j=i+1; j < n; j++){
                        let child = records[j];
                        let $childTd = $rows[j].find('td.o_tree_level[data-level="'+ parent.data.level +'"]');
                        $childTd.append('<span class="o_tree_line o_line_top"></span>');

                        if (childIds.includes(child.data.line_id)){
                            $childTd.append('<span class="o_tree_line o_line_right"></span>');
                        }
                        if (child.data.line_id === childIds[childIds.length - 1]){
                            break;
                        }

                        $childTd.append('<span class="o_tree_line o_line_bottom"></span>');
                    }
                }

                if (parent.data.parent_id > 0){
                    $parentTd.append('<span class="o_tree_line o_line_left o_with_icon"></span>');
                }

                if ($row.data('expand')){
                    $parentTd.append('<span class="o_tree_collapse fa fa-minus-square-o"></span>');
                } else {
                    $parentTd.append('<span class="o_tree_collapse fa fa-plus-square-o"></span>');
                }
            }

            return $rows;
        },

        _renderFooter: function () {
            var $tfoot = this._super.apply(this, arguments);
            var maxLevel = Math.max.apply(Math, _.map(this.state.data, record => record.data ? record.data.level : 1));
            if (isFinite(maxLevel) && maxLevel > 0){
                for (let i=0; i < maxLevel + 1; i++){
                    $tfoot.find('tr').append($('<td>'));
                };
            }
            return $tfoot;
        },

        _onRemoveIconClick: function (event) {
            var $tr = $(event.target).closest('tr');
            var rowIndex = $tr.prop('rowIndex') - 1;
            var recordID = this._getRecordID(rowIndex);
            var record = this._getRecord(recordID);

            delete this.rowExpand[record.id];
            this._super.apply(this, arguments);
        },

        _onToggleTree: function(ev){
            this._collapseTree($(ev.data.target), ev.data.collapse)
        },

        _onClickCollapse: function(ev){
            var $tr = $(ev.currentTarget).parent().parent();
            this.trigger('toggle_tree', {data: {target: $tr[0]}});
        },

        _triggerToggle: function(lineID, collapse){
            var $tr = this.$el.find('tr[data-line-id="'+ lineID +'"]');
            this.trigger('toggle_tree', {data: {target: $tr[0], collapse: collapse}});
        },

        _collapseTree: function($tr, collapse){
            var self = this;
            var $toggler = $tr.find('.o_tree_collapse');

            var rowIndex = $tr.prop('rowIndex') - 1;
            var recordID = this._getRecordID(rowIndex);
            var record = this._getRecord(recordID);
            var $td = $tr.find('td.o_tree_level[data-level="'+ record.data.level +'"]');

            if (!record.data.product_id){
                return;
            }

            var $trChild = this.$el.find('tr[data-parent-id="'+ record.data.line_id +'"]:not(.o_no_bom)');

            if (collapse === undefined){
                $trChild.toggleClass('d-none');
                $toggler.toggleClass('fa-minus-square-o');
                $toggler.toggleClass('fa-plus-square-o');
                $td.find('.o_line_bottom').toggleClass('d-none');
            } else {
                if (collapse){
                    $trChild.addClass('d-none');
                    $toggler.removeClass('fa-minus-square-o');
                    $toggler.addClass('fa-plus-square-o');
                    $td.find('.o_line_bottom').addClass('d-none');
                } else {
                    $trChild.removeClass('d-none');
                    $toggler.addClass('fa-minus-square-o');
                    $toggler.removeClass('fa-plus-square-o');
                    $td.find('.o_line_bottom').removeClass('d-none');
                }
            }

            let expand = $toggler.hasClass('fa-minus-square-o');
            $tr.attr('data-expand', expand);
            this.rowExpand[record.id] = expand;

            _.each($trChild, function(tr){
                self._collapseTree($(tr), collapse=!expand);
            });
        }
    });

    var FieldOne2ManyTree = relational_fields.FieldOne2Many.extend({
        className: 'o_field_one2many o_field_one2many_tree',

        _getRenderer: function () {
            return ListRendererTree;
        },

        // _onFieldChanged: function (ev) {
        //     var changes = ev.data.changes;
        //     if ('produce' in changes){
        //         var record = this.renderer._getRecord(ev.data.dataPointID);
        //         ev.data.onSuccess = this.renderer._triggerToggle.bind(this.renderer, record.data.line_id, false);
        //     }
        //     this._super(ev);
        // }
    });

    registry.add('one2many_tree', FieldOne2ManyTree);

    return {
        FieldOne2ManyTree: FieldOne2ManyTree
    };
});