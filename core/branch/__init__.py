# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

""" TODO
Make this module standalone and let the operations and rules changes come from the equip modules.
Removing this module's dependencies on an existing database causes a lot of errors. 
So temporarily left as is. """

from . import models
from . import reports
from . import wizard
from . import controllers
from .hooks import post_init_hook

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
