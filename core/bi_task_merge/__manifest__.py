# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Merge Project Tasks',
    'version': '14.0.0.0',
    'summary': 'This modules helps to merge tasks and it will merge timesheet of tasks too merge task with its timesheet merger project task merger task management merge subtask merge project subtask merger',
    'description': """
        project tasks merge
        task merger
        merge tasks project 
        project merge tasks
        task tracking, task management, project task , task allocation , task        
        -Add Subtasks on Project Task, Add Subtasks on task. Custom task, Custom project, Customized task. Divide task. Custom Project management. Sub-task for task. Parent child task.Subtask Management on Project.Delegation on Task, Issue ticket, Task tickit, Add task, improve task management, divide task, task break system, 
        task merge
    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    'depends': ['base','project','hr_timesheet'],
    'data': [
            'security/ir.model.access.csv',
            'view/task.xml'
             ],
	'qweb': [
		],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    "live_test_url":'https://youtu.be/S_Vx3JOsgBs',
    "images":['static/description/Banner.png'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
