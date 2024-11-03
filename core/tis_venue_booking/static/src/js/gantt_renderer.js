odoo.define('tis_venue_booking.GanttRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var core = require('web.core');
var field_utils = require('web.field_utils');
var time = require('web.time');

var _lt = core._lt;

return AbstractRenderer.extend({
	className: "o_gantt_view",

	/**
	 * @overrie
	 */
	init: function () {
		this._super.apply(this, arguments);

		var self = this;

		this.chart_id = _.uniqueId();
		this.gantt_events = [];

		// The type of the view:
		// gantt = classic gantt view (default)
		// consolidate = values of the first children are consolidated in the gantt's task
		// planning = children are displayed in the gantt's task
		this.type = this.arch.attrs.type || 'gantt';

		_.each(['fold_last_level', 'round_dnd_dates', 'create', 'delete', 'edit',
			'drag_resize', 'duration_unit', 'action', 'relative_field', 'string'], function (key) {
			self[key] = self.arch.attrs[key];
		});

		this.consolidation_max = [];
		if (this.arch.attrs.consolidation_max) {
			this.consolidation_max = JSON.parse(this.arch.attrs.consolidation_max);
		}
	},
	/**
	 * @override
	 */
	destroy: function () {
		while (this.gantt_events.length) {
			gantt.detachEvent(this.gantt_events.pop());
		}
		this._super();
	},

	//--------------------------------------------------------------------------
	// Private
	//--------------------------------------------------------------------------

	/**
	 * configure templates for dhtmlXGantt
	 * @private
	 */
	_configGantt: function () {
		var self = this;

		gantt.config.autosize = "y";
		gantt.config.round_dnd_dates = false;
		gantt.config.drag_links = false;
		gantt.config.drag_progress = false;
		gantt.config.drag_resize = true;
		gantt.config.grid_width = 250;
		gantt.config.row_height = 30;
		gantt.config.duration_unit = "minute";
		gantt.config.initial_scroll = false;
		gantt.config.preserve_scroll = true;
		gantt.config.columns = [{
			name: "text",
			label: _lt("Gantt View"),
			tree: true,
			width: '*'
		}];
		gantt.templates.grid_folder = function () {
			return "";
		};
		gantt.templates.grid_file = function () {
			return "";
		};
		gantt.templates.grid_indent = function () {
			return "<div class='gantt_tree_indent' style='width:20px;'></div>";
		};
		gantt.config.start_on_monday = moment().startOf("week").day();
		gantt.config.start_date = this.state.start_date;
		gantt.config.end_date = this.state.end_date;

		// dnd by date
		gantt.config.round_dnd_dates = !!this.round_dnd_dates;

		// Set resizing of tasks
		if (this.drag_resize === '0' || this.drag_resize === 'false' || this.edit === 'false') {
			gantt.config.drag_resize = false;
		}

		// Set drag_move of tasks
		gantt.config.drag_move = this.edit ? JSON.parse(this.edit) : true;

		// Configure the duration_unit
		if (this.duration_unit) {
			gantt.config.duration_unit = this.duration_unit;
		}

		// the class of the task bar
		gantt.templates.task_class = function (start, end, task) {
			var classes = ["o_gantt_color" + task.color + "_0"];
			if (self.type === "consolidate" || self.type === "planning") {
				classes.push('consolidation');
				if (task.is_group) {
					classes.push("has_child");
				} else {
					classes.push("is_leaf");
				}
			}
			return classes.join(" ");
		};

		// the class for the rows
		gantt.templates.task_row_class = function (start, end, task) {
			var classes = ["level_" + task.$level];
			return classes;
		};

		// The class for the cells
		gantt.templates.task_cell_class = function (item, date) {
			var classes = "date_" + date.getTime();
			var today = new Date();
			if (self.state.scale !== "year" && (date.getDay() === 0 || date.getDay() === 6)) {
				classes += " weekend_task";
			}
			if (self.state.scale !== "day" && date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getYear() === today.getYear()) {
				classes += " today";
			}
			return classes;
		};

		gantt.templates.date_scale = null;

		// Task text format
		var mapping = this.state.mapping;
		gantt.templates.task_text = function (start, end, task) {
			// default
			var text = "";
			// consolidation
			if (self.type === "consolidate" || self.type === "planning") {
				if (task.is_group) {
					text = self._consolidationChildren(task);
				} else if (self.state.fields[mapping.consolidation]) {
					var field = self.state.fields[mapping.consolidation];
					var consolidation = field_utils.format[field.type](task.consolidation, field);
					text = consolidation + "<span class=\"half_opacity\"> " + self.state.fields[mapping.consolidation].string + "</span>";
				}
			}
			return text;
		};
	},
	/**
	 * @private
	 * @param {any} tasks
	 * @param {any} grouped_by
	 * @param {any} groups
	 */
	_configureGanttChart: function (tasks, grouped_by, groups) {
		var self = this;
		this.gantt_events.push(gantt.attachEvent("onTaskClick", function (id, e) {
			// If we are in planning, we want a single click to open the task. If there is more than one task in the clicked range, the bar is unfold
			if (self.type === 'planning' && e.target.className.indexOf('inside_task_bar') > -1) {
				var ids = e.target.attributes.consolidation_ids.value;
				if (ids.indexOf(" ") > -1){
					// There is more than one task
					return true;
				} else {
					// There is only one task
					return self.trigger_up('task_display', gantt.getTask(ids));
				}
			}

			// If we are not in a planning, the bar is unfolded if children
			if(gantt.getTask(id).is_group) return true;

			// Case where the user want to make an action on a task click
			if(e.target.className == "gantt_task_content" || e.target.className == "gantt_task_drag task_left" || e.target.className == "gantt_task_drag task_right") {
				if(this.action) {
					var actual_id = parseInt(id.split("gantt_task_").slice(1)[0]);
					if(this.relative_field) {
						new Model("ir.model.data").call("xmlid_lookup", [this.action]).done(function (result) {
							var add_context = {};
							add_context["search_default_" + this.relative_field] = actual_id;
							self.do_action(result[2], {'additional_context': add_context});
						});
					}
					return false;
				}
			}

			// If the user click on an empty row, it start a crate widget
			if (id.indexOf("unused") >= 0) {
				var task = gantt.getTask(id);
				var key = "default_"+task.create[0];
				var context = {};
				context[key] = task.create[1][0];
				self.trigger_up('task_create', context);
			} else {
				self.trigger_up('task_display', gantt.getTask(id));
			}
			return true;
		}));
		// Remove double click
		this.gantt_events.push(gantt.attachEvent("onTaskDblClick", function (){ return false; }));
		// Fold and unfold project bar when click on it
		this.gantt_events.push(gantt.attachEvent("onBeforeTaskSelected", function (id) {
			if(gantt.getTask(id).is_group){
				$("[task_id="+id+"] .gantt_tree_icon").click();
				return false;
			}
			return true;
		}));

		// Drag and drop
		var update_date_parent = function (id) {
			// Refresh parent when children are resize
			var start_date, stop_date;
			var clicked_task = gantt.getTask(id);
			if (!clicked_task.parent) {
				return;
			}

			var parent = gantt.getTask(clicked_task.parent);

			_.each(gantt.getChildren(parent.id), function (task_id){
				var task_start_date = gantt.getTask(task_id).start_date;
				var task_stop_date = gantt.getTask(task_id).end_date;
				if(!start_date) start_date = task_start_date;
				if(!stop_date) stop_date = task_stop_date;
				if(start_date > task_start_date) start_date = task_start_date;
				if(stop_date < task_stop_date) stop_date = task_stop_date;
			});
			parent.start_date = start_date;
			parent.end_date = stop_date;
			gantt.updateTask(parent.id);
			if (parent.parent) update_date_parent(parent.id);
		};
		/**
		 * Triggered at the start of a task drag. We use this hook to store directly on the
		 * tasks their current date start/end so that we can restore their state if the drag
		 * is not successful.
		 */
		this.gantt_events.push(gantt.attachEvent("onBeforeTaskDrag", function (id, mode, e){
			var task = gantt.getTask(id);
			task._original_start_date = task.start_date;
			task._original_end_date = task.end_date;
			this.lastX = e.pageX;
			if (task.is_group) {
				var attr = e.target.attributes.getNamedItem("consolidation_ids");
				if (attr) {
					var children = attr.value.split(" ");
					this.drag_child = children;
					_.each(this.drag_child, function (child_id) {
						var child = gantt.getTask(child_id);
						child._original_start_date = child.start_date;
						child._original_end_date = child.end_date;
					});
				}
			}
			return true;
		}));
		this.gantt_events.push(gantt.attachEvent("onTaskDrag", function (id, mode, task, original, e){
			if(gantt.getTask(id).is_group){
				// var d is the number of millisecond for one pixel
				var d;
				if (self.state.scale === "day") d = 72000;
				if (self.state.scale === "week") d = 1728000;
				if (self.state.scale === "month") d = 3456000;
				if (self.state.scale === "year") d = 51840000;
				var diff = (e.pageX - this.lastX) * d;
				this.lastX = e.pageX;

				if (task.start_date > original.start_date){ task.start_date = original.start_date; }
				if (task.end_date < original.end_date){ task.end_date = original.end_date; }

				if (this.drag_child){
					_.each(this.drag_child, function (child_id){
						var child = gantt.getTask(child_id);
						var nstart = +child.start_date + diff;
						var nstop = +child.end_date + diff;
						if (nstart < gantt.config.start_date || nstop > gantt.config.end_date){
							return false;
						}
						child.start_date = new Date(nstart);
						child.end_date = new Date(nstop);
						gantt.updateTask(child.id);
						update_date_parent(child_id);
					});
				}
				gantt.updateTask(task.id);
				return false;
			}
			update_date_parent(id);
			return true;
		}));

		/**
		 * This will trigger_up `task_changed`, which will write. This write can fail
		 * if, for example, constraints defined on the model are not met. In this case, we have to
		 * replace the task at its original place.
		 */
		this.gantt_events.push(gantt.attachEvent("onAfterTaskDrag", function (id){
			var update_task = function (task_id) {
				var task = gantt.getTask(task_id);
				self.trigger_up('task_changed', {
					task: task,
					success: function () {
						update_date_parent(task_id);
					},
					fail: function () {
						task.start_date = task._original_start_date;
						task.end_date = task._original_end_date;
						gantt.updateTask(task_id);
						delete task._original_start_date;
						delete task._original_end_date;
						update_date_parent(task_id);
					}});
			};

			// A group of tasks has been dragged
			if (gantt.getTask(id).is_group && this.drag_child) {
				_.each(this.drag_child, function (child_id) {
					update_task(child_id);
				});
			}

			// A task has been dragged
			update_task(id);
		}));

		this.gantt_events.push(gantt.attachEvent("onGanttRender", function () {
			// show the focus date
			if(!self.open_task_id || self.type == 'planning'){
				gantt.showDate(self.state.focus_date);
			} else {
				if (gantt.isTaskExists("gantt_task_"+self.open_task_id)) {
					gantt.showTask("gantt_task_"+self.open_task_id);
					gantt.selectTask("gantt_task_" + self.open_task_id);
				}
			}

			self.open_task_id = undefined;

			return true;
		}));
	},
	/**
	 * @private
	 * @param {any} parent
	 * @returns {string}
	 */
	_consolidationChildren: function (parent) {
		var self = this;
		var grouped_by = this.state.to_grouped_by;
		var children = self._getAllChildren(parent.id);
		var consolidation_max = this.consolidation_max[grouped_by[0]] || false;
		var mapping = this.state.mapping;

		// First step : create a list of object for the children. The contains (left, consolidation
		// value, consolidation color) where left is position in the bar, and consolidation value is
		// the number to add or remove, and the color is [color, sequence] from the last group_by
		// with these information.
		var leftParent = gantt.getTaskPosition(parent, parent.start_date, parent.end_date).left;
		var getTuple = function (acc, task_id) {
			var task = gantt.getTask(task_id);
			var position = gantt.getTaskPosition(task, task.start_date, task.end_date || task.start_date);
			var left = position.left - leftParent;
			var right = left + position.width;
			var start = {type: "start",
						 task: task,
						 left: left,
						 consolidation: task.consolidation,
						};
			var stop = {type: "stop",
						task: task,
						left: right,
						consolidation: -(task.consolidation),
					   };
			if (task.consolidation_exclude) {
				start.consolidation_exclude = true;
				start.color = task.consolidation_color;
				stop.consolidation_exclude = true;
				stop.color = task.consolidation_color;
			}
			acc.push(start);
			acc.push(stop);
			return acc;
		};
		var steps = _.reduce(children, getTuple, []);

		// Second step : Order it by "left"
		var orderSteps = _.sortBy(steps, function (el) {
			return el.left;
		});

		// Third step : Create the html for the bar
		// html : the final html code
		var html = "";
		// acc : the amount to display inside the task
		var acc = 0;
		// last_left : the left position of the previous task
		var last_left = 0;
		// exclude : A list of task that are not compatible with the other ones (must be hached)
		var exclude = [];
		// not_exclude : the number of task, that are compatible
		var not_exclude = 0;
		// The ids of the task (exclude and not_exclude)
		var ids = [];
		orderSteps.forEach(function (el) {
			var width = Math.max(el.left - last_left , 0);
			var padding_left = (width === 0) ? 0 : 4;
			if (not_exclude > 0 || exclude.length > 0) {
				var classes = [];
				//content
				var content;
				if (self.type === 'consolidate') {
					var field = self.state.fields[mapping.consolidation];
					var label = self.string || field.string;
					var acc_format = field_utils.format[field.type](acc, field);
					content = acc_format + "<span class=\"half_opacity\"> " + label + "</span>";
					if (acc === 0 || width < 15 || (consolidation_max && acc === consolidation_max)) content = "";
				} else {
					if (exclude.length + not_exclude > 1) {
						content = exclude.length + not_exclude;
					} else {
						content = el.task.text;
					}
				}
				//pointer
				var pointer = (exclude.length === 0 && not_exclude === 0) ? "none" : "all";
				// Color 
				if (exclude.length > 0) {
					classes.push("o_gantt_color" + _.last(exclude) + "_0");
					if (not_exclude) {
						classes.push("exclude");
					}
				} else {
					var opacity = (consolidation_max) ? 5 - Math.floor(10*((acc/(2*consolidation_max)))) : 1;
					if (acc === 0){
						classes.push("transparent");
					} else if ((consolidation_max) && acc > consolidation_max){
						classes.push("o_gantt_color_red");
					} else if (consolidation_max && parent.create[0] === grouped_by[0]) {
						classes.push("o_gantt_colorgreen_" + opacity);
					} else if (parent.consolidation_color){
						classes.push("o_gantt_color" + parent.consolidation_color + "_" + opacity);
					} else {
						classes.push("o_gantt_color7_" + opacity);
					}
				}
				html += "<div class=\"inside_task_bar "+ classes.join(" ") +"\" consolidation_ids=\"" + 
					ids.join(" ") + "\" style=\"pointer-events: "+pointer+"; padding-left: "+ padding_left + 
					"px; left:"+(last_left )+"px; width:"+width+"px;\">"+content+"</div>";
			}
			// since the forwardport of 9fe5006bb, 2240e7d50 is probably not
			// necessary anymore, so it could be removed in master
			acc = Math.round((acc + el.consolidation) * 100) / 100;
			last_left = el.left;
			if(el.type === "start"){
				if (el.consolidation_exclude ) exclude.push(el.task.color);
				else not_exclude++;
				ids.push(el.task.id);
			} else {
				if(el.consolidation_exclude) exclude.pop();
				else not_exclude--;
				ids = _.without(ids, el.task.id);
			}
		});
		return html;
	},
	/**
	 * @private
	 * @param {any} ganttTasks
	 */
	_ganttContainer: function (ganttTasks) {
		// horrible hack to make sure that something is in the dom with the required id.  The problem is that
		// the action manager renders the view in a document fragment. More explaination : GED
		var temp_div_with_id;
		if (this.$div_with_id){
			temp_div_with_id = this.$div_with_id;
		}
		this.$div_with_id = $('<div>').attr('id', this.chart_id);
		this.$div_with_id.wrap('<div></div>');
		this.$div = this.$div_with_id.parent();
		this.$div.prependTo(document.body);

		// Initialize the gantt chart
		while (this.gantt_events.length) {
			gantt.detachEvent(this.gantt_events.pop());
		}
		this._scaleZoom(this.state.scale,this.state);
		gantt.init(this.chart_id);
		gantt._click.gantt_row = undefined; // Remove the focus on click

		gantt.clearAll();
		gantt.showDate(this.state.focus_date);
		gantt.parse({"data": ganttTasks});
		gantt.sort(function (a, b){
			if (gantt.hasChild(a.id) && !gantt.hasChild(b.id)){
				return -1;
			} else if (!gantt.hasChild(a.id) && gantt.hasChild(b.id)) {
				return 1;
			} else if (a.index > b.index) {
				return 1;
			} else if (a.index < b.index) {
				return -1;
			} else {
				return 0;
			}
		});

		// End of horrible hack
		var scroll_state = gantt.getScrollState();
		this.$el.empty();
		this.$el.append(this.$div.contents());
		gantt.scrollTo(scroll_state.x, scroll_state.y);
		this.$div.remove();
		if (temp_div_with_id) temp_div_with_id.remove();
	},
	/**
	 * @private
	 * @param {any} id
	 * @returns {any}
	 */
	_getAllChildren: function (id) {
		var children = [];
		gantt.eachTask(function (task) {
			if (!task.is_group) {
				children.push(task.id);
			}
		}, id);
		return children;
	},
	/**
	 * @private
	 * @returns {Deferred}
	 */
	_render: function () {
		this._configGantt();
		this._renderGantt();
		return $.when();
	},
	/**
	 * Prepare the tasks and group by's to be handled by dhtmlxgantt and render
	 * the view. This function also contains workaround to the fact that
	 * the gantt view cannot be rendered in a documentFragment.
	 *
	 * @private
	 */
	_renderGantt: function () {
		var self = this;

		var mapping = this.state.mapping;
		var grouped_by = this.state.to_grouped_by;

		// Prepare the tasks
		var tasks = _.compact(_.map(this.state.data, function (task) {
			task = _.clone(task);

			var task_start = time.auto_str_to_date(task[mapping.date_start]);
			if (!task_start) {
				return false;
			}

			var task_stop;
			var percent;
			if (task[mapping.date_stop]) {
				task_stop = time.auto_str_to_date(task[mapping.date_stop]);
				// If the date_stop is a date, we assume that the whole day should be included.
				if (self.state.fields[mapping.date_stop].type === 'date') {
					task_stop.setTime(task_stop.getTime() + 86400000);
				}
				if (!task_stop) {
					task_stop = moment(task_start).clone().add(1, 'hours').toDate();
				}
			} else {
				// FIXME this code branch is not tested
				if (!mapping.date_delay) {
					return false;
				}
				var field = self.state.fields[mapping.date_delay];
				var tmp = field_utils.format[field.type](task[mapping.date_delay], field);
				if (!tmp) {
					return false;
				}
				var m_task_start = moment(task_start).add(tmp, gantt.config.duration_unit);
				task_stop = m_task_start.toDate();
			}

			if (_.isNumber(task[mapping.progress])) {
				percent = task[mapping.progress] || 0;
			} else {
				percent = 100;
			}

			task.task_start = task_start;
			task.task_stop = task_stop;
			task.percent = percent;

			// Don't add the task that stops before the min_date
			// Usefull if the field date_stop is not defined in the gantt view
			if (self.min_date && task_stop < new Date(self.min_date)) {
				return false;
			}

			return task;
		}));

		// get the groups
		var split_groups = function (tasks, grouped_by) {
			if (grouped_by.length === 0) {
				return tasks;
			}
			var groups = [];
			_.each(tasks, function (task) {
				var group_name = task[_.first(grouped_by)];
				var group = _.find(groups, function (group) {
					return _.isEqual(group.name, group_name);
				});
				if (group === undefined) {
					// Create the group of the other levels
					group = {name:group_name, tasks: [], __is_group: true,
							 group_start: false, group_stop: false, percent: [],
							 open: true};

					// Add the group_by information for creation
					group.create = [_.first(grouped_by), task[_.first(grouped_by)]];

					// folded or not
					if ((self.fold_last_level && grouped_by.length <= 1) ||
						self.state.context.fold_all ||
						self.type === 'planning') {
						group.open = false;
					}

					// the group color
					// var model = self.state.fields[_.first(grouped_by)].relation;
					// if (model && _.has(color_by_group, model)) {
					//     group.consolidation_color = color_by_group[model][group_name[0]];
					// }

					groups.push(group);
				}
				if (!group.group_start || group.group_start > task.task_start) {
					group.group_start = task.task_start;
				}
				if (!group.group_stop || group.group_stop < task.task_stop) {
					group.group_stop = task.task_stop;
				}
				group.percent.push(task.percent);
				if (self.open_task_id === task.id && self.type !== 'planning') {
					group.open = true; // Show the just created task
				}
				group.tasks.push(task);
			});
			_.each(groups, function (group) {
				group.tasks = split_groups(group.tasks, _.rest(grouped_by));
			});
			return groups;
		};
		var groups = split_groups(tasks, grouped_by);

		// If there is no task, add a dummy one
		if (groups.length === 0) {
			groups = [{
				'id': 0,
				'display_name': '',
				'task_start': this.state.focus_date.toDate(),
				'task_stop': this.state.focus_date.toDate(),
				'percent': 0,
			}];
		}

		// Creation of the chart
		var gantt_tasks = [];
		var generate_tasks = function (task, level, parent_id) {
			if ((task.__is_group && !task.group_start) || (!task.__is_group && !task.task_start)) {
				return;
			}
			if (task.__is_group) {
				// Only add empty group for the first level
				if (level > 0 && task.tasks.length === 0){
					return;
				}

				var project_id = _.uniqueId("gantt_project_");
				var field = self.state.fields[grouped_by[level]];
				var group_name = task[mapping.name] ? field_utils.format[field.type](task[mapping.name], field) : "-";
				// progress
				var sum = _.reduce(task.percent, function (acc, num) { return acc+num; }, 0);
				var progress = sum / task.percent.length / 100 || 0;
				var t = {
					'id': project_id,
					'text': group_name,
					'is_group': true,
					'start_date': task.group_start,
					'duration': gantt.calculateDuration(task.group_start, task.group_stop),
					'progress': progress,
					'create': task.create,
					'open': task.open,
					'consolidation_color': task.color || 0,
					'index': gantt_tasks.length,
				};
				if (parent_id) { t.parent = parent_id; }
				gantt_tasks.push(t);
				_.each(task.tasks, function (subtask) {
					generate_tasks(subtask, level+1, project_id);
				});
			}
			else {
				var duration = (task.task_stop - task.task_start) / 60000;
				// Consolidation
				gantt_tasks.push({
					'id': "gantt_task_" + task.id,
					'text': task.display_name || '',
					'active': task.active || true,
					'start_date': task.task_start,
					'duration': duration,
					'progress': task.percent / 100,
					'parent': parent_id || 0,
					'consolidation': task[mapping.consolidation] || null,
					'consolidation_exclude': self.consolidation_exclude || null,
					'color': task.color || 0,
					'index': gantt_tasks.length,
				});
			}
		};
		_.each(groups, function (group) { generate_tasks(group, 0); });

		this._ganttContainer(gantt_tasks);
		this._configureGanttChart(tasks, grouped_by, gantt_tasks);
	},
	/**
	 * @private
	 * @param {string} value either 'day', 'week', 'month' or 'year
	 */
	_scaleZoom: function (value,state) {
		gantt.config.step = 1;
		gantt.config.min_column_width = 50;
		gantt.config.scale_height = 50;
		var today = new Date();

		function css(date) {
			if(date.getDay() === 0 || date.getDay() === 6) return "weekend_scale";
			if(date.getMonth() === today.getMonth() && date.getDate() === today.getDate()) return "today";
		}
		switch (value) {

			case "day":
				if(state.btn_id == 'half_day')
				{
					gantt.templates.scale_cell_class = css;
					gantt.config.scale_unit = "day";
					gantt.config.date_scale = "%d %M";
					gantt.config.subscales = [{unit:"hour", step:12, date:"%H h"}];
					gantt.config.scale_height = 27;
					break;
				}
				else if(state.btn_id == 'qtr_day')
				{
					gantt.templates.scale_cell_class = css;
					gantt.config.scale_unit = "day";
					gantt.config.date_scale = "%d %M";
					gantt.config.subscales = [{unit:"hour", step:6, date:"%H h"}];
					gantt.config.scale_height = 27;
					break;
				}
				else{
					gantt.templates.scale_cell_class = css;
					gantt.config.scale_unit = "day";
					gantt.config.date_scale = "%d %M";
					gantt.config.subscales = [{unit:"hour", step:1, date:"%H h"}];
					gantt.config.scale_height = 27;
					break;
				}
			   
			case "week":
				var weekScaleTemplate = function (date){
					var dateToStr = gantt.date.date_to_str("%d %M %Y");
					var endDate = gantt.date.add(gantt.date.add(date, 1, "week"), -1, "day");
					return dateToStr(date) + " - " + dateToStr(endDate);
				};
				gantt.config.scale_unit = "week";
				gantt.templates.date_scale = weekScaleTemplate;
				gantt.config.subscales = [{unit:"day", step:1, date:"%d, %D", css:css}];
				break;
			case "month":
				gantt.config.scale_unit = "month";
				gantt.config.date_scale = "%F, %Y";
				gantt.config.subscales = [{unit:"day", step:1, date:"%d", css:css}];
				gantt.config.min_column_width = 25;
				break;
			case "year":
				gantt.config.scale_unit = "year";
				gantt.config.date_scale = "%Y";
				gantt.config.subscales = [{unit:"month", step:1, date:"%M"}];
				break;
		}
	},
});

});
