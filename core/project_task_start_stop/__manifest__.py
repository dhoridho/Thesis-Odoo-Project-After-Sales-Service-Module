# -*- coding: utf-8 -*-
{
    'name': 'Project Task Start/Stop and Update Timesheet',
    'summary': "Project Task Start/Stop and Update Timesheet",
    'description': "Project Task Start/Stop and Update Timesheet",

    'author': 'iPredict IT Solutions Pvt. Ltd.',
    'website': 'http://ipredictitsolutions.com',
    'support': 'ipredictitsolutions@gmail.com',

    'category': 'Project',
    'version': '1.1.1',
    'depends': ['project', 'hr_timesheet'],

    'data': [
        'security/ir.model.access.csv',
        'security/task_start_stop_security.xml',
        'wizard/task_description.xml',
        'views/res_config_setting.xml',
        'views/project_task.xml',
    ],

    'license': "OPL-1",
    'price': 15,
    'currency': "EUR",

    'auto_install': False,
    'installable': True,

    'images': ['static/description/banner.png'],
    'pre_init_hook': 'pre_init_check',
}
